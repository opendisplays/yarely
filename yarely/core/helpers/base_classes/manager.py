# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


# Standard library imports
import copy
import datetime
import logging
import re
import shlex
import threading
import time
import uuid
from functools import wraps
from subprocess import Popen, PIPE
from xml.etree import ElementTree

# Third party imports
import zmq

# Local (Yarely) imports
from yarely.core.helpers.zmq import ZMQ_ADDRESS_INPROC
from yarely.core.helpers.zmq import ZMQ_ADDRESS_LOCALHOST
from yarely.core.helpers.zmq import ZMQ_SOCKET_LINGER_MSEC
from yarely.core.helpers.base_classes import ApplicationError
from yarely.core.helpers.base_classes import ApplicationWithConfig
from yarely.core.helpers.base_classes import Struct, ZMQRPC

log = logging.getLogger(__name__)

LOG_REGEXP = '(?:(?P<level>DEBUG|INFO|WARNING|ERROR): )?(?P<msg>.*)'
DEFAULT_LOG_LEVEL = 'WARNING'
SUBPROCESS_ID_STR_TEMPLATE = '{ms:x}:{id:x}'
SUBPROCESS_LOGGER_FORMAT_TEMPLATE = '(spid={id_str}) {msg}'
ZMQ_INTERNAL_TERMINATOR_PORT = 5554
ZMQ_POLL_TIMEOUT = 500                # Milliseconds
SUBPROCESS_CHECKIN_TIMEOUT = 5        # Seconds
SUBPROCESS_KILLTERM_TIMEOUT = 5       # Seconds
SUBPROCESS_REGISTRATION_TIMEOUT = 10   # Seconds
SUBPROCESS_CHECK_INTERVAL = 0.5       # Seconds
SUBPROCESS_FAILED_LIMIT = 5
SUBPROCESS_RESTART_SLEEP = 10         # Seconds
WARN_NO_REPLY = "No reply generated in ZMQ request handler, reply with error."


class ManagerError(ApplicationError):
    """Base class for Yarely Manager errors."""
    pass


class ManagerNotExecutingError(ManagerError):
    """Base class for Yarely Manager thread execution errors."""
    pass


class HandlerStub(Struct):
    """Stub class to represent information about a Handler within the
    Manager.

    For use in the Manager._registered_handlers dictionary.

    """
    def __setattr__(self, name, value):
        if name == 'command_line_args' and isinstance(value, str):
            value = shlex.split(value)
        super().__setattr__(name, value)


def check_handler_token(fn):
    """Decorator to check that the token in a ZMQ message corresponds to
    a known handler. The wrapped message will still get called even if
    no handler is found.

    """
    @wraps(fn)
    def new(obj, msg_root, elem_root):
        """
        :param obj: the object on which to call the wrapped message.
        :type obj: a :class:`Manager` instance.
        :param msg_root: the root element for the ZMQ message.
        :type msg_root: an :class:`xml.etree.ElementTree.Element` instance.
        :param elem_root: the focal element for the ZMQ message (e.g. `ping`).
        :type elem_root: an :class:`xml.etree.ElementTree.Element` instance.

        """

        handler = None
        token = msg_root.attrib['token']
        with obj._lock:
            handler = obj._lookup_executing_handler_with_token(token)
        if not handler:
            call = '{root}->{call}'
            call = call.format(root=msg_root.tag, call=elem_root.tag)
            lmsg = '{call} received for unknown handler: token is {token}'
            log.warning(lmsg.format(call=call, token=token))
        return fn(obj, msg_root, elem_root)
    return new


class Manager(ApplicationWithConfig, ZMQRPC):
    """Base class for Yarely Manager applications."""

    def __init__(self, zmq_req_port, description):
        """
        :param int zmq_req_port: the port number to which Handlers will send
            requests destined for this Manager (i.e. the port on which this
            Manager should open a REP socket).
        :param string description: a text description that will be used
            by :meth:`~Application.process_arguments()` if an alternative is
            not directly supplied to the method.

        """
        self.zmq_req_port = zmq_req_port
        super().__init__(description)

        # ZMQ setup
        self.zmq_context = zmq.Context()
        self.zmq_manager_term_identifier = "manager_term_{id}".format(
            id=id(self)
        )

        # Thread syncronisation
        self._stop_request = threading.Event()
        self._lock = threading.RLock()

        # We maintain an internal dictionary for control of currently
        # executing Handler processes.
        # The dictionary holds a SubprocessExecutionWithErrorCapturing
        # instance and is keyed by the instance ID.
        self._executing_handlers = {}

        # Subclasses determine how the '_registered_handlers'
        # dictionary is keyed by providing the implementation of this
        # _init_handlers() method.
        self._registered_handlers = {}
        self._init_handlers()
        self.reset_lock = threading.Lock()

    def _check_handlers(self):
        """Executes in separate thread: _handler_status_check_thread."""
        while not self._stop_request.wait(SUBPROCESS_CHECK_INTERVAL):
            with self._lock:
                handlers = self._executing_handlers.copy()
                for handler_id, handler in handlers.items():
                    if handler.erroneous_state_requires_stop():
                        self.failed_handler_count += 1
                        log.debug(
                            "Trying to restart handler {handler} - "
                            "attempt number {count}.".format(
                                handler=handler,
                                count=self.failed_handler_count
                            )
                        )

                        # Copy key features from existing handler
                        # We only take the first three args here to crop out
                        # the ZMQ TCP address and security token. This one gets
                        # regenerated by the handler starter method. The first
                        # three parameters consist of the python path and the
                        # path to the handler.
                        command_line_args = handler.command_line_args[:3]
                        handler_params = handler.handler_params

                        # Stop the existing handler
                        self.stop_handler(handler_id)

                        # If this has failed too often, then we will restart
                        # ZMQ context and reinitialise ourselves. We want to
                        # wait a few seconds in case there is a background
                        # thread trying to start a replacement handler.
                        if self.failed_handler_count > SUBPROCESS_FAILED_LIMIT:
                            log.debug(
                                "Handler restart has failed {} times. "
                                "Restarting ZMQ now.".format(
                                    self.failed_handler_count
                                )
                            )
                            threading.Thread(target=self._restart_zmq).start()
                            return  # Stop this endless loop now.

                        # Start a replacement handler
                        #
                        # We don't want to keep endlessly restarting a failed
                        # handler. This is unlikely to happen, but a short
                        # break before calling 'start' will ensure that
                        # repeated failures won't result in a spinning CPU.
                        replacement_handler = HandlerStub(
                            command_line_args=command_line_args,
                            params_over_zmq=handler_params
                        )
                        replacement_handler_kwargs = {
                            "handler_stub": replacement_handler
                        }
                        threading.Timer(
                            interval=2, function=self.start_handler,
                            kwargs=replacement_handler_kwargs
                        ).start()

    def _generate_params(self, handler):
        params_root = ElementTree.Element('params')
        param = ElementTree.Element('param', tag='param', attrib={
            'name': 'token', 'value': handler.security_token
        })
        params_root.append(param)
        for key, value in handler.handler_params.items():
            param = ElementTree.Element(
                'param', attrib={'name': key, 'value': value}
            )
            params_root.append(param)
        return params_root

    def _handle_incoming_zmq(self):
        """Executes in separate thread: _zmq_messaging_thread."""

        # NOTE - We shouldn't need the lock here because access to the
        # zmq socket should ONLY ever happen in one thread (this one!)
        # and logging is already threadsafe - we delegate operations
        # that might need the lock to _handle_zmq_msg().

        # Initialise sockets
        zmq_poller = zmq.Poller()
        zmq_termination_reply_socket = self.zmq_context.socket(zmq.REP)
        zmq_reply_socket = self.zmq_context.socket(zmq.REP)
        zmq_reply_socket.bind(
            ZMQ_ADDRESS_LOCALHOST.format(port=self.zmq_req_port)
        )
        zmq_termination_reply_socket.bind(
            ZMQ_ADDRESS_INPROC.format(
                identifier=self.zmq_manager_term_identifier
            )
        )
        zmq_poller.register(zmq_reply_socket, zmq.POLLIN)
        zmq_poller.register(zmq_termination_reply_socket, zmq.POLLIN)

        # Provide a method to loop over sockets that have data
        def _loop_over_sockets():
            term = False
            for sock in socks_with_data:
                if sock is zmq_termination_reply_socket:
                    term = True
                elif not term:  # If we're not in the process of terminating...
                    msg = sock.recv().decode()
                    reply = self._handle_zmq_msg(msg)
                    if reply is None:
                        log.warning(WARN_NO_REPLY)
                        reply = self._encapsulate_reply(self._generate_error())
                    sock.send(ElementTree.tostring(reply))
            return term

        # Poll for messages
        while True:
            socks_with_data = dict(zmq_poller.poll())
            if socks_with_data:
                term = _loop_over_sockets()
                if term:
                    break

        # Cleanup ZMQ
        zmq_poller.unregister(zmq_reply_socket)
        zmq_poller.unregister(zmq_termination_reply_socket)
        zmq_reply_socket.close()
        zmq_termination_reply_socket.close()

    # NOTE - We don't use the decorator check_handler_token here
    # because this is the one-off registration token. The decorator
    # is used for the lifetime token generated during this call.
    def _handle_register(self, msg_root):
        token = msg_root.attrib['token']
        with self._lock:
            handler = self._lookup_executing_handler_with_token(token)
            if not handler:
                lmsg = 'Spoof handler registration attempt: token is {token}'
                log.warning(lmsg.format(token=token))
            else:
                handler.register()
                reply = self._encapsulate_reply(self._generate_params(handler))
                self.failed_handler_count = max(self.failed_handler_count-1, 0)
                return reply

    @check_handler_token
    def _handle_request_ping(self, msg_root, msg_elem):
        """
        Handles an incoming ping request.

        This implementation updates the recorded time at which the sending
        Handler was recorded to have checked in and then replies to the
        Handler with a pong.

        :param msg_root: The root element for the incoming ping message.
        :type msg_root: an :class:`xml.etree.ElementTree.Element` instance.
        :param msg_elem: The element representing the ping portion of the
            incoming message.
        :type msg_elem: an :class:`xml.etree.ElementTree.Element` instance.

        """
        token = msg_root.attrib['token']
        with self._lock:
            handler = self._lookup_executing_handler_with_token(token)
            if not handler:
                msg = 'Ping received for None handler, token is {token}'
                log.error(msg.format(token=token))
            else:
                handler.last_checkin = time.time()
            reply = self._encapsulate_reply(self._generate_pong())
            return reply

    def _lookup_executing_handler_with_token(self, token):
        with self._lock:
            for handler in self._executing_handlers.values():
                if handler.has_token(token):
                    return handler
        return None

    def _restart_zmq(self):
        """Restart all sockets and handlers.
        First, this method calls the global stop method which will terminate
        all handlers and ZMQ sockets. Second, it will reinitialise the ZMQ
        context in case it was left in the wrong state and eventually call
        the start method which will reinitialise all threads and handlers.

        """
        log.warning("Going to restart ZMQ now... ")
        with self.reset_lock:
            self.stop()

            # Give it some time to terminate...
            time.sleep(SUBPROCESS_RESTART_SLEEP)

            self.failed_handler_count = 0

            # Reinitialise the context and start all handlers again.
            self.zmq_context = zmq.Context()
            self._stop_request.clear()

            self.start()

    def add_handler(self, key, value):
        """Add a handler to the list of registered handlers.

        :param string key: the key against which the supplied handler should
            be indexed.
        :param value: the handler to be added.
        :type value: :class:`~manager.HandlerStub`.

        """
        with self._lock:
            self._registered_handlers[key] = value

    def get_handler_stub(self, key):
        """Get the registered handler stub associated with the given key.

        :param string key: the key to lookup a handler stub for.
        :rtype: :class:`~manager.HandlerStub`

        """
        with self._lock:
            handler_stub = self._registered_handlers[key]
        return handler_stub

    def start(self):
        """Main entry point."""
        # IMPORTANT - Don't call super().start() here, it raises
        # NotImplementedError

        # Initialise the internal failure counter
        self.failed_handler_count = 0

        # Start a new thread to monitor the state of executing subprocesses.
        self._handler_status_check_thread = threading.Thread(
            target=self._check_handlers
        )
        self._handler_status_check_thread.name = 'Handler Status Checker'
        self._handler_status_check_thread.daemon = True
        self._handler_status_check_thread.start()

        # Start a new thread to create and monitor ZMQ sockets.
        self._zmq_messaging_thread = threading.Thread(
            target=self._handle_incoming_zmq
        )
        self._zmq_messaging_thread.name = 'ZMQ Messenger'
        self._zmq_messaging_thread.daemon = True
        self._zmq_messaging_thread.start()

    def start_handler(self, handler_stub):
        """Start a new subprocess (Handler) using the specified command
        line arguments. Once it is started and has registered over ZMQ it
        will be sent the specified params via ZMQ.

        :param handler_stub: the uri string to be matched.
        :type handler_stub: a :class:`~manager.HandlerStub` instance that
            describes the Handler to be started.
        :return: the subprocess ID for the newly started Handler.
        :rtype: int

        """
        handler = copy.deepcopy(handler_stub)
        params_over_zmq = handler.params_over_zmq if hasattr(
            handler, 'params_over_zmq'
        ) else dict()
        command_line_args = handler.command_line_args if hasattr(
            handler, 'command_line_args'
        ) else list()
        command_line_args.append(
            ZMQ_ADDRESS_LOCALHOST.format(port=self.zmq_req_port)
        )
        subproc = SubprocessExecutionWithErrorCapturing(
            command_line_args, params_over_zmq
        )
        with self._lock:
            if (
                self._stop_request.is_set() or
                not self._handler_status_check_thread.is_alive()
            ):
                msg = ('Cannot start handler - handler status checker stopped '
                       'or stopping')
                raise ManagerNotExecutingError(msg)
            subprocess_id = subproc.start()
            self._executing_handlers[subprocess_id] = subproc
        return subprocess_id

    def stop_handler(self, handler_id):
        """Stop the specified subprocess (Handler).

        :param int handler_id: the subprocess ID of the Handler to be stopped.

        """
        with self._lock:
            self._executing_handlers[handler_id].stop()
            self._executing_handlers.pop(handler_id)

    def stop(self):
        """Terminate execution of the Manager and associated Handlers."""
        # Terminate ZMQ-related threads
        zmq_termination_request_socket = self.zmq_context.socket(zmq.REQ)
        zmq_termination_request_socket.setsockopt(
            zmq.LINGER, ZMQ_SOCKET_LINGER_MSEC
        )
        zmq_termination_request_socket.connect(
            ZMQ_ADDRESS_INPROC.format(
                identifier=self.zmq_manager_term_identifier
            )
        )
        zmq_termination_request_socket.send_unicode('TERMINATE')
        zmq_termination_request_socket.close()
        self._zmq_messaging_thread.join()

        # Terminate handlers
        with self._lock:
            for handler_id in self._executing_handlers.copy().keys():
                msg = 'Terminating handler with ID {handler_id}'
                log.debug(msg.format(handler_id=handler_id))
                self.stop_handler(handler_id)
            self._stop_request.set()
        self._handler_status_check_thread.join()

        # Final cleanup - we save the parent stop() and the zmq context
        # until last.
        super().stop()
        self.zmq_context.term()


class SubprocessExecutionWithErrorCapturing:
    """FIXME"""

    def __init__(self, subproc_args, handler_params):
        """
        :param list subproc_args: arguments to be given to the subprocess at
            point of execution.
        :param dict handler_params: parameters to be sent to the subprocess
            over ZMQ once it is executing.

        """
        # Intialise logging
        _id_extras = {
            "ms": datetime.datetime.utcnow().microsecond,
            "id": id(self)
        }
        self._id_str = SUBPROCESS_ID_STR_TEMPLATE.format(**_id_extras)
        self.log = SubprocessExecutionLoggerAdapter(
            log.getChild(self.__class__.__name__), {'id_str': self._id_str}
        )

        # Set args for subprocess (to be given at point of execution)
        # and params (to be given during execution over ZMQ).
        self.command_line_args = subproc_args
        self.handler_params = handler_params

        # Setup the secure token - initally for registration (done over ZMQ),
        # then a new one will be generated for subsequent operations.
        self.security_token = str(uuid.uuid4())

        # Prepare a new thread to read the subprocess's stderr and write
        # to our log file.
        self._error_reader_thread = threading.Thread(target=self._error_reader)
        name = 'Subprocess Error Reader {id_str}'.format(id_str=self._id_str)
        self._error_reader_thread.name = name
        self._error_reader_thread.daemon = True

        # Compile the regexp used to read log messages over stderr
        self.regexp = re.compile(LOG_REGEXP)

        # FLAGS:
        #
        # The registered flag is used to indicate whether (and when) the
        # register() method has been called.
        #
        # The started flag is used to indicate whether (and when) the
        # start() method has been called.
        #
        # The _stop_request flag is used to help spot errors - if the
        # thread has stopped and the flag isn't set then the handler
        # has exited unexpectedly.
        #
        # The last_checkin flag is used to indicate whether (and when) the
        # handler checked in over ZMQ.
        self.registered = False
        self.started = False
        self._stop_request = False
        self.last_checkin = None

    def _error_reader(self):
        """Executes in separate thread: _error_reader_thread."""
        # Set the started flag
        self.started = time.time()

        # Read from stderr and log the message
        while True:
            line_in = self.subproc.stderr.readline()
            if line_in:
                line_in = line_in.strip().decode()
                match = self.regexp.match(line_in)
                (level, msg) = match.group('level',   'msg')
                level = DEFAULT_LOG_LEVEL if not level else level
                self.log.log(logging.getLevelName(level), msg)
            else:
                break

        # Handle termination
        # This should never evaluate to True, but the poll() call also
        # sets the returncode attribute of self.subproc.
        if self.subproc.poll() is None:
            self.log.debug('Reached EOF but process is still executing')
        return_code = self.subproc.returncode
        if return_code == 0:
            log_level = logging.DEBUG
        else:
            log_level = logging.DEBUG
        msg = 'Detected process termination with returncode {rtncode}'
        self.log.log(log_level, msg.format(rtncode=return_code))
        msg = 'Detected process termination, daemon thread will stop'
        self.log.debug(msg)

    def _registration_expired(self):
        """Checks if this object's registration period (for ZMQ registration)
        has expired.

        """
        now = time.time()
        registration_expiry_time = (
          self.started + SUBPROCESS_REGISTRATION_TIMEOUT
        )
        if registration_expiry_time <= now:
            self.log.error("Registration expiry check: registration expired")
            return True
        diff = registration_expiry_time - now
        msg = 'Registration expiry check: registration expires in {diff:.2}s'
        self.log.debug(msg.format(diff=diff))
        return False

    def erroneous_state_requires_stop(self):
        """Checks if this object is in an error state that means it's
        execution should be stopped.

        :rtype: boolean

        """
        # Either we've not been asked to started yet
        if not self.started:
            self.log.debug('Status check: not started yet')

        # Or we've been asked to stop
        elif self._stop_request:
            if self._error_reader_thread.is_alive():
                msg = 'Status check: stopped or stopping upon request'
                self.log.debug(msg)
                # FIMXE - Should this timeout somehow?

        # Or we expect normal execution
        else:
            if not self._error_reader_thread.is_alive():
                msg = 'Status check: stopped unexpectedly (handler error)'
                self.log.debug(msg)
                return True
            elif not self.registered:
                return self._registration_expired()
            else:
                # Detect processes that haven't recently checked in via ZMQ
                now = time.time()
                if not self.last_checkin:
                    due = self.registered + SUBPROCESS_CHECKIN_TIMEOUT
                else:
                    due = self.last_checkin + SUBPROCESS_CHECKIN_TIMEOUT
                if now > due:
                    self.log.debug('Status check: checkin overdue')
                return now > due
        return False

    def has_token(self, token):
        """Checks if this object's security token is the same as the
        supplied token.

        :param string token: the token to compare against.
        :rtype: boolean

        """
        return self.security_token == token

    def register(self):
        """Mark this subprocess as registered."""
        self.registered = time.time()
        self.security_token = str(uuid.uuid4())
        self.log.debug('Subprocess registration')

    def start(self):
        """Start execution of the subprocess and associated error reader
        thread.

        """
        # Each handler is started with two arguments: 1) the ZMQ address to
        # connect back to the manager on 2) an initial security token to
        # be sent in the first ZMQ message back to the manager (i.e. the
        # registration message.
        self.command_line_args.append(self.security_token)
        msg = 'Starting subprocess: args are {args}'
        self.log.debug(msg.format(args=self.command_line_args))

        # IMPORTANT - trying to access stdout/stdin here may cause deadlock.
        # We're not interested in them anyway so don't put them in the Popen
        # call.
        self.subproc = Popen(self.command_line_args, stderr=PIPE,
                             start_new_session=True)

        # Start the error reader thread (stderr -> log).
        self.log.debug('Starting thread for subprocess')
        self._error_reader_thread.start()
        return self._id_str

    def stop(self):
        """Stop subprocess execution."""
        # Avoid executing this when the process is already stopped/stopping
        if self._stop_request:
            return
        self._stop_request = True

        # FIXME - Try and do a 'soft' kill of the child process first (via ZMQ)

        # Hard kill the child process
        if self.subproc.poll() is None:
            try:
                self.subproc.terminate()
            except:
                pass
            time.sleep(SUBPROCESS_KILLTERM_TIMEOUT)
            if self.subproc.poll() is None:
                self.log.warning('Subprocess did not terminate, sending kill')
                try:
                    self.subproc.kill()
                except:
                    pass
                time.sleep(SUBPROCESS_KILLTERM_TIMEOUT)
                if self.subproc.poll() is None:
                    self.log.warning('Subprocess did not respond to kill')

        # The process should be dead now so we wait for the error
        # reading thread to finish.
        self._error_reader_thread.join()


class SubprocessExecutionLoggerAdapter(logging.LoggerAdapter):
    """A :class:`~logging.LoggerAdapter` to add subprocess IDs to log
    messages recorded by the parent.

    """

    def process(self, msg, kwargs):
        """Modifies the message and/or keyword arguments passed to a logging
        call in order to insert contextual information.

        This implementation ensures that the subprocess ID is recorded for
        any subprocess Exceptions that will be logged by the parent.

        :param string msg: the message format string to be passed to the
            logging call.
        :param dict kwargs: the keyword arguments to be passed to the
            logging call.
        :return: modified versions of the arguments (msg, kwargs) passed in.
        :rtype: a (msg, kwargs) tuple.

        """
        msg = SUBPROCESS_LOGGER_FORMAT_TEMPLATE.format(msg=msg, **self.extra)
        return super().process(msg, kwargs)
