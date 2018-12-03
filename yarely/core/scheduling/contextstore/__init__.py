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
import logging
import re
import sqlite3
from xml.etree import ElementTree as ET

# Internal Yarely imports
from yarely.core.scheduling.contextstore.constants import (
    CONTEXT_TYPE_PAGEVIEW, CONTEXT_TYPE_SENSOR_UPDATE,
    CONTEXT_TYPE_TOUCH_INPUT, CONTEXT_TABLE_NAME, CONTEXT_TYPE_CONTENT_TRIGGER
)
from yarely.core.subscriptions.subscription_parser import ContentItem


# SQLite commands
CREATE_CONTEXT_TABLE = (
    "CREATE TABLE IF NOT EXISTS {table} ("
    "context_id INTEGER PRIMARY KEY, created DATETIME DEFAULT "
    "CURRENT_TIMESTAMP, context_type TEXT, content_item_xml TEXT)"
)

INSERT_CONTEXT_RECORD = (
    "INSERT INTO {table} (context_type, content_item_xml) "
    "VALUES ('{context_type}', '{content_item_xml}')"
)
SELECT_CONTEXT_RECORD_ORDER_BY_DATE = (
    "SELECT context_type, content_item_xml, created, "
    "datetime(created, 'localtime') AS created_localtime "
    "FROM {table} "
    "WHERE {where_clause} "
    "ORDER BY created {order} "
    "LIMIT {limit}"
)
SELECT_CONTEXT_RECORD_BY_TYPE_ORDER_BY_DATE_DESC = (
    SELECT_CONTEXT_RECORD_ORDER_BY_DATE.format(
        where_clause="context_type == '{context_type}'", order="DESC",
        table='{table}', limit="{limit}"
    )
)
SELECT_CONTEXT_RECORD_BY_TYPE_GROUP_BY_ORDER_BY_DATE = (
    "SELECT content_item_xml, count(*) as num_of_entries "
    "FROM {table} "
    "WHERE context_type == '{context_type}' "
    "AND created > '{created}' "
    "GROUP BY {group_by} "
    "ORDER BY num_of_entries ASC "
    "LIMIT {limit}"
)
SELECT_CONTEXT_RECORD_BY_TYPE_MOST_RECENT = (
    "SELECT DISTINCT content_item_xml "
    "FROM {table} "
    "WHERE context_type == '{context_type}' "
    "ORDER BY rowid DESC "
    "LIMIT {limit}"
)

# Each context type will get its own table in the database?
CONTEXT_TYPE = (
    CONTEXT_TYPE_SENSOR_UPDATE, CONTEXT_TYPE_TOUCH_INPUT, CONTEXT_TYPE_PAGEVIEW,
    CONTEXT_TYPE_CONTENT_TRIGGER
)


log = logging.getLogger(__name__)


class UnsupportedContextTypeError(Exception):
    """ This error gets raised when an unsupported or unknown context type is
    supposed to be either read from the context store or written into it.
    """
    pass


class ContextStore(object):
    """ This is the handler that translates requests from Yarely to the
    underlying database used.

    SQLite3 for Python allows to access a database file by multiple processes
    and threads.
    """

    def __init__(self, db_path):
        """
        :param string db_path: FIXME.

        """
        self.db_path = db_path
        self._initialise_database()

    @staticmethod
    def _convert_content_item_to_str(content_item):
        """ Convert ContentItem objects to one-line string. Get rid of any
        spacing etc. as to make the grouping by content item easier.
        """

        # Fixme (low priority) - this sometimes doesn't shorten correctly.
        content_item_str = content_item.get_xml()

        # Cleanup entries as there is usually a lot of whitespace between XML
        # entries and get rid of the spare new line - outputs everything in
        # one line which should also make queries easier.
        # Matches all \n followed by whitespace.
        pattern = r'\n[\s]*'
        regex = re.compile(pattern)
        cleaned_output = regex.sub('', content_item_str)

        return cleaned_output

    def _initialise_database(self):
        # Create file if not exists
        # Todo: check write permissions here!
        open(self.db_path, 'a').close()

        # Create tables if not exist
        db_connection = sqlite3.connect(self.db_path)

        with db_connection:
            db_connection.executescript(CREATE_CONTEXT_TABLE.format(
                table=CONTEXT_TABLE_NAME
            ))
        db_connection.close()

    def _exec_select_query(self, sql):
        # Todo: check if db_path exists?
        db_connection = sqlite3.connect(self.db_path)

        with db_connection:
            # Fetch the entries by row
            db_connection.row_factory = self._dict_factory
            db_cursor = db_connection.cursor()
            db_cursor.execute(sql)
            rows = db_cursor.fetchall()
            db_cursor.close()
        db_connection.close()

        return rows

    @staticmethod
    def _dict_factory(cursor, row):
        # Convert SQLite row to dict - from Python doc.
        # content_item_xml gets converted into a ContentItem object
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]

            # Handling ContentItem objects
            if col[0] == 'content_item_xml':
                if not d[col[0]]:
                    d['content_item'] = None
                    continue

                try:
                    content_item_xml = ET.fromstring(d[col[0]])
                    content_item = ContentItem(content_item_xml)
                    d['content_item'] = content_item
                except ET.ParseError:
                    d['content_item'] = None

            # Handling created and created_localtime objects.
            if col[0].startswith('created'):
                # 2015-06-19 10:11:21
                tmp_datetime = datetime.datetime.strptime(
                    d[col[0]], "%Y-%m-%d %H:%M:%S"
                )
                d[col[0]] = tmp_datetime

        return d

    def add_context(self, context_type, content_item):
        """ Write new context/sensor information into the context store. This
        method is thread safe. Context should be a dictionary that maps back to
        the database structure.

        :param string context_type: FIXME.
        :param content_item: FIXME.
        :type content_item: a :class:`ContentItem` object.
        :rtype: FIXME
        :return: context id of the created database entry.

        """
        # Stop here if we don't support the context type.
        if context_type not in CONTEXT_TYPE:
            raise UnsupportedContextTypeError()

        # Sometimes content_item might be empty. Then we just save an empty
        # string to the context store so that the context_type event gets
        # stored.
        content_item_xml = None
        if content_item:
            content_item_xml = self._convert_content_item_to_str(content_item)

        # Connect to the database and build the SQL query.
        db_connection = sqlite3.connect(self.db_path)
        db_cursor = db_connection.cursor()

        # Insert the data
        with db_connection:
            sql = INSERT_CONTEXT_RECORD.format(
                context_type=context_type, content_item_xml=content_item_xml,
                table=CONTEXT_TABLE_NAME
            )
            db_cursor.execute(sql)
            row_id = db_cursor.lastrowid

        # Cleanup
        db_cursor.close()
        db_connection.close()

        log.debug(
            "Added context information: content item: '{content_item}'"
            " - type: '{context_type}' - row id {row_id}".format(
                content_item=str(content_item), context_type=context_type,
                row_id=row_id
            )
        )
        return row_id

    def get_latest_context_by_type(self, context_type, n=1):
        """Returns the most recent n (default is 1) elements of a specified
        context_type from the context store.

        :param string context_type: FIXME.
        :param integer n: FIXME.
        :rtype: FIXME
        :return: FIXME.

        """

        # Stop here if we don't support the context type.
        if context_type not in CONTEXT_TYPE:
            raise UnsupportedContextTypeError()

        sql = SELECT_CONTEXT_RECORD_BY_TYPE_ORDER_BY_DATE_DESC.format(
            context_type=context_type, limit=n, table=CONTEXT_TABLE_NAME,
        )
        rows = self._exec_select_query(sql)
        return rows

    def get_latest_content_items_by_context_type(self, context_type, n=1):
        """This returns the most recent n (default is 1) ContentItem objects
        in a list of dicts consisting of the ContentItem and created datetime
        of a specified context_type from the context store.

        :param string context_type: FIXME.
        :param integer n: FIXME.
        :rtype: FIXME
        :return: FIXME.

        """
        rows = self.get_latest_context_by_type(context_type, n)
        return rows

    def get_latest_content_item_counts(
            self, context_type, until_datetime, n=1000
    ):
        """FIXME.

        :param string context_type: FIXME.
        :param until_datetime: FIXME.
        :type until_datetime: FIXME.
        :param integer n: FIXME.
        :rtype: FIXME
        :return: FIXME.

        """
        sql = SELECT_CONTEXT_RECORD_BY_TYPE_GROUP_BY_ORDER_BY_DATE.format(
            table=CONTEXT_TABLE_NAME, context_type=context_type,
            created=until_datetime, group_by='content_item_xml', limit=n
        )
        return self._exec_select_query(sql)

    def get_latest_content_item_played(
            self, context_type, until_datetime, n=1000
    ):
        """FIXME.

        :param string context_type: FIXME.
        :param until_datetime: FIXME.
        :type until_datetime: FIXME.
        :param integer n: FIXME.
        :rtype: FIXME
        :return: FIXME.

        """
        sql = SELECT_CONTEXT_RECORD_BY_TYPE_MOST_RECENT.format(
            table=CONTEXT_TABLE_NAME, context_type=context_type,
            limit=n
        )
        return self._exec_select_query(sql)
