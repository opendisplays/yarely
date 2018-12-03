# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


"""Yarely execution control module with Cocoa specialisms"""


# Standard library imports
import logging
import os
import signal

# Third party imports
import AppKit
import Foundation
from PyObjCTools import AppHelper
import objc


log = logging.getLogger(__name__)


def application_loop(concrete, *args, **kwargs):
    """Main entry point - creates a new Application instance (whose specific
    implementation is provided by concrete) and starts execution. Listens
    for SIGINT and SIGTERM signals, posting a Cocoa termination notification
    when they are received.

    For use by modules containing classes that extend
    yarely.core.helpers.base_classes.Application that need to use
    the Cocoa event loop system.

    :param class concrete: a subclass of Application.

    """
    application = concrete(*args, **kwargs)   # Instantiate the concrete class

    signal_observer = _install_cocoa_signal_observer()

    def _sigterm(signum, frame):
        """SIGTERM handler, attempt a clean termination."""
        _terminate('SIGTERM')

    def _sigint(signum, frame):
        """SIGINT handler, attempt a clean termination."""
        _terminate('SIGINT')

    def _terminate(cause):
        """Attempt a clean termination logging the cause."""
        log.info('Termination from {cause}'.format(cause=cause))
        AppHelper.callAfter(
            AppKit.NSApplication.sharedApplication().terminate_,
            signal_observer
        )

    signal.signal(signal.SIGTERM, _sigterm)
    signal.signal(signal.SIGINT, _sigint)

    application.process_arguments()
    application.start()
    AppHelper.runEventLoop()

# The Cocoa signal observer ensures that Python is awakened from the RunLoop
# when a signal arrives.  The signal is processed by Python's C implementation
# and added to the interpreter's stack of operations to perform once the
# current operation on the main thread completes and control is handed back
# to native Python code.  The Cocoa observer ensures control passes back to a
# native Python method quickly - the signal will be delivered just before
# _SignalFDObserver.readCompletionNotification_ is called.
#
# Because the signal arrives just before readCompletionNotification_ is called
# we cannot catch an exception caused by a signal (such as KeyboardInterrupt).
# Therefore we handle SIGINT manually above.


def _install_cocoa_signal_observer():
    """Install and return the Cocoa signal observer."""
    signal_pipe_r, signal_pipe_w = os.pipe()
    signal_observer = _SignalFDObserver.alloc().\
        initWithFileDescriptor_(signal_pipe_r)

    # FIXME below is a workaround for buggy Python 3.5
    # Otherwise it was giving an "ValueError: the fd X must be in
    # non-blocking mode" error when calling set_wakeup_fd on line 78 when
    # starting the facade.
    import fcntl
    fcntl.fcntl(signal_pipe_w, fcntl.F_SETFL, os.O_NONBLOCK)
    # End of workaround.

    signal.set_wakeup_fd(signal_pipe_w)
    signal_observer.registerForNotifications()
    return signal_observer


class _SignalFDObserver(AppKit.NSObject):
    def initWithFileDescriptor_(self, fd):
        """Designated initializer for _SignalFDObserver.

        :param fd: FIXME.
        :type fd: an integer file descriptor.
        :rtype: :class:`_SignalFDObserver`

        """
        self = objc.super(_SignalFDObserver, self).init()
        self._file_handle = Foundation.NSFileHandle.alloc().\
            initWithFileDescriptor_closeOnDealloc_(fd, True)
        return self

    def registerForNotifications(self):
        """Register for notification of read events on the file descriptor."""
        notification_center = Foundation.NSNotificationCenter.defaultCenter()
        notification_center.addObserver_selector_name_object_(
            self, "readCompletionNotification:",
            Foundation.NSFileHandleReadCompletionNotification,
            self._file_handle
        )
        self._file_handle.readInBackgroundAndNotify()

    def readCompletionNotification_(self, notification):
        """Called by the notification center to ensure native Python is
        executed shortly after a signal is delivered.

        Repeat the read operation to handle the next signal.

        :param notification: FIXME.
        :type notification: FIXME.

        """
        self._file_handle.readInBackgroundAndNotify()
