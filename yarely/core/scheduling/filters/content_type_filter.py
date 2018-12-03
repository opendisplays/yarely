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

# Local (Yarely) imports
from yarely.core.content import get_initial_args, UnsupportedMimeTypeError
from yarely.core.scheduling.filters import DepthFirstFilter


log = logging.getLogger(__name__)


class ContentTypeFilter(DepthFirstFilter):
    """Goes through every ContentItem in the CDS and removes files that have
    are of a content type that Yarely can't play. The resulting CDS consists
    of ContentItems that are supported by our renderers. We are using the
    'get_initial_args' method that would throw an error if a content item is
    not supported by renderers.

    """

    def keep_item(self, content_item):
        """Determines if the specified item should be kept. If this method
        returns False then the item will be filtered out of the CDS.

        :param content_item: the item to check.
        :type content_item: a :class:`ContentItem` instance.

        """
        try:
            get_initial_args(content_item.get_content_type())
        except UnsupportedMimeTypeError:
            log.debug("Unrecognized Mime Type for: {}".format(str(content_item)))
            return False

        return True
