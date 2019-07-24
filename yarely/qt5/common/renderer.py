# -*- coding: utf-8 -*-
#
# Copyright 2011-2019 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


# Standard library imports
import logging
from xml.etree import ElementTree

# Local (Yarely) imports
from yarely.core.helpers.base_classes import Handler
from yarely.qt5.common.qt_events import BecomeVisibleQEvent, PrepareContentQEvent

# External imports
from PySide2 import QtGui, QtCore, QtWidgets


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

    def start(self, qt_window=None):
        """Main entry point.
        """
        super().start(register=False)
        self.qt_window = qt_window
        self.register()

    def handle_register_reply_params(self, msg_root, msg_elem):
        """A temporary handler until the manager is in place.

        :param msg_root: The root element for the incoming message.
        :type msg_root: an :class:`xml.etree.ElementTree.Element` instance.
        :param msg_elem: The element representing the body of the incoming
            message.
        :type msg_elem: an :class:`xml.etree.ElementTree.Element` instance.

        """
        super().handle_register_reply_params(msg_root, msg_elem)

    def _handle_reply_params(self, msg_root, msg_elem):
        """A fudge until the Renderer Manager is in place."""
        super()._handle_reply_params(msg_root, msg_elem)

        # FIXME - allowing 'url' is deprecated, we should stick to uri.
        # stop allowing 'url' in future.
        if 'url' in self.params:
            self.uri = self.params['url']
        elif 'path' in self.params:
            self.uri = self.params['path']
        else:
            self.uri = self.params['uri']

        log.info("URI is '{uri}'".format(uri=self.uri))
        QtCore.QCoreApplication.postEvent(self.qt_window, PrepareContentQEvent())

    def handle_prepare(self):
        """Handle a 'prepare' request from the manager."""
        log.debug("Handling a prepare request")

    def handle_become_visible(self):
        """Handle a 'become visible' request from the manager."""
        log.debug("Handling a become_visible request")

        def became_visible(window):
            """Callback when window becomes visible."""

            # Notifying Display Manager that the window has loaded.
            etree = self._encapsulate_request(self._generate_msg_finished_loading())
            self.zmq_request_queue.put_nowait(etree)

            # Calling method for subclass.
            # self.do_became_visible()

    def handle_become_invisible(self):
        """Handle a 'become invisible' request from the manager."""
        log.debug("Handling a become_invisible request")

    def handle_terminate(self):
        """Handle a 'terminate' request from the manager."""
        log.debug("Handling a terminate request")

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

    def prepare_failed(self):
        """Notify the manager that preparation has failed."""
        log.warning("Preparation failed.")

        # Notifying manager that we are done preparing.
        etree = self._encapsulate_request(
            self._generate_msg_preparation_failed()
        )
        self.zmq_request_queue.put_nowait(etree)

    def prepare_successful(self):
        # Notifying manager that we are done preparing.
        etree = self._encapsulate_request(
            self._generate_msg_finished_loading()
        )
        self.zmq_request_queue.put_nowait(etree)
        QtCore.QCoreApplication.postEvent(self.qt_window, BecomeVisibleQEvent())
