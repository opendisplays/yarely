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
from xml.etree import ElementTree


class ZMQRPCError(Exception):
    """Base class for ZMQ RPC errors."""
    def __init__(self, msg):
        """:param string msg: a descriptive error message."""
        MSG_PREFIX = 'Invalid RPC XML: '
        super().__init__(MSG_PREFIX + msg)


class ZMQRPC(object):
    """Provides some common ZMQ RPC operations."""

    def _encapsulate_reply(self, children):
        """Wrap the specified child XML elements in a reply element.

        :param children: FIXME.
        :type children: FIXME.

        """
        if hasattr(self, 'params') and 'token' in self.params:
            root = ElementTree.Element(
                'reply', attrib={'token': self.token}
            )
        else:
            root = ElementTree.Element('reply')
        if isinstance(children, ElementTree.Element):
            root.append(children)
        else:
            root.extend(children)
        return root

    def _encapsulate_request(self, children):
        """Wrap the specified child XML elements in a request element.

        :param children: FIXME.
        :type children: FIXME.

        """
        if hasattr(self, 'params') and 'token' in self.params:
            root = ElementTree.Element(
                'request', attrib={'token': self.token}
            )
        else:
            root = ElementTree.Element('request')
        if isinstance(children, ElementTree.Element):
            root.append(children)
        else:
            root.extend(children)
        return root

    def _generate_error(self, msg=None):
        """Generate an XML error element (with the given message if
        specified).

        :param string msg: FIXME.

        """

        if msg:
            error_root = ElementTree.Element('error', attrib={'message': msg})
        else:
            error_root = ElementTree.Element('error')
        return error_root

    def _generate_ping(self):
        """Generate an XML ping element."""
        return ElementTree.Element('ping')

    def _generate_pong(self):
        """Generate an XML pong element."""
        return ElementTree.Element('pong')

    def _handle_request_ping(self, msg_root, msg_elem):
        """
        Handles an incoming ping request.

        This implementation replies to the Handler with a pong.

        :param msg_root: The root element for the incoming ping message.
        :type msg_root: an :class:`xml.etree.ElementTree.Element` instance.
        :param msg_elem: The element representing the ping portion of the
            incoming message.
        :type msg_elem: an :class:`xml.etree.ElementTree.Element` instance.

        """
        return self._encapsulate_reply(self._generate_pong())

    def _handle_zmq_msg(self, msg):
        """Handle a message received over ZMQ.

        :param string msg: the (XML) message to be handled.

        """
        emsg = ("Received message of type '{msg_type}', no callable found.")

        # Everything received over ZMQ should be XML
        root = ElementTree.XML(msg)

        # Special case - registration
        if root.tag == 'register':
            fn = getattr(self, '_handle_register', None)
            if fn and callable(fn):
                return fn(root)
            else:
                raise ZMQRPCError(emsg.format(msg_type='register'))

        # Everything else (i.e request/reply)
        for elem in root:
            fn_name = '_handle_{root}_{elem}'.format(
              root=root.tag, elem=elem.tag
            )
            fn = getattr(self, fn_name, None)
            if fn and callable(fn):
                return fn(root, elem)
            else:
                msg_type = '{rt}->{elem}'.format(rt=root.tag, elem=elem.tag)
                raise ZMQRPCError(emsg.format(msg_type=msg_type))
