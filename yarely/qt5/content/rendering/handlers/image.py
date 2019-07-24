# -*- coding: utf-8 -*-
#
# Copyright 2011-2019 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.

import sys, os

from PySide2 import QtGui, QtCore, QtWidgets
from PySide2.QtCore import Qt

from yarely.qt5.common.window import QtWindow, FullscreenQtWindow
from yarely.qt5.common.renderer import Renderer


class ImageViewer(FullscreenQtWindow):

    def __init__(self, qapp, args):
        super().__init__(qapp)
        self.renderer = Renderer("Image Renderer")
        self.renderer.process_arguments(args)
        self.renderer.start(self)

    def load_content(self):
        print(self.renderer.uri)
        self.load_fullscreen_image(self.renderer.uri)
        self.show()

    def become_visible(self):
        self.fade_in()

    def load_fullscreen_image(self, source):
        if(os.path.isfile(source)):
            label = QtWidgets.QLabel(self)
            pixmap = QtGui.QPixmap(source)
            pixmap_resized = pixmap.scaled(self.screen_width, self.screen_height, QtCore.Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(pixmap_resized)

            # Center image
            x_pos = (self.screen_width - pixmap_resized.width())/2
            y_pos = (self.screen_height - pixmap_resized.height())/2
            label.setGeometry(x_pos, y_pos, pixmap_resized.width(), pixmap_resized.height())

            # Report back
            self.renderer.prepare_successful()
            print("load finished succesfully")

        else:
            self.renderer.prepare_failed()
            print("src file does not exsist")


            
            
class QApplication(QtWidgets.QApplication):

    def __init__(self):
        super(QApplication,self).__init__(sys.argv)
        self.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        self.view=ImageViewer(self, sys.argv)
        print('end')
        sys.exit(self.exec_())


if __name__ == '__main__':
    print("IMAGE VIEWER START___")
    QApplication()
