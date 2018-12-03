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
from datetime import datetime, timedelta
import logging

# Internal Yarely imports
from yarely.core.scheduling.contextstore.constants import CONTEXT_TYPE_PAGEVIEW
from yarely.core.scheduling.schedulers.lottery import LotteryTicketAllocator


UNTIL_DATETIME_COUNT = timedelta(hours=2)

log = logging.getLogger(__name__)


class _RecencyBasedAllocator(LotteryTicketAllocator):
    """Distribute tickets based on the count of recently played content items.

    """

    @staticmethod
    def _content_item_comparison_weak(item_a, item_b):
        """Compare two ContentItem objects with each other in a weak way -
        we only take the filename and path into consideration and ignore
        constraints (as the proper __eq__ method would do).

        """
        return str(item_a) == str(item_b)

    @classmethod
    def _content_item_in_list(cls, content_item, list_of_items):
        for item_in_list in list_of_items:
            if cls._content_item_comparison_weak(item_in_list, content_item):
                return True
        return False

    def _filter_played_items(self, played_content_items):
        """Filter the previously played content items for these that are in
        the CDS.

        """
        eligible_content_items = self.cds.get_content_items()
        remove_items = []
        for item in played_content_items:
            if self._content_item_in_list(
                    item['content_item'], eligible_content_items
            ):
                continue
            remove_items.append(item)

        for item in remove_items:
            played_content_items.remove(item)

        return played_content_items

    def _least_played_content_items(self):
        # Getting the counts for content items that were played within within
        # the last UNTIL_DATETIME_COUNT hours.
        until_datetime = datetime.now() - UNTIL_DATETIME_COUNT
        counts = self.context_store().get_latest_content_item_played(
            context_type=CONTEXT_TYPE_PAGEVIEW, until_datetime=until_datetime
        )
        counts = list(reversed(counts))
        return counts

    def _get_not_played_items(self, played_content_items):
        content_items = self.cds.get_content_items()
        not_played_items = []
        played_content_items_list = [
            item['content_item'] for item in played_content_items
        ]

        for item in content_items:
            if self._content_item_in_list(item, played_content_items_list):
                continue

            tmp_entry = {'content_item': item, 'num_of_entries': 0}
            not_played_items.append(tmp_entry)

        return not_played_items

    def allocate_tickets(self):
        """Allocate 1/2 of all tickets to the least played content item,
        then 1/2 of the remaining tickets to the next least played item etc.
        until we run out of tickets. This way we prioritise content items that
        haven't been played for a long time.

        """

        # Get all items that were played...
        played_content_items = self._least_played_content_items()

        log.debug("Nu of played content items {}".format(
            len(played_content_items)
        ))

        # ... filter these items out that are not eligible to play right now...
        filtered_content_items = self._filter_played_items(
            played_content_items
        )

        log.debug("Number of filtered content items {}".format(
            len(filtered_content_items)
        ))

        # ... and populate the list with items that weren't played at all.
        filtered_content_items.extend(
            self._get_not_played_items(filtered_content_items)
        )

        log.debug("Number of content items considered for algorithm {}".format(
            len(filtered_content_items)
        ))

        # Our pointer for walking through the list of filtered content items.
        pointer = 0

        while self.tickets_for_allocation:
            # Always allocate half of the available tickets to the first
            # content item in the list
            num_of_tickets = int(len(self.tickets_for_allocation)/2) + 1
            log.debug("{} tickets for {}".format(
                num_of_tickets, str(filtered_content_items[pointer])
            ))

            for i in range(0, num_of_tickets):
                tmp_ticket = self.tickets_for_allocation.pop()
                tmp_ticket.assign_item(
                    filtered_content_items[pointer]['content_item']
                )
                self.allocated_tickets.put_nowait(tmp_ticket)

            # Start with the first one in case we don't have many content items
            pointer = (pointer + 1) % len(filtered_content_items)

        self.ready = True
