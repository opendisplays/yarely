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

# Internal Yarely imports
from yarely.core.scheduling.constants import DEFAULT_CONTENT_DURATION
from yarely.core.scheduling.schedulers.lottery import LotteryTicketAllocator


# Lookup table for optimisation: object ID to calculated ratios
_CACHE = dict()
log = logging.getLogger(__name__)


class _DurationBasedAllocator(LotteryTicketAllocator):
    """Allocate LotteryTickets to each ContentItem based on their duration.
    Longer content items will get most tickets, and shorter items not so many.

    """

    FAVOUR_SHORT_ITEMS = 1
    FAVOUR_LONG_ITEMS = 0    # DEFAULT
    VALID_SORT_ORDERS = [FAVOUR_SHORT_ITEMS, FAVOUR_LONG_ITEMS]

    def __init__(self, *args, **kwargs):
        global _CACHE
        super().__init__(*args, **kwargs)

        # Sort order (do we prefer short content items or long ones)
        self.sort_order = self.FAVOUR_LONG_ITEMS
        if 'sort_order' in kwargs:
            self.sort_order = kwargs['sort_order']
            if self.sort_order not in self.VALID_SORT_ORDERS:
                raise ValueError()

        # We maintain a cache for content item durations.
        # Here we reset the cache since object ids may have been reused since
        # the last time this allocator was used.
        _CACHE = dict()

    def allocate_tickets(self):
        """Allocates a proportion of tickets to each content item based
        on their duration.

        """

        # Grab all the items we need to allocate tickets to
        content_items = self.cds.get_content_items()

        # Convert these items to a list of tuples: (content_item, duration)
        content_item_duration_pairs = list()
        for content_item in content_items:
            content_item_duration_pairs.append(
                (content_item, get_duration(content_item))
            )

        # Allocate tickets
        self._allocate(content_item_duration_pairs)

    def _allocate(self, content_item_duration_pairs):
        log.debug("DurationBasedAllocator starting with {} tickets".format(
            len(self.tickets_for_allocation)
        ))

        # Sort items by duration -- initially shortest to longest,
        # but the end result should be that the items we should be giving
        # preference to (as specified by self.sort_order) come at the
        # BEGINNING of the list. That means once we've done the initial sort
        # we then do a quick check to see if we should reverse the list.
        content_item_duration_pairs.sort(key=lambda x: x[1])
        if self.sort_order is self.FAVOUR_LONG_ITEMS:
            content_item_duration_pairs.reverse()

        # Ensure (if possible) that every item gets at least one ticket
        for (content_item, duration) in content_item_duration_pairs:
            # Check we haven't run out of tickets to allocate
            if not self.tickets_for_allocation:
                break

            # Allocate one ticket to this item
            log.debug(
                "item {} with duration of {} seconds has been allocated "
                "1 ticket".format(content_item, duration)
            )
            ticket = self.tickets_for_allocation.pop()
            ticket.assign_item(content_item)
            self.allocated_tickets.put_nowait(ticket)

        # If all the tickets have been allocated now, then we're done already
        if not self.tickets_for_allocation:
            self.ready = True
            return

        # Count up how many more tickets remain for us to allocate
        ticket_count = len(self.tickets_for_allocation)
        log.debug("DurationBasedAllocator has {} tickets remaining".format(
            ticket_count
        ))

        # Calculate the total duration (in seconds)
        (tmp, durations) = zip(*content_item_duration_pairs)
        total_duration = sum(durations)

        # Calculate the ratio of tickets per second of duration
        tickets_per_second = ticket_count / total_duration

        # Allocate the remaining tickets based on this ratio
        for (i, (content_item, duration)) in enumerate(
            content_item_duration_pairs
        ):

            # For each content item we'll calculate how many tickets we should
            # allocate (rounded to the nearest whole number but never more
            # than the number of tickets available.
            tickets_for_item = min(
                round(tickets_per_second * duration),
                len(self.tickets_for_allocation)
            )

            # Occasionally rounding errors mean that the last item
            # gets a different number of tickets than the rounding would have
            # given out... tough, it'll just have to take whatever is left.
            if i is len(content_item_duration_pairs)-1:
                tickets_for_item = len(self.tickets_for_allocation)

            log.debug(
                "item {} with duration of {} seconds has been allocated "
                "{}/{} tickets".format(
                    content_item, duration, tickets_for_item,
                    ticket_count
                )
            )

            # Allocate the right number of tickets and put them in the
            # allocated pool.
            for i in range(tickets_for_item):
                ticket = self.tickets_for_allocation.pop()
                ticket.assign_item(content_item)
                self.allocated_tickets.put_nowait(ticket)

            # Check that there's still some tickets to allocate
            if not self.tickets_for_allocation:
                log.debug("no more tickets to allocate")
                break

        self.ready = True


def get_duration(content_item):
    """Returns athe duration (in seconds) of the specified content item.

    If no PreferredDurationConstraint is specified, then the scheduler's
    default duration is used.

    :param content_item: FIXME.
    :type content_item: FIXME.
    :rtype: float

    """
    global _CACHE

    # Retrieve value from cache if available
    content_item_id = id(content_item)
    if content_item_id not in _CACHE:
        _CACHE[content_item_id] = dict()
    elif 'duration' in _CACHE[content_item_id]:
        return _CACHE[content_item_id]['duration']

    # Get the duration
    duration = content_item.get_duration()
    duration = duration if duration is not None else DEFAULT_CONTENT_DURATION

    # Cache and return the duration
    _CACHE[content_item_id]['duration'] = duration
    return duration
