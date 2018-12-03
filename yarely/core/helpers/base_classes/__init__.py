# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


"""Yarely base classes module"""

# Nice alphabetically ordered imports
from yarely.core.helpers.base_classes.application import (
  Application, ApplicationError, ApplicationConfigurationError,
  ApplicationWithBasicLogging, ApplicationWithConfig
)

# We import Struct before Manager because Manager depends on Struct
from yarely.core.helpers.base_classes.struct import Struct

# We import ZMQRPC before Handler and Manager because they depend on ZMQRPC
from yarely.core.helpers.base_classes.zmq_rpc import ZMQRPC

# Then back to nice alphabetically ordered imports
from yarely.core.helpers.base_classes.handler import Handler
from yarely.core.helpers.base_classes.handler import HandlerError
from yarely.core.helpers.base_classes.manager import HandlerStub
from yarely.core.helpers.base_classes.manager import Manager
from yarely.core.helpers.base_classes.pull_handler import PullHandler
from yarely.core.helpers.base_classes.uri_manager import URIManager

__all__ = ['Application', 'ApplicationConfigurationError', 'ApplicationError',
           'ApplicationWithConfig', 'ApplicationWithBasicLogging', 'Handler',
           'HandlerError', 'HandlerStub', 'Manager', 'PullHandler', 'Struct',
           'URIManager', 'ZMQRPC']
