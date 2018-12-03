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
import threading
from queue import Queue


log = logging.getLogger(__name__)


class LotteryTicketAllocator(threading.Thread):
    """Base class for lottery ticket allocators. When writing a ticket
    allocator, please make sure that __init__ gets always called.

    """
    def __init__(
        self, thread_name, context_store, filtered_cds, tickets_for_allocation
    ):
        """

        :param string thread_name: FIXME.
        :param context_store: FIXME.
        :type context_store: FIXME.
        :param filtered_cds: FIXME.
        :type filtered_cds: FIXME.
        :param tickets_for_allocation: FIXME.
        :type tickets_for_allocation: FIXME.

        """
        #  """ FIXME - references to context_store and filtered_cds """
        super().__init__(name=thread_name)
        self.thread_name = thread_name

        self.context_store = context_store
        self.cds = filtered_cds

        # Queue of "empty" tickets that can be used to generate tickets.
        self.tickets_for_allocation = tickets_for_allocation

        # Assigned tickets should be stored in this queue. It will be read out
        # by the LotteryScheduler when it expects the output to be done.
        self.allocated_tickets = Queue()

        # Indicates if the ticket allocation has finished.
        self.ready = False

    def allocate_tickets(self):
        """This method will be called once the thread starts in order to
        initiate the lottery ticket allocation. The ticket allocator can use
        empty pre-generated tickets out of self.tickets_for_allocation which is
        a Queue. In future it could block on this queue and wait for an
        additional set of tickets to be made available to this ticket allocator
        (although this functionality we will probably implement later).

        After a certain amount of time the LotteryScheduler will fetch
        self.allocated_tickets. This queue should _only_ consist of lottery
        tickets that have an item assigned to it.

        If the ticket allocation process has finished, self.ready should be set
        to True.

        NOTE: the LotteryScheduler can terminate the ticket allocation
        process at any time and just grab tickets from the queue when it thinks
        it has enough tickets to make the scheduling decision.

        :raises NotImplementedError: always.

        """

        # Either iterate through self.tickets or wait on that queue for new
        # tickets to be assigned. For now it will have a set amount of tickets
        # allocated by the time the ticket allocator gets initialised.

        self.ready = True

        raise NotImplementedError()

    def run(self):
        """Starting the ticket allocation process as soon as the thread
        starts.

        """
        log.debug(
            "Starting ticket allocator: {}".format(self.__class__.__name__)
        )
        self.allocate_tickets()

    def __str__(self):
        return self.__class__.__name__


class LotteryTicket(object):
    """Lottery tickets should be based on this class to allow storing a
    reference to the content item that is allocated to this ticket.

    """

    def __init__(self, item=None, allocated_by=None):
        """
        :param item: FIXME.
        :type item: FIXME.
        :param allocated_by: FIXME.
        :type allocated_by: FIXME.

        """
        self.item = item
        self.allocated_by = allocated_by

    def assign_item(self, item):
        """Assigning content items to a lottery ticket.

        :param item: FIXME.
        :type item: FIXME.

        """
        # TODO - check here if self.item was not none?
        self.item = item

    @classmethod
    def generate_empty_lottery_tickets(cls, amount):
        """Generates a set of empty lottery ticket objects.

        :param integer amount: number of tickets to generate.

        """

        tickets = set()

        for i in range(amount):
            tmp_ticket = cls()
            tickets.add(tmp_ticket)

        return tickets

    def get_item(self):
        """FIXME.

        :rtype: FIXME

        """
        return self.item

    def __repr__(self):
        return str(self.item)


# This local import appears at the bottom of the file to avoid a circular
# import problem (the allocator class in this file extends the
# LotteryTicketAllocator class provided above). Making the allocator
# available at this package level makes for cleaner imports in the rest of
# the scheduling code.


from yarely.core.scheduling.schedulers.lottery.\
    duration_based_allocator import (
      _DurationBasedAllocator as DurationBasedAllocator
)                                                                        # NOQA
from yarely.core.scheduling.schedulers.lottery.\
    equal_distribution_allocator import (
      _EqualDistributionAllocator as EqualDistributionAllocator
)                                                                        # NOQA
from yarely.core.scheduling.schedulers.lottery.random_allocator import (
      _RandomAllocator as RandomAllocator
)                                                                        # NOQA
from yarely.core.scheduling.schedulers.lottery.ratio_allocator import (
      _RatioAllocator as RatioAllocator
)                                                                        # NOQA
from yarely.core.scheduling.schedulers.lottery.recency_based_allocator import (
      _RecencyBasedAllocator as RecencyBasedAllocator
)                                                                        # NOQA


__all__ = [
    "DurationBasedAllocator", "EqualDistributionAllocator", "RandomAllocator",
    "RatioAllocator", "RecencyBasedAllocator"
]
