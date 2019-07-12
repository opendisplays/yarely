# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


"""Renderer and caching related constants."""

# FIXME -- will need fixing for multiple platforms
_ARG_RENDER_NAMESPACE = 'yarely.qt5.content.rendering.handlers'

_MIME_TYPE_CONFIG_MAP = {
    'application/pdf': {
        'module': '.image', 'param_type': 'path', 'precache': True,
        'stream': False, 'restart_renderer': False
    },
    'image': {
        'module': '.image', 'param_type': 'path', 'precache': True,
        'stream': False, 'restart_renderer': False
    },
    'text': {
        'module': '.web', 'param_type': 'uri', 'precache': False,
        'stream': False, 'restart_renderer': False
    },
    'video': {
        'module': '.video', 'param_type': 'uri', 'precache': True,
        'stream': False, 'restart_renderer': True
    },
    'video/vnd.vlc': {
        'module': '.video', 'param_type': 'uri', 'precache': False,
        'stream': True, 'restart_renderer': True
    },
    'video/quicktime': {
        'module': '.video', 'param_type': 'uri', 'precache': True,
        'stream': False, 'restart_renderer': True
    },
}

# For fading windows...
_FADING_ANIMATION_DURATION = 2.5
