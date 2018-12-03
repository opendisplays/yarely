# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


"""Platform specific methods for the linux platform"""

# Local imports
from yarely.core.platform import common_posix


def get_available_space_in_bytes(path):
    """Return the number of bytes available in the given path."""
    return common_posix.get_available_space_in_bytes(path)


def get_local_path_from_uri(uri):
    """Return a local file path from the specified file URI."""
    return common_posix.get_local_path_from_uri(uri)


def get_uri_from_local_path(path):
    """Return a file URI for the specified local file."""
    return common_posix.get_uri_from_local_path(path)
