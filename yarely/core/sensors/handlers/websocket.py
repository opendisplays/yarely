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
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.websocket

# Local (Yarely) imports
from yarely.core.helpers.base_classes import Handler, HandlerError
from yarely.core.helpers.execution import application_loop


log = logging.getLogger(__name__)

HANDLER_DESCRIPTION = "Handler for web socket sensing"


class SocketHandlerError(HandlerError):
    """Base class for socket sensor errors."""
    pass


class WebSocketServer(tornado.websocket.WebSocketHandler):
    """Tornado WebSocket server listening for Websocket messages. This class
    consists of a reference to WebSocketHandler that gets called for each new
    message.

    """

    def _get_ack(self, message_obj):
        """Create acknowledgement message to be sent to the client."""
        message = {"event": "ack", "data": message_obj['data']}
        return json.dumps(message)

    def check_origin(self, origin):
        # Returning True accepts cross-origin traffic, i.e. the Websocket
        # message does not have to come from the same hostname as this server
        # is running on.

        # FIXME: RETURNING TRUE IS POTENTIALLY NOT SAFE.
        # FIXME: use white list here to only allow messages from safe origins.
        return True

    def initialize(self, ws_handler_instance):
        self.ws_handler_instance = ws_handler_instance

    def on_close(self,):
        log.debug('Connection closed.')

    def on_message(self, message):
        log.debug("Message received: {}".format(message))

        # We expect the Websocket message to be valid JSON.
        try:
            message_obj = json.loads(message)
        except ValueError as e:
            log.warning("Invalid Websocket request received: {}".format(e))
            return

        self.ws_handler_instance.handle_socket_data(message_obj)

        # Acknowledging that we have processed the message by sending back a
        # ACK event consisting of the original request.
        # Todo: notify the client if we were not able to process the request.
        self.write_message(self._get_ack(message_obj))

    def open(self):
        log.debug('New connection opened.')


class WebSocketHandler(Handler):
    """This class provides the ability to listen for WebSocket requests from
    a Tornado websocket server. The websocket server calls handle_socket_data
    of this class each time it receives a new message.

    """

    def __init__(self):
        super().__init__(HANDLER_DESCRIPTION)
        self._stop_request = threading.Event()
        self.tornado_application = None
        self.tornado_http_server = None
        self.message_lock = threading.Lock()

    def _check_stop_request(self):
        if self._stop_request.is_set():
            log.info("Stop request, going to stop Websocket handler.")
            self.stop()

    def _generate_sensor_update(self, data):
        root = ElementTree.Element(
            'sensor_update', attrib={'source': 'websocket'}
        )

        # If 'data' is XML, then we parse it. Otherwise we just add it as
        # text to the element tree.
        try:
            root.append(ElementTree.XML(data))
        except ExpatError:
            root.text = data
        return root

    def _handle_reply_params(self, msg_root, msg_elem):
        super()._handle_reply_params(msg_root, msg_elem)
        port = int(self.params['port'])
        log.info('Port number is {port}'.format(port=port))

        # Start accepting requests
        if not self._stop_request.is_set():
            # Start the Tornado server initialisation in a separate Thread --
            # this allows the main thread to continue with ZMQ-related
            # behaviour.
            threading.Thread(
                target=self._initialise_websocket_server, kwargs={'port': port}
            ).start()

    def _initialise_websocket_server(self, port):
        """Initialise Tornado URI paths and start the IOLoop to listen for
        requests.

        """
        self.tornado_application = tornado.web.Application([
            (r'/', WebSocketServer, {'ws_handler_instance': self})
        ])
        self.tornado_http_server = tornado.httpserver.HTTPServer(
            self.tornado_application
        )
        self.tornado_http_server.listen(port)

        # Adding periodic callback to check whether _stop_request is set to be
        # able to exit out of the IO Loop.
        log.info("Adding periodic callback.")
        tornado.ioloop.PeriodicCallback(self._check_stop_request, 500).start()

        log.info("Going to start Tornado now.")
        tornado.ioloop.IOLoop.instance().start()

    def handle_socket_data(self, message):
        """Handling incoming requests from Websocket. This method is
        thread-safe.

        :param string message: FIXME.

        """
        with self.message_lock:
            log.debug("Received Websocket message: {}.".format(message))

            # Check if the message has the right format at all.
            if 'data' not in message:
                log.info("Data missing in Websocket message.")
                return

            # We only care about Pings, not Pongs.
            if 'event' in message and message['event'] != 'ping':
                log.info("Unexpected 'event' in Websocket message: {}.".format(
                    message['event']
                ))
                return

            # Wrap the received data up in XML and put on the ZMQ message queue
            # for distribution to the sensor manager and scheduler.
            data_str = message['data']
            etree = self._encapsulate_request(
                self._generate_sensor_update(data_str)
            )
            self.zmq_request_queue.put_nowait(etree)

    def start(self):
        super().start()
        log.info('Websocket Handler launched.')

    def stop(self):
        self._stop_request.set()
        super().stop()
        tornado.ioloop.IOLoop.instance().stop()

        log.info('Websocket Handler stopped')

if __name__ == "__main__":
    application_loop(WebSocketHandler)
