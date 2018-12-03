# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


"""Render a movie on the Darwin platform via VLC"""


# Standard library imports
import logging

# Third party imports
import AppKit
import Foundation
from PyObjCTools import AppHelper
import objc

# "Local" third party imports
from includes import libvlc

# Local (Yarely) imports
from yarely.darwin.common.content.rendering import Renderer
from yarely.darwin.common.window import BaseWindow
from yarely.darwin.common.window.layout import XYWidthHeightLayoutDelegate
from yarely.darwin.common.window.presentation import FadingPresentationDelegate
from yarely.darwin.helpers.execution import application_loop


log = logging.getLogger(__name__)


APPLICATION_DESCRIPTION = "Render a movie on the Darwin platform via VLC"


class VLCRenderer(Renderer):
    """FIXME."""

    def _handle_reply_params(self, msg_root, msg_elem):
        """A fudge until the Renderer Manager is in place."""
        super()._handle_reply_params(msg_root, msg_elem)

        self.uri = self.params['uri']

        log.info("URI is '{uri}'".format(uri=self.uri))
        AppHelper.callAfter(self.handle_prepare)

    def do_prepare(self):
        """Prepare an item of content for display."""

        window = VLCWindow.alloc().init()
        window.set_presentation_delegate(FadingPresentationDelegate())
        self.set_window(window)

        self.vlc_view = AppKit.NSView.alloc().initWithFrame_(
                Foundation.NSZeroRect)

        self.vlc_instance = libvlc.Instance(b"vlc", b"--no-video-title-show")
        self.vlc_media = self.vlc_instance.media_new(self.uri)

        self.vlc_player = self.vlc_instance.media_player_new()
        self.vlc_player.set_media(self.vlc_media)
        self.vlc_player.set_nsobject(objc.pyobjc_id(self.vlc_view))
        self.vlc_player.video_set_deinterlace(b"interlaced")

        # This doesn't really belong here...
        if (
            "layout_style" in self.params and
            self.params["layout_style"] == "x_y_width_height"
        ):
            layout_delegate = XYWidthHeightLayoutDelegate(
                    int(self.params["layout_x"]),
                    int(self.params["layout_y"]),
                    int(self.params["layout_width"]),
                    int(self.params["layout_height"]))
            self.get_window().set_layout_delegate(layout_delegate)

        self.get_window().setContentView_(self.vlc_view)

        # Make the background black
        background_nscolour = AppKit.NSColor.\
            colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, 1)
        self.get_window().setBackgroundColor_(background_nscolour)

    def do_became_visible(self):
        """FIXME."""
        self.get_window().lock_level()
        self.vlc_player.play()


class VLCWindow(BaseWindow):
    def init(self):
        self.level_locked = False
        self = super().init()
        return self

    def setLevel_(self, windowLevel):
        """FIXME.

        :param windowLevel: FIXME.
        :type windowLevel: FIXME.

        """
        if not self.level_locked:
            super().setLevel_(windowLevel)

    def lock_level(self):
        """FIXME."""
        self.level_locked = True

if __name__ == "__main__":
    application_loop(VLCRenderer, description=APPLICATION_DESCRIPTION)
