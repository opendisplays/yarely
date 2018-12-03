# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


"""Platform specific methods for the win32 platform"""

# Standard library imports
import urllib.parse

# Third party imports
import win32file

# Local imports
from yarely.core.platform import PlatformError


def get_available_space_in_bytes(path):
    r"""Return the number of bytes available in the given path.

    The meaning of 'available' varies between host platforms but the
    intention is to return the writable space available to this process
    (i.e. implentations try to take user quotas or filesystem restrictions
    into account).

    The space is not reserved so this value can only be used as a
    hint - it is not a guarantee that the space will be available for
    consumption at a later point.

    :param string path: a string or bytes object giving the pathname of the
        path to be checked.
    :return: if successful, a non-zero value representing the number of
        bytes available; if the function fails, the return value is zero (0).
    :rtype: int

    Example:

      >>> get_available_space_in_bytes("c:\\")    # doctest: +SKIP
      1435425335

    """
    return win32file.GetDiskFreeSpaceEx(path)[0]


def get_local_path_from_uri(uri):
    """Return a local file path from the specified file URI."""
    # On Windows, urllib.parse.urlparse() doesn't return a path with
    # forward slashes so we put them in before we return the value.
    # Windows also keeps the localhost '/' in at the start of path
    # so we chop this off before the replace operation.
    parse_result = urllib.parse.urlparse(uri)
    if parse_result.scheme != 'file':
        raise PlatformError('URI must have scheme of type file')
    path = parse_result.path.lstrip('/').replace('/', '\\')
    return path


def get_uri_from_local_path(path):
    """Return a file URI for the specified local file."""
    # On Windows, urllib.parse.urlunparse() doesn't do the right thing with
    # forward slashes so we replace these before we start.
    path = path.replace('\\', '/')
    parse_result = urllib.parse.ParseResult(
        scheme='file', netloc='', path=path, params='', query='', fragment=''
    )
    return urllib.parse.urlunparse(parse_result)
