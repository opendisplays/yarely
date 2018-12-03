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
from xml.etree import ElementTree

# Third party imports
import AppKit
from PyObjCTools import AppHelper

# Local (Yarely) imports
from yarely.core.helpers.base_classes import Handler
# from yarely.core.helpers.decorators import log_exception
from yarely.darwin.common.content.rendering import RendererApplicationDelegate
from yarely.darwin.common.window import BaseWindow
from yarely.darwin.common.window.presentation import FadingPresentationDelegate


log = logging.getLogger(__name__)

# A few marker objects that do_prepare can return to highlight unusual events.
PREPARATION_NOT_YET_COMPLETE = object()
"""A marker object that `do_prepare()` can return to indicate that renderer
preparation is not yet completed.

"""
PREPARATION_FAILED = object()
"""A marker object that `do_prepare()` can return to indicate that renderer
preparation failed.

"""


class Renderer(Handler):
    """A specialisation of the Handler that provides a common base to
    Cocoa Renderers.

    This class maintains a window and handles commands from the Manager,
    subclasses should only need to implement do_prepare to apply an NSView
    to the window object.

    """

    def start(self, application_delegate=None):
        """Main entry point.

        If application_delegate is None (default) a new instance of
        RendererApplicationDelegate will be allocated and initialised.
        If application_delegate is not None it is assumed to be an already
        allocated and initialised instance of RendererApplicationDelegate.

        :param application_delegate: FIXME.
        :type application_delegate: FIXME.

        """

        super().start(register=False)
        if application_delegate is None:
            application_delegate = RendererApplicationDelegate.alloc().\
                    initWithRenderer_(self)

        # We need to retain the application delegate somewhere, though
        # we shouldn't need to access it again.
        self._application_delegate = application_delegate

        self.application = AppKit.NSApplication.sharedApplication()
        self.application.setDelegate_(application_delegate)

    # @log_exception(log)
    def cocoa_start(self, register=True):
        """Main entry point for Cocoa operations that require an autorelease
        pool and UI access.

        Create a window with a default presentation delegate.  Register with
        the manager if register is True (default).

        :param boolean register: FIXME.

        """

        window = BaseWindow.alloc().init()
        window.set_presentation_delegate(FadingPresentationDelegate())
        self.set_window(window)

        if register:
            self.register()

    def get_window(self):
        """Return the NSWindow instance.

        :rtype: :class:`NSWindow`

        """
        return self._window

    def set_window(self, window):
        """Set the :class:`NSWindow` instance.

        :param window: the :class:`NSWindow` instance.
        :type window: a :class:`NSWindow` instance.

        """
        self._window = window

    def handle_register_reply_params(self, msg_root, msg_elem):
        """A temporary handler until the manager is in place.

        :param msg_root: The root element for the incoming message.
        :type msg_root: an :class:`xml.etree.ElementTree.Element` instance.
        :param msg_elem: The element representing the body of the incoming
            message.
        :type msg_elem: an :class:`xml.etree.ElementTree.Element` instance.

        """
        super().handle_register_reply_params(msg_root, msg_elem)

    def handle_prepare(self):
        """Handle a 'prepare' request from the manager."""
        log.debug("Handling a prepare request")
        AppHelper.callAfter(self._do_prepare)

    def handle_become_visible(self):
        """Handle a 'become visible' request from the manager."""
        log.debug("Handling a become_visible request")

        def became_visible(window):
            """Callback when window becomes visible."""

            # Notifying Display Manager that the window has loaded.
            etree = self._encapsulate_request(self._generate_msg_finished_loading())
            self.zmq_request_queue.put_nowait(etree)

            # Calling method for subclass.
            self.do_became_visible()

        self.get_window().become_visible(became_visible)

    def handle_become_invisible(self):
        """Handle a 'become invisible' request from the manager."""
        log.debug("Handling a become_invisible request")

        def became_invisible(window):
            """Callback when window becomes invisible."""
            log.debug("Window is invisible")

            # FIXME - notify the manager that operation has completed.
            # For now, terminate.
            self.handle_terminate()

        self.get_window().become_invisible(became_invisible)

    def handle_terminate(self):
        """Handle a 'terminate' request from the manager."""
        log.debug("Handling a terminate request")
        AppKit.NSApplication.sharedApplication().terminate_(self)
        log.debug("Terminated")

    def _add_arguments(self, arg_parser):
        # We want to store a unique ID for our renderer so that we know which
        # one is talking back to the manager.
        super(Renderer, self)._add_arguments(arg_parser)
        arg_parser.add_argument(
            "--uuid", action='store', dest='uuid',
            help="Unique identifier used for communication to display manager."
        )

    def _generate_msg_preparation_failed(self):
        root = ElementTree.Element('preparation_failed', attrib={'id': self.uuid})
        return root

    def _generate_msg_finished_loading(self):
        root = ElementTree.Element('finished_loading', attrib={'id': self.uuid})
        log.debug("Window {}".format(self.uuid))
        return root

    def _handle_arguments(self, args):
        super(Renderer, self)._handle_arguments(args)
        self.uuid = args.uuid

    # @log_exception(log)
    def _do_prepare(self):
        """Calls self.do_prepare() and notifies the manager of the completion
        by calling self.prepare_successful() unless self.do_prepare() returns:

        *   PREPARATION_FAILED, in which case self.prepare_failed() is called
            instead of prepare_successful.

        or,

        *   PREPARATION_NOT_YET_COMPLETE, in which case self.do_prepare takes
            on the responsibility of calling self.prepare_successful() once the
            preparation phase is complete (or self.prepare_failed() if it has
            failed)

        """
        log.debug("Preparing...")
        preparation_result = self.do_prepare()
        if preparation_result is PREPARATION_FAILED:
            self.prepare_failed()
        elif preparation_result is PREPARATION_NOT_YET_COMPLETE:
            log.debug("do_prepare reports preparation not yet complete")
        else:
            self.prepare_successful()

    def prepare_failed(self):
        """Notify the manager that preparation has failed."""
        log.warning("Preparation failed.")

        # Notifying manager that we are done preparing.
        etree = self._encapsulate_request(
            self._generate_msg_preparation_failed()
        )
        self.zmq_request_queue.put_nowait(etree)

    def prepare_successful(self):
        """Notify the manager that preparation was successful."""
        log.debug("Preparation successful.")

        # For now, become visible
        self.handle_become_visible()

    def do_prepare(self):
        """Subclasses should replace this stub method with one that handles
        their preparation requirements.

        """
        pass

    def do_became_visible(self):
        """Subclasses should replace this stub method with one that handles
        their preparation requirements.

        """
        pass
