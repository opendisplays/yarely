# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


# Local (Yarely) imports
from yarely.core.content import MIME_TYPE_CONFIG_MAP


class UnsupportedMimeTypeError(Exception):
    """FIXME."""
    pass


def get_initial_args(content_type):
    """Trying to match the content type into the list of supported
    renderers. If we can't find an appropriate renderer, we will raise
    UnsupportedMimeTypeError. Otherwise we will return an initial dictionary of
    arguments that will have to be called in order to start the renderer.

    :param string content_type: FIXME.
    :rtype: dict
    :raises UnsupportedMimeTypeError: if no renderer is found.

    """
    if content_type in MIME_TYPE_CONFIG_MAP:
        return MIME_TYPE_CONFIG_MAP[content_type]

    # This handles different split types in case the full MIME type
    # wasn't recognised:
    #     - ';' splits for 'application/pdf ; charset' and only considers
    #       the first part, i.e. 'application/pdf' in this example.
    #     - '/' splits for 'application/pdf' and will only consider
    #       anything before the split, i.e. 'application' in this example.
    splits = [';', '/']

    for split in splits:
        simple_content_type = content_type.split(split)[0]
        if simple_content_type in MIME_TYPE_CONFIG_MAP:
            return MIME_TYPE_CONFIG_MAP[simple_content_type]

    raise UnsupportedMimeTypeError()
