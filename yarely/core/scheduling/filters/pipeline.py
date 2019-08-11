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
from yarely.core.scheduling.constants import CONTEXT_STORE_DEFAULT_DB_PATH
from yarely.core.scheduling.contextstore import ContextStore
from yarely.core.scheduling.filters import (
    CacheFilter, ConstraintsAreMetFilter, ContentTypeFilter, PriorityFilter,
    TouchInputFilter, WebContentStatusFilter, TacitaFilter
)


# First we check if the display can technically play certain content items,
# e.g. due to the type, caching and if web content is reachable. Then we check
# constraints that are defined in the CDS.
# Tacita should come before PriorityFilter.
# Todo: we might need an emergency content filter
DEFAULT_FILTERS = (
    TouchInputFilter, ContentTypeFilter, CacheFilter, # WebContentStatusFilter,  # Fixme
    TacitaFilter, ConstraintsAreMetFilter, PriorityFilter
)


log = logging.getLogger(__name__)


benchmark_logger = logging.getLogger('benchmarks')


class FilterPipeline(object):
    """ Runs all filters on the content descriptor set in order. If at least
    one filter removes an item from the CDS, it will not be shown on the
    display.

    """

    def __init__(self, scheduler_mgr):
        """
        :param scheduler_mgr: FIXME.
        :type scheduler_mgr: FIXME.

        """
        self.scheduler_mgr = scheduler_mgr
        self._initialise_filters()
        self.context_store = ContextStore(CONTEXT_STORE_DEFAULT_DB_PATH)

    def _config(self):
        """ FIXME """
        return self.scheduler_mgr.config

    def _initialise_filters(self):
        """ This method is turning filters from config entries into objects to
        be called. It will overwrite self.list_of_filters
        """
        self.filters = DEFAULT_FILTERS

        # TODO - read in the config and check for individual list of filters

    def filter_cds(self, cds):
        """Runs each of the pipeline filters in turn. The output of one filter
        operating becomes the input to the next. Returns either None if there
        is no items eligible to play or a list of filtered content items by
        keeping the original hierarchy.

        :rtype: FIXME

        """

        filtered_cds = copy.copy(cds)

        for FilterClass in self.filters:
            log.debug(
                "Starting filter: {filter_name} with {num_of_items} "
                "items".format(
                    filter_name=FilterClass.__name__,
                    num_of_items=len(filtered_cds.get_content_items())
                )
            )

            benchmark_logger.info(
                "start_filter_{}".format(FilterClass.__name__)
            )

            tmp_filter = FilterClass(
                filtered_cds, self.context_store, self._config()
            )
            filtered_cds = tmp_filter.filter_cds()

            benchmark_logger.info(
                "end_filter_{}".format(FilterClass.__name__)
            )

            log.debug(
                "Done with {} items".format(
                    len(filtered_cds.get_content_items())
                )
            )

            # Stop the filtering process if there is no items left.
            if not filtered_cds:
                break

        return filtered_cds
