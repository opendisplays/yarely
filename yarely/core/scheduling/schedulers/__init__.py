# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


# Local (Yarely) imports
from yarely.core.scheduling.constants import CONTEXT_STORE_DEFAULT_DB_PATH
from yarely.core.scheduling.contextstore import ContextStore


class Scheduler(object):
    """A scheduler must always extend this base class. It should implement
    get_item_to_schedule. It is expected that this method returns at any time
    the item that should be _now_ shown on the display. This could be the same
    item that is on the screen right now, or a new item which would trigger
    rescheduling.

    Each scheduler has access to the manager instance which consists of the
    content descriptor set, currently played item on the screen, duration left,
    access to the Yarely config instance, and all other context information.

    """

    def __init__(self, scheduler_mgr):
        self.scheduler_mgr = scheduler_mgr
        self.context_store_local = ContextStore(CONTEXT_STORE_DEFAULT_DB_PATH)

    def config(self):
        """FIXME.

        :rtype: FIXME
        :return: FIXME.

        """
        return self.scheduler_mgr.config

    def context_store(self):
        """FIXME.

        :rtype: FIXME
        :return: FIXME.

        """
        return self.context_store_local

    def filtered_cds(self):
        """Returns a reference to the filtered content descriptor set that is
        stored in the scheduler manager instance.

        :rtype: FIXME
        :return: FIXME.

        """
        return self.scheduler_mgr.filtered_cds

    def get_item_to_schedule(self):
        """FIXME.

        :raises NotImplementedError: always.

        """
        #  """ FIXME - get cds, pick item, check for recursion, return item """

        # Get the latest and content descriptor set consisting of items that
        # are eligible to play.
        cds = self.filtered_cds()
        if cds:
            # Of these items pick one to be displayed on the screen. Return
            # this item.
            pass

        raise NotImplementedError()
