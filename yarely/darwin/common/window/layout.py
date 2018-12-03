# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


# Third party imports
import AppKit
import Foundation


class LayoutDelegate(object):
    """FIXME."""
    def layout_window(self, window):
        """Position the window on screen.

        Subclasses should implement this method.

        :param window: FIXME.
        :type window: FIXME.

        """
        raise NotImplementedError()


class FullscreenLayoutDelegate(LayoutDelegate):
    """FIXME."""
    def layout_window(self, window):
        """Position the window to cover the whole screen.

        :param window: FIXME.
        :type window: FIXME.

        """
        screen = AppKit.NSScreen.mainScreen()
        screen_rect = screen.frame()

        frame_rect = window.frameRectForContentRect_(screen_rect)

        window.setFrame_display_(frame_rect, False)


class XYWidthHeightLayoutDelegate(LayoutDelegate):
    """FIXME."""
    def __init__(self, x, y, width, height):
        """

        :param int x: FIXME.
        :param int y: FIXME.
        :param int width: the required window width.
        :param int height: the required window height.

        """
        super().__init__()

        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def layout_window(self, window):
        """Position the window at the provided coordinates.

        :param window: FIXME.
        :type window: FIXME.

        """

        point = Foundation.NSPoint(self.x, self.y)
        size = Foundation.NSSize(self.width, self.height)
        content_rect = Foundation.NSRect(point, size)

        frame_rect = window.frameRectForContentRect_(content_rect)

        window.setFrame_display_(frame_rect, False)
