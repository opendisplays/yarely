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
import logging
import sqlite3
from xml.etree import ElementTree

# Local (Yarely) imports
'''from yarely.core.subscriptions.subscription_manager.subscription_manager \
    import SubscriptionMangerError'''    # FIXME
from yarely.core.subscriptions.subscription_parser import ContentDescriptorSet

log = logging.getLogger(__name__)

# Local SQL Queries
#
# NOTE - Use INT rather than INTEGER in xml_link to AVOID an
# AUTOINCREMENT field
SQL_CREATE_TABLES = '''
    CREATE TABLE IF NOT EXISTS xml (xml_id INTEGER PRIMARY KEY, xml TEXT);
    CREATE TABLE IF NOT EXISTS uri (xml_id INTEGER, uri TEXT PRIMARY KEY);
    CREATE TABLE IF NOT EXISTS xml_link (
        parent_id INTEGER, child_id INT PRIMARY KEY
    );
'''
SQL_DELETE_URIS = 'DELETE FROM uri WHERE xml_id = ?'
SQL_INSERT_XML = 'INSERT INTO xml (xml) VALUES (?)'
SQL_REPLACE_LINK = 'REPLACE INTO xml_link (parent_id, child_id) VALUES (?, ?)'
SQL_REPLACE_URI = 'REPLACE INTO uri (xml_id, uri) VALUES (?, ?)'
SQL_SELECT_CHILDREN_GIVEN_UID = '''
    SELECT child_id FROM xml_link WHERE parent_id = ?
'''
SQL_SELECT_PARENT_GIVEN_UID = '''
    SELECT parent_id FROM xml_link WHERE child_id = ?
'''
SQL_SELECT_UID_GIVEN_URI = 'SELECT xml_id FROM uri WHERE uri = ?'
SQL_SELECT_URIS_GIVEN_UID = 'SELECT uri from uri WHERE xml_id = ?'
SQL_SELECT_XML_GIVEN_UID = 'SELECT xml FROM xml WHERE xml_id = ?'
SQL_UPDATE_XML = 'UPDATE xml SET xml = ? WHERE xml_id = ?'


'''class SubscriptionMangerPersistenceError(SubscriptionMangerError):
    """Base class for subscription manager persistence errors"""
    pass
'''    # FIXME


class PersistentStore:
    """Manages persistence"""

    def __init__(self, db_path):
        """Default constructor - Creates a new PersistentStore.

        :param string db_path: the path for the (new or existing) SQLite
            database file.

        """
        self.db_path = db_path

        # Create file if not exists
        open(self.db_path, 'a').close()

        # Create tables if not exists
        db_connection = sqlite3.connect(self.db_path)
        with db_connection:
            db_connection.executescript(SQL_CREATE_TABLES)
        db_connection.close()

    def select_child_ids(self, xml_id):
        """Lookup the children (a list of IDs) for the specified XML ID.
        Return an empty list if no children found.

        :param xml_id: FIXME.
        :type xml_id: FIXME.
        :rtype: list

        """
        db_connection = sqlite3.connect(self.db_path)
        with db_connection:
            db_connection.row_factory = sqlite3.Row
            db_cursor = db_connection.cursor()
            db_cursor.execute(SQL_SELECT_CHILDREN_GIVEN_UID, (xml_id,))
            child_ids = [row['child_id'] for row in db_cursor]
            db_cursor.close()
        db_connection.close()
        return child_ids

    def select_parent_id(self, xml_id):
        """Lookup the parent XML ID for the specified XML ID.
        Return None if no parent found.

        :param xml_id: FIXME.
        :type xml_id: FIXME.
        :rtype: FIXME

        """
        db_connection = sqlite3.connect(self.db_path)
        with db_connection:
            db_connection.row_factory = sqlite3.Row
            db_cursor = db_connection.cursor()
            db_cursor.execute(SQL_SELECT_PARENT_GIVEN_UID, (xml_id,))
            row = db_cursor.fetchone()
            parent_id = row['parent_id'] if row is not None else None
            db_cursor.close()
        db_connection.close()
        return parent_id

    def select_root_id_where_uri(self, uri):        # FIXME - name?
        """Get the XML ID of the top-level root for this URI from the
        persistent store. Return None if no entry for this URI can be
        found.

        :param string uri: FIXME.
        :rtype: FIXME

        """
        # First convert this URI to an XML ID
        xml_id = self.select_xml_id_where_uri(uri)
        if xml_id is None:
            return None

        # Then iterate look for parent relationships.
        # Once we run out of parents we return the last XML ID retreived.
        parent_id = self.select_parent_id(xml_id)
        while parent_id:
            xml_id = parent_id
            parent_id = self.select_parent_id(xml_id)

        return xml_id

    def select_xml(self, xml_id):
        """Lookup the persistent XML for this XML ID.
        Returns None if no XML found.

        :param xml_id: FIXME.
        :type xml_id: FIXME.
        :rtype: FIXME

        """
        db_connection = sqlite3.connect(self.db_path)
        with db_connection:
            db_connection.row_factory = sqlite3.Row
            db_cursor = db_connection.cursor()
            db_cursor.execute(SQL_SELECT_XML_GIVEN_UID, (xml_id,))
            row = db_cursor.fetchone()
            xml = row['xml'] if row is not None else None
            db_cursor.close()
        db_connection.close()
        return xml

    def select_xml_id_where_uri(self, uri):
        """Lookup the persistent XML ID for this URI.
        Return None if no entry for this URI can be found.

        :param string uri: FIXME.
        :rtype: FIXME

        """
        db_connection = sqlite3.connect(self.db_path)
        with db_connection:
            db_connection.row_factory = sqlite3.Row
            db_cursor = db_connection.cursor()
            db_cursor.execute(SQL_SELECT_UID_GIVEN_URI, (uri,))
            row = db_cursor.fetchone()
            xml_id = row['xml_id'] if row is not None else None
            db_cursor.close()
        db_connection.close()
        return xml_id

    def store_descriptor_set(self, descriptor_set):
        """FIXME

        :param descriptor_set: FIXME.
        :type descriptor_set: FIXME.

        """

        # Lookup URIs to see if this CDS has previously been stored
        # Note - we used files[0] here as the CDS already checks that
        # there's exactly one file.
        #
        # FIXME - handle >1 source that disgaree about the xml id
        for source in descriptor_set.get_files()[0].get_sources():
            xml_id = self.select_xml_id_where_uri(source.get_uri())
            if xml_id is not None:
                break

        db_connection = sqlite3.connect(self.db_path)
        with db_connection:
            db_connection.row_factory = sqlite3.Row
            db_cursor = db_connection.cursor()

            # Insert/Update the XML for this CDS
            xml = descriptor_set.get_inline_xml()
            if xml_id is None:
                xml = '' if xml is None else xml
                db_cursor.execute(SQL_INSERT_XML, (xml,))
                xml_id = db_cursor.lastrowid
            elif xml:
                db_cursor.execute(SQL_UPDATE_XML, (xml, xml_id))

            # Update the URIs stored for this CDS.
            # NOTE - Again we use files[0] here.
            db_cursor.execute(SQL_DELETE_URIS, (xml_id,))
            for source in descriptor_set.get_files()[0].get_sources():
                db_cursor.execute(
                    SQL_REPLACE_URI, (xml_id, source.get_uri())
                )

            # Cleanup
            db_cursor.close()
        db_connection.close()

        # Create links for children of this set
        for child in descriptor_set.get_children():
            if (
                isinstance(child, ContentDescriptorSet) and
                child.get_type() == 'remote'
            ):

                # NOTE - The recursive call cannot be inside the
                # db_connection context manager otherwise the
                # database will be locked.
                child_id = self.store_descriptor_set(child)
                db_connection = sqlite3.connect(self.db_path)
                with db_connection:
                    db_connection.execute(
                        SQL_REPLACE_LINK, (xml_id, child_id)
                    )

        return xml_id

    def to_etree_elem(self, xml_id):
        """Create an ElementTree Element from the persistent store,
        based on the specified XML ID. Return None if no parsable XML
        found for the specified XML ID.

        :param xml_id: FIXME.
        :type xml_id: FIXME.
        :rtype: FIXME

        """
        # Lookup the XML for this ID and parse it into an etree Element.
        try:
            stored_xml = self.select_xml(xml_id)
            if stored_xml is None:
                return None
            etree = ElementTree.XML(stored_xml)
        except ElementTree.ParseError:
            return None
        db_children = self.select_child_ids(xml_id)
        used_children = []

        # Replace children
        for elem in list(etree.findall('content-set')):
            if elem.attrib.get('type', 'remote') == 'remote':

                # Pull out the sources
                requires_file = elem.find('requires-file')
                if requires_file is None:
                    return None
                sources = requires_file.find('sources')
                if sources is None:
                    return None

                # Pull out the URI for each source
                for source in sources:
                    if sources.text is None:
                        return None
                    uri = source.text.strip()

                    # Try and find an XML ID for this URI
                    child_id = self.select_xml_id_where_uri(uri)

                    # Do the replacement
                    if child_id is not None:
                        if child_id not in db_children:
                            msg = ("DB Integrity error? "
                                   "{child!r} not in {children!r}")
                            msg = msg.format(child=child_id,
                                             children=db_children)
                            log.debug(msg)
                        else:
                            used_children.append(child_id)
                            new_elem = self.to_etree_elem(child_id)
                            if new_elem is not None:
                                # Merge constraints from original placeholder
                                # set with constraints from new set
                                cds_orig = ContentDescriptorSet(elem)
                                cstrnts_elm_orig = cds_orig.get_constraints(
                                    recurse_up_tree=False,
                                    return_as_etree_elem=True
                                )
                                cnstrnts_elm_new = new_elem.find('constraints')
                                if cnstrnts_elm_new is not None:
                                    cnstrnts_elm_new.extend([
                                        child for child in cstrnts_elm_orig
                                    ])
                                else:
                                    new_elem.append(cstrnts_elm_orig)

                                # Pop the new element where the placeholder was
                                i = etree.getchildren().index(elem)
                                etree.insert(i, new_elem)

                            # Remove the placeholder
                            etree.remove(elem)
        if set(db_children) != set(used_children):
            msg = "DB Integrity error? {s1!r} != {s2!r}"
            msg = msg.format(s1=set(db_children), s2=set(used_children))
            log.debug(msg)

        return etree
