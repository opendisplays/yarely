# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


""" Yarely ZMQ module. """

ZMQ_SOCKET_NO_LINGER = 0
ZMQ_REQUEST_TIMEOUT_MSEC = 1000
ZMQ_SOCKET_LINGER_MSEC = 1000
ZMQ_ADDRESS_LOCALHOST = 'tcp://127.0.0.1:{port}'
ZMQ_ADDRESS_INPROC = 'inproc://{identifier}'

# DEFAULT PORT NUMBERS
#
# Note - Dynamic, private or ephemeral ports: 49152-65535.
# We'll use those in the region: 55343+.
ZMQ_SUBSMANAGER_REQ_PORT = 55343
ZMQ_SENSORMANAGER_REQ_PORT = 55344
ZMQ_RENDERER_REQ_PORT = 55345

ZMQ_SUBSMANAGER_REP_PORT = 55346
ZMQ_SENSORMANAGER_REP_PORT = 55347
ZMQ_DISPLAYCONTROLLER_REP_PORT = 55348
