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
import unittest

# Local (Yarely) imports
from yarely.core.helpers import singleton, Singleton


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
    tests.addTests(doctest.DocTestSuite(singleton))
    return tests


class SingletonTestCase(unittest.TestCase):
    """FIXME"""

    @classmethod
    def setUpClass(cls):
        """FIXME"""

        class SingletonA(object, metaclass=Singleton):
            def __init__(self, flag):
                self.flag = flag

        class SingletonB(object, metaclass=Singleton):
            def __init__(self, flag):
                self.flag = flag

        # singleton_a uses args, whilst singleton_b uses kwargs
        cls._singleton_a_true = SingletonA(True)
        cls._singleton_a_false = SingletonA(False)
        cls._singleton_b_true = SingletonB(flag=True)
        cls._singleton_b_false = SingletonB(flag=False)

    def test_single_instance_per_class(self):
        """FIXME"""
        self.assertIs(self._singleton_a_true, self._singleton_a_false)

    def test_different_classes_have_different_instances(self):
        """FIXME"""
        self.assertIsNot(self._singleton_a_true, self._singleton_b_true)

    def test_first_instance_args_taken(self):
        """FIXME"""
        self.assertIs(self._singleton_a_true.flag, True)

    def test_second_instance_args_ignored(self):
        """FIXME"""
        self.assertIs(self._singleton_a_false.flag, True)

    def test_first_instance_kwargs_taken(self):
        """FIXME"""
        self.assertIs(self._singleton_b_true.flag, True)

    def test_second_instance_kwargs_ignored(self):
        """FIXME"""
        self.assertIs(self._singleton_b_false.flag, True)
