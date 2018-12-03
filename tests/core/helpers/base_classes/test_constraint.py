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
import datetime
import doctest
import random
import time
import unittest
from xml.etree import ElementTree

# Local (Yarely) imports
from yarely.core.helpers.base_classes import constraint


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
    tests.addTests(doctest.DocTestSuite(constraint))
    return tests


class DateTimeConstraintConditionTestCase(unittest.TestCase):
    """FIXME"""

    def test_datetime(self):
        """FIXME"""
        now = datetime.datetime.today()
        result = constraint.DateTimeConstraintCondition(now)
        self.assertEqual(result.data, now)

    def test_float_timestamp(self):
        """FIXME"""
        now = time.time()
        datetime_now = datetime.datetime.fromtimestamp(now)
        result = constraint.DateTimeConstraintCondition(now)
        self.assertEqual(result.data, datetime_now)

    def test_int_timestamp(self):
        """FIXME"""
        now = int(time.time())
        datetime_now = datetime.datetime.fromtimestamp(now)
        result = constraint.DateTimeConstraintCondition(now)
        self.assertEqual(result.data, datetime_now)

    def test_list_ymdhms(self):
        """FIXME"""
        (year, month, day) = (2012, 1, 12)
        (hour, minute, second) = (14, 13, 50)
        result = constraint.DateTimeConstraintCondition(
            [year, month, day, hour, minute, second]
        )
        self.assertEqual(
            result.data,
            datetime.datetime(year, month, day, hour, minute, second)
        )

    def test_list_ymdhmsm(self):
        """FIXME"""
        (year, month, day) = (2012, 1, 12)
        (hour, minute, second, microsecond) = (14, 13, 50, 888)
        result = constraint.DateTimeConstraintCondition(
            [year, month, day, hour, minute, second, microsecond]
        )
        self.assertEqual(
            result.data, datetime.datetime(
                year, month, day, hour, minute, second, microsecond
            )
        )

    def test_list_ymdhmsmz(self):
        """FIXME"""
        (year, month, day) = (2012, 1, 12)
        (hour, minute, second, microsecond) = (14, 13, 50, 888)
        tzinfo = None
        result = constraint.DateTimeConstraintCondition(
            [year, month, day, hour, minute, second, microsecond, tzinfo]
        )
        self.assertEqual(
            result.data, datetime.datetime(
                year, month, day, hour, minute, second, microsecond, tzinfo
            )
        )

    def test_str_timestamp(self):
        """FIXME"""
        now = time.time()
        datetime_now = datetime.datetime.fromtimestamp(now)
        result = constraint.DateTimeConstraintCondition(str(now))
        self.assertEqual(result.data, datetime_now)

    def test_str_datetime(self):
        """FIXME"""
        datetimestr = '2012-01-12 14:13:50'
        result = constraint.DateTimeConstraintCondition(datetimestr)
        self.assertEqual(
            result.data, datetime.datetime.strptime(
                datetimestr, constraint.DateTimeConstraintCondition.STR_FORMAT
            )
        )

    def test_str_unparsable(self):
        """FIXME"""
        with self.assertRaises(constraint.DateTimeConstraintConditionError):
            constraint.DateTimeConstraintCondition('unparsable')

    def test_tuple_datetime(self):
        """FIXME"""
        today = datetime.date.today()
        noon = datetime.time(12)
        result = constraint.DateTimeConstraintCondition((today, noon))
        self.assertEqual(result.data, datetime.datetime.combine(today, noon))


class DayOfWeekConstraintConditionTestCase(unittest.TestCase):
    """FIXME"""

    def test_between(self):
        """Tests a valid day-of-week constraint defined with a between tag.

        Verifies that a day-of-week constraint containing a single
        'between' tag is correctly parsed into a DayOfWeekConstraint object.

        """
        between_test_str = '''
            <day-of-week>
                <between start="monday" end="sunday"/>
            </day-of-week>
        '''
        etree = ElementTree.XML(between_test_str)
        dow_constraint = constraint.DayOfWeekConstraint(etree)
        for i in range(7):
            self.assertEqual(
                dow_constraint._data[i].start_time, datetime.time.min
            )
            self.assertEqual(
                dow_constraint._data[i].end_time, datetime.time.max
            )

    def test_weekdays(self):
        """FIXME"""
        weekdays_test_str = '''
            <day-of-week>
                <Saturday time_start="09:00:00" time_end="12:00:00"/>
                <Sunday time_start="10:00:00" time_end="11:30:00"/>
            </day-of-week>
        '''
        etree = ElementTree.XML(weekdays_test_str)
        dow_constraint = constraint.DayOfWeekConstraint(etree)
        for i in range(5):
            self.assertIsNone(dow_constraint._data[i].start_time)
        self.assertEqual(
            dow_constraint._data[5].start_time, datetime.time(9, 0, 0)
        )
        self.assertEqual(
            dow_constraint._data[6].start_time, datetime.time(10, 0, 0)
        )
        self.assertEqual(
            dow_constraint._data[5].end_time, datetime.time(12, 0, 0)
        )
        self.assertEqual(
            dow_constraint._data[6].end_time, datetime.time(11, 30, 0)
        )


class PriorityConstraintConditionTestCase(unittest.TestCase):
    """FIXME"""

    def test_str(self):
        priorities = constraint.PriorityConstraint.ALL_PRIORITIES
        index = random.randrange(len(priorities) - 1)
        result = constraint.PriorityConstraintCondition(priorities[index])
        self.assertEqual(result.data, priorities[index])

    def test_str_unparsable(self):
        """FIXME"""
        with self.assertRaises(constraint.PriorityConstraintConditionError):
            constraint.PriorityConstraintCondition('unparsable')

    def test_index(self):
        """FIXME"""
        priorities = constraint.PriorityConstraint.ALL_PRIORITIES
        index = random.randrange(len(priorities) - 1)
        result = constraint.PriorityConstraintCondition(index)
        self.assertEqual(result.data, priorities[index])

    def test_index_outofrange(self):
        """FIXME"""
        priorities = constraint.PriorityConstraint.ALL_PRIORITIES
        with self.assertRaises(constraint.PriorityConstraintConditionError):
            constraint.PriorityConstraintCondition(len(priorities))
