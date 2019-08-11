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
import threading
from xml.etree import ElementTree

# Third party imports
import zmq

# Local (Yarely) imports
from yarely.core.helpers.base_classes.zmq_rpc import ZMQRPC
from yarely.core.helpers.zmq import (
    ZMQ_ADDRESS_INPROC,  ZMQ_ADDRESS_LOCALHOST, ZMQ_SOCKET_LINGER_MSEC,
    ZMQ_SENSORMANAGER_REQ_PORT, ZMQ_SUBSMANAGER_REQ_PORT
)
from yarely.core.scheduling.constants import CONTEXT_STORE_DEFAULT_DB_PATH
from yarely.core.scheduling.contextstore import (
    ContextStore, UnsupportedContextTypeError
)
from yarely.core.subscriptions.subscription_parser import (
    SubscriptionElement, XMLSubscriptionParser, XMLSubscriptionParserError
)


log = logging.getLogger(__name__)
benchmark_logger = logging.getLogger('benchmarks')


class _ContextConstraintsParser(ZMQRPC):
    """The Scheduler Context and Constraints parser handles incoming ZMQ
    requests from both the subscription and sensor manager, and forwards
    updates from the subscription manager to the scheduler manager instance.
    Incoming context information from the sensors will be written into the
    context store before the scheduler manager will be notified about a new
    update.

    """
    def __init__(self, scheduler_mgr):
        """
        :param scheduler_mgr: FIXME
        :type scheduler_mgr: FIXME

        """
        self.scheduler_mgr = scheduler_mgr
        self.context_store = ContextStore(CONTEXT_STORE_DEFAULT_DB_PATH)

        # This thread will listen for incoming data on REPly sockets connected
        # to the subscription and sensor managers.
        self._zmq_scheduler_reply_thread = None

        # ZMQ initialisation
        self.zmq_scheduler_term_identifier = "zmq_scheduling_term_{id}".format(
            id=id(self)
        )
        self.zmq_context = zmq.Context()

    @staticmethod
    def _get_context_type(message):
        """Returns the context type for an incoming raw sensor update which is
        usually the name of the root XML tag.

        """
        return message.get('event')

    def _handle_incoming_zmq(self):
        """Handles incoming requests. Uses _handle_zmq_messages to map requests
        on to methods.

        """
        # Create reply socket to subscription manager
        zmq_subsmanager_reply_socket = self.zmq_context.socket(zmq.REP)
        zmq_subsmanager_reply_socket.setsockopt(
            zmq.LINGER, ZMQ_SOCKET_LINGER_MSEC
        )
        zmq_subsmanager_reply_socket.bind(
            ZMQ_ADDRESS_LOCALHOST.format(port=ZMQ_SUBSMANAGER_REQ_PORT)
        )

        # Create a reply socket to the sensor manager
        zmq_sensormanager_reply_socket = self.zmq_context.socket(zmq.REP)
        zmq_sensormanager_reply_socket.setsockopt(
            zmq.LINGER, ZMQ_SOCKET_LINGER_MSEC
        )
        zmq_sensormanager_reply_socket.bind(
            ZMQ_ADDRESS_LOCALHOST.format(port=ZMQ_SENSORMANAGER_REQ_PORT)
        )

        # Create termination socket
        zmq_termination_reply_socket = self.zmq_context.socket(zmq.REP)
        zmq_termination_reply_socket.bind(
            ZMQ_ADDRESS_INPROC.format(
                identifier=self.zmq_scheduler_term_identifier
            )
        )

        # Register all sockets
        zmq_poller = zmq.Poller()
        zmq_poller.register(zmq_subsmanager_reply_socket, zmq.POLLIN)
        zmq_poller.register(zmq_sensormanager_reply_socket, zmq.POLLIN)
        zmq_poller.register(zmq_termination_reply_socket, zmq.POLLIN)

        # Provide a method to loop over sockets that have data. It tries to
        # find matching methods for incoming requests/replies with
        # _handle_zmq_msg().
        def _loop_over_sockets():
            term = False

            for sock in socks_with_data:
                if sock is zmq_termination_reply_socket:
                    return True

                msg = sock.recv().decode()
                reply = self._handle_zmq_msg(msg)

                # Check if we got a valid reply from the method called.
                if reply is None:
                    log.warning(
                        "No reply generated, replying with error!"
                    )
                    reply = self._encapsulate_reply(self._generate_error())

                sock.send(ElementTree.tostring(reply))

            return term

        # Look at all incoming messages
        while True:
            socks_with_data = dict(zmq_poller.poll())

            if socks_with_data:
                term = _loop_over_sockets()

                if term:
                    break

        # Cleanup ZMQ
        zmq_poller.unregister(zmq_subsmanager_reply_socket)
        zmq_poller.unregister(zmq_sensormanager_reply_socket)
        zmq_poller.unregister(zmq_termination_reply_socket)
        zmq_subsmanager_reply_socket.close()
        zmq_sensormanager_reply_socket.close()
        zmq_termination_reply_socket.close()

    def _handle_request_sensor_update(self, msg_root, msg_elem):
        """This method is listening for sensor updates (e.g. interest counts
        from Mercury, or touch screen inputs if it is running on a touch
        display. All sensor updates will be stored within the context store
        that is accessible to all Yarely (and Scheduler) components. After each
        sensor update coming in, we will trigger the item scheduling of the
        Scheduler Manager.
        """

        msg_string = ElementTree.tostring(msg_elem)
        log.info("Receiving sensor update: {}".format(msg_string))

        # Write the incoming XML data into the context store. We expect this to
        # be a ContentItem element.

        # If we received a trigger to show the touch input overlay, then we
        # will call the appropriate method from here.
        touch_input = msg_elem.find('touch_input')
        if touch_input is not None and touch_input.text == 'touch_button_push':
            threading.Thread(
                target=self.scheduler_mgr._initialise_touch_selection
            ).start()
            return self._encapsulate_reply(self._generate_pong())

        # Parse the incoming XML into a ContentItem object and read out the
        # context type.
        parsed_content_item = self._parse_raw_context_information(msg_elem)
        context_type = self._get_context_type(msg_elem)

        # Write this to the database
        try:
            self.context_store.add_context(context_type, parsed_content_item)
        except UnsupportedContextTypeError:
            log.error("Trying to write unsupported sensor update: {}".format(
                msg_string
            ))

        # Report on incoming sensor updates to the analytics service.
        self.scheduler_mgr.report_event(
            category='Sensor Update', action=context_type, value=1,
            label=str(parsed_content_item)
        )

        # Trigger new item scheduling after receiving new context information.
        # We want to do this in a separate thread so that we don't block on
        # item_scheduling.
        threading.Thread(target=self.scheduler_mgr.item_scheduling).start()

        return self._encapsulate_reply(self._generate_pong())

    def _handle_request_subscription_update(self, msg_root, msg_elem):
        """This handles incoming updates from the subscription manager. The
        subscription sends off a content descriptor set (that might be not
        complete yet) as a raw string. This will be parsed into a valid CDS
        object and then forwarded to the Scheduler Manager. This update will
        possible trigger rescheduling of displayed content items.

        """

        # TODO - check msg_root vs msg_elem
        # TODO - handle incomplete CDS updates

        log.debug("Handling subscription update...")

        benchmark_logger.info("received_cds")

        parsed_cds = self._parse_raw_cds_xml(msg_elem)

        benchmark_logger.info("parsed_cds")
        benchmark_logger.info("number_of_items {}".format(len(parsed_cds)))

        if parsed_cds is not None:
            self.scheduler_mgr.cds_updates.put(parsed_cds)
        # FIXME: do we want to do something more if parsed_cds is None?

        return self._encapsulate_reply(self._generate_pong())

    @staticmethod
    def _parse_raw_cds_xml(raw_cds_xml):
        """ Trying to parse the a raw string consisting of a content descriptor
        set. If the raw CDS XML is empty or invalid, it will return None and
        create an error log.

        """
        log.debug("Parsing XML Subscription")
        cds = None

        try:
            cds_xml_parser = XMLSubscriptionParser(raw_cds_xml)
            cds = cds_xml_parser.get_descriptor_set()

        except XMLSubscriptionParserError as err:
            # FIXME: what should happen if parsing fails?
            log.error("Parsing raw CDS XML failed with error: {}".format(err))

        return cds

    @staticmethod
    def _parse_raw_content_item_xml(raw_content_item_xml):
        log.debug("Parsing XML Content Item")
        content_item = None

        try:
            content_item = SubscriptionElement(raw_content_item_xml)
        except XMLSubscriptionParserError as err:
            log.error(
                "Parsing raw content item XML failed with error: {}".format(
                    err
                )
            )

        return content_item

    def _parse_raw_context_information(self, message):
        """FIXME."""
        if not isinstance(message, ElementTree.Element):
            # Fixme - raise appropriate error here
            return

        # We assume that each message has a wrapper around and the (one) child
        # of message is the actual ContentItem or ContentDescriptorSet.

        # Sensor update... content item.
        try:
            child = message[0]
        except IndexError:
            return None

        content_item = self._parse_raw_content_item_xml(child)
        return content_item

    def start(self):
        """Start listening for incoming requests/replies. The mapping from
        request to method is done in _handle_incoming_zmq.

        """
        self._zmq_scheduler_reply_thread = threading.Thread(
            target=self._handle_incoming_zmq
        )
        t_name = 'ZMQ Scheduler Reply Thread'
        self._zmq_scheduler_reply_thread.name = t_name
        self._zmq_scheduler_reply_thread.daemon = True
        self._zmq_scheduler_reply_thread.start()

    def stop(self):
        """Terminate all threads that were started by this class."""

        # TODO - do we want to send a 'turn off' event to the display here?

        # Terminate ZMQ-related threads
        zmq_termination_request_socket = self.zmq_context.socket(zmq.REQ)
        zmq_termination_request_socket.setsockopt(
            zmq.LINGER, ZMQ_SOCKET_LINGER_MSEC
        )
        zmq_termination_request_socket.connect(
            ZMQ_ADDRESS_INPROC.format(
                identifier=self.zmq_scheduler_term_identifier
            )
        )
        zmq_termination_request_socket.send_unicode('TERMINATE')
        zmq_termination_request_socket.close()
        self._zmq_scheduler_reply_thread.join()

        self.zmq_context.term()
