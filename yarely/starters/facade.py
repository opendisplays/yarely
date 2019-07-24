#!/usr/bin/env python3

# -*- coding: utf-8 -*-
#
# Copyright 2011-2019 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


import common

module_name_template = "yarely.{platform}.facade"
requirements = []

common.launch_application(module_name_template, requirements)
