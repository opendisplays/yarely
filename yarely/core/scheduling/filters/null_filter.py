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
from yarely.core.scheduling.filters import Filter


class NullFilter(Filter):
    """This null filter just returns the original content descriptor set
    without any filtering.

    """

    def filter_cds(self):
        """Returns the original content descriptor set without any filtering.

        :rtype: FIXME
        :return: FIXME.

        """
        return self.cds
