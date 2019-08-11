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

log = logging.getLogger('benchmarks')
benchmark_logger = logging.getLogger('benchmarks')


class _RecencyBasedAllocator(LotteryTicketAllocator):
    """Distribute tickets based on the count of recently played content items.

    """

    def _least_played_content_items(self):
        # Getting the counts for content items that were played within within
        # the last UNTIL_DATETIME_COUNT hours.
        until_datetime = datetime.now() - UNTIL_DATETIME_COUNT
        counts = self.context_store().get_latest_content_item_played(
            context_type=CONTEXT_TYPE_PAGEVIEW, until_datetime=until_datetime
        )
        counts = list(reversed(counts))
        return counts

    def allocate_tickets(self):
        """Allocate 1/2 of all tickets to the least played content item,
        then 1/2 of the remaining tickets to the next least played item etc.
        until we run out of tickets. This way we prioritise content items that
        haven't been played for a long time.

        """

        benchmark_logger.info("start_recency_allocator")

        # Get list of content items and generate set for faster lookup.
        cds_list = self.cds.get_content_items()

        # Prepare a dict and set of each content item for efficient lookups
        # later-on.
        str_to_item_cds = dict()
        cds_set = set()

        for item in cds_list:
            item_str = str(item)
            str_to_item_cds[item_str] = item
            cds_set.add(item_str)

        # Get all items that were played from the Context Store.
        played_content_items = self._least_played_content_items()

        log.debug("Nu of played content items {}".format(
            len(played_content_items)
        ))

        # Filter items out that are not eligible to play right now.
        to_remove = list()
        filtered_str_set = set()  # For efficient lookups...

        for played_item_cds in played_content_items:
            item_str = str(played_item_cds['content_item'])
            if item_str not in cds_set:
                to_remove.append(played_item_cds)
                continue
            filtered_str_set.add(item_str)

        filtered_content_items = played_content_items

        for remove_item in to_remove:
            filtered_content_items.remove(remove_item)

        # Add those that have not been played

        for item in cds_list:
            if str(item) in filtered_str_set:
                continue
            tmp_entry = {'content_item': item, 'num_of_entries': 0}
            filtered_content_items.insert(0, tmp_entry)

        # Our pointer for walking through the list of filtered content items.
        pointer = 0

        while self.tickets_for_allocation:
            # Always allocate half of the available tickets to the first
            # content item in the list
            num_of_tickets = int(len(self.tickets_for_allocation)/2) + 1
            benchmark_logger.debug("{} tickets for {}".format(
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

        benchmark_logger.info("end_recency_allocator")
