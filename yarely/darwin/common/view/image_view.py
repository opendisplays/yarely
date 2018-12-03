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
import Foundation
import objc

# Local (Yarely) imports
# from yarely.core.helpers.decorators import log_exception


log = logging.getLogger(__name__)


class CenteredImageView(AppKit.NSView):
    """Provide an NSView that scales and draws a supplied image."""
    def initWithImage_scale_(self, image, scale):
        """Designated initializer for CenteredImageView.

        :param image: FIXME.
        :type image: an :class:`NSImage` instance.
        :param float scale: describes how to scale the image.
            A scale value of 1 will fill the view with the image without
            cropping.
            A scale value of 0.5 will fill the centre half of the view.
            A scale value of 2 will the view with the centre half of the image.
            A scale value of zero or negative will not scale the image.
        :rtype: :class:`CenteredImageView`
        :return: FIXME.

        """

        frame_rect = Foundation.NSRect((0, 0), (0, 0))
        self = objc.super(CenteredImageView, self).initWithFrame_(frame_rect)

        self._image = image
        self._scale = scale

        return self

    # @log_exception(log)
    def drawRect_(self, dirty_rect):
        """Draw the image.

        :param dirty_rect: FIXME.
        :type dirty_rect: FIXME.

        """
        scaled_rect = self._calculateImageScalingRect()
        self._image.drawInRect_fromRect_operation_fraction_(
            scaled_rect, Foundation.NSZeroRect, AppKit.NSCompositeCopy, 1.0
        )

    def _calculateImageScalingRect(self):
        """Provide an NSRect describing the position and size of the image."""

        view_rect = self.frame()
        image_size = self._image.size()

        view_size = view_rect.size
        view_width = view_size.width
        view_height = view_size.height

        image_width = image_size.width
        image_height = image_size.height

        if self._scale > 0:
            # Scale the image relative to our frame (scale == 1 means fill
            # the frame with image).
            width_scale = view_width / image_width
            height_scale = view_height / image_height

            frame_scale = min(width_scale, height_scale)

            resulting_width = (image_width * frame_scale) * self._scale
            resulting_height = (image_height * frame_scale) * self._scale

        else:
            # Don't scale the image - use the source size.
            resulting_width = image_width
            resulting_height = image_height

        scaled_rect = Foundation.NSRect()

        scaled_rect.size.width = resulting_width
        scaled_rect.size.height = resulting_height

        scaled_rect.origin.x = (view_width - resulting_width) / 2
        scaled_rect.origin.y = (view_height - resulting_height) / 2

        log.debug("Scaled image rect: {rect}".format(rect=scaled_rect))

        return scaled_rect
