# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


""" Yarely config module. """

# Local imports
from yarely.core.config.parse_config import (
    _YarelyConfig as YarelyConfig, ConfigParsingError
)

__all__ = ["YarelyConfig", "ConfigParsingError"]
