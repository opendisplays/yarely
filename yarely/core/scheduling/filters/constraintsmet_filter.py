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
from yarely.core.scheduling.filters import ConditionFilter


class ConstraintsAreMetFilter(ConditionFilter):
    """Calls the constraints_are_met method on each of the entries in the CDS.
    If there is a content item that doesn't match the constraints, it will be
    deleted from the content descriptor set.

    """

    def _get_condition(self):
        """For running a simple date/time constraints filter we just need to
        return a None condition.

        """
        return None
