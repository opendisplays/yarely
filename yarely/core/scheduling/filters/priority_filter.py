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
from yarely.core.scheduling.filters import ConditionFilter
from yarely.core.subscriptions.subscription_parser import (
    PriorityConstraint, PriorityConstraintCondition
)


log = logging.getLogger(__name__)


class PriorityFilter(ConditionFilter):
    """Priority filter clears searches in the incoming CDS for highest
    priority items only and discards all low-priority items.

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_priority_level = None

    def _get_condition(self):
        return self._current_priority_level

    def filter_cds(self):
        """Returns either None if there is no items eligible to play or a list
        of filtered content items by keeping the original hierarchy.

        :rtype: FIXME
        :return: FIXME.

        """
        log.debug("Running priority filter.")

        priority_levels = reversed(
            range(len(PriorityConstraint.ALL_PRIORITIES))
        )

        # Loop through all priorities starting with the highest. Stop as soon
        # as we have at least one eligible element and return this as the
        # filtered CDS.
        for priority_level in priority_levels:
            self._current_priority_level = PriorityConstraintCondition(
                priority_level
            )

            # Start the normal condition filtering process.
            tmp_cds = super().filter_cds()

            # If there is at least one eligible element, stop here and return
            # this as the filtered CDS.
            number_of_content_items = len(tmp_cds.get_content_items())
            if number_of_content_items > 0:
                log.debug(
                    "Stopping at priority level {} with {} elements".format(
                        priority_level, number_of_content_items
                    )
                )
                return tmp_cds

        return self.cds
