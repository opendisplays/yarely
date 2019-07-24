# -*- coding: utf-8 -*-
#
# Copyright 2011-2019 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.

import sys,time

from PySide2 import QtCore, QtWidgets
from PySide2.QtWebEngineWidgets import QWebEnginePage, QWebEngineView

from yarely.qt5.common.window import FullscreenQtWindow
from yarely.qt5.common.renderer import Renderer


class WebRenderer(FullscreenQtWindow):

    def __init__(self, qapp, args):
        super().__init__(qapp)
        self.renderer = Renderer("Web Renderer")
        self.renderer.process_arguments(args)
        self.renderer.start(self)

    def load_content(self):
        print(self.renderer.uri)
        self.loadPage(self.renderer.uri)
        self.show()

    def become_visible(self):
        self.fade_in()
        
    def loadPage(self, url):
        self.webEngineView = QWebEngineView()
        self.setCentralWidget(self.webEngineView)
        self.webEngineView.page().loadStarted.connect(self.loadStartedHandler)
        self.webEngineView.page().loadProgress.connect(self.loadProgressHandler)
        self.webEngineView.page().loadFinished.connect(self.loadFinishedHandler)
        self.webEngineView.load(QtCore.QUrl(url))

    def load(self):
        url = QUrl.fromUserInput(self.addressLineEdit.text())
        if url.isValid():
            self.webEngineView.load(url)

    def loadStartedHandler(self):
        print(time.time(), ": load started")

    def loadProgressHandler(self, prog):
        print(time.time(), ":load progress", prog)

    def loadFinishedHandler(self, status):
        # Report back
        if(status):
            self.renderer.prepare_successful()
            print(time.time(), ": load finished succesfully")
        else:
            self.renderer.prepare_failed()
            print(time.time(), ": page did not load succesfully")


class QApplication(QtWidgets.QApplication):

    def __init__(self):
        super(QApplication,self).__init__(sys.argv)
        self.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        self.view=WebRenderer(self, sys.argv)
        print('end')
        sys.exit(self.exec_())


if __name__ == '__main__':
    print("IMAGE VIEWER START___")
    QApplication()
