# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


"""Render a webpage on the Darwin platform."""

# Standard library imports
import logging
import os.path
import warnings

# Third party imports
import AppKit
import Foundation
import WebKit
import objc
from PyObjCTools import AppHelper

# Local (Yarely) imports
from yarely.core.helpers.decorators import log_exception
from yarely.darwin.common.content.rendering import (
    Renderer, PREPARATION_NOT_YET_COMPLETE
)
from yarely.darwin.common.window.layout import XYWidthHeightLayoutDelegate
from yarely.darwin.helpers.execution import application_loop


log = logging.getLogger(__name__)


APPLICATION_DESCRIPTION = "Render a webpage on the Darwin platform"

WEBKIT_LOCAL_STORAGE_DATABASE_PATH = os.path.join(
    os.path.expanduser('~'), 'Library', 'WebKit', 'LocalStorage'
)


class WebFrameLoadDelegate(AppKit.NSObject):
    """FIXME."""

    def initWithWebRenderer_(self, web_renderer):
        """Designated initializer for WebFrameLoadDelegate

        :param web_renderer: FIXME.
        :type web_renderer: a :class:`WebRenderer` instance.
        :rtype: :class:`WebFrameLoadDelegate`

        """
        self = objc.super(WebFrameLoadDelegate, self).init()
        self._web_renderer = web_renderer
        return self

    @log_exception(log)
    def webView_didFinishLoadForFrame_(self, sender, frame):
        """Invoked when a page load completes - informs the web renderer
        that preparation is complete.

        :param sender: FIXME.
        :type sender: FIXME.
        :param frame: FIXME.
        :type frame: FIXME.

        """
        log.debug("webView:didFinishLoadForFrame:{}".format(frame))
        if frame is self._web_renderer.web_view.mainFrame():
            log.debug("Finished loading main frame")
            self._web_renderer.prepare_successful()
        else:
            log.debug("Ignoring didFinishLoadForFrame - not main frame")

    @log_exception(log)
    def webView_didCommitLoadForFrame_(self, sender, frame):
        """FIXME.

        :param sender: FIXME.
        :type sender: FIXME.
        :param frame: FIXME.
        :type frame: FIXME.

        """
        log.debug("webView:didCommitLoadForFrame:")
        if self._web_renderer.uri.startswith(
          'http://gerrard.lancs.ac.uk/WindTurbineSignalR'
        ):
            log.info(
                "WindTurbineSignalR never-sends-didFinishLoadForFrame bodge"
            )
            self._web_renderer.prepare_successful()


class WebRenderer(Renderer):
    def _handle_reply_params(self, msg_root, msg_elem):
        """A fudge until the Renderer Manager is in place."""
        super()._handle_reply_params(msg_root, msg_elem)

        # FIXME - allowing 'url' is deprecated, we should stick to uri.
        # stop allowing 'url' in future.
        if 'url' in self.params:
            self.uri = self.params['url']
            warnings.warn(
                "The URL parameter is deprecated in favour of URI.",
                DeprecationWarning
            )
        else:
            self.uri = self.params['uri']

        log.info("URI is '{uri}'".format(uri=self.uri))
        AppHelper.callAfter(self.handle_prepare)

    def do_prepare(self):
        """Prepare an item of content for display.

        :rtype: FIXME.
        :return: FIXME.

        """
        # Set the HTML5 localStorage database location
        web_preferences = WebKit.WebPreferences.standardPreferences()
        web_preferences._setLocalStorageDatabasePath_(
            WEBKIT_LOCAL_STORAGE_DATABASE_PATH
        )

        self.web_view = WebKit.WebView.alloc().\
            initWithFrame_frameName_groupName_(
                Foundation.NSZeroRect, None, None
        )

        self.web_frame_load_delegate = WebFrameLoadDelegate.alloc().\
            initWithWebRenderer_(self)
        self.web_view.setFrameLoadDelegate_(self.web_frame_load_delegate)

        ns_url = Foundation.NSURL.alloc().initWithString_(self.uri)
        ns_url_request = Foundation.NSURLRequest.alloc().initWithURL_(ns_url)
        self.web_view.mainFrame().loadRequest_(ns_url_request)
        self.web_view.mainFrame().frameView().setAllowsScrolling_(False)

        # This doesn't really belong here...
        if (
            "layout_style" in self.params and
            self.params["layout_style"] == "x_y_width_height"
        ):
            layout_delegate = XYWidthHeightLayoutDelegate(
                int(self.params["layout_x"]), int(self.params["layout_y"]),
                int(self.params["layout_width"]),
                int(self.params["layout_height"])
            )
            self.get_window().set_layout_delegate(layout_delegate)

        if "layout_window_level_increase" in self.params:
            self.get_window().set_level_increase(
                int(self.params["layout_window_level_increase"])
            )

        self.get_window().setContentView_(self.web_view)

        # The web_frame_load_delegate will call prepare_successful once
        # the page content has successfully loaded.
        return PREPARATION_NOT_YET_COMPLETE

if __name__ == "__main__":
    application_loop(WebRenderer, description=APPLICATION_DESCRIPTION)
