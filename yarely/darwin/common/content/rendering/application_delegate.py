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

# Third party imports
import AppKit
import objc

# Local (Yarely) imports
# from yarely.core.helpers.decorators import log_exception


log = logging.getLogger(__name__)


class RendererApplicationDelegate(AppKit.NSObject):
    def initWithRenderer_(self, renderer):
        """Designated initializer for RendererApplicationDelegate.

        :param renderer: FIXME.
        :type renderer: a :class:`Renderer` instance.
        :rtype: :class:`RendererApplicationDelegate`

        """
        self = objc.super(RendererApplicationDelegate, self).init()

        self._renderer = renderer
        self._terminating = False

        return self

    # NOQA  @log_exception(log)  # FIXME - decorator doesn't seem to pass thru `notification`?!
    def applicationDidFinishLaunching_(self, notification):
        """Handle an application finished launching event.

        :param notification: FIXME.
        :type notification: FIXME.

        """
        log.debug("applicationDidFinishLaunching:")
        self._renderer.cocoa_start()

    # @log_exception(log)   # FIXME - as above?
    def applicationShouldTerminate_(self, sender):
        """Handle a query as to whether the application should terminate.

        :param sender: FIXME.
        :type sender: FIXME.
        :rtype: FIXME

        """
        log.debug("applicationShouldTerminate:")

        # Safety - terminate immediately on the second request
        if self._terminating:
            msg = "Second termination request, terminating immediately"
            log.info(msg)
            AppKit.NSApplication.sharedApplication().\
                replyToApplicationShouldTerminate_(True)
            return AppKit.NSTerminateNow

        self._terminating = True

        # Make the content invisible before terminating to allow the
        # presentation animation to play.

        def became_invisible(window):
            log.debug("Window is invisible")
            log.info("Terminating")

            # Actually terminate
            AppKit.NSApplication.sharedApplication().\
                replyToApplicationShouldTerminate_(True)

        log.debug("Making window invisible")
        self._renderer.get_window().become_invisible(became_invisible)

        # Don't terminate quite yet - let the presentation animation
        # complete.
        return AppKit.NSTerminateLater
