# -*- coding: utf-8 -*-
#
# Copyright 2011-2019 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.

import sys

from PySide2 import QtGui, QtCore, QtWidgets

from yarely.qt5.common.window import FullscreenQtWindow
from yarely.qt5.common.renderer import Renderer

import vlc


class VideoViewer(FullscreenQtWindow):

    def __init__(self, qapp, args):
        super().__init__(qapp)
        self.renderer = Renderer("Video Renderer")
        self.renderer.process_arguments(args)
        self.renderer.start(self)

    def load_content(self):
        print(self.renderer.uri)
        self.load_fullscreen_video(self.renderer.uri)
        self.show()

    def become_visible(self):
        self.mediaplayer.play()
        self.fade_in()

    def load_fullscreen_video(self, source):
        try:
            """Create video widget set it to window and make it visible"""
            # creating a basic vlc instance
            self.instance = vlc.Instance()
            # creating an empty vlc media player
            self.mediaplayer = self.instance.media_player_new()
            self.videoframe = QtWidgets.QWidget(self)
            self.setCentralWidget(self.videoframe)
            self.media = self.instance.media_new(source)
            # put the media in the media player
            self.mediaplayer.set_media(self.media)
            self.mediaplayer.audio_set_volume(0)

            """Connect to QFrame
            # the media player has to be 'connected' to the QFrame
            # (otherwise a video would be displayed in it's own window)
            # this is platform specific!
            # you have to give the id of the QFrame (or similar object) to
            # vlc, different platforms have different functions for this
            """
            if sys.platform.startswith('linux'): # for Linux using the X Server
                self.mediaplayer.set_xwindow(self.videoframe.winId())
            elif sys.platform == "win32": # for Windows
                self.mediaplayer.set_hwnd(self.videoframe.winId())
            elif sys.platform == "darwin": # for MacOS
                self.mediaplayer.set_nsobject(int(self.videoframe.winId()))
            self.renderer.prepare_successful()

        except:
            self.renderer.prepare_failed()
            print("unknown error")
                

class QApplication(QtWidgets.QApplication):

    def __init__(self):
        super(QApplication,self).__init__(sys.argv)
        self.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        self.view=VideoViewer(self, sys.argv)
        print('end')
        sys.exit(self.exec_())


if __name__ == '__main__':
    print("IMAGE VIEWER START___")
    QApplication()
