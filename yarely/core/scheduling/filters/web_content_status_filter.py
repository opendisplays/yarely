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
from urllib import request

# Local (Yarely) imports
from yarely.core.content.caching import Cache
from yarely.core.scheduling.filters import DepthFirstFilter


log = logging.getLogger(__name__)


class WebContentStatusFilter(DepthFirstFilter):
    """ This filter checks if (web) content items exist. The filter only
    considers content items for checking that do not need to be cached. For
    items that have to be cached, the cache manager should take care of this
    validation.

    """

    def keep_item(self, content_item):

        """Determines if the specified item should be kept. If this method
        returns False then the item will be filtered out of the CDS.

        In this implementation, we only keep an item if the URL exists and if
        the web server has returned a valid status code (between 200 and 399).

        :param content_item: the item to check.
        :type content_item: a :class:`ContentItem` instance.

        """
        # We only care about content that doesn't need to be cached.
        if Cache.needs_to_be_cached(content_item):
            return True

        uri = str(content_item)

        # We fake the user-agent as some web servers wouldn't return the
        # content and raise 403 instead.
        req = request.Request(uri, headers={'User-Agent': 'Mozilla/5.0'})

        # Check if the URL exists at all first.
        try:
            response_status = request.urlopen(req).getcode()
        except request.URLError:
            log.info("Content item does not exist: {}".format(uri))
            return False

        # Anything between 200 and 399 is fine, >400 is an error.
        return 200 <= response_status < 400
