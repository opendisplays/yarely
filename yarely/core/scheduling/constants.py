# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


# Standard library imports
import os.path


# Renderer and caching related constants
DEFAULT_CONTENT_DURATION = 15  # seconds
DISPLAY_ADDITIONAL_KEEP_ALIVE = 20  # seconds

# Context-Store default values
CONTEXT_STORE_DB_FILENAME = "yarely_context_store.sqlite"
CONTEXT_STORE_DEFAULT_DB_PATH = os.path.join(
    "/", "tmp", CONTEXT_STORE_DB_FILENAME
)

# Touch input threshold - past seconds in which touch should be considered.
TOUCH_INPUT_TIME_THRESHOLD = 2  # seconds
TACITA_CONTENT_TRIGGER_THRESHOLD = 30  # seconds
TOUCH_INPUT_TIME_THRESHOLD = 5  # seconds
TOUCH_INPUT_CONTENT_TYPE_BUTTON = 'text/html; touch_button'
TOUCH_INPUT_CONTENT_TYPE_APP_SELECTION = 'text/html; touch_app_selection'
TOUCH_INPUT_LAYOUT_MARGIN = 20  # pixel
TOUCH_INPUT_APP_SELECTION_TIMEOUT = 10  # seconds
TOUCH_INPUT_APP_SELECTION_POSITION = 'touch_interaction_app_selection'
TOUCH_INPUT_BUTTON_POSITION = 'touch_interaction_button'
