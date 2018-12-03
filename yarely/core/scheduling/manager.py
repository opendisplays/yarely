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
import queue
import threading
import time

# Third-party imports
from phemelibrary import PhemeAnalytics

# Local Yarely imports
from yarely.core.content.caching import CacheManager
from yarely.core.displaycontroller import DisplayClient
from yarely.core.helpers.base_classes.application import ApplicationWithConfig
from yarely.core.helpers.decorators.lock_counter import semaphore_lock_decorator
from yarely.core.helpers.execution import application_loop
from yarely.core.scheduling.constants import (
    CONTEXT_STORE_DEFAULT_DB_PATH, DEFAULT_CONTENT_DURATION,
    DISPLAY_ADDITIONAL_KEEP_ALIVE, TOUCH_INPUT_CONTENT_TYPE_APP_SELECTION,
    TOUCH_INPUT_CONTENT_TYPE_BUTTON, TOUCH_INPUT_LAYOUT_MARGIN,
    TOUCH_INPUT_APP_SELECTION_TIMEOUT, TOUCH_INPUT_APP_SELECTION_POSITION,
    TOUCH_INPUT_BUTTON_POSITION
)
from yarely.core.scheduling import ContextConstraintsParser
from yarely.core.scheduling.contextstore import ContextStore
from yarely.core.scheduling.contextstore.constants import CONTEXT_TYPE_PAGEVIEW
from yarely.core.scheduling.display import DisplayManager
from yarely.core.scheduling.filters.pipeline import FilterPipeline
from yarely.core.scheduling.schedulers.lottery.pipeline import LotterySchedulerPipeline


log = logging.getLogger(__name__)


class SchedulingManager(ApplicationWithConfig):
    """The scheduling manager starts and manages the threads that are
    listening for incoming subscription and sensor updates, receives the parsed
    CDS, runs filters on these elements, and calls a scheduler to find the next
    item to be shown on the screen. The scheduler manager then calls the
    appropriate renderers for the next content item.

    """

    def __init__(self):
        description = "Scheduling Manager"
        super().__init__(description)

        # Initialise context and constraints parser
        self.cc_parser = ContextConstraintsParser(self)

        # Storing both the original and filtered CDS
        self.cds = None
        self.filtered_cds = None

        # FIXME - ContextStore takes a path to the SQLite database file
        # self.context_store = ContextStore(None)
        self.context_store = None

        # Allows us to power control the display
        self.display_client = DisplayClient()

        # Queues for handling CDS updates from Context and Constraints Parser
        self.cds_updates = queue.Queue()

        # Initialise filters
        self.filter_pipeline = FilterPipeline(self)

        # Initialise scheduler, can be switched to other scheduler
        self.scheduler_pipeline = LotterySchedulerPipeline(self)

        # Currently active piece of content. This is a reference to a Display
        # instance. Display instances store the current item as well as a
        # reference to the currently displayed renderer subprocess. We will not
        # initialise it yet as the Manager instance might not have started yet
        # properly. We will initialise this one as soon as we need it.
        self.display_manager = DisplayManager(self)

        # Current timer that will call the item scheduling method to trigger a
        # running the scheduler to find a new item.
        self.item_scheduling_timer = None

        # Cache Manager that we will initialise as soon as we need it
        self.cache_manager = None

        # Analytics library will be initialised as soon as we need it
        self.analytics = None

        # TODO - get this from config!
        self.number_of_items = 1  # Todo: we only support 1 at the moment.
        self.display_resolution_width = 1920
        self.display_resolution_height = 1080

        # Check whether we are using extended analytics reporting that consists
        # of the current state of the scheduler.
        self.extended_analytics = False

        # Flag that counts the number of times item scheduling was called.
        self.semaphore_lock_decorator_flag = 0

    def _cache_cds(self):
        """Add all items to the cache queue from CacheManager."""

        # Get all content items and add one by one to the cache queue.
        content_items = self.cds.get_content_items(flatten=True)
        for content_item in content_items:
            self.cache_manager.cache_file(content_item)

    def _display_split_screen(self, items):
        """ Split items on the screen and show multiple items at the time. """

        if not items:
            return

        # Handle our standard case here if there is just one item to show.
        if len(items) == 1:
            self.display_manager.display_item(items[0])
            return

        # TODO - error handling? Check if renderer started successfully.
        # TODO - error handling in Display
        # if not successful, start immediately new item scheduling to get a
        # different piece of content.
        for i in range(len(items)):
            # Start on the top with playing the image.
            layout_y = (
                (self.display_resolution_height*i / len(items)) +
                self.display_resolution_height / len(items)
            )

            # Always line up with the left hand side of the screen.
            layout_x = 0

            # Make sure it uses up the entire width and height it can.
            layout_width = self.display_resolution_width
            layout_height = self.display_resolution_height / len(items)

            tmp_layout = {
                "layout_style": "x_y_width_height", "layout_x": str(layout_x),
                "layout_y": str(layout_y), "layout_width": str(layout_width),
                "layout_height": str(layout_height)
            }

            # Displaying this item. Items probably won't appear at the very
            # same time.
            self.display_manager.display_item(items[i], tmp_layout, i)

    def _get_item_by_content_type(self, content_type):
        """ Get the first content item of a given content type! """
        if not self.cds:
            return None

        content_items = self.cds.get_content_items()

        for content_item in content_items:
            if content_item.get_content_type() == content_type:
                return content_item

        return None

    def _initialise_analytics(self):
        # Prevent Yarely from crashing when tracking_id wasn't specified in the
        # config by setting it to None. In this case the analytics module will
        # not be tracking anything!
        analytics_tracking_id = self.config.get(
            'Analytics', 'tracking_id', fallback=None
        )

        self.extended_analytics = self.config.get(
            'Analytics', 'activate_extended_analytics', fallback=False
        )

        if analytics_tracking_id is None:
            log.error(
                "Analytics tracking_id not specified in Yarely config!"
            )

        self.analytics = PhemeAnalytics(analytics_tracking_id)

    def _initialise_cache_manager(self):
        cache_dir = self.config.get(
            'CacheFileStorage', 'CacheLocation', fallback="/tmp"
        )
        self.cache_manager = CacheManager(cache_dir)
        self.cache_manager.start()

    def _initialise_constants(self):
        """ Initialising some constants such as default content duration. """

        # Get the default content duration. Overwrite from config.
        self.content_duration = self.config.get(
            'Scheduling', 'DefaultContentDuration',
            fallback=DEFAULT_CONTENT_DURATION
        )

    def _initialise_context_store(self):
        # Same as with analytics, we want to initialise it when we actually
        # need it and after everything has loaded.
        context_store_path = self.config.get(
            'ContextStore', 'ContextStorePath',
            fallback=CONTEXT_STORE_DEFAULT_DB_PATH
        )
        self.context_store = ContextStore(context_store_path)

    def _initialise_display_manager(self):
        self.display_manager = DisplayManager(self)

    def _initialise_touch_button(self):
        """ This is initialising the touch button window. If the content
        descriptor set consists of a content item of a `touch button` type,
        then it will be initialised and displayed over all other existing
        windows.
        """

        log.debug("Initialising touch button.")

        # Stop here if there are no content items at all.
        if not self.cds:
            log.debug("No CDS, stopping initialisation.")
            return

        # Stop here if we have initialised the touch button already.
        active_touch_button = (
            self.display_manager.get_active_item(TOUCH_INPUT_BUTTON_POSITION)
        )[0]
        if active_touch_button:
            log.debug("Touch button was already initialised.")
            return

        # Stop here if the display is not touch-enabled.
        # It must consist of both the touch button and the app selection page.
        content_item_touch = self._get_item_by_content_type(
            TOUCH_INPUT_CONTENT_TYPE_BUTTON
        )
        content_item_app_selection = self._get_item_by_content_type(
            TOUCH_INPUT_CONTENT_TYPE_APP_SELECTION
        )

        if not (content_item_touch and content_item_app_selection):
            log.debug("Touch button and/or app selection page not in CDS.")
            return

        # Make it a square button. This should match the display resolution.
        # This is optimised for 1920x1080 displays.
        # Todo: make this variable
        layout_width = 200
        layout_height = 130

        # Align on the bottom right.
        layout_y = TOUCH_INPUT_LAYOUT_MARGIN
        layout_x = (
            self.display_resolution_width - layout_width
            - TOUCH_INPUT_LAYOUT_MARGIN
        )

        touch_button_layout = {
            "layout_style": "x_y_width_height", "layout_x": str(layout_x),
            "layout_y": str(layout_y), "layout_width": str(layout_width),
            "layout_height": str(layout_height),
            "layout_window_level_increase": str(1)
        }

        self.display_manager.display_item(
            content_item_touch, touch_button_layout,
            TOUCH_INPUT_BUTTON_POSITION
        )

    def _initialise_touch_selection(self):

        log.debug("Initialising touch selection.")

        layout_width = (
            self.display_resolution_width - TOUCH_INPUT_LAYOUT_MARGIN * 2
        )
        layout_height = 130

        # Align on the bottom right.
        layout_y = TOUCH_INPUT_LAYOUT_MARGIN
        layout_x = (
            self.display_resolution_width - layout_width
            - TOUCH_INPUT_LAYOUT_MARGIN
        )

        tmp_layout = {
            "layout_style": "x_y_width_height", "layout_x": str(layout_x),
            "layout_y": str(layout_y), "layout_width": str(layout_width),
            "layout_height": str(layout_height),
            "layout_window_level_increase": str(2)
        }

        content_item_app_selection = self._get_item_by_content_type(
            TOUCH_INPUT_CONTENT_TYPE_APP_SELECTION
        )

        # Make it visible!
        self.display_manager.display_item(
            content_item_app_selection, tmp_layout,
            TOUCH_INPUT_APP_SELECTION_POSITION
        )

        threading.Timer(
            TOUCH_INPUT_APP_SELECTION_TIMEOUT,
            self.display_manager.remove_item, kwargs={
                'position': TOUCH_INPUT_APP_SELECTION_POSITION
            }
        ).start()

    def _start_item_scheduling_timeout(self, timeout=5):
        """ Starts new timeout for item scheduling and kills existing one.
        In case we didn't find an item to schedule, we wouldn't pass in a
        specific timeout - so we set it to 5 seconds.
        """

        self.report_internal_scheduler_state('start_item_scheduling_timeout')

        # First stop  current timeout in case there is one.
        self._stop_item_scheduling_timeout()

        self.item_scheduling_timer = threading.Timer(
            timeout, self.item_scheduling
        )
        self.item_scheduling_timer.start()

    def _stop_displaying_items(self):
        if self.display_manager is not None:
            self.display_manager.remove_items()

    def _stop_item_scheduling_timeout(self):
        if self.item_scheduling_timer is not None:
            self.item_scheduling_timer.cancel()

    def _track_pageview_for_context_store(self, item):
        """Storing the currently showing item in the internal context store.

        """
        if self.context_store is None:
            self._initialise_context_store()

        self.context_store.add_context(CONTEXT_TYPE_PAGEVIEW, item)

    def _track_pageview_for_ixion(self, item):
        """ We extract the URI and both MD5 and SHA1 hash from the item and
        report it back to the analytics service. For the latter we start a new
        thread so that the application doesn't block on this.

        """
        if self.analytics is None:
            self._initialise_analytics()

        # We are only reporting the first URI in the list.
        content_uri = str(item)
        content_file = item.get_files()[0]

        # Trying to get the MD5 and SHA1 hash of the content item.
        try:
            content_md5 = content_file.get_md5_hash()
        except NameError:
            content_md5 = None

        try:
            content_sha1 = content_file.get_sha1_hash()
        except NameError:
            content_sha1 = None

        self.analytics.track_pageview_async(
            document_location=content_uri, document_hash_md5=content_md5,
            document_hash_sha1=content_sha1
        )

    def _update(self, cds):
        """This method will update the internal CDS only if the new CDS is
        different to the old CDS. If the update was performed, this method will
        return 'True', in any other cases 'False'. With each update that
        consists of new files it will also add these to the cache.

        """

        # Stop here if the new CDS equals the stored one.
        if self.cds == cds:
            return False

        # Replace stored content descriptor set in case it is different and
        # return True to trigger new content scheduling.
        self.cds = cds
        return True

    @semaphore_lock_decorator
    def item_scheduling(self):
        """Walk through the whole process of scheduling content items. This
        consists of (1) stopping all background timeouts that could start
        this thread, (2) calling the filtering pipeline, (3) request an item
        to be shown on the screen based on the filtered set.

        If a ContentItem was selected by the scheduler, we will display it on
        the screen and start the timeout to rerun this method after the item
        duration. If no item duration was specified, we will just use
        DEFAULT_CONTENT_DURATION for the timeout. If no item was selected or if
        all items were filtered out, we will rerun this method after the
        default timeout. If the item that was selected is the same as the
        currently shown item, we will rerun this method either after the
        remaining content duration (if specified) or after default duration.

        """

        # Report our internal state.
        self.report_internal_scheduler_state('start_item_scheduling')

        # Kill the timer thread here if there is one - just to make sure that
        # this method gets called only once (even if a subs update comes in).
        self._stop_item_scheduling_timeout()

        self.report_internal_scheduler_state('start_filter')
        self.filtered_cds = self.filter_pipeline.filter_cds(self.cds)

        # Check if there is any items left at all
        if not self.filtered_cds:
            # Make sure we take the current item offline if there was one.
            self._stop_displaying_items()

            # This will trigger new drawing in case there will be new items.
            self._start_item_scheduling_timeout()
            return

        new_item = self.scheduler_pipeline.get_items_to_schedule(1)

        # Check if we got an item at all.
        if new_item is None or not new_item:
            self._start_item_scheduling_timeout()
            return

        # We only handle the case of one item at a time here.
        new_item = new_item[0]

        # Find the longest content duration, using default duration if None
        # is specified. If we want to display multiple content items, we will
        # stick to the longest one in case that's a video.
        # Get the duration of the new content item.
        new_item_duration = (
            new_item.get_duration() if new_item.get_duration() is not None
            else DEFAULT_CONTENT_DURATION
        )

        # Now lets calculate the 'keep alive' duration for the display. This
        # should be a few seconds longer than the content duration.
        display_keep_alive_duration = (
            new_item_duration + DISPLAY_ADDITIONAL_KEEP_ALIVE
        )

        # Only continue scheduling item if it is different to the current item.
        active_item, active_timestamp = self.display_manager.get_active_item()

        if new_item == active_item:

            logging.debug("SAME ITEM!")

            # Check the time difference between now and item first time
            # displayed and compare it with the content duration.
            active_item_duration = active_item.get_duration()

            # Make sure we ping the display to stay alive also if the content
            # didn't change.
            self.display_client.keep_display_alive_duration(
                display_keep_alive_duration
            )

            # If we don't have a content duration it doesn't matter, we can
            # just restart item scheduling with default timeout.
            # We will also ping the analytics here so that the monitoring won't
            # complain that the display is not reporting anything (for the case
            # that the schedule only consists of one item).
            if active_item_duration is None:
                # active_item and new_item are the same in this case.
                self.report_pageview(active_item)
                self._start_item_scheduling_timeout(DEFAULT_CONTENT_DURATION)
                return

            # Otherwise we want to make sure that the item restarts after its
            # time runs out, especially important for videos.
            time_difference = time.time() - active_timestamp

            # Stop here if the item still has time left. Restart timeout in
            # this case with the amount of time the item has left though.
            if time_difference < active_item_duration:
                self._start_item_scheduling_timeout(int(time_difference))
                return

            # Otherwise continue and re-schedule the piece of content.

        log.debug("NEW ITEM TO SCHEDULE: {}".format(new_item))

        # Errors are now handled by Display Manager.
        # If the renderer was able to display the content item, it will
        # automatically trigger a page view event. Otherwise it will trigger
        # item scheduling.
        self.display_manager.display_item(new_item)

        # We just assume here that it worked out to show the item and keep
        # the display awake. This will keep the last item visible on the
        # screen.
        self.display_client.keep_display_alive_duration(
            display_keep_alive_duration
        )

        # Restart item scheduling after the content duration of new item.
        self._start_item_scheduling_timeout(new_item_duration)

        log.debug("Timeout: {}".format(self.item_scheduling_timer))

    def main(self):
        """Running in the background and constantly waiting for new updates
        coming in through the cds_update queue. It will trigger new item
        scheduling if the updated CDS differs to the previously stored CDS.

        """

        log.debug("Waiting for Subscription Updates.")

        while True:
            try:
                # Block on queue for one second.
                latest_cds_update = self.cds_updates.get(True, 1)
            except queue.Empty:
                # Skip the current loop if we didn't get an updated CDS.
                continue

            # If the CDS wasn't updated because it equals the old one, then we
            # can just skip this one. Otherwise we want to re-initiate caching
            # and rescheduling.
            if not self._update(latest_cds_update):
                continue

            log.debug(
                "Received new Subscription Update with {} items".format(
                    len(latest_cds_update.get_content_items())
                )
            )

            # Cache all items since we got some new
            self._cache_cds()

            # Start item scheduling
            self.item_scheduling()

            # Check if we have to (re-) initialise the touch button.
            self._initialise_touch_button()

    def report_event(self, category, action, value, label=None):
        """ Report a custom event for our analytics service. This is just a wrapper around the
         native library made accessible to all child processes of the scheduler.

         This method is asynchronous.
         """
        self.analytics.track_event_async(
            category=category, action=action, value=value, label=label
        )

    def report_internal_scheduler_state(self, state, value=1):
        """Report the current state of the scheduler back to the analytics
        service. As we are using the async method of the Ixion package, this
        method is thread-safe.

        Extended analytics logging must be activated in the yarely config under
        'Analytics' with 'activate_extended_analytics' set to True.

        """

        # Stop here if we don't have extended analytics activated (default).
        if not self.extended_analytics:
            return

        # The category will be parsed by the backend.
        category = "yarely_scheduler_state"
        action = state
        label = 'Current yarely scheduler state is {}'.format(state)

        log.debug("REPORTING {label} with value {value}".format(
            label=label, value=value
        ))

        self.analytics.track_event_async(
            category=category, action=action, value=value, label=label
        )

    def report_pageview(self, item):
        """ Tracking the page view of an item for the context store and
        external analytics service. This method is asynchronous.
        """
        self._track_pageview_for_ixion(item)
        self._track_pageview_for_context_store(item)

    def start(self):
        """First start the context and constraints parser as a separate
        thread and then start the scheduler manager main method to listen
        for subscription and sensor updates.

        """

        log.info("|===================================|")
        log.info("|====== STARTING SCHEDULER V2 ======|")
        log.info("|===================================|")

        # Initialise some packages first.
        self._initialise_constants()
        self._initialise_cache_manager()
        self._initialise_analytics()
        self._initialise_display_manager()

        # Start context and constraints parser, scheduler and display manager.
        self.cc_parser.start()
        self.display_manager.start()
        self.main()

    def stop(self):
        """Call the stop method for the context and constraints parser before
        we are stopping the manager.

        """
        self.cc_parser.stop()
        self.display_manager.stop()


if __name__ == "__main__":
    application_loop(SchedulingManager)
