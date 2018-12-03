# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


"""Platform specific methods for the SAMPLE platform"""


def get_available_space_in_bytes(path):
    """Return the number of bytes available in the given path."""
    raise NotImplementedError()


def get_local_path_from_uri(uri):
    """Return a local file path from the specified file URI."""
    raise NotImplementedError()


def get_uri_from_local_path(path):
    """Return a file URI for the specified local file."""
    raise NotImplementedError()
