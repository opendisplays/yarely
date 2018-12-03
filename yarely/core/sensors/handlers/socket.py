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
import logging
import socket
import threading
from xml.etree import ElementTree
from xml.parsers.expat import ExpatError

# Local (Yarely) imports
from yarely.core.helpers.base_classes import Handler, HandlerError
from yarely.core.helpers.execution import application_loop

log = logging.getLogger(__name__)

BUFFER_SIZE = 4096
HANDLER_DESCRIPTION = "Handler for socket sensing"
MAX_CONNECTIONS = 5
NO_BLOCKING = 0
WAIT_INTERVAL = 0.1


class SocketHandlerError(HandlerError):
    """Base class for socket sensor errors."""
    pass


class SocketHandler(Handler):
    """The SocketHandler class provides a sensor handler for socket
    sensing.

    """

    def __init__(self):
        super().__init__(HANDLER_DESCRIPTION)
        self._stop_request = threading.Event()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def _generate_sensor_update(self, data):
        root = ElementTree.Element(
            'sensor_update', attrib={}
        )
        try:
            root.append(ElementTree.XML(data))
        except ExpatError:
            root.text = ElementTree.XML(data)
        return root

    def _handle_reply_params(self, msg_root, msg_elem):
        super()._handle_reply_params(msg_root, msg_elem)
        port = int(self.params['port'])
        log.info('Port number is {port}'.format(port=port))
        try:
            self.sock_addr = (self.params['host'], port)
        except KeyError:
            addr = socket.gethostbyname(socket.gethostname())
            log.info(
                'No host address specified, using {addr}'.format(addr=addr)
            )
            self.sock_addr = (addr, port)
        self.sock.bind(self.sock_addr)
        self.sock.listen(MAX_CONNECTIONS)

        # We need to be able to exit even if a client is holding a
        # connection open so we set a timeout on the socket.
        self.sock.settimeout(WAIT_INTERVAL)

        # Start accepting requests
        if not self._stop_request.is_set():
            self._socket_accept_thread.start()

    def _handle_socket_connections(self):
        while not self._stop_request.wait(WAIT_INTERVAL):
            try:
                # Accept connection
                (connection, address) = self.sock.accept()
                log.info(
                    'Accepted connection from {addr}'.format(addr=address)
                )

                # Start thread to handle socket connections and messages
                connection_id = id(connection)
                sock_reader = threading.Thread(
                    target=self._handle_socket_data,
                    kwargs={'address': address, 'connection': connection}
                )
                sock_reader.name = 'Socket Receiver {conn} ({addr})'.format(
                    conn=connection_id, addr=address
                )
                sock_reader.daemon = True
                self._socket_reader_threads[connection_id] = sock_reader
                self._socket_reader_threads[connection_id].start()

            except socket.timeout:
                pass

    def _handle_socket_data(self, connection, address=None):
        # We need to be able to exit even if a client is holding a
        # connection open so we set a timeout on the socket.
        connection.settimeout(WAIT_INTERVAL)

        # Loop until application termination or client disconnect
        all_data = ''
        while not self._stop_request.wait(WAIT_INTERVAL):

            # We expect each connection to result in a single data message
            # (for now) so we'll assemble this then forward over ZMQ.
            try:
                data = connection.recv(BUFFER_SIZE)
                if not data:
                    break
                all_data += data.decode()
            except socket.timeout:
                pass    # No data but connected, continue (for now...
# NOQA                  # maybe we should drop the connection?)

        log.info('Received data from {addr}: {data}'.format(
            addr='socket' if address is None else address,
            data=all_data
        ))
        etree = self._encapsulate_request(
            self._generate_sensor_update(all_data)
        )
        self.zmq_request_queue.put_nowait(etree)
        connection.close()
        self._socket_reader_threads.pop(id(connection))

    def start(self):
        """Main entry point."""
        super().start()
        log.info('Socket Handler Launched')

        # Start thread to handle socket connections and messages
        self._socket_accept_thread = threading.Thread(
            target=self._handle_socket_connections
        )
        self._socket_accept_thread.name = 'Socket Connections Monitor'
        self._socket_accept_thread.daemon = True
        self._socket_reader_threads = dict()

    def stop(self):
        self._stop_request.set()
        try:
            self._socket_accept_thread.join()
        except RuntimeError:
            pass        # _socket_accept_thread not started yet
        for socket_reader_thread in self._socket_reader_threads:
            socket_reader_thread.join()
        self.sock.close()
        super().stop()
        log.info('Socket Handler Stopped')


if __name__ == "__main__":
    application_loop(SocketHandler)
