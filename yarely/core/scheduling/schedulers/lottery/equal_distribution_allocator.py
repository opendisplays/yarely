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
import random

# Local (Yarely) imports
from yarely.core.scheduling.schedulers.lottery import LotteryTicketAllocator


class _EqualDistributionAllocator(LotteryTicketAllocator):
    """Equally distribute available tickets to all content items."""

    def allocate_tickets(self):
        """Allocate the same amount of tickets to all content items. If there
         is more content items than tickets available, then we allocate one
         ticket to a random content item.

         """
        content_items = self.cds.get_content_items()
        content_items_pointer = 0

        # Randomise content list since it's unlikely that the number of
        # tickets divides neatly by the number of content items.
        random.shuffle(content_items)

        # Loop as long as we have tickets and just keep grabbing content items
        # from the list.
        for ticket in self.tickets_for_allocation:
            ticket.assign_item(content_items[content_items_pointer])
            self.allocated_tickets.put_nowait(ticket)
            content_items_pointer = (
                (content_items_pointer + 1) % len(content_items)
            )

        self.ready = True
