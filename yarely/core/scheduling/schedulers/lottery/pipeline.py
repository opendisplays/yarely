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
import json
import logging
import queue
import random
import time

# Local (Yarely) imports
from yarely.core.scheduling.schedulers import Scheduler
from yarely.core.scheduling.schedulers.lottery import (
    LotteryTicket, RatioAllocator
)


# Configuration for the lottery scheduler
# All methods that can allocate tickets. Number of tickets each of these can
# allocate is specified as 'lottery_tickets'.
DEFAULT_TICKET_ALLOCATORS = {
    RatioAllocator: {'lottery_tickets': 1000}
}
DEFAULT_TICKET_ALLOCATOR_TIMEOUT_SEC = 15


log = logging.getLogger(__name__)


class LotterySchedulerPipeline(Scheduler):
    """ The Lottery Scheduler runs a set of ticket allocators (defined in
    LOTTERY_ALLOCATORS, this can be adjusted in the Yarely config) that
    allocate a number of tickets to each content item. Once all tickets were
    allocated, the Lottery Scheduler draws the "winner". The winner ticket
    consists of a reference to the item to be shown which will then be returned
    to the manager instance.
    """

    def __init__(self, scheduler_mgr):
        super().__init__(scheduler_mgr)
        self.ticket_pool = set()
        self.ticket_allocator_threads = set()
        self._initialise_ticket_allocators()

    def _all_ticket_allocators_ready(self):
        """ Loop through all instances and check if the allocators are ready.
        """
        for allocator in self.ticket_allocator_threads:
            if not allocator.ready:
                return False
        return True

    def _draw_winner(self):
        """ FIXME """
        winning_ticket = random.sample(self.ticket_pool, 1)[0]
        self._report_winning_ticket(winning_ticket)
        return winning_ticket

    def _grab_tickets_from_allocators(self):
        for allocator in self.ticket_allocator_threads:
            while True:
                try:
                    allocated_ticket = allocator.allocated_tickets.get_nowait()
                except queue.Empty:
                    break

                # For each allocated ticket, set the corresponding allocator.
                allocated_ticket.allocated_by = allocator
                self.ticket_pool.add(allocated_ticket)

    def _initialise_ticket_allocators(self):
        """ Initialising the list of ticket allocators. In future this will
         read a list of active ticket allocators from the config. Right now
         it just uses the default list.
         """

        # TODO - read in the config and check for individual list of allocators
        self.ticket_allocators = DEFAULT_TICKET_ALLOCATORS

    def _report_allocator_tickets(self):
        """ This method generates a dictionary that for each content item
        counts the number of tickets that were allocated by a certain ticket
        allocator.
        """
        tickets_for_item = dict()

        for ticket in self.ticket_pool:
            item = str(ticket.get_item())

            allocator = str(ticket.allocated_by)

            # If we never looked at the item.
            if item not in tickets_for_item:
                tickets_for_item[item] = {allocator: 0}

            # If we never had the allocator for this item.
            if allocator not in tickets_for_item[item]:
                tickets_for_item[item][allocator] = 0

            tickets_for_item[item][allocator] += 1

        # Check if we have considered all allocators.
        for item, item_value in tickets_for_item.items():
            for allocator in DEFAULT_TICKET_ALLOCATORS:
                if allocator.__name__ in item_value:
                    continue
                log.debug("EXTENDED {}".format(item_value))
                item_value.update({allocator.__name__: 0})

        self.scheduler_mgr.report_internal_scheduler_state(
            'ticket_allocations', json.dumps(tickets_for_item)
        )

    def _report_winning_ticket(self, winning_ticket):
        """ Reporting the winning ticket and the ticket allocator that has
        allocated the content item to this ticket.
        """
        tmp_report = {
            'winning_item': str(winning_ticket.get_item()),
            'ticket_allocator': str(winning_ticket.allocated_by)
        }
        self.scheduler_mgr.report_internal_scheduler_state(
            'winner_draw', json.dumps(tmp_report)
        )

    def _start_lottery_ticket_allocators(self):

        count_total_empty_tickets = 0

        # Get rid of all ticket allocators from the last iteration.
        # Todo: reuse old allocators instead of clearing here.
        self.ticket_allocator_threads.clear()

        for AllocatorClass in self.ticket_allocators:
            config = self.ticket_allocators[AllocatorClass]
            num_of_tickets = config['lottery_tickets']
            count_total_empty_tickets += num_of_tickets
            empty_tickets = LotteryTicket.generate_empty_lottery_tickets(
                num_of_tickets
            )
            tmp_allocator = AllocatorClass(
                AllocatorClass.__name__, self.context_store,
                self.filtered_cds(), empty_tickets
            )
            log.debug(
                "ALLOCATOR {} with {} empty tickets and {} items.".format(
                    AllocatorClass.__name__, len(empty_tickets),
                    len(self.filtered_cds().get_content_items())
                )
            )
            tmp_allocator.start()
            self.ticket_allocator_threads.add(tmp_allocator)

        self.scheduler_mgr.report_internal_scheduler_state(
            'lottery_scheduler_total_empty_tickets', count_total_empty_tickets
        )

    def get_items_to_schedule(self, number_of_items=1):
        """ FIXME """

        self.scheduler_mgr.report_internal_scheduler_state(
            'start_lottery_scheduler_ticket_allocation'
        )

        # Empty ticket pool
        self.ticket_pool = set()

        # (Re-) allocate tickets into the ticket pool.
        self._start_lottery_ticket_allocators()

        # Keep checking if all ticket allocators are ready. We will wait until
        # all ticket allocators are done with the ticket allocation and then
        # grab all the tickets afterwards.
        while not self._all_ticket_allocators_ready():
            time.sleep(0.1)

        self.scheduler_mgr.report_internal_scheduler_state(
            'start_lottery_scheduler_item_drawing'
        )

        # Get all tickets now.
        self._grab_tickets_from_allocators()

        # TODO - cleanup allocator threads here?

        self._report_allocator_tickets()

        # Check if there are any tickets allocated at all.
        if not self.ticket_pool:
            return None

        # Find the winners
        winners = [self._draw_winner() for _ in range(number_of_items)]

        # TODO recursion:
        # - Check if the 'winner' item is a recursive scheduler.
        # - Decision needs to be made whether we want to have recursive
        #   schedulers or recursive ticket allocators instead.
        # - If recursive schedulers, then the schedulers maybe need to allow
        #   passing in a content descriptor set that only consists of some
        #   elements relevant to that recursive scheduler?

        # Get the items and return the list of items.
        return [winner.get_item() for winner in winners]
