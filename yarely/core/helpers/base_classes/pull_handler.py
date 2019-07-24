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
import time
from threading import Timer


# Local (Yarely) imports
from yarely.core.helpers import conversions
from yarely.core.helpers.base_classes import Handler, HandlerError


log = logging.getLogger(__name__)

# There's no point continually retrying if the file source or the zmq
# server has gone away. The DEFAULT_WINDOW is the initial time period
# (in seconds) to wait before a retry after the first failure. The
# actual window used will increase with each successive failure (see
# PullHandler._fail()).
DEFAULT_WINDOW = 60                # Seconds
DEFAULT_REFRESH_RATE = '1 HOUR'


class PullHandlerError(HandlerError):
    """Base class for pull handler errors."""
    pass


class PullHandler(Handler):
    """Base class for pull-based handlers (i.e. those that reload something
    at a specified refresh rate).

    In the event that the pull operation fails to complete, the handler will
    wait for a backoff period (window) before retrying the operation.
    The initial (default) value of the window is specified by DEFAULT_WINDOW,
    the actual backoff in each failure case is twice the last backoff (the
    backoff is reset to the default value as soon as an operation completes
    successfully. In no case will the backoff period exceed the specified
    refresh rate - once the backoff window reaches the refresh rate, there
    are no further increases to the backoff period.

    """

    def __init__(self, description):
        super().__init__(description)
        self.last_read = None
        self.read_timer = None
        self.window = DEFAULT_WINDOW

    def _handle_reply_params(self, msg_root, msg_elem):
        super()._handle_reply_params(msg_root, msg_elem)
        try:
            self.set_refresh_rate(self.params['refresh'])
        except KeyError:
            self.set_refresh_rate(DEFAULT_REFRESH_RATE)
        self.start_read_timer(0.1)        # Near-immediate read

    def _fail(self, cause):
        self.window = min(self.window * 2, self.refresh_rate)
        self.start_read_timer(self.window)
        log.warning(cause)

    def _success(self):
        self.last_read = time.time()
        self.window = DEFAULT_WINDOW
        self.start_read_timer(self.refresh_rate)

    def set_refresh_rate(self, refresh_rate):
        """Set the refresh rate for this handler.

        :param refresh_rate: a time interval string. E.g. "1 SECOND",
            "2 MINUTES".

        """
        try:
            # Internally we'll always store the refresh rate as a number
            # of seconds.
            self.refresh_rate = conversions.time_interval_in_seconds(
                                refresh_rate)
        except conversions.ConversionError as e:
            msg = 'Could not parse refresh rate "{rate}"'
            raise PullHandlerError(msg.format(rate=refresh_rate)) from e

        # Reset the read timer to reflect the new rate
        #
        # NOTE - if we were previously in the failure state the next
        # check will now come round too quickly. This could be FIXMEd in
        # a subsequent version but it's not not important enough right
        # now.
        if self.read_timer:
            now = time.time()
            due = self.last_read + self.refresh_rate
            if due <= now:
                self.start_read_timer(0.1)        # Near-immediate read
            else:
                self.start_read_timer(due - now)

    def start_read_timer(self, timer_duration):
        """Start a timer for the given period (in seconds). Once the
        timer expires, call self.read().

        :param float timer_duration: the time to wait before calling
            self.read().

        """
        if self.read_timer:
            self.read_timer.cancel()
        self.read_timer = Timer(timer_duration, self.read)
        self.read_timer.start()
