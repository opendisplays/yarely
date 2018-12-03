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
_ARG_RENDER_NAMESPACE = 'yarely.darwin.content.rendering.handlers'

_MIME_TYPE_CONFIG_MAP = {
    'application/pdf': {
        'module': '.image', 'param_type': 'path', 'precache': True,
        'stream': False},
    'image': {
        'module': '.image', 'param_type': 'path', 'precache': True,
        'stream': False},
    'text': {
        'module': '.web', 'param_type': 'uri', 'precache': False,
        'stream': False},
    'video': {
        'module': '.qtmovie', 'param_type': 'uri', 'precache': True,
        'stream': False},
    'video/vnd.vlc': {
        'module': '.vlc', 'param_type': 'uri', 'precache': False,
        'stream': True},
    'video/quicktime': {
        'module': '.vlc', 'param_type': 'uri', 'precache': True,
        'stream': False},
}

# For fading windows...
_FADING_ANIMATION_DURATION = 0.8
