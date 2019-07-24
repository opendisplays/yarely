# -*- coding: utf-8 -*-
#
# Copyright 2011-2019 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


from PySide2.QtCore import QEvent


class PrepareContentQEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self):
        super(PrepareContentQEvent, self).__init__(self.EVENT_TYPE)


class BecomeVisibleQEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self):
        super(BecomeVisibleQEvent, self).__init__(self.EVENT_TYPE)


class TerminateViewQEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self):
        super(TerminateViewQEvent, self).__init__(self.EVENT_TYPE)
