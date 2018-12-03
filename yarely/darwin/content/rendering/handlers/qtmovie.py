# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


"""Render a movie on the Darwin platform via QuickTime"""


# Standard library imports
import logging

# Third party imports
import Foundation
import QTKit
from PyObjCTools import AppHelper

# Local (Yarely) imports
from yarely.darwin.common.content.rendering import Renderer, PREPARATION_FAILED
from yarely.darwin.common.window.layout import XYWidthHeightLayoutDelegate
from yarely.darwin.helpers.execution import application_loop


log = logging.getLogger(__name__)


APPLICATION_DESCRIPTION = "Render a movie on the Darwin platform via QuickTime"


class QTMovieRenderer(Renderer):
    """FIXME."""

    def _handle_reply_params(self, msg_root, msg_elem):
        """A fudge until the Renderer Manager is in place."""
        super()._handle_reply_params(msg_root, msg_elem)

        self.uri = self.params['uri']

        log.info("URI is '{uri}'".format(uri=self.uri))
        AppHelper.callAfter(self.handle_prepare)

    def do_prepare(self):
        """Prepare an item of content for display."""
        self.qt_movie_view = QTKit.QTMovieView.alloc().initWithFrame_(
            Foundation.NSZeroRect
        )

        ns_url = Foundation.NSURL.alloc().initWithString_(self.uri)

        (self.qt_movie, qt_movie_error) = QTKit.QTMovie.alloc().\
            initWithURL_error_(ns_url, None)

        if self.qt_movie is None:
            log.warning(
                "QTMovie failed to load: {descr}, {reason}".format(
                    descr=qt_movie_error.localizedDescription(),
                    reason=qt_movie_error.localizedFailureReason()
                )
            )
            return PREPARATION_FAILED

        self.qt_movie_view.setMovie_(self.qt_movie)
        self.qt_movie_view.setControllerVisible_(False)
        self.qt_movie_view.setPreservesAspectRatio_(True)

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

        self.get_window().setContentView_(self.qt_movie_view)

    def do_became_visible(self):
        """FIXME."""
        self.qt_movie.play()

if __name__ == "__main__":
    application_loop(QTMovieRenderer, description=APPLICATION_DESCRIPTION)
