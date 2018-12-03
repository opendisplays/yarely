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
import copy
import logging

# Local (Yarely) imports
from yarely.core.scheduling.filters import Filter
from yarely.core.subscriptions.subscription_parser import (
    ContentItem, ContentDescriptorSet
)


log = logging.getLogger(__name__)


class DepthFirstFilter(Filter):
    """Base class for performing Depth First Searches on Content Descriptor
    Set instances. On every ContentItem it calls the keep_item() method which
    should be implemented in a child class. It will either return True to keep
    the ContentItem in the CDS, or False to get it removed.

    """

    def keep_item(self, content_item):
        """Determines if the specified item should be kept. If this method
        returns False then the item will be filtered out of the CDS.

        This method gets called for each ContentItem in the CDS. Override
        this method for own condition testing and make sure it always returns
        either False (to delete content_item from CDS) or True (to keep it).

        :param content_item: the item to check.
        :type content_item: a :class:`ContentItem` instance.

        """
        raise NotImplementedError()

    def _remove_recursively(self, root):
        """Walks recursively through the CDS and deletes a content item if
        self.keep_item evaluates to False.

        """
        # Stop if we reached a content item
        if not isinstance(root, ContentDescriptorSet):
            return

        children = root.get_children_reference()

        # Storing a list of items to delete because we don't want to remove
        # children while we iterate over them.
        children_to_delete = []

        for child in children:

            # Walk deeper until we find a ContentItem object.
            if not isinstance(child, ContentItem):
                self._remove_recursively(child)
                continue

            # Check if we can keep the item or not..
            if self.keep_item(child):
                continue

            # Delete the child from the tree after walking through the list.
            children_to_delete.append(child)

        # Now let's delete all the items we were supposed to.
        for child_to_delete in children_to_delete:
            root.remove_child(child_to_delete)

    def filter_cds(self):
        """This is the main method for starting the depth first search. It
        first creates a copy of the CDS and calls _remove_recursively() on it.
        If you overwrite this method, make sure it always returns a CDS.

        """
        log.debug("Running {} filter.".format(self.__class__.__name__))

        tmp_cds = copy.copy(self.cds)

        # Start the recursive depth-first search.
        self._remove_recursively(tmp_cds)

        log.debug("Done with {} items.".format(len(tmp_cds)))

        return tmp_cds
