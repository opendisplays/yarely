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
import logging
import queue
import threading
import time
from xml.etree import ElementTree

# Third party imports
import zmq

# Local (Yarely) imports
from yarely.core.helpers.zmq import ZMQ_ADDRESS_INPROC
from yarely.core.helpers.zmq import ZMQ_REQUEST_TIMEOUT_MSEC
from yarely.core.helpers.zmq import ZMQ_SOCKET_LINGER_MSEC
from yarely.core.helpers.zmq import ZMQ_SOCKET_NO_LINGER
from yarely.core.helpers.base_classes import ApplicationWithBasicLogging
from yarely.core.helpers.base_classes import ApplicationError
from yarely.core.helpers.base_classes import ZMQRPC

log = logging.getLogger(__name__)


SUBPROCESS_CHECKIN_INTERVAL = 1
"""Frequency with which subprocesses are expected to check in (in seconds)."""

_TERMINATION_MARKER = object()
WARN_NO_REPLY = 'Expected reply from Manager not received, will retry.'


class HandlerError(ApplicationError):
    """Base class for handler errors."""
    pass


class HandlerRPCError(HandlerError):
    """Base class for handler<->manager RPC errors."""
    def __init__(self, msg):
        MSG_PREFIX = 'Invalid RPC XML: '
        super().__init__(MSG_PREFIX + msg)


class Handler(ApplicationWithBasicLogging, ZMQRPC):
    """A base class for handlers.

    Subclasses can add end handle extra command line arguments by
    overriding Handler._add_arguments() and Handler._handle_arguments()
    which are both called by Handler.process_arguments().

    """

    def __init__(self, description):
        super().__init__(description)
        self.zmq_context = zmq.Context()
        self.zmq_handler_term_identifier = "handler_term_{id}".format(
            id=id(self)
        )
        self.zmq_request_queue = queue.Queue()        # Queue of infinite size
        self.registered = False
        self.params = {}

    def _add_arguments(self, arg_parser):
        super()._add_arguments(arg_parser)
        arg_parser.add_argument("zmq", help="A ZMQ conenction string")
        tkn_help = "A one-off security token for registration with the manager"
        arg_parser.add_argument("token", help=tkn_help)

    def _generate_register(self, registration_token):
        root = ElementTree.Element(
            'register', attrib={'token': registration_token}
        )
        return root

    def _generate_subscription_update(self, uri, subscription_xml):
        root = ElementTree.Element(
            'subscription_update', attrib={'uri': uri}
        )
        root.append(ElementTree.XML(subscription_xml))
        return root

    def _handle_arguments(self, args):
        super()._handle_arguments(args)
        self.zmq_req_addr = args.zmq
        self.registration_token = args.token

    def _handle_reply_params(self, msg_root, msg_elem):
        log_msg = 'Params received from Manager: {msg}'
        xml = ElementTree.tostring(msg_elem)
        log.debug(log_msg.format(msg=xml))
        for param in msg_elem:
            if param.tag == 'param':
                self.params[param.attrib['name']] = param.attrib['value']
            else:
                raise HandlerRPCError('Params contained a non-param tag')
        try:
            self.token = self.params['token']
        except KeyError:
            msg = 'Params did not contain compulsory parameter: token'
            raise HandlerRPCError(msg)
        self.registered = True

    def _handle_reply_pong(self, msg_root, msg_elem):
        """
        Handles an incoming pong reply message.

        This implementation does not do anything at all.

        :param msg_root: The root element for the incoming ping message.
        :type msg_root: an :class:`xml.etree.ElementTree.Element` instance.
        :param msg_elem: The element representing the ping portion of the
            incoming message.
        :type msg_elem: an :class:`xml.etree.ElementTree.Element` instance.

        """
        # FIXME - are we keeping tabs on the manager?
        pass

    def _handle_zmq(self):
        """Executes in separate thread: _zmq_messaging_thread."""

        # Provide some constants used as the return codes of nested
        # function _loop_over_sockets()
        NO_DATA = 0
        TERM = -1

        # Initialise ZMQ request socket
        zmq_request_socket = self.zmq_context.socket(zmq.REQ)
        zmq_request_socket.setsockopt(zmq.LINGER, ZMQ_SOCKET_LINGER_MSEC)
        zmq_request_socket.connect(self.zmq_req_addr)

        # Initialise ZMQ socket to watch for termination before recvs
        # (we use the request queue to watch for termination before sends).
        zmq_termination_reply_socket = self.zmq_context.socket(zmq.REP)
        zmq_termination_reply_socket.bind(
            ZMQ_ADDRESS_INPROC.format(
                identifier=self.zmq_handler_term_identifier
            )
        )

        # Initialise ZMQ Poller for recvs
        zmq_request_poller = zmq.Poller()
        zmq_request_poller.register(zmq_request_socket, zmq.POLLIN)
        zmq_request_poller.register(zmq_termination_reply_socket, zmq.POLLIN)

        # Provide a method to loop over sockets that have data
        def _loop_over_sockets():
            rtn = NO_DATA
            for sock in socks_with_data:
                if sock is zmq_termination_reply_socket:
                    return TERM
                elif sock is zmq_request_socket:
                    reply = sock.recv().decode()
                    if not reply:
                        continue
                    self._handle_zmq_msg(reply)
                    rtn = len(reply)
                else:
                    log.info(
                        'Unhandled socket data: {sock}'.format(sock=sock)
                    )
            return rtn

        # Time the last request was sent (unix timestamp)
        last_request = 0

        while True:
            # Send a message from the message queue
            try:
                qitem = self.zmq_request_queue.get(
                    timeout=SUBPROCESS_CHECKIN_INTERVAL
                )

                # First check for termnation
                if qitem is _TERMINATION_MARKER:
                    break

                # We've not been asked to terminate, so send
                # the message over ZMQ.

                # Queue items are ElementTree Elements, so we encode them to a
                # byte representation.
                encoded_qitem = ElementTree.tostring(qitem, encoding="UTF-8")

                last_request = time.time()
                zmq_request_socket.send(encoded_qitem)

                # Every send should have an associated receive.
                expect_reply = True
                result = None
                while expect_reply:
                    socks_with_data = dict(
                        zmq_request_poller.poll(ZMQ_REQUEST_TIMEOUT_MSEC)
                    )
                    if socks_with_data:
                        result = _loop_over_sockets()
                        if result is TERM:          # Terminate
                            break
                        elif result is NO_DATA:     # Rebuild socket
                            log.warning(WARN_NO_REPLY)
                            zmq_request_socket.setsockopt(zmq.LINGER,
                                                          ZMQ_SOCKET_NO_LINGER)
                            zmq_request_socket.close()
                            zmq_request_poller.unregister(zmq_request_socket)
                            zmq_request_socket = self.zmq_context.socket(
                                                 zmq.REQ)
                            zmq_request_socket.setsockopt(
                                zmq.LINGER, ZMQ_SOCKET_LINGER_MSEC
                            )
                            zmq_request_socket.connect(self.zmq_req_addr)
                            zmq_request_poller.register(zmq_request_socket,
                                                        zmq.POLLIN)
                            zmq_request_socket.send(encoded_qitem)
                        else:
                            assert(result > 0)
                            expect_reply = False    # Success!
                if result is TERM:
                    break

            except queue.Empty:
                pass

            # We do this last so we don't check in if we've just sent data
            # If we're not registered yet, we can't checkin
            next_checkin = last_request + SUBPROCESS_CHECKIN_INTERVAL
            if self.registered and next_checkin <= time.time():
                self.check_in()

        zmq_request_socket.close()

    def check_in(self):
        """Provide an occasional check-in (ping) to the Manager via ZMQ."""
        etree = self._encapsulate_request(self._generate_ping())
        self.zmq_request_queue.put_nowait(etree)

    def register(self):
        """Register this Handler to the Manager via ZMQ."""
        etree = self._generate_register(self.registration_token)
        self.zmq_request_queue.put_nowait(etree)

    def start(self, register=True):
        """Main entry point.

        :param boolean register: If `register` is True (default), register
            with the manager, otherwise the caller will need to explictly
            call :meth:`~self.register()` once it is ready.

        """
        if register:
            self.register()

        # Start a new thread to create and monitor ZMQ sockets.
        self._zmq_messaging_thread = threading.Thread(
            target=self._handle_zmq
        )
        self._zmq_messaging_thread.name = 'ZMQ Messenger'
        self._zmq_messaging_thread.daemon = True
        self._zmq_messaging_thread.start()

    def stop(self):
        """Application termination cleanup."""
        # Send a ZMQ request to the inproc socket to be picked up by the poller
        zmq_termination_request_socket = self.zmq_context.socket(zmq.REQ)
        zmq_termination_request_socket.setsockopt(
            zmq.LINGER, ZMQ_SOCKET_LINGER_MSEC
        )
        zmq_termination_request_socket.connect(
            ZMQ_ADDRESS_INPROC.format(
                identifier=self.zmq_handler_term_identifier
            )
        )
        zmq_termination_request_socket.send_unicode('TERMINATE')
        zmq_termination_request_socket.close()

        # And then pop a message on the queue of messages to go out just in
        # case we'd otherwise be blocked at that line.
        self.zmq_request_queue.put_nowait(_TERMINATION_MARKER)

        # Now join the ZMQ thread and then call the parent class's stop() for
        # final cleanup.
        self._zmq_messaging_thread.join()
        super().stop()
        self.zmq_context.term()
