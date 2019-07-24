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
import os
import subprocess
import termios
import threading
import time
from xml.etree import ElementTree

# Third party imports
import zmq

# Local (Yarely) imports
from yarely.core.helpers.base_classes import ApplicationWithConfig
from yarely.core.helpers.base_classes.zmq_rpc import ZMQRPC
from yarely.core.helpers.execution import application_loop
from yarely.core.helpers.zmq import (
    ZMQ_ADDRESS_INPROC, ZMQ_DISPLAYCONTROLLER_REP_PORT, ZMQ_ADDRESS_LOCALHOST,
    ZMQ_SOCKET_LINGER_MSEC
)
from yarely.core.includes.phemelibrary import PhemeAnalytics


log = logging.getLogger(__name__)

SUBPROCESS_CHECKIN_INTERVAL = 1        # Seconds
_TERMINATION_MARKER = object()
QUEUE_TIMEOUT = 1                      # Seconds
WARN_NO_REPLY = 'Expected reply from Scheduler not received.'
DISPLAY_STATE_POLLING_FREQ = 3  # Seconds

# FIXME path
DISPLAY_DEVICE_DIRECTORY = os.path.abspath(__file__)[
    :-len('display_controller.py')
]
DISPLAY_DEVICE_DRIVER_SUFFIX = '_display_device.py'
DISPLAY_IS_ON = "IS_ON"
DISPLAY_IS_OFF = "IS_OFF"
DISPLAY_UNKNOWN_STATE = "UNKNOWN_STATE"

LINESPEED_DISPLAY = termios.B9600
# FIXME
ZMQ_SCHEDULER_ADDR = ZMQ_ADDRESS_LOCALHOST.format(
    port=ZMQ_DISPLAYCONTROLLER_REP_PORT
)


class DisplayControllerError(Exception):
    """Base class for display controller errors"""
    pass


class DisplayController(threading.Thread):
    """ Starts a thread that can send power commands to the display
    asynchronously.

    """
    def __init__(
            self, display_serial, analytics_tracking_id, display_type='sony'
    ):
        """
        :param display_serial: FIXME.
        :type display_serial: FIXME.
        :param analytics_tracking_id: FIXME.
        :type analytics_tracking_id: FIXME.
        :param display_type: FIXME.
        :type display_type: FIXME.

        """
        threading.Thread.__init__(self)
        self.daemon = True
        self.analytics = PhemeAnalytics(analytics_tracking_id)
        self.display_type = display_type
        self.display_power_status = None
        self.recvd_change = threading.Event()
        self.display_serial = display_serial
        self.update_display_power_status()
        self.keep_display_on_until = time.time() + 7

    def _get_args_for_display_device(self):
        display_device_path = os.path.join(
            DISPLAY_DEVICE_DIRECTORY,
            self.display_type + DISPLAY_DEVICE_DRIVER_SUFFIX
        )
        return ['python3', display_device_path]

    def _intended_display_power_status(self):
        now = time.time()
        diff = self.keep_display_on_until - now
        if diff > 0:
            return DISPLAY_IS_ON
        return DISPLAY_IS_OFF

    def _turn_display(self, new_state='ON'):
        log.debug("Turning display {}".format(new_state))
        args = self._get_args_for_display_device()
        args += [new_state, self.display_serial]
        subprocess.call(args)
        self.update_display_power_status()

    def _turn_off(self):
        """Send turn off command to the display immediately. """
        self._turn_display('OFF')

    def _turn_on(self):
        """Send turn on command to the display immediately. """
        self._turn_display('ON')

    def run(self):
        while True:
            # Find out what the power status should be
            power_state_should_be = self._intended_display_power_status()

            # Update display_is_on to real power state of display
            self.update_display_power_status()

            log.debug(
                "Display status should be {}".format(power_state_should_be)
            )
            log.debug(
                "Display status is {}".format(self.display_power_status)
            )

            # If the power status matches, wait and continue
            if self.display_power_status == power_state_should_be:
                self.recvd_change.wait(DISPLAY_STATE_POLLING_FREQ)
                continue

            # Set the appropriate display power status in case it doesn't match
            if power_state_should_be == DISPLAY_IS_ON:
                self._turn_on()
            else:
                self._turn_off()

            # Sleep until the next check...
            self.recvd_change.wait(DISPLAY_STATE_POLLING_FREQ)
            self.recvd_change.clear()

    def update_display_power_status(self):
        """Update the internal display state variable (display_is_on)."""

        # Build a set of args to pass to subprocess
        args = self._get_args_for_display_device()
        args += ['GET_POWER_STATUS', self.display_serial]

        # Make the subprocess call -- note that a non-zero exit status will
        # trigger a CalledProcessError.
        try:
            process_output = subprocess.check_output(args)

        except subprocess.CalledProcessError as err:
            log.error(
                'Failed to communicate with display.'
                'Command was {cmd}, exit code is {status}.'.format(
                    cmd=err.cmd, status=err.returncode
                )
            )
            # Stop here if we can't get a connection to the display anyway.
            self.display_power_status = DISPLAY_UNKNOWN_STATE
            return

        # Decode the byte string read from the subprocess call
        process_output = process_output.decode("utf-8").rstrip()

        # Check to see if the current display state is different to previous
        # state.
        new_display_state = process_output
        old_display_state = self.display_power_status

        # We only report back the power status if it has actually changed.
        if new_display_state != old_display_state:
            self.display_power_status = new_display_state
            self.analytics.track_event_async(
                category='display power status', action=process_output,
                value=None
            )

    def update_keep_display_on_until(self, until):
        """FIXME.

        :param until: the time to keep this display on until (a unix
            timestamp).
        :type until: integer, OR float.

        """
        self.keep_display_on_until = until
        logging.debug("Updated keep_display_on_until to {}".format(until))


class DisplayControllerReceiver(ApplicationWithConfig, ZMQRPC):
    """Creates a socket to receive commands from Scheduler Manager."""

    def __init__(self):
        super().__init__('DisplayControllerReceiver')
        self.connection_requests = dict()
        self.display_controller = None
        self.display_type = None
        self.zmq_display_term_identifier = "display_term_{id}".format(
            id=id(self)
        )
        self.zmq_context = zmq.Context()
        self._zmq_scheduler_reply_thread = None

    def _handle_arguments(self, args):
        """Handle arguments received from the argument parser."""
        super()._handle_arguments(args)

        # The device display serial
        self.display_device_serial = self.config.get(
            'DisplayDevice', 'DisplayDeviceSerialUSBName', fallback=None
        )

        # Read Analytics Tracking ID
        self.analytics_tracking_id = self.config.get(
            'Analytics', 'tracking_id', fallback=None
        )

    def _handle_request_display_on(self, msg_root, msg_elem):
        """Update incoming 'until' attribute and pass it through to the
        display controller.

        """
        until_timestamp = float(msg_elem.attrib['until'])
        logging.debug(
            "Received ZMQ request to keep display on until {}".format(
                until_timestamp
            )
        )
        self.display_controller.update_keep_display_on_until(until_timestamp)
        return self._encapsulate_reply(self._generate_pong())

    def _handle_incoming_zmq(self):
        """Executes in separate thread: _zmq_req_to_scheduler_thread."""

        # Initialise ZMQ reply socket to scheduler
        zmq_scheduler_reply_socket = self.zmq_context.socket(zmq.REP)
        zmq_scheduler_reply_socket.setsockopt(
            zmq.LINGER, ZMQ_SOCKET_LINGER_MSEC
        )
        zmq_scheduler_reply_socket.bind(ZMQ_SCHEDULER_ADDR)

        # Initialise ZMQ reply socket to watch for termination
        zmq_termination_reply_socket = self.zmq_context.socket(zmq.REP)
        zmq_termination_reply_socket.bind(
            ZMQ_ADDRESS_INPROC.format(
                identifier=self.zmq_display_term_identifier
            )
        )

        # Initialise ZMQ poller to watch REP sockets
        zmq_poller = zmq.Poller()
        zmq_poller.register(zmq_scheduler_reply_socket, zmq.POLLIN)
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
                    log().warning("No reply generated, replying with error!")
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
        zmq_poller.unregister(zmq_scheduler_reply_socket)
        zmq_poller.unregister(zmq_termination_reply_socket)
        zmq_scheduler_reply_socket.close()
        zmq_termination_reply_socket.close()

    def _initialise_display_controller(self):
        self.display_controller = DisplayController(
            self.display_device_serial, self.analytics_tracking_id,
            self.display_type
        )
        self.display_controller.start()

    def _initialise_display_type(self):
        try:
            device_type = self.config.get(
                'DisplayDevice', 'DeviceType', fallback='sony'
            )
            self.display_type = device_type
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass

    def start(self):
        """The main execution method for this application."""

        # First we have to initialise the display type before we initialise
        # the display controller! The second needs the display type.
        self._initialise_display_type()
        self._initialise_display_controller()

        # Now lets start ZMQ
        self._zmq_scheduler_reply_thread = threading.Thread(
            target=self._handle_incoming_zmq
        )
        t_name = 'ZMQ reply socket monitor'
        self._zmq_scheduler_reply_thread.name = t_name
        self._zmq_scheduler_reply_thread.daemon = True
        self._zmq_scheduler_reply_thread.start()

    def stop(self):
        """Application termination cleanup."""
        # Terminate ZMQ-related threads
        zmq_termination_request_socket = self.zmq_context_req.socket(zmq.REP)
        zmq_termination_request_socket.setsockopt(
            zmq.LINGER, ZMQ_SOCKET_LINGER_MSEC
        )
        zmq_termination_request_socket.connect(
            ZMQ_ADDRESS_INPROC.format(
                identifier=self.zmq_display_term_identifier
            )
        )
        zmq_termination_request_socket.send_unicode('TERMINATE')
        zmq_termination_request_socket.close()
        self._zmq_scheduler_reply_thread.join()

        super().stop()
        self.zmq_context_req.term()


if __name__ == "__main__":
    application_loop(DisplayControllerReceiver)
