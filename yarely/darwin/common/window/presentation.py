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


# _retained_objects holds a selection of NSObject instances that we are
# manually retaining until the completion delegate completes.  The key is a
# completion delegate instance whilst the value is a (Python) list of
# (Python) NSObject instances. Once the delegate completes it will remove its
# entry, automatically releasing the appropriate NSObject instances.
_retained_objects = {}


class PresentationDelegate(object):
    """A base class for presentation delegates."""
    def __init__(self):
        self._visible = False

    def become_visible(self, window, callback):
        """Make the window visible.

        callback(window) is called once the window is visible.

        If the window is currently visible (or in the process of becoming so),
        callback immediately.

        :param window: FIXME.
        :type window: FIXME.
        :param callback: FIXME.
        :type callback: a callable.

        """
        if self._visible:
            log.debug("Window already visible. Bug in caller?")
            callback(window)

        self._visible = True
        self._become_visible(window, callback)

    def _become_visible(self, window, callback):
        """Make the window visible.

        callback(window) is called once the window is visible.

        Subclasses should implement this method, which is only called after
        ensuring the window is not already visible.

        :param window: FIXME.
        :type window: FIXME.
        :param callback: FIXME.
        :type callback: a callable.
        :raises NotImplementedError: always.

        """
        raise NotImplementedError()

    def become_invisible(self, window, callback):
        """Make the window invisible.

        callback(window) is called once the window is visible.

        If the window is currently visible (or in the process of becoming so),
        callback immediately.

        :param window: FIXME.
        :type window: FIXME.
        :param callback: FIXME.
        :type callback: a callable.

        """
        if not self._visible:
            log.debug("Window already invisible. Bug in caller?")
            callback(window)

        self._visible = False
        self._become_invisible(window, callback)

    def _become_invisible(self, window, callback):
        """Make the window invisible.

        callback(window) is called once the window is invisible.

        Subclasses should implement this method, which is only called after
        ensuring the window is not already invisible.

        :param window: FIXME.
        :type window: FIXME.
        :param callback: FIXME.
        :type callback: a callable.
        :raises NotImplementedError: always.

        """
        raise NotImplementedError()


class DefaultPresentationDelegate(PresentationDelegate):
    """A simple presentation delegate with no bells or whistles."""
    def become_visible(self, window, callback):
        """Make the window visible immediately.

        callback(window) is called once the window is visible.

        :param window: FIXME.
        :type window: FIXME.
        :param callback: FIXME.
        :type callback: a callable.

        """
        window.makeKeyAndOrderFront_(self)
        callback(window)

    def become_invisible(self, window, callback):
        """Make the window invisible immediately.

        callback(window) is called once the window is invisible.

        :param window: FIXME.
        :type window: a :class:`BaseWindow` instance.
        :param callback: FIXME.
        :type callback: a callable.

        """
        window.close()
        callback(window)


class AnimationCompletionDelegate(AppKit.NSObject):
    """Provide an NSAnimation Delegate that runs a callback once completed."""
    def initWithWindow_callback_(self, window, callback):
        """Designated initializer for AnimationCompletionDelegate.

        :param window: FIXME.
        :type window: a :class:`BaseWindow` instance.
        :param callback: will be called on animation completion.
        :type callback: a callable.
        :rtype: :class:`AnimationCompletionDelegate`
        :return: FIXME.

        """

        self = objc.super(AnimationCompletionDelegate, self).init()

        self.window = window
        self.callback = callback

        return self

    def _complete(self):
        """Handle a completion message by calling callback(window)."""
        self.callback(self.window)
        del _retained_objects[self]

    # @log_exception(log)
    def animationDidStop_(self, animation):
        """Handle an animation stop event.

        :param animation: FIXME.
        :type animation: FIXME.

        """
        self._complete()

    # @log_exception(log)
    def animationDidEnd_(self, animation):
        """Handle an animation end event.

        :param animation: FIXME.
        :type animation: FIXME.

        """
        self._complete()


class FadingPresentationDelegate(PresentationDelegate):
    """A presentation delegate that gently fades the window in and out."""
    def perform_animation(self, window, effect_key, callback):
        """Animate window, calling callback on completion.

        :param window: a BaseWindow instance to be animated.
        :type window: a :class:`BaseWindow` instance.
        :param effect_key: the animation effect.
        :type effect_key: FIXME.
        :param callback: will be called on animation completion.
        :type callback: a callable.

        """
        view_animations = ({
            AppKit.NSViewAnimationTargetKey: window,
            AppKit.NSViewAnimationEffectKey: effect_key
        },)

        view_animations_nsarray = AppKit.NSArray.alloc().initWithArray_(
            view_animations
        )

        ns_view_animation = AppKit.NSViewAnimation.alloc()\
            .initWithViewAnimations_(view_animations_nsarray)

        animation_delegate = AnimationCompletionDelegate.alloc()\
            .initWithWindow_callback_(window, callback)

        objects_to_retain = []
        _retained_objects[animation_delegate] = objects_to_retain

        ns_view_animation.setDuration_(0.8)

        ns_view_animation.setDelegate_(animation_delegate)
        ns_view_animation.startAnimation()

    def _become_visible(self, window, callback):
        """Make the window visible by fading it in.

        callback(window) is called once the window is visible.

        :param window: FIXME.
        :type window: FIXME.
        :param callback: FIXME.
        :type callback: a callable.

        """
        window.setAlphaValue_(0)
        window.makeKeyAndOrderFront_(self)

        self.perform_animation(
            window, AppKit.NSViewAnimationFadeInEffect, callback
        )

    def _become_invisible(self, window, callback):
        """Make the window invisible by fading it out.

        callback(window) is called once the window is invisible.

        :param window: FIXME.
        :type window: FIXME.
        :param callback: FIXME.
        :type callback: a callable.

        """
        self.perform_animation(
            window, AppKit.NSViewAnimationFadeOutEffect, callback
        )
