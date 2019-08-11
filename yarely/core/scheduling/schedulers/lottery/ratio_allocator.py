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
import random

# Internal Yarely imports
from yarely.core.helpers.base_classes.constraint import PlaybackConstraint
from yarely.core.scheduling.constants import DEFAULT_CONTENT_DURATION
from yarely.core.scheduling.schedulers.lottery import LotteryTicketAllocator


benchmark_logger = logging.getLogger('benchmarks')

# Lookup table for optimisation: object ID to calculated ratios
_CACHE = dict()
log = logging.getLogger(__name__)


class _SimplePerItemRatioAllocator(LotteryTicketAllocator):
    """ Allocate LotteryTickets to each ContentItem based on their ratio
    constraints.

    This allocator is not intelligent enough to balance for content duration
    etc.

    """

    def __init__(self, *args, **kwargs):
        global _CACHE
        super().__init__(*args, **kwargs)

        # Need to reset the cache as object ids may be reused
        _CACHE = dict()

    def allocate_tickets(self):
        """ Allocates a proportion of tickets to each content item based
        on their ratio constraints.

        """
        # Grab all the items we need to allocate tickets to
        content_items = self.cds.get_content_items()

        # Convert these items to a list of tuples: (content_item, scaled_ratio)
        content_item_ratio_pairs = list()
        for content_item in content_items:
            content_item_ratio_pairs.append(
                (content_item, get_scaled_ratio(content_item))
            )

        self._allocate(content_item_ratio_pairs)

    def _allocate(self, content_item_ratio_pairs):
        total_ticket_count = len(self.tickets_for_allocation)
        log.debug("RatioAllocator starting with {} tickets".format(
            total_ticket_count
        ))

        # It's highly unlikely that multiplying the ratio (a fraction between
        # 0 and 1) is going to yield nice whole numbers of tickets to allocate.
        # As part of our coping strategy we'll randomly order the items so that
        # if we have too many/too few tickets at the end of allocation we don't
        # always give these to the same item.
        random.shuffle(content_item_ratio_pairs)

        for (content_item, item_ratio) in content_item_ratio_pairs:

            # For each content item we'll calculate how many tickets we should
            # allocate (rounded to the nearest whole number).
            # However, the last items may just have to take whatever is left.
            tickets_for_item = min(
                round(total_ticket_count * item_ratio),
                len(self.tickets_for_allocation)
            )

            # Each item must be allocated at least one ticket
            tickets_for_item = max(tickets_for_item, 1)

            log.debug(
                "item {} with ratio {} has been allocated"
                "{}/{} tickets".format(
                    content_item, item_ratio, tickets_for_item,
                    total_ticket_count
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

        benchmark_logger.info("end_ratio_allocator")


class _RatioAllocator(_SimplePerItemRatioAllocator):
    """ Allocate LotteryTickets to each ContentItem based on their ratio
    constraints and their duration.

    """

    def allocate_tickets(self):
        """ Allocates a proportion of tickets to each content item based
        on their ratio constraints and duration.

        """

        benchmark_logger.info("start_ratio_allocator")

        # Grab all the items we need to allocate tickets to
        content_items = self.cds.get_content_items()

        # Get the total duration for all content items
        total_content_duration = 0
        for c in content_items:
            total_content_duration += get_duration(c)

        # Allocate each item a duration purely based on ratio
        # And then divide the result by the actual duration
        revised_ratios = list()
        total_revised_ratios = 0
        for c in content_items:
            revised_ratio = (
                get_scaled_ratio(c) * total_content_duration / get_duration(c)
            )
            revised_ratios.append(
                revised_ratio
            )
            total_revised_ratios += revised_ratio

        # And then finally scale that number back to a ratio
        revised_ratios = [
            (1/total_revised_ratios) * revised_ratio
            for revised_ratio in revised_ratios
        ]

        # Now we have a sensible ratio so we can do our allocation
        # Convert the new ratios and the content items to a list of tuples in
        # the form (content_item, scaled_ratio)
        self._allocate(list(zip(content_items, revised_ratios)))


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


def get_scaled_ratio(content_item):
    """Returns a scaled ratio value for the specified content item (0-1).

    :param content_item: FIXME.
    :type content_item: FIXME.
    :rtype: float

    """
    global _CACHE

    # Retrieve value from cache if available
    content_item_id = id(content_item)
    if content_item_id not in _CACHE:
        _CACHE[content_item_id] = dict()
    elif 'scaled_ratio' in _CACHE[content_item_id]:
        return _CACHE[content_item_id]['scaled_ratio']

    # Get unscaled ratio for this item
    local_ratio = get_unscaled_ratio(content_item)
    all_ratios = [local_ratio]
    if local_ratio is None:
        specified_ratios = list()
        specified_ratio_sum = 0
        unspecified_ratio_items = [content_item]
    else:
        specified_ratios = [local_ratio]
        specified_ratio_sum = local_ratio
        unspecified_ratio_items = list()

    # Then check for siblings and grab all of their ratios
    # Note that for speed reasons we don't use list comprehensions here
    sibling_ratios = list()
    siblings = content_item.get_siblings()
    for sibling in siblings:
        sibling_unscaled_ratio = get_unscaled_ratio(sibling)
        sibling_ratios.append(sibling_unscaled_ratio)
        all_ratios.append(sibling_unscaled_ratio)
        if sibling_unscaled_ratio is None:
            unspecified_ratio_items.append(sibling)
        else:
            specified_ratios.append(sibling_unscaled_ratio)
            specified_ratio_sum += sibling_unscaled_ratio

    # If we have some items (including this one) without a set
    # ratio, we need to try and calculate them a ratio value.
    unspecified_ratio_count = len(unspecified_ratio_items)
    if unspecified_ratio_count and specified_ratio_sum < 1:
        default_ratio = (1-specified_ratio_sum)/unspecified_ratio_count
    elif unspecified_ratio_count:
        default_ratio = specified_ratio_sum/len(all_ratios)

    # Next we need to make sure that the total ratios add up exactly to 1.
    unspecified_ratios_sum = (
        unspecified_ratio_count * default_ratio
        if unspecified_ratio_count else 0
    )
    all_ratios_sum = specified_ratio_sum + unspecified_ratios_sum
    scale_factor = 1 if all_ratios_sum == 1 else 1 / all_ratios_sum

    # Get info about our parent's ratio
    parent = content_item.get_parent()
    parent_ratio = get_scaled_ratio(parent) if parent is not None else 1

    # Nearly done! Scale and cache the ratios for each item.
    self_plus_siblings = [content_item] + siblings
    for c in self_plus_siblings:

        # Scale each content item's ratio
        unscaled_ratio = get_unscaled_ratio(c)
        sibling_scaled_ratio = (
            unscaled_ratio if unscaled_ratio is not None else default_ratio
        ) * scale_factor

        # OK, local ratio should now be beautifully scaled in line with
        # any siblings, final bit of math just needs to account for the
        # parent ratio
        _CACHE[id(c)]['scaled_ratio'] = parent_ratio * sibling_scaled_ratio

    return _CACHE[content_item_id]['scaled_ratio']


def get_unscaled_ratio(content_item):
    """Returns the associated PlaybackConstraint ratio for the specified
    content item. If no ratio is found, return
    PlaybackConstraint.UNSCALED_RATIO_DEFAULT

    :param content_item: FIXME.
    :type content_item: FIXME.
    :rtype: float

    """
    global _CACHE

    # Retrieve value from cache if available
    content_item_id = id(content_item)
    if content_item_id not in _CACHE:
        _CACHE[content_item_id] = dict()
    elif 'unscaled_ratio' in _CACHE[content_item_id]:
        return _CACHE[content_item_id]['unscaled_ratio']

    # Try to find a PlaybackConstraint for this item (non-recursively) that
    # specifies the ratio.
    local_constraints = content_item.get_constraints(
        recurse_up_tree=False, constraint_type=PlaybackConstraint
    )
    local_ratio_constraints = [
        c for c in local_constraints if c.get_unscaled_ratio() is not None
    ]

    # It should only be valid for there to be 0 or 1 PlaybackConstraints with
    # a ratio specified so we can safely take the first one. Any more than 1
    # PlaybackConstraint gives undefined behaviour anyway.
    try:
        local_ratio = local_ratio_constraints[0].get_unscaled_ratio()
    except IndexError:
        local_ratio = PlaybackConstraint.UNSCALED_RATIO_DEFAULT

    # Cache and return the ratio value
    _CACHE[content_item_id]['unscaled_ratio'] = local_ratio
    return local_ratio
