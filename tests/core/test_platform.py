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
import doctest
import tempfile
import unittest
import urllib.parse

# Local (Yarely) imports
from yarely.core import platform


def load_tests(loader, tests, ignore):
    """FIXME

    :param loader: FIXME.
    :type loader: FIXME.
    :param tests: FIXME.
    :type tests: FIXME.
    :param ignore: FIXME.
    :type ignore: FIXME.
    :rtype: FIXME.

    """
    tests.addTests(doctest.DocTestSuite(platform))
    return tests


class GetAvailableSpaceInBytesTestCase(unittest.TestCase):
    """FIXME"""

    @classmethod
    def setUpClass(cls):
        cls._path = tempfile.gettempdir()

    def setUp(self):
        self._result = platform.get_available_space_in_bytes(self._path)

    def test_numerical_result(self):
        """FIXME"""
        self.assertIsInstance(self._result, int)

    def test_positive_result(self):
        """FIXME"""
        self.assertGreaterEqual(self._result, 0)


class URILocalPathConversionTestCase(unittest.TestCase):
    """FIXME"""

    @classmethod
    def setUpClass(cls):
        cls._path = tempfile.gettempdir()

    def setUp(self):
        self._result = platform.get_uri_from_local_path(self._path)

    def test_geturi_string_result(self):
        """FIXME"""
        self.assertIsInstance(self._result, str)

    def test_geturi_reverse_result(self):
        """FIXME"""
        self.assertEqual(
            self._path, platform.get_local_path_from_uri(self._result)
        )

    def test_getlocalpath_raises(self):
        """FIXME"""
        erroneous_result = urllib.parse.ParseResult(
            scheme='http', netloc='', path=self._path, params='', query='',
            fragment=''
        )
        parsed_erroneous = urllib.parse.urlunparse(erroneous_result)
        with self.assertRaises(platform.PlatformError):
            platform.get_local_path_from_uri(parsed_erroneous)
