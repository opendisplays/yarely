#!/usr/bin/env python3


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

# Local (Yarely) imports
from yarely.core import platform
from yarely.core.helpers.base_classes import PullHandler, HandlerError
from yarely.core.helpers.execution import application_loop

log = logging.getLogger(__name__)

HANDLER_DESCRIPTION = "Handler for file-based subscription sources"


class FileHandlerError(HandlerError):
    """Base class for file handler errors."""
    pass


class FileHandler(PullHandler):
    """The FileHandler class provides a handler for file-based
    subscription sources.

    """

    def __init__(self):
        super().__init__(HANDLER_DESCRIPTION)

    def _handle_reply_params(self, msg_root, msg_elem):
        super()._handle_reply_params(msg_root, msg_elem)
        self.file_source = platform.get_local_path_from_uri(self.params['uri'])

    def read(self):
        """Attempt to read XML from the file associated with this handler.
        Successfully read XML will be sent on to the Manager associated
        with this handler.

        """
        # Pull the XML from the file
        try:
            with open(self.file_source) as file_handle:
                xml = file_handle.read().strip()
        except IOError as e:
            self._fail('Error reading path: {e}'.format(e=e))
            return

        # Send XML to the manager
        try:
            # FIXME - Ultimately we don't want to send the URI back
            # The manager should know which URI we're handling?
            # (Although this would change again when handlers do >1 URI)
            uri = platform.get_uri_from_local_path(self.file_source)
            etree = self._encapsulate_request(
                self._generate_subscription_update(uri, xml)
            )
            self.zmq_request_queue.put_nowait(etree)
        except Exception as e:
            self._fail('Error writing update event: {e}'.format(e=e))
            return

        self._success()

    def start(self):
        """Main entry point."""
        super().start()
        log.info('File Handler Launched')


if __name__ == "__main__":
    application_loop(FileHandler)
