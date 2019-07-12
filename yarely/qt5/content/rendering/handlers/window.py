# -*- coding: utf-8 -*-
#
# Copyright 2011-2019 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


from PySide2 import QtGui, QtCore, QtWidgets
from PySide2.QtCore import Qt


class QtWindow(QtWidgets.QMainWindow):

    def __init__(self, q_application, x, y, width, height):
        super(QtWindow, self).__init__()
        
        # Referencing the QtApplication (parent of the widget)
        self.q_application = q_application
        
        self.x = 0
        self.y = 0
        self.screen_width = width
        self.screen_height = height
        
        # Render user interface
        self.init_window()
        # self.start()
        self.installEventFilter(self)

    def mousePressEvent(self, event):
        self.fade_out_and_exit()

    def eventFilter(self, object, event):
        # print(event, event.type(), CustomQTEventTest)
        if event.type() == QtCore.QEvent.WindowActivate:
            print("widget window has gained focus")
            return True
        elif event.type()== QtCore.QEvent.WindowDeactivate:
            print("widget window has lost focus")
            return True
        elif event.type()== QtCore.QEvent.MouseButtonPress:
            print("MouseButtonPress")
            self.fade_out_and_exit()
            return True
        
        # Internal Events
        elif event.type() == PrepareContentQEvent.EVENT_TYPE:
            print("send load content event")
            self.load_content()
            return True
        elif event.type() == BecomeVisibleQEvent.EVENT_TYPE:
            print("send visible event")
            self.become_visible()
            return True

        elif event.type() == TerminateViewQEvent.EVENT_TYPE:
            print("send terminate event")
            #self.terminate()
            return True

        return False    
            
    """Prepare the Window"""   
    def init_window(self):
        self.define_window()
        self.hide_cursor()

    def define_window(self):
        # Hide frame and titlebar and always stay out of focus
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint) # or self.setWindowFlags(Qt.WA_ShowWithoutActivating)
        # Set zero margins for window
        self.setContentsMargins(0,0,0,0) 
        # Set size and position
        self.setGeometry(self.x, self.y, self.screen_width, self.screen_height) #set size to fullscreen
        # Set background color black
        self.setStyleSheet("background: black")
        # Set window transparent
        self.setWindowOpacity(0) #render invisible (opacity 0)
        
    def hide_cursor(self):
        """ Make mousecursor invisible. Fix bug on init by moveing pointer out
        of the visible area.
        """
        cursor = QtGui.QCursor(Qt.BlankCursor)
        cursor.setPos(self.screen_width*10, self.screen_height*10)
        cursor.setPos(self.screen_width/2, self.screen_height/2)
        self.setCursor(cursor)
    
    def fade_in(self):
        self.animation = QtCore.QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(1000)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.start()
        
    def fade_out_and_exit(self):
        self.animation = QtCore.QPropertyAnimation(self, b"windowOpacity")
        self.animation.finished.connect(self.exit_q_application)
        self.animation.setDuration(1000)
        self.animation.setStartValue(1)
        self.animation.setEndValue(0)
        self.animation.start()

    def exit_q_application(self):
        self.q_application.quit()

        
class FullscreenQtWindow(QtWindow):
    """FIXME."""
    def __init__(self, q_application):
        """
        :param int width: the required window width.
        :param int height: the required window height.

        """
        screen = q_application.desktop().screenGeometry()
        
        x = 0
        y = 0
        screen_width = screen.width()
        screen_height = screen.height()
        super().__init__(q_application, x, y, screen_width, screen_height)
