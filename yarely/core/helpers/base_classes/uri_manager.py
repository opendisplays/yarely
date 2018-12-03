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
import copy
import urllib.parse

# Local (Yarely) imports
from yarely.core.helpers.base_classes import Manager


class URIManager(Manager):
    """A base class for Managers that launch Handlers in response to URIs."""

    def __init__(self, zmq_req_port, description):
        """
        :param int zmq_req_port: the port number to which Handlers will send
            requests destined for this Manager (i.e. the port on which this
            Manager should open a REP socket).
        :param string description: a text description that will be used
            by :meth:`~Application.process_arguments()` if an alternative is
            not directly supplied to the method.

        """
        super().__init__(zmq_req_port, description)

    def _lookup_executing_handler_with_uri(self, uri):
        with self._lock:
            for handler in self._executing_handlers.values():
                if handler.handler_params['uri'] == uri:
                    return handler
        return None

    def get_uri_handler_stub(self, uri):
        """Get the handler associated with the addressing scheme for
        the specified URI.

        :param string uri: the uri string to be matched.
        :rtype: :class:`~manager.HandlerStub`.

        """
        splitresult = urllib.parse.urlsplit(uri)
        handler = copy.deepcopy(self.get_handler_stub(splitresult.scheme))
        handler.params_over_zmq = {'uri': uri}
        return handler
