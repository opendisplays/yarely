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
from yarely.core.scheduling.filters import DepthFirstFilter


class ConditionFilter(DepthFirstFilter):
    """The condition filter is capable of filtering the content descriptor set
    by a specified condition which will be passed through to the
    constraints_are_met() method.

    """

    def _get_condition(self):
        """This method will be called to retrieve the condition to be used
        for the filter. This method must be overwritten for the Filter to work
        properly.

        :raises NotImplementedError: always.

        """
        raise NotImplementedError()

    def keep_item(self, content_item):
        """Determines if the specified item should be kept. If this method
        returns False then the item will be filtered out of the CDS.

        In this implementation, we this method calls constraints_are_met
        recursively on all children of the root element (depth first). If
        constraints aren't met, the child will be removed from its parent.

        :param content_item: the item to check.
        :type content_item: a :class:`ContentItem` instance.

        """
        return content_item.constraints_are_met(
            condition=self._get_condition(), ignore_unimplemented=True,
            recurse_up_tree=True
        )
