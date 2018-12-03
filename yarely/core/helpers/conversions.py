# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


""" Yarely conversions module. """

# Standard library imports
import re


class ConversionError(Exception):
    """Base class for conversion errors."""
    pass


_compiled_regexp = {}

# ----------------------------------------------------------------------
# ---           UNIT OF INFORMATION CONVERSIONS (TO BYTES)           ---
# ----------------------------------------------------------------------
#
# To add new unit of information, update the _BYTE_MULTIPLIERS
# dictionary.
#
# The _BYTE_MULTIPLIERS keys should contain only the uppercase
# characters A-Z. The character I should be used no more than once
# in each key and only to specify an IEC binary prefix -- it should not
# be used in SI decimal prefixes.
#
_BYTE_MULTIPLIERS = {
    'B': 1,
    'KB': 1000,
    'KIB': 1024,
    'MB': 1000 * 1000,
    'MIB': 1024 * 1024,
    'GB': 1000 * 1000 * 1000,
    'GIB': 1024 * 1024 * 1024,
    'TB': 1000 * 1000 * 1000 * 1000,
    'TIB': 1024 * 1024 * 1024 * 1024,
}
_BYTE_REGEXP = '^(?P<value>[0-9]+)(?: ?(?P<unit>(?:[KMGT][i]?)?[B]?))$'
_BYTE_REGEXP_KEY = 'byte_multipliers'


class UnitOfInformationConversionError(ConversionError):
    """Base class for unit of information errors."""
    def __init__(self, msg):
        """:param string msg: a descriptive error message."""
        MSG_PREFIX = 'Failed to convert unit of information: '
        MSG_SUFFIX = '\n Accepted unit types: {types}.'
        self.valid_units = [
            unit.replace('I', 'i', 1) for unit in _BYTE_MULTIPLIERS.keys()
        ]
        self.valid_units.sort()
        msg_suffix = MSG_SUFFIX.format(types=', '.join(self.valid_units))
        super().__init__(MSG_PREFIX + msg + msg_suffix)


def unit_of_information_in_bytes(in_str):
    """Convert the specified unit of information string and return the value as
    a number of bytes.

    :param string in_str: the unit interval string to be converted.
    :return: the number of bytes.
    :rtype: int
    :raises UnitOfInformationConversionError: raised if `in_str` cannot be
        parsed as a valid unit of information string.

    Example:

        >>> a = unit_of_information_in_bytes("1")
        >>> b = unit_of_information_in_bytes("1B")
        >>> c = unit_of_information_in_bytes("1 B")
        >>> a == b == c == 1
        True

        >>> unit_of_information_in_bytes("1 KB")
        1000

        >>> unit_of_information_in_bytes("1 KiB")
        1024

    """
    if _BYTE_REGEXP_KEY not in _compiled_regexp:
        _compiled_regexp[_BYTE_REGEXP_KEY] = re.compile(
            _BYTE_REGEXP, flags=re.IGNORECASE
        )
    _byte_regexp = _compiled_regexp[_BYTE_REGEXP_KEY]
    match = _byte_regexp.match(in_str)
    if not match:
        msg = "unknown unit of information '{in_str}'".format(in_str=in_str)
        raise UnitOfInformationConversionError(msg)
    (value, unit) = match.group('value', 'unit')
    (value, unit) = (int(value), unit.upper() if unit else 'B')
    unit = unit + 'B' if unit[-1] != 'B' else unit
    return value * _BYTE_MULTIPLIERS[unit]


# ----------------------------------------------------------------------
# ---               TIME UNIT CONVERSIONS (TO SECONDS)               ---
# ----------------------------------------------------------------------
#
# To add new time unit, update the _TIME_INTERVALS dictionary.
#
# The _TIME_INTERVALS keys should contain only the uppercase
# characters A-Z.
#
_TIME_INTERVALS = {
    'SEC': 1,
    'SECOND': 1,
    'MIN': 60,
    'MINUTE': 60,
    'HR': 60 * 60,
    'HOUR': 60 * 60,
    'DAY': 60 * 60 * 24,
    'WK': 60 * 60 * 24 * 7,
    'WEEK': 60 * 60 * 24 * 7
}
_TIME_UNITS = '|'.join(_TIME_INTERVALS)
_TIME_INTERVAL_REGEXP = '^(?P<value>[0-9]*)(?: ?(?P<unit>{units})S?)?$'
_TIME_INTERVAL_REGEXP = _TIME_INTERVAL_REGEXP.format(units=_TIME_UNITS)
_TIME_REGEXP_KEY = 'time_interval'


class TimeIntervalConversionError(ConversionError):
    """Base class for time interval conversion errors."""
    def __init__(self, msg):
        """:param string msg: a descriptive error message."""
        MSG_PREFIX = 'Failed to convert time interval: '
        MSG_SUFFIX = '\n Accepted interval types: {types}.'
        self.valid_intervals = list(_TIME_INTERVALS.keys())
        self.valid_intervals.sort()
        msg_suffix = MSG_SUFFIX.format(types=', '.join(self.valid_intervals))
        super().__init__(MSG_PREFIX + msg + msg_suffix)


def time_interval_in_seconds(in_str):
    """Convert the specified time interval string and return the value as a
    number of seconds.

    :param string in_str: the time interval string to be converted.
    :return: the number of seconds.
    :rtype: int
    :raises TimeIntervalConversionError: raised if `in_str` cannot be
        parsed as a valid time interval string.


    Example:

        >>> a = time_interval_in_seconds("1")
        >>> b = time_interval_in_seconds("1 SECOND")
        >>> c = time_interval_in_seconds("1 SECONDS")
        >>> d = time_interval_in_seconds("1 SEC")
        >>> e = time_interval_in_seconds("1 SECS")
        >>> f = time_interval_in_seconds("1SECOND")
        >>> g = time_interval_in_seconds("1SECONDS")
        >>> h = time_interval_in_seconds("1SEC")
        >>> i = time_interval_in_seconds("1SECS")
        >>> a == b == c == d == e == f == g == h == i == 1
        True

        >>> time_interval_in_seconds("60 seconds")
        60

        >>> time_interval_in_seconds("1 minute")
        60

    """
    if _TIME_REGEXP_KEY not in _compiled_regexp:
        _compiled_regexp[_TIME_REGEXP_KEY] = re.compile(
            _TIME_INTERVAL_REGEXP, flags=re.IGNORECASE
        )
    _time_interval_regexp = _compiled_regexp[_TIME_REGEXP_KEY]
    match = _time_interval_regexp.match(in_str)
    if not match:
        msg = "unknown interval '{in_str}'".format(in_str=in_str)
        raise TimeIntervalConversionError(msg)
    (value, unit) = match.group('value', 'unit')
    (value, unit) = (int(value), unit.upper() if unit else 'SECOND')
    return value * _TIME_INTERVALS[unit]
