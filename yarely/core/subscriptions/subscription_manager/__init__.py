# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


"""Yarely subscription management module"""

from yarely.core.subscriptions.subscription_manager import (
  __main__, persistence, subscription_manager
)

__all__ = ["__main__", "persistence", "subscription_manager"]
