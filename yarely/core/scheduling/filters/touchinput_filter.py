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
import datetime
import logging

# Local (Yarely) imports
from yarely.core.scheduling.constants import TOUCH_INPUT_TIME_THRESHOLD
from yarely.core.scheduling.contextstore.constants import (
    CONTEXT_TYPE_TOUCH_INPUT
)
from yarely.core.scheduling.filters import DepthFirstFilter
from yarely.core.subscriptions.subscription_parser import (
    ContentDescriptorSet
)


log = logging.getLogger(__name__)


class TouchInputFilter(DepthFirstFilter):
    """FIXME."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.touch_content_item = None

    @staticmethod
    def _content_item_comparison_weak(item_a, item_b):
        """ Compare two ContentItem objects with each other in a weak way -
        we only take the filename and path into consideration and ignore
        constraints (as the proper __eq__ method would do).

        """
        if item_a is None or item_b is None:
            log.debug("Item is None")
            return False

        return item_a.get_xml() == item_b.get_xml()

    def _get_touch_input(self):
        ctxt = self.context_store
        recent_event = ctxt.get_latest_content_items_by_context_type(
            CONTEXT_TYPE_TOUCH_INPUT
        )

        if not recent_event:
            return None

        content_item = recent_event[0]['content_item']
        content_item_created = recent_event[0]['created_localtime']

        # Check time
        start_time = datetime.datetime.now() - datetime.timedelta(
            seconds=TOUCH_INPUT_TIME_THRESHOLD
        )
        if content_item_created < start_time:
            return None

        if isinstance(content_item, ContentDescriptorSet):
            return content_item.get_children()[0]

        return content_item

    def keep_item(self, content_item):
        """Determines if the specified item should be kept. If this method
        returns False then the item will be filtered out of the CDS.

        In this implementation, we compare each item from the CDS against the
        touch input. We only keep items that do match the input.

        :param content_item: the item to check.
        :type content_item: a :class:`ContentItem` instance.

        """
        return self._content_item_comparison_weak(
            content_item, self.touch_content_item
        )

    def filter_cds(self):
        """FIXME."""

        log.debug("Touch input filter.")

        self.touch_content_item = self._get_touch_input()

        if not self.touch_content_item:
            return self.cds

        log.debug("Found content item in context store: {}".format(
            str(self.touch_content_item)
        ))

        # Start the filtering process to see if the touch input ContentItem
        # was originally part of the CDS. We only want to play items that were
        # scheduled in the first place.
        filtered_cds = super().filter_cds()

        # Return the original CDS if the touch input wasn't part of the CDS.
        if not filtered_cds:
            log.info("Touch input not part of original CDS. Ignoring it.")
            return self.cds

        return filtered_cds
