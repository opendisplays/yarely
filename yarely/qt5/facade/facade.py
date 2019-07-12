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

from yarely.qt5.common.window import FullscreenQtWindow




class Facade(FullscreenQtWindow):
    def __init__(self, q_application):
        super().__init__(q_application)
        self.start()
        
    def start(self):
        """TODO - Relative path"""
        self.render_logo("/home/yarely/proj/yarely-local/assets/logo.png")
        self.show()
        self.fade_in()
        
    def render_logo(self, source):
        self.setStyleSheet("background: qradialgradient(cx:.5, cy:.5, radius: .7,fx:0.48, fy:0.83, stop:0 #03759b, stop:1 #003B50)")

        if(os.path.isfile(source)):
            label = QtWidgets.QLabel(self) 
            label.setStyleSheet("background: none")
            pixmap = QtGui.QPixmap(source)
            pixmap_resized = pixmap.scaled(self.screen_width/2.5, self.screen_height/2.5, QtCore.Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(pixmap_resized)

            # Center image
            x_pos = (self.screen_width - pixmap_resized.width())/2
            y_pos = (self.screen_height - pixmap_resized.height())/2.5
            label.setGeometry(x_pos, y_pos, self.screen_width/2.5, self.screen_height/2.5);

        else:
            print("file not found")

        
class QApplication(QtWidgets.QApplication):
    
    def __init__(self):
        super(QApplication,self).__init__(sys.argv)
        self.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        self.view=Facade(self)
        sys.exit(self.exec_())

        
def main():
    QApplication()
