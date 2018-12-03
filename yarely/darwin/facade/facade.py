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


"""Obscure the underlying OS desktop from view.

The facade opens a full-screen window with no visible controls or borders.
The window is filled with a background colour (optionally, an image is loaded
and scaled whilst keeping the aspect ratio.)

"""

# Standard library imports
import configparser
import logging

# Third party imports
import AppKit
import Foundation
from PyObjCTools import AppHelper
import objc

# Local (Yarely) imports
from yarely.core.helpers.base_classes import (
    ApplicationWithConfig, ApplicationConfigurationError
)
from yarely.core.helpers.colour import RGBColour
# from yarely.core.helpers.decorators import log_exception
from yarely.darwin.common.view.image_view import CenteredImageView
from yarely.darwin.common.window import BaseWindow
from yarely.darwin.common.window.presentation import FadingPresentationDelegate
from yarely.darwin.helpers.execution import application_loop


log = logging.getLogger(__name__)


FACADE_CONFIG_SECTION = "Facade"

FALLBACK_BACKGROUND_COLOUR = RGBColour("#E6A9EC")
"""
The fallback background colour is a pleasing pink.
This isn't black on purpose - it's not terribly offensive, but it makes it
visually clear that the configuration has not loaded.

"""
FALLBACK_IMAGE_SCALE = 1.0

APPLICATION_DESCRIPTION = "Obscure the desktop OS"


class FacadeView(CenteredImageView):
    """FIXME."""
    # @log_exception(log)
    def mouseDown_(self, the_event):
        """Terminate the application on mouse down.

        :param the_event: FIXME.
        :type the_event: FIXME.

        """
        AppKit.NSApplication.sharedApplication().terminate_(self)


class FacadeWindow(BaseWindow):
    """FIXME."""
    def init(self):
        """Designated initializer for FacadeWindow.
        :rtype: :class:`FacadeWindow`
        :return: the initialised :class:`FacadeWindow`.

        """
        self = objc.super(FacadeWindow, self).init()

        self.setLevel_(self.level() - 1)
        self.set_presentation_delegate(FadingPresentationDelegate())

        return self

    # @log_exception(log)
    def mouseDown_(self, the_event):
        """Terminate the application on mouse down.

        :param the_event: FIXME.
        :type the_event: FIXME.

        """
        AppKit.NSApplication.sharedApplication().terminate_(self)


class FacadeApplicationDelegate(AppKit.NSObject):
    """FIXME."""
    def initWithFacade_(self, facade):
        """Designated initializer for FacadeApplicationDelegate.

        :param facade: FIXME.
        :type facade: a :class:`Facade` instance.
        :rtype: :class:`FacadeApplicationDelegate`
        :return: FIXME.

        """
        self = objc.super(FacadeApplicationDelegate, self).init()

        self._facade = facade
        self._terminating = False

        return self

    # @log_exception(log)
    def applicationDidFinishLaunching_(self, notification):
        """Handle an application finished launching event.

        :param notification: FIXME.
        :type notification: FIXME.

        """
        log.debug("applicationDidFinishLaunching")
        self._facade.cocoa_start()

    # @log_exception(log)
    def applicationShouldTerminate_(self, sender):
        """Handle a request that the application terminate.

        :param sender: FIXME.
        :type sender: FIXME.
        :rtype: FIXME
        :return: FIXME.

        """
        log.debug("applicationShouldTerminate")

        # Safety - terminate immediately on the second request
        if self._terminating:
            msg = "Second termination request, terminating immediately"
            log.info(msg)
            self._facade.application.replyToApplicationShouldTerminate_(True)
            return AppKit.NSTerminateNow

        self._terminating = True

        # Make the content invisible before terminating to allow
        # the presentation animation to play.

        def became_invisible(window):
            log.debug("Window is invisible")
            log.info("Terminating")

            # Actually terminate
            self._facade.application.replyToApplicationShouldTerminate_(True)

        log.debug("Making window invisible")
        self._facade.window.become_invisible(became_invisible)

        # Don't terminate quite yet - let the presentation animation
        # complete.
        return AppKit.NSTerminateLater


class Facade(ApplicationWithConfig):
    """Main application.

    Transfers control into the Cocoa event loop.

    """
    def process_arguments(self):
        """Process the command line arguments."""
        try:
            super(Facade, self).process_arguments()
        except ApplicationConfigurationError:
            # Facade should continue using default values if loading the
            # configuration failed.
            self.config = None

    def start(self):
        self.application = AppKit.NSApplication.sharedApplication()
        delegate = FacadeApplicationDelegate.alloc().initWithFacade_(self)
        self.application.setDelegate_(delegate)
        AppHelper.runEventLoop()

    def cocoa_start(self):
        """Instantiate & configure the required screens, windows & views."""
        # Default values in case initialising or parsing configuration fails
        self._image_path = None
        self._image_scale = None
        self._background_colour = None
        self._image = None

        if self.config is not None:
            self._process_config(self.config)

        self._log_initial_configuration()

        self.window = FacadeWindow.alloc().init()

        self._load_image()

        self._set_background_colour()

        if self._image is not None and self._image_scale is None:
            self._image_scale = FALLBACK_IMAGE_SCALE

        self._log_computed_configuration()

        if self._image is not None:
            self.view = FacadeView.alloc().initWithImage_scale_(
                    self._image, self._image_scale)
            self.window.setContentView_(self.view)

        # Activate the application so that it can control the mouse cursor's
        # visibility (and then hide the cursor)
        self.application.activateIgnoringOtherApps_(True)
        AppKit.NSCursor.hide()

        def became_visible(window):
            """Callback when window becomes visible."""
            log.debug("Window is visible")

        log.info("Ready")
        log.debug("Making window visible")
        self.window.become_visible(became_visible)

    def _process_config(self, config):
        """Update our configuration from a YarelyConfig instance"""
        try:
            self._image_path = config.get(FACADE_CONFIG_SECTION, "ImagePath")
        except configparser.NoOptionError:
            # It's ok not to specify a value..
            pass
        except Exception:
            # ..but if it's specified and broken somehow, log a warning
            msg = "Failed to get valid configuration item 'ImagePath'"
            log.exception(msg)

        try:
            self._background_colour = config.getcolour(
                    FACADE_CONFIG_SECTION, "BackgroundColour")
        except configparser.NoOptionError:
            # It's ok not to specify a value..
            pass
        except Exception:
            # ..but if it's specified and can't be parsed as a colour try
            # parsing as a pixel coord tuple (if image_path is set)

            if self._image_path is None:
                log.exception(
                    "Failed to get valid configuration item 'BackgroundColour'"
                )
            else:
                try:
                    self._background_colour = config.gettuple(
                        FACADE_CONFIG_SECTION, "BackgroundColour"
                    )
                except Exception:
                    # If it still can't be parsed, log a warning
                    log.exception(
                        "Failed to get valid configuration item "
                        "'BackgroundColour'"
                    )

        try:
            self._image_scale = config.getfloat(
                FACADE_CONFIG_SECTION, "ImageScale"
            )
        except configparser.NoOptionError:
            # It's ok not to specify a value..
            pass
        except Exception:
            # ..but if it's specified and broken somehow, log a warning
            msg = "Failed to get valid configuration item 'ImageScale'"
            log.exception(msg)

    def _log_initial_configuration(self):
        """Log the initial configuration."""
        log.info("Initial configuration:")
        self._log_configuration()

    def _log_computed_configuration(self):
        """Log the completed configuration."""
        log.info("Computed configuration:")
        self._log_configuration()

    def _log_configuration(self):
        """Log the configuration."""
        log.info("    Background colour: {background_colour!r}".format(
                background_colour=self._background_colour))
        log.info("    Image path: {image_path!r}".format(
                image_path=self._image_path))
        log.info("    Image scale: {image_scale!r}".format(
                image_scale=self._image_scale))

    def _load_image(self):
        """Load self._imath_path into self._image - an NSIMage."""
        if self._image_path is not None:
            self._image = AppKit.NSImage.alloc().initWithContentsOfFile_(
                    self._image_path)

            if self._image is None:
                log.error("Failed to load image")

                self._image_path = None
                self._image_scale = None
                # If image loading has failed, we can't get a background colour
                # from a pixel tuple.
                if isinstance(self._background_colour, tuple):
                    msg = (
                        "Unable to read background colour from image "
                        "(cause: image failed to load), using fallback "
                        "background colour"
                    )
                    log.warning(msg)
                    self._background_colour = None

        else:
            self._image_scale = None

    def _set_background_colour(self):
        """Set the background window's colour."""
        if isinstance(self._background_colour, tuple):
            background_colour_point = Foundation.NSPoint(
                    *self._background_colour)
            image_rep = self._image.representations()[0]
            pixel_colour = image_rep.colorAtX_y_(
                background_colour_point.x, background_colour_point.y
            )

            if pixel_colour is None:
                msg = (
                    "Unable to read background colour from image (cause: "
                    "Outside image boundaries?  Non-bitmap "
                    "representation?), using fallback background colour"
                )
                log.error(msg)
                self._background_colour = None

            else:
                # We have to pass Nones in because Cocoa modifies in place
                # and we have to stick to the call signature.  We don't care
                # about the alpha value.
                arithmetic_rgb = pixel_colour.getRed_green_blue_alpha_(
                    None, None, None, None
                )[:3]

                self._background_colour = RGBColour(arithmetic_rgb)

        if self._background_colour is None:
            self._background_colour = FALLBACK_BACKGROUND_COLOUR

        (r, g, b) = self._background_colour.as_arithmetic_triplet()
        background_nscolour = AppKit.NSColor.\
            colorWithCalibratedRed_green_blue_alpha_(r, g, b, 1)

        self.window.setBackgroundColor_(background_nscolour)


def main():
    """Called by __main__.py to execute the module."""
    application_loop(Facade, description=APPLICATION_DESCRIPTION)
