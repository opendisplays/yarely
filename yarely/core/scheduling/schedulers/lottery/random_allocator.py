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

# Internal Yarely imports
from yarely.core.scheduling.schedulers.lottery import LotteryTicketAllocator


class _RandomAllocator(LotteryTicketAllocator):
    """Randomly distribute available tickets to content items."""

    def allocate_tickets(self):
        """Randomly allocate tickets to content items. This makes no
        guarantees that every item will be given tickets -- it's random :).


        """

        content_items = self.cds.get_content_items()  # a list

        # Loop as long as we have tickets and just keep grabbing random
        # content items from the list -- content items may be chosen
        # multiple times (random.choice() samples with replacement).
        for ticket in self.tickets_for_allocation:
            ticket.assign_item(random.choice(content_items))
            self.allocated_tickets.put_nowait(ticket)

        self.ready = True
