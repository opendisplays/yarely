# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


# Local (Yarely) imports
from yarely.core.content.caching import Cache
from yarely.core.scheduling.filters import DepthFirstFilter


class CacheFilter(DepthFirstFilter):
    """Goes through every ContentItem in the CDS and removes files that have
    not been cached yet. The resulting CDS consists of ContentItems that cannot
    be cached (e.g. web-based applications) or ContentItems that appear in the
    cache. This filter does not trigger caching in case a file was not cached
    yet.

    """

    def __init__(self, cds, context_store, config):
        """
        :param cds: FIXME.
        :type cds: FIXME.
        :param context_store: FIXME.
        :type context_store: FIXME.
        :param config: FIXME.
        :type config: FIXME.

        """
        super().__init__(cds, context_store, config)
        self._initialise_cache()

    def _initialise_cache(self):
        cache_dir = self.config.get(
            'CacheFileStorage', 'CacheLocation', fallback="/tmp"
        )
        self.cache = Cache(cache_dir)

    def keep_item(self, content_item):
        """Determines if the specified item should be kept. If this method
        returns False then the item will be filtered out of the CDS.

        In this implementation, if a file wasn't successfully cached it will
        be removed from the CDS for now.

        :param content_item: the item to check.
        :type content_item: a :class:`ContentItem` instance.

        """
        # If the file needs to be cached, check if it is. Otherwise always
        # return True (e.g. for websites).
        if self.cache.needs_to_be_cached(content_item):
            # We don't care about the actual file hashes here, just want to see
            # if the file exists at all (otherwise the filter will take too
            # long to complete). Therefore we use strict=True here.
            return self.cache.file_cached(content_item, strict=False)
        return True
