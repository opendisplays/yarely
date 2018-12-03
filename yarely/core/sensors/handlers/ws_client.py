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
import json
import logging
import threading
from xml.etree import ElementTree
from xml.parsers.expat import ExpatError

# Third-party packages
import tornado.httpclient
import tornado.ioloop
import tornado.gen
import tornado.web
import tornado.websocket

# Local (Yarely) imports
from yarely.core.helpers.base_classes import Handler, HandlerError
from yarely.core.helpers.execution import application_loop


log = logging.getLogger(__name__)

HANDLER_DESCRIPTION = "Handler for web socket client connections"
RECONNECT_TIMEOUT = 0.5  # seconds


class SocketHandlerError(HandlerError):
    """Base class for socket sensor errors."""
    pass


class WSClientHandler(Handler):
    """This class provides the ability to listen for WebSocket requests from
    a Tornado websocket server. The websocket server calls handle_socket_data
    of this class each time it receives a new message.

    """
    def __init__(self):
        super().__init__(HANDLER_DESCRIPTION)
        self._stop_request = threading.Event()
        self.tornado_application = None
        self.message_lock = threading.Lock()

    def _check_stop_request(self):
        if self._stop_request.is_set():
            log.info(
                "WS_CLIENT Stop request, going to stop Websocket handler."
            )
            self.stop()

    def on_message(self, message):
        """FIXME.

        :param string message: the received message, should be valid JSON.

        """
        log.debug("WS_CLIENT Message received: {}".format(message))

        if not message:
            return

        # We expect the Websocket message to be valid JSON.
        try:
            message_obj = json.loads(message)
        except ValueError as e:
            log.warning(
                "WS_CLIENT Invalid Websocket request received: {}".format(e)
            )
            return

        self.handle_socket_data(message_obj)

        # Acknowledging that we have processed the message by sending back a
        # ACK event consisting of the original request.
        # Todo: notify the client if we were not able to process the request.
        self.ws.write_message(self._get_ack(message_obj))

    def _get_ack(self, message_obj):
        """ Create acknowledgement message to be sent to the client. """
        data = None

        if 'data' in message_obj:
            data = message_obj['data']

        message = {"event": "ack", "data": data}
        return json.dumps(message)

    @staticmethod
    def _generate_sensor_update(event, data):
        root = ElementTree.Element(
            'sensor_update', attrib={'source': 'websocket', 'event': event}
        )

        log.debug('DATA: {}'.format(data))

        # If 'data' is XML, then we parse it. Otherwise we just add it as
        # text to the element tree.
        try:
            root.append(ElementTree.XML(data))
        except ExpatError:
            root.text = data
        except TypeError:
            root.text = str(data)
        except ElementTree.ParseError as e:
            log.warning('Malformed XML received: {}'.format(e))
            return root

        return root

    def _handle_reply_params(self, msg_root, msg_elem):
        super()._handle_reply_params(msg_root, msg_elem)

        self._ws_server_host = self.params['ws_server_host']
        self._ws_server_path = self.params['ws_server_path']
        self._display_id = self.params['display_id']
        self._beacon_id = self.params['beacon_id']

        # Start accepting requests
        if not self._stop_request.is_set():
            # Start the Tornado server initialisation in a separate Thread --
            # this allows the main thread to continue with ZMQ-related
            # behaviour.
            log.info("WS_CLIENT starting separate thread")
            threading.Thread(
                target=self._initialise_ws_client
            ).start()

    @tornado.gen.coroutine
    def _websocket_client(self, url):
        log.debug("WS CLIENT tyring to connect now...{}".format(url))

        try:
            self.ws = yield tornado.websocket.websocket_connect(url)
        except:
            tornado.ioloop.IOLoop.instance().call_later(
                RECONNECT_TIMEOUT, self._websocket_client, url
            )
            log.warning("WS_CLIENT could not connect to {}".format(url))
            return

        # If connected send a dictionary with the display ID.
        tmp = {
            'event': 'init', 'data': {
                'display_id': self._display_id, 'beacon_id': self._beacon_id
            }
        }
        self.ws.write_message(json.dumps(tmp))

        while True:
            msg = yield self.ws.read_message()
            if msg is None:
                log.info("WS_CLIENT closed connection?")
                # Trying to reconnect if connection was closed.
                tornado.ioloop.IOLoop.instance().call_later(
                    RECONNECT_TIMEOUT, self._websocket_client, url
                )
                break
            self.on_message(msg)

    def _initialise_ws_client(self):
        """
        """

        url = "{server}{path}".format(
            server=self._ws_server_host, path=self._ws_server_path
        )

        log.info("WS_CLIENT Starting connection now...")
        log.info("WS_CLIENT Connecting to {}".format(url))
        self._websocket_client(url)
        #
        # while True:
        #     msg = yield conn.read_message()
        #     if msg is None: break
        #     # Do something with msg

        # Adding periodic callback to check whether _stop_request is set to be
        # able to exit out of the IO Loop.
        log.info("WS_CLIENT Adding periodic callback.")
        tornado.ioloop.PeriodicCallback(self._check_stop_request, 500).start()
        tornado.ioloop.IOLoop.instance().start()

    def handle_socket_data(self, message):
        """ Handling incoming requests from Websocket. This method is
        thread-safe.

        :param string message: FIXME.

        """
        with self.message_lock:
            log.debug("WS_CLIENT Received Websocket message: {}.".format(message))

            supported_events = ['ping', 'content_trigger']

            # We only care about events we support.
            if 'event' in message and message['event'] not in supported_events:
                log.info("WS_CLIENT Unexpected 'event': {}.".format(
                    message['event']
                ))
                return

            # Check if the message has the right format at all.
            if 'data' not in message:
                log.info("WS_CLIENT Data missing in Websocket message.")
                return

            if message['event'] == 'ping':
                log.info("WS_CLIENT ping received")
                return

            # Wrap the received data up in XML and put on the ZMQ message queue
            # for distribution to the sensor manager and scheduler.
            data_str = message['data']

            # In case data is empty
            log.info("WS_CLIENT data_str {}".format(data_str))
            if not data_str:
                return
            if data_str == 'connected':
                return
            if data_str == 'ping':
                return

            etree = self._encapsulate_request(
                self._generate_sensor_update(message['event'], data_str)
            )
            self.zmq_request_queue.put_nowait(etree)

    def start(self):
        super().start()
        log.info('WS_CLIENT handler launched.')

    def stop(self):
        self._stop_request.set()
        super().stop()
        tornado.ioloop.IOLoop.instance().stop()

        log.info('WS_CLIENT Handler stopped')

if __name__ == "__main__":
    application_loop(WSClientHandler)
