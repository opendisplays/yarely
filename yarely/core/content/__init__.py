# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


# Import constants first as these are used in caching
from yarely.core.content.constants import (
    _ARG_RENDER_NAMESPACE as ARG_RENDER_NAMESPACE,
    _MIME_TYPE_CONFIG_MAP as MIME_TYPE_CONFIG_MAP,
    _FADING_ANIMATION_DURATION as FADING_ANIMATION_DURATION
)
from yarely.core.content import caching
from yarely.core.content.helpers import (
    get_initial_args, UnsupportedMimeTypeError
)


__all__ = [
    "ARG_RENDER_NAMESPACE", "caching", "FADING_ANIMATION_DURATION",
    "MIME_TYPE_CONFIG_MAP", 'get_initial_args', 'UnsupportedMimeTypeError'
]