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


log = logging.getLogger(__name__)


class Filter(object):
    """FIXME."""

    def __init__(self, cds, context_store, config):
        """
        :param cds: FIXME.
        :type cds: FIXME.
        :param context_store: FIXME.
        :type context_store: FIXME.
        :param config: FIXME.
        :type config: FIXME.

        """
        self.cds = copy.copy(cds)
        self.config = config
        self.context_store = context_store

    def filter_cds(self):
        """Returns either None if there is no items eligible to play or a list
        of filtered content items by keeping the original hierarchy.

        :raises NotImplementedError: always.

        """
        raise NotImplementedError()


# These local imports appear at the bottom of the file to avoid a circular
# import problem (each filter class in these files extends the Filter class
# provided above). Making them available at this package level makes for
# cleaner imports in the rest of the scheduling code.
#
# DepthFirstFilter should come first -- more things depend on this filter
# than anything else.
from yarely.core.scheduling.filters.depth_first_filter import (
    DepthFirstFilter
)                                                                        # NOQA
#
# Then import most of the rest
from yarely.core.scheduling.filters.cache_filter import CacheFilter      # NOQA
from yarely.core.scheduling.filters.condition_filter import (
    ConditionFilter
)                                                                        # NOQA
from yarely.core.scheduling.filters.constraintsmet_filter import (
    ConstraintsAreMetFilter
)                                                                        # NOQA
from yarely.core.scheduling.filters.content_type_filter import (
    ContentTypeFilter
)                                                                        # NOQA
from yarely.core.scheduling.filters.null_filter import NullFilter        # NOQA
from yarely.core.scheduling.filters.priority_filter import (
    PriorityFilter
)                                                                        # NOQA
from yarely.core.scheduling.filters.touchinput_filter import (
    TouchInputFilter
)                                                                        # NOQA
from yarely.core.scheduling.filters.web_content_status_filter import (
    WebContentStatusFilter
)                                                                        # NOQA
from yarely.core.scheduling.filters.tacita_filter import TacitaFilter    # NOQA
#
# Import this one LAST, it depends on all of the others
from yarely.core.scheduling.filters import pipeline                      # NOQA

__all__ = [
    "CacheFilter", "ConditionFilter", "ConstraintsAreMetFilter",
    "ContentTypeFilter", "DepthFirstFilter", "Filter",
    "NullFilter", "pipeline", "PriorityFilter", "TouchInputFilter",
    "WebContentStatusFilter", "TacitaFilter"
]
