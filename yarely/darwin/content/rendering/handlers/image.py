# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


"""Render an image on the Darwin platform."""

# Standard library imports
import logging

# Third party imports
import AppKit
from PyObjCTools import AppHelper

# Local (Yarely) imports
from yarely.darwin.common.content.rendering import Renderer, PREPARATION_FAILED
from yarely.darwin.common.view.image_view import CenteredImageView
from yarely.darwin.common.window.layout import XYWidthHeightLayoutDelegate
from yarely.darwin.helpers.execution import application_loop


log = logging.getLogger(__name__)


APPLICATION_DESCRIPTION = "Render an image on the Darwin platform"


class ImageRenderer(Renderer):
    """FIXME."""

    def _handle_reply_params(self, msg_root, msg_elem):
        """A fudge until the Renderer Manager is in place."""
        super()._handle_reply_params(msg_root, msg_elem)
        self.image_path = self.params['path']
        msg = "Image path is '{image_path}'"
        log.info(msg.format(image_path=self.image_path))
        AppHelper.callAfter(self.handle_prepare)

    def do_prepare(self):
        """Prepare an item of content for display."""
        image = AppKit.NSImage.alloc().initWithContentsOfFile_(self.image_path)
        if image is None:
            # Give up if the image hasn't loaded.
            return PREPARATION_FAILED

        self.view = CenteredImageView.alloc().initWithImage_scale_(
                image, 1)

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

        self.get_window().setContentView_(self.view)

        # Make the background black
        background_nscolour = AppKit.NSColor.\
            colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, 1)
        self.get_window().setBackgroundColor_(background_nscolour)


if __name__ == "__main__":
    application_loop(ImageRenderer, description=APPLICATION_DESCRIPTION)
