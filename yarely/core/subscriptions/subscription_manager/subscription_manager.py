#!/usr/bin/env python3


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
import configparser
import logging
import queue
import threading
import time
from xml.etree import ElementTree

# Third party imports
import zmq

# Local (Yarely) imports
from yarely.core import platform
from yarely.core.helpers.base_classes import (
    ApplicationError, HandlerStub, URIManager
)
from yarely.core.helpers.base_classes.manager import check_handler_token
from yarely.core.helpers.execution import application_loop
from yarely.core.helpers.zmq import (
    ZMQ_ADDRESS_INPROC, ZMQ_ADDRESS_LOCALHOST, ZMQ_SOCKET_LINGER_MSEC,
    ZMQ_SOCKET_NO_LINGER, ZMQ_REQUEST_TIMEOUT_MSEC, ZMQ_SUBSMANAGER_REP_PORT,
    ZMQ_SUBSMANAGER_REQ_PORT
)
from yarely.core.subscriptions.subscription_parser import (
    XMLSubscriptionParser, XMLSubscriptionParserError, ContentDescriptorSet
)
from yarely.core.subscriptions.subscription_manager.persistence import (
    PersistentStore
)

log = logging.getLogger(__name__)

SUBPROCESS_CHECKIN_INTERVAL = 1        # Seconds
_TERMINATION_MARKER = object()
QUEUE_TIMEOUT = 1                      # Seconds
WARN_NO_REPLY = 'Expected reply from Scheduler not received, will retry.'

# When reading in subscriptions, one subscription may contain a
# reference to another. For example, the root content collection (of
# type file) almost certainly contains subscriptions to other sources.
#
# For security reasons, not all forms of subscription scheme can be
# referenced from every other (specifically, one can imagine a
# remote content collection specifying a local file source could
# potentially be a significant security flaw.
#
# The following dictionary therefore maps acceptable nesting patterns
# in the form:
#   'parent_scheme':['acceptable_child_scheme1', 'acceptable_child_scheme2']
#
# Because this is global accross handlers (e.g. two handlers providing
# http handling still have the same nesting policies this is specified
# in the manager.
#
# Note that a certain scheme is always acceptable to itself (i.e. an
# HTTP scheme can open an HTTP, a FILE can open a FILE) without
# inclusion in ACCEPTABLE_NESTING.
ACCEPTABLE_NESTING = {
    'file': ['http'],
}


class SubscriptionMangerError(ApplicationError):
    """Base class for subscription manager errors"""
    pass


class SubscriptionManager(URIManager):
    """Manages subscriptions"""

    def __init__(self):
        """Default constructor - Creates a new SubscriptionManager."""
        description = "Manage Yarely subscriptions"

        # The parent constructor provides config and logging and gets a
        # starting set of handlers using this classes _init_handlers() method.
        super().__init__(ZMQ_SUBSMANAGER_REP_PORT, description)
        self.registered = False

        # Setup for ZMQ Scheduler Messaging
        self.zmq_subsmanager_term_identifier = "subsmanager_term_{id}".format(
            id=id(self)
        )
        self.zmq_scheduler_req_addr = ZMQ_ADDRESS_LOCALHOST.format(
            port=ZMQ_SUBSMANAGER_REQ_PORT
        )
        self.zmq_scheduler_request_queue = queue.Queue()   # Q of infinite size

    @staticmethod
    def _can_nest(parent, child):
        """Determines whether the child source type can be contained within
        the parent source type.

        When reading in subscriptions, one subscription may contain a
        reference to another. For example, the root content collection (of
        type file) almost certainly contains subscriptions to other sources.

        For security reasons, not all forms of subscription scheme can be
        referenced from every other (specifically, one can imagine a
        remote content collection specifying a local file source could
        potentially be a significant security flaw.

        The ACCEPTABLE_NESTING dictionary therefore maps acceptable nesting
        patterns in the form:
            'parent_scheme':['acceptable_child_scheme1',
                             'acceptable_child_scheme2']
        Because this is global accross handlers (e.g. two handlers providing
        http handling still have the same nesting policies this is specified
        in the manager.

        Note that a certain scheme is always acceptable to itself (i.e. an
        HTTP scheme can open an HTTP, a FILE can open a FILE) without
        inclusion in ACCEPTABLE_NESTING

        This method checks the ACCEPTABLE_NESTING dictionary to see if the
        specified child source type can be contained within the specified
        parent source type.

        """
        if parent == child:
            return True
        if parent not in ACCEPTABLE_NESTING:
            return False
        return child in ACCEPTABLE_NESTING[parent]

    def _handle_arguments(self, args):
        """Handle arguments received from the argument parser."""
        super()._handle_arguments(args)

        # The subscription_root is a local file which provides the top-level
        # content collection.
        self.subscription_root = self.config.get('SubscriptionManagement',
                                                 'SubscriptionRoot')

        # Make sure there's a file available for the local database and
        # create any tables that don't exist.
        #
        # Note - SQLite doesn't support access from mutliple threads so
        # we don't keep the connection/cursor we've created, instead we
        # make sure it's closed cleanly. We'll reopen it when we need it
        # next.
        db_path = self.config.get('SubscriptionManagement', 'PersistTo')
        self._persistent_store = PersistentStore(db_path)

    def _handle_zmq_req_to_scheduler(self):
        """Executes in separate thread: _zmq_req_to_scheduler_thread."""

        # Provide some constants used as the return codes of nested
        # function _loop_over_sockets()
        NO_DATA = 0
        TERM = -1

        # Initialise ZMQ request socket
        zmq_request_socket = self.zmq_context.socket(zmq.REQ)
        zmq_request_socket.setsockopt(zmq.LINGER, ZMQ_SOCKET_LINGER_MSEC)
        zmq_request_socket.connect(self.zmq_scheduler_req_addr)

        # Initialise ZMQ socket to watch for termination before recvs
        # (we use the request queue to watch for termination before sends).
        zmq_termination_reply_socket = self.zmq_context.socket(zmq.REP)
        zmq_termination_reply_socket.bind(
            ZMQ_ADDRESS_INPROC.format(
                identifier=self.zmq_subsmanager_term_identifier
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
                qitem = self.zmq_scheduler_request_queue.get(
                    timeout=QUEUE_TIMEOUT
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
                            assert result > 0
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

    def _handle_reply_pong(self, msg_root, msg_elem):
        # FIXME
        self.registered = True

    @check_handler_token
    def _handle_request_subscription_update(self, msg_root, msg_elem):

        token = msg_root.attrib['token']
        with self._lock:
            handler = self._lookup_executing_handler_with_token(token)
            handler.last_checkin = time.time()
            try:
                subs_parser = XMLSubscriptionParser(msg_elem)
            except XMLSubscriptionParserError:
                log.exception('Failed to parse subscription update.')
                return self._encapsulate_reply(self._generate_pong())
            content_descriptor_set = subs_parser.get_descriptor_set()
            self._persistent_store.store_descriptor_set(content_descriptor_set)

            # Launch any new handlers
            for child in content_descriptor_set.get_children():
                if (
                    isinstance(child, ContentDescriptorSet) and
                    child.get_type() == 'remote'
                ):
                    sources = child.get_files()[0].get_sources()

                    # See if this child already has a handler
                    is_handled = False
                    for source in sources:
                        if (
                            self._lookup_executing_handler_with_uri(
                              source.get_uri()
                            ) is not None
                        ):
                            is_handled = True
                            break

                    # Launch a new handler if required
                    #    (FIXME: should we put this on a queue?)
                    if not is_handled:
                        source = sources[0]
                        handler = self.get_uri_handler_stub(source.get_uri())
                        if source.refresh:
                            handler.params_over_zmq['refresh'] = source.refresh
                        self.start_handler(handler)

            # Send an update to the scheduler
            root_xml_id = self._persistent_store.select_root_id_where_uri(
                msg_elem.attrib['uri']
            )
            subs_update_root = ElementTree.Element(
                'subscription_update', attrib={
                    'uri': platform.get_uri_from_local_path(
                        self.subscription_root
                    )
                }
            )
            xml_children = self._persistent_store.to_etree_elem(root_xml_id)
            if xml_children is None:
                msg = 'Not ready to send update yet (xml_children is None)'
                log.debug(msg)
            else:
                subs_update_root.append(xml_children)
                self.zmq_scheduler_request_queue.put_nowait(
                    self._encapsulate_request(subs_update_root)
                )

            return self._encapsulate_reply(self._generate_pong())

    def _init_handlers(self):
        # The _registered_handlers dictionary is keyed by addressing scheme,
        # current keys are:
        #     'file' => Handles a locally stored xml file.
        #     'http' => Handles remotely stored xml file to be fetched over
        #               http.
        python_launch_str = 'python3 -m {module}'
        file_handler = HandlerStub(
            command_line_args=python_launch_str.format(
                module='yarely.core.subscriptions.handlers.file'
            )
        )
        http_handler = HandlerStub(
            command_line_args=python_launch_str.format(
                module='yarely.core.subscriptions.handlers.http'
            )
        )
        self.add_handler('file', file_handler)
        self.add_handler('http', http_handler)

    def check_in(self):
        """Provide an occasional check-in to the Scheduler via ZMQ."""
        etree = self._encapsulate_request(self._generate_ping())
        self.zmq_scheduler_request_queue.put_nowait(etree)

    def start(self):
        """The main execution method for this application"""
        super().start()

        # Start the root handler
        uri = platform.get_uri_from_local_path(self.subscription_root)
        handler = self.get_uri_handler_stub(uri)
        try:
            handler.params_over_zmq['refresh'] = self.config.get(
                'SubscriptionManagement', 'RefreshRate'
            )
        except configparser.NoOptionError:
            pass        # Trust the handler to use its default
        self.start_handler(handler)

        # Start a new thread to create a ZMQ socket and send messages to
        # the scheduler
        self._zmq_req_to_scheduler_thread = threading.Thread(
            target=self._handle_zmq_req_to_scheduler
        )
        t_name = 'ZMQ Request Messenger (-> Scheduler)'
        self._zmq_req_to_scheduler_thread.name = t_name
        self._zmq_req_to_scheduler_thread.daemon = True
        self._zmq_req_to_scheduler_thread.start()

    def stop(self):
        # Send a ZMQ request to the inproc socket to be picked up by the poller
        zmq_termination_request_socket = self.zmq_context.socket(zmq.REQ)
        zmq_termination_request_socket.setsockopt(
            zmq.LINGER, ZMQ_SOCKET_LINGER_MSEC
        )
        zmq_termination_request_socket.connect(
            ZMQ_ADDRESS_INPROC.format(
                identifier=self.zmq_subsmanager_term_identifier
            )
        )
        zmq_termination_request_socket.send_unicode('TERMINATE')
        zmq_termination_request_socket.close()

        # And then pop a message on the queue of messages to go out just in
        # case we'd otherwise be blocked at that line.
        self.zmq_scheduler_request_queue.put_nowait(_TERMINATION_MARKER)

        # Now join the ZMQ thread and then call the parent class's stop() for
        # final cleanup.
        self._zmq_req_to_scheduler_thread.join()
        super().stop()


def main():
    application_loop(SubscriptionManager)
