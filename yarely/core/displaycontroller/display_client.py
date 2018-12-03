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
from datetime import datetime
import logging
import queue
import threading
import time

# Third party packages
import zmq

# Local (Yarely) imports
from yarely.core.helpers.zmq import (
    ZMQ_ADDRESS_LOCALHOST, ZMQ_DISPLAYCONTROLLER_REP_PORT
)

log = logging.getLogger(__name__)

DISPLAY_ON_XML = (
    "<request token='UNUSED'><display_on until='{timestamp}'/></request>"
)
REQUEST_TIMEOUT = 2500
_TERMINATION_MARKER = object()


class DisplayClient(object):
    """Display Client can send requests to the display controller to keep the
    display physically turned on and alive. This is asynchronously by adding
    requests to a message queue.

    """

    def __init__(self):
        self.context = zmq.Context(1)
        self.poll = zmq.Poller()
        self._make_client()
        self.msg_queue = queue.Queue()   # Q of infinite size
        self.queue_processor = threading.Thread(target=self._handle_queue)
        self.queue_processor.daemon = True
        self.queue_processor.start()

    def _make_client(self):
        self.client = self.context.socket(zmq.REQ)
        self.client.connect(ZMQ_ADDRESS_LOCALHOST.format(
            port=ZMQ_DISPLAYCONTROLLER_REP_PORT
        ))
        self.poll.register(self.client, zmq.POLLIN)

    def _send_request(self, request):
        self.client.send_unicode(request)
        expect_reply = True

        while expect_reply:
            socks = dict(self.poll.poll(REQUEST_TIMEOUT))
            if socks.get(self.client) == zmq.POLLIN:
                reply = self.client.recv()
                if not reply:
                    break
                else:
                    expect_reply = False
                    self.client.setsockopt(zmq.LINGER, 0)
                    self.client.close()
                    self.poll.unregister(self.client)
                    self._make_client()
            else:
                expect_reply = False
                self.client.setsockopt(zmq.LINGER, 0)
                self.client.close()
                self.poll.unregister(self.client)
                self._make_client()

    def _handle_queue(self):
        while True:
            # Send a message from the message queue
            try:
                qitem = self.msg_queue.get(timeout=1)

                # First check for termnation
                if qitem is _TERMINATION_MARKER:
                    break

                # We've not been asked to terminate, so send
                # the message.
                self._send_request(qitem)

            except queue.Empty:
                pass

    def keep_display_alive_until(self, until_timestamp):
        """Keeping the display alive until a certain time.

        :param integer until_timestamp: the time to keep this display on
            until (a unix timestamp).

        """
        until_log = datetime.fromtimestamp(until_timestamp).strftime(
            '%Y-%m-%d %H:%M:%S'
        )
        log.debug("Keep display alive until: {}".format(until_log))
        message = DISPLAY_ON_XML.format(timestamp=until_timestamp)
        self.msg_queue.put_nowait(message)

    def keep_display_alive_duration(self, duration):
        """Keeping the display alive for a certain duration.

        :param duration: duration in seconds.
        :type duration: integer, OR float.

        """
        now = time.time()
        self.keep_display_alive_until(now + duration)
