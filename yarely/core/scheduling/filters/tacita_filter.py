import datetime
import logging
from xml.etree import ElementTree

from yarely.core.scheduling.constants import TACITA_CONTENT_TRIGGER_THRESHOLD
from yarely.core.scheduling.contextstore.constants import (
    CONTEXT_TYPE_CONTENT_TRIGGER
)
from yarely.core.subscriptions.subscription_parser import (
    ContentItem, ContentDescriptorSet, SubscriptionElement, SubscriptionElementFile
)
from yarely.core.scheduling.filters import DepthFirstFilter


log = logging.getLogger(__name__)


class TacitaFilter(DepthFirstFilter):
    """ This filter checks if personalised content exists and prioritises this
    content. It further checks if the personalised content (from the context
    store) is part of the CDS.

    TODO: create base class that this filter can share with touchinput filter.
    TODO: read out priroity from content item XML (which is a content set?)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.requested_content_files = set()

    def get_tacita_content_request(self):
        recent_event = self.context_store.get_latest_content_items_by_context_type(
            CONTEXT_TYPE_CONTENT_TRIGGER
        )

        log.debug('Tacita recent event: {}'.format(recent_event))

        if not recent_event:
            return None

        content_item_xml_str = recent_event[0]['content_item_xml']
        content_item = None

        content_item_created = recent_event[0]['created_localtime']

        # Check time
        start_time = datetime.datetime.now() - datetime.timedelta(
            seconds=TACITA_CONTENT_TRIGGER_THRESHOLD
        )

        log.debug(content_item_created)
        log.debug(start_time)

        if content_item_created < start_time:
            return None

        if not content_item_xml_str:
            return None

        content_item_xml = ElementTree.fromstring(content_item_xml_str)

        # Use the appropriate parser here
        content_type = content_item_xml.tag

        if content_type == 'content-item':
            content_item = ContentItem(content_item_xml)

        if content_type == 'content-set':
            content_item = ContentDescriptorSet(content_item_xml)

        if isinstance(content_item, ContentDescriptorSet):
            # In this case we want to get all content item files and add these into the set
            content_items = content_item.get_content_items()

            for item in content_items:
                files = item.get_files()
                for file in files:
                    file_source = file.get_sources()[0].get_uri()
                    self.requested_content_files.add(file_source)

        if isinstance(content_item, ContentItem):
            files = content_item.get_files()
            for file in files:
                file_source = file.get_sources()[0].get_uri()
                self.requested_content_files.add(file_source)

        if isinstance(content_item, SubscriptionElementFile):
            # In this case we can just add the content item into the set
            self.requested_content_files.add(content_item)

        return content_item

    def keep_item(self, content_item):
        """ Comparing each item from the CDS whether it matches the touch
        input. Only keeping the item that does match the input.
        """
        log.debug('Tacita requested files: {}'.format(str(self.requested_content_files)))
        log.debug('Tacita from CDS: {}'.format(content_item))

        for content_file in self.requested_content_files:
            log.debug("Tacita comparing {} - {}".format(str(content_file), str(content_item)))
            if str(content_item).startswith(str(content_file)):
                return True

        return False

    def filter_cds(self):
        """ FIXME """

        log.debug("Tacita input filter.")

        self.get_tacita_content_request()

        log.debug(self.requested_content_files)

        if not self.requested_content_files:
            return self.cds

        # Start the filtering process to see if the touch input ContentItem
        # was originally part of the CDS. We only want to play items that were
        # scheduled in the first place.
        filtered_cds = super().filter_cds()

        # Return the original CDS if the touch input wasn't part of the CDS.
        if not filtered_cds:
            log.info("Tacita input not part of original CDS. Ignoring it.")
            return self.cds

        return filtered_cds
