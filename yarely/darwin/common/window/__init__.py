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
import objc

# Local (Yarely) imports
from yarely.darwin.common.window.presentation import (
    DefaultPresentationDelegate
)
from yarely.darwin.common.window.layout import FullscreenLayoutDelegate


DEFAULT_WINDOW_LEVEL = AppKit.NSPopUpMenuWindowLevel - 1


class BaseWindow(AppKit.NSWindow):
    """A base class for Windows that support a presentation delegate."""
    _presentation_delegate = DefaultPresentationDelegate()
    _layout_delegate = FullscreenLayoutDelegate()

    def init(self):
        """
        :rtype: :class:`BaseWindow`

        """
        self = objc.super(
            BaseWindow, self
        ).initWithContentRect_styleMask_backing_defer_(
            Foundation.NSZeroRect, AppKit.NSBorderlessWindowMask,
            AppKit.NSBackingStoreBuffered, True
        )
        self.setLevel_(DEFAULT_WINDOW_LEVEL)
        return self

    @objc.python_method
    def set_presentation_delegate(self, presentation_delegate):
        """Replace the presentation delegate.

        :param presentation_delegate: FIXME.
        :type presentation_delegate: FIXME.

        """
        self._presentation_delegate = presentation_delegate

    @objc.python_method
    def set_layout_delegate(self, layout_delegate):
        """Replace the layout delegate.

        :param layout_delegate: FIXME.
        :type layout_delegate: FIXME.

        """
        self._layout_delegate = layout_delegate

    @objc.python_method
    def set_level_increase(self, level_increase):
        """ Increase the (default) window level by `level_increase`.

        :param level_increase: FIXME.

        """
        self.setLevel_(DEFAULT_WINDOW_LEVEL + level_increase)

    @objc.python_method
    def become_visible(self, callback):
        """Ask the layout delegate to position the window, then ask the
        presentation delegate to make the window visible.

        callback will be called with no arguments once the window is visible.

        :param callback: FIXME.
        :type callback: a callable.

        """
        self._layout_delegate.layout_window(self)
        self._presentation_delegate.become_visible(self, callback)

    @objc.python_method
    def become_invisible(self, callback):
        """Ask the presentation delegate to make the window invisible.

        callback will be called with no arguments once the window is invisible.

        :param callback: FIXME.
        :type callback: a callable.

        """
        self._presentation_delegate.become_invisible(self, callback)
