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
import os
import threading
import time
import uuid
from xml.etree import ElementTree

# Third party imports
import zmq

# Local (Yarely) imports
from yarely.core.helpers.base_classes.manager import (
    SubprocessExecutionWithErrorCapturing
)
from yarely.core.helpers.base_classes.zmq_rpc import ZMQRPC
from yarely.core.helpers.zmq import (
    ZMQ_ADDRESS_INPROC, ZMQ_ADDRESS_LOCALHOST, ZMQ_RENDERER_REQ_PORT,
    ZMQ_SOCKET_LINGER_MSEC
)
from yarely.core import platform
import yarely.core.content.caching  # circular import...
from yarely.core.content import (
    FADING_ANIMATION_DURATION, ARG_RENDER_NAMESPACE, get_initial_args
)


log = logging.getLogger(__name__)
DEFAULT_POSITION = 0  # Default position of the main content.


class RendererError(Exception):
    """FIXME."""
    pass


class ExecutingRenderer(object):
    """ Each instance of this class holds a reference to a renderer that is (or
    will be) displaying a content item on the display.
    """
    def __init__(
            self, subprocess, position, renderer_uuid, content_item,
            is_visible=False, active_timestamp=None
    ):
        """
        :param subprocess: reference to the corresponding subprocess.
        :param position: unique identifier for the position on which the
        rendeer is displaying content.
        :param renderer_uuid: unique identifier for the renderer (this is
        required to recognize ZMQ replies from the renderer.
        :param content_item: content_item instance that is (or will be)
        displayed on the screen.
        :param is_visible: True indicates that the renderer is currently
        visible on the screen, False otherwise.
        :param active_timestamp: time at which the content item became visible
        on the screen.
        :return:
        """
        self.content_item = content_item
        self.subprocess = subprocess
        self.position = position
        self.renderer_uuid = renderer_uuid
        self.is_visible = is_visible
        self.active_timestamp = active_timestamp
        self.has_registered = False

    def start(self):
        """ Start the subprocess linked to this renderer. """
        self.subprocess.start()

    def stop(self):
        """ Stop the subprocess linked to this renderer and mark it as not
        visible anymore.
        """
        log.debug("stopping... {}".format(self.position))
        self.subprocess.stop()
        self.is_visible = False


class DisplayManager(ZMQRPC):
    """ Managing renderer and items displayed on the screen at different
    positions.

    In order to show an item on the screen, display_item method needs to be
    called by passing in the Content Item, and optional layout and position
    parameters. Please see content_item for more detail.

    This class holds references to all running renderers and maintains access
    to these references in a manner that is thread-safe. Further it maintains
    only one visible renderer at a position - all other renderers will be
    stopped and removed.

    Each time a new item is displayed on the screen, this class waits for
    renderers to report that the preparation was successful in which case the
    previous renderer at the same position will be terminated, or that the
    preparation has failed in which case the item scheduling process will be
    triggered to find a new item.
    """

    def __init__(self, scheduler_mgr):
        """
        :param scheduler_mgr: FIXME.
        :type scheduler_mgr: FIXME.

        """
        self.scheduler_mgr = scheduler_mgr
        self._zmq_display_renderer_reply_thread = None

        # Initialise ZMQ
        self.zmq_context = zmq.Context()
        self.zmq_scheduler_term_identifier = "zmq_scheduling_term_{id}".format(
            id=id(self)
        )

        self.cache = None

        # Keeping all renderers in a dictionary (key is renderer_uuid).
        self._renderers_lock = threading.RLock()
        self._renderers = dict()

    def _initialise_cache(self):
        cache_dir = self._config().get(
            'CacheFileStorage', 'CacheLocation', fallback="/tmp"
        )
        self.cache = yarely.core.content.caching.Cache(cache_dir)

    def _check_item_is_at_position(self, item, position):

        renderer = self._get_renderer_at_position(position)

        if not renderer:
            return False

        return renderer.content_item == item

    def _cleanup_renderers(self, position=DEFAULT_POSITION):
        """ Delete all renderers that have registered but are not visible at
        a given position.
        """
        to_delete = list()

        with self._renderers_lock:
            for renderer in self._renderers.values():

                if renderer.position != position:
                    continue

                # Skip each renderer that hasn't registered yet as it may be
                # in the process of becoming visible.
                if not renderer.has_registered:
                    continue

                # Skip each renderer that is visible.
                if renderer.is_visible:
                    continue

                # Delete all renderer that are not visible but have registered.
                to_delete.append(renderer.renderer_uuid)

        for renderer_uuid in to_delete:
            # Stop each renderer in a clean manner and then remove from dict.
            self._stop_renderer(renderer_uuid)
            self._remove_renderer(renderer_uuid)

    def _config(self):
        return self.scheduler_mgr.config

    def _display_item(self, item, layout, position):
        """ Start new renderer and take old item off the screen.  This method
        will block until the renderer has started.
        """
        log.debug("Display {item} at position {position}".format(
            item=str(item), position=position)
        )

        content_type = item.get_content_type()
        args = get_initial_args(content_type)

        # If the item is already up on the display and the args for the
        # content time indicate that it does not need to be restarted,
        # then we skip and just leave it on.
        if self._check_item_is_at_position(item, position) and not args['restart_renderer']:
            log.debug(
                "Item {item} already at position {pos}. Not taking "
                "it off again.".format(item=item, pos=position)
            )
            return

        # Now we can start the renderer and wait for it to register.
        # Anything else will be done in self._handle_request_finished_loading.
        renderer_id = self._start_renderer(item, position, layout)
        log.debug("Started renderer with id: {}".format(renderer_id))

    @staticmethod
    def _generate_params(params):
        """Helper to generate valid params XML."""
        params_root = ElementTree.Element('params')
        param = ElementTree.Element(
            'param', attrib={'name': 'token', 'value': 'UNUSED'}
        )
        params_root.append(param)
        for key, value in params.items():
            param = ElementTree.Element(
                'param', attrib={'name': key, 'value': value}
            )
            params_root.append(param)
        return params_root

    def _get_renderer(self, renderer_uuid):
        """ Get renderer instance for given renderer_uuid or None if it doesn't
        exist.
        """
        with self._renderers_lock:
            if renderer_uuid not in self._renderers:
                return None

            return self._renderers[renderer_uuid]

    def _get_renderer_at_position(self, position):
        with self._renderers_lock:
            for renderer_uuid, renderer in self._renderers.items():
                if renderer.position == position and renderer.is_visible:
                    return renderer
            return None

    def _get_renderer_uuid(self, msg_elem):
        """ Extract the renderer ID from a ZMQ message. """

        try:
            renderer_uuid = msg_elem.attrib['id']
        except KeyError:
            log.error("Invalid ZMQ message: {}".format(
                ElementTree.tostring(msg_elem)
            ))
            return None

        if not self._get_renderer(renderer_uuid):
            log.error("Renderer reporting that is not registered: {}".format(
                id
            ))
            return None

        return renderer_uuid

    @classmethod
    def _get_yarely_module_starter_path(cls):
        return os.path.join(
            cls._get_yarely_parent(), 'yarely', 'starters',
            'yarely_module_starter.sh'
        )

    @staticmethod
    def _get_yarely_parent():
        """Return a string indicating the directory to change into.
        Default: '$HOME/proj'

        The default value may be overridden by setting the environment variable
        YARELY_PARENT.

        Borrowed from /misc/deployment/starters/common.py
        """

        if "YARELY_PARENT" in os.environ:
            return os.environ["YARELY_PARENT"]

        return os.path.join(os.environ.get("HOME"), "proj")

    def _lookup_executing_renderer_with_token(self, token):
        with self._renderers_lock:
            for renderer in self._renderers.values():
                if renderer.subprocess.has_token(token):
                    return renderer
        return None

    def _set_renderer_visible(self, renderer):
        """ There can be only one visible renderer at a time at one position.
        This method will maintain only one visible renderer at a time at one
        position and thus trigger the following:

        - The new renderer will be marked as visible.
        - All other renderers at the same position, that are registered, will
          be stopped and removed from the internal dictionary.

        Only the renderer associated to `renderer_uuid` will remain active and
        visible.
        """
        with self._renderers_lock:
            log.debug("Making {} visible at {}".format(
                renderer.content_item, renderer.position
            ))

            # Now we can mark this renderer as visible.
            renderer.is_visible = True
            renderer.active_timestamp = time.time()

            # All other renderers at this position should be marked as not
            # visible.
            for iter_renderer in self._renderers.values():
                if renderer is iter_renderer:
                    continue
                if not iter_renderer.has_registered:
                    continue
                if renderer.position != iter_renderer.position:
                    continue

                self._stop_renderer(iter_renderer.renderer_uuid)

            # Delete all invisible (but registered) renderers from the
            # dictionary to clear up some memory.
            self._cleanup_renderers(renderer.position)

    def _remove_renderer(self, renderer_uuid):
        """ Deleting reference to renderer_uuid from the internal dict.
        Please note that you should terminate the associated renderer before
        calling this method.
        """
        with self._renderers_lock:
            log.debug("Removing renderer uuid {}".format(renderer_uuid))
            del self._renderers[renderer_uuid]

    def _handle_request_finished_loading(self, msg_root, msg_elem):
        """ This method will be called when renderers have finished loading
        requested content.
        """
        renderer_uuid = self._get_renderer_uuid(msg_elem)
        renderer = self._get_renderer(renderer_uuid)

        # Handle None renderer  FIXME
        if not renderer:
            log.warning("Unknown renderer finished loading?")
            return self._encapsulate_reply(self._generate_pong())

        # Get the corresponding item and position, and add it to the dict of
        # active items on the screen.

        log.debug("New item {item} at position {pos}.".format(
            item=renderer.content_item, pos=renderer.position
        ))

        # Report that we have opened a content item after the animation has
        # finished and the item became visible on the screen.
        threading.Timer(
            FADING_ANIMATION_DURATION, self.scheduler_mgr.report_pageview,
            kwargs={'item': renderer.content_item}
        ).start()

        # Give the display some time to finish the animation before we take the
        # old item off. We don't want to block here though!
        threading.Timer(
            FADING_ANIMATION_DURATION, self._set_renderer_visible, kwargs={
                'renderer': renderer
            }
        ).start()

        return self._encapsulate_reply(self._generate_pong())

    def _handle_request_preparation_failed(self, msg_root, msg_elem):
        """ This method will be called when a renderer has failed to load an
        item.
        """

        # We want to log this case.
        renderer_uuid = self._get_renderer_uuid(msg_elem)
        renderer = self._get_renderer(renderer_uuid)

        error_msg = (
            "Failed to load {item} by renderer {subp} at position "
            "{pos}".format(
                item=str(renderer.content_item), subp=renderer_uuid,
                pos=renderer.position
            )
        )
        log.error(error_msg)

        # Notify analytics about this error.
        self.scheduler_mgr.report_event(
            category="ERROR", action="preparation_failed", value=None,
            label=error_msg
        )

        # Stop the renderer process as it's still running.
        self._stop_renderer(renderer_uuid)

        # We can remove the renderer from our references.
        self._remove_renderer(renderer_uuid)

        # Since this is running in a separate thread, we should just trigger
        # new item scheduling instead of raising an error. We don't want to
        # wait for it to finish though.
        threading.Thread(target=self.scheduler_mgr.item_scheduling).start()

        return self._encapsulate_reply(self._generate_pong())

    def _handle_incoming_zmq(self):
        """ Listen for incoming requests from renderers and map it on the
        appropriate method.
        """

        # Create reply socket to display manager.
        zmq_reply_socket = self.zmq_context.socket(zmq.REP)
        zmq_reply_socket.setsockopt(zmq.LINGER, ZMQ_SOCKET_LINGER_MSEC)
        zmq_reply_socket.bind(
            ZMQ_ADDRESS_LOCALHOST.format(port=ZMQ_RENDERER_REQ_PORT)
        )

        # Register this socket
        zmq_poller = zmq.Poller()
        zmq_poller.register(zmq_reply_socket, zmq.POLLIN)

        # Create termination socket
        zmq_termination_reply_socket = self.zmq_context.socket(zmq.REP)
        zmq_termination_reply_socket.bind(
            ZMQ_ADDRESS_INPROC.format(
                identifier=self.zmq_scheduler_term_identifier
            )
        )

        # Provide a method to loop over sockets that have data. It tries to
        # find matching methods for incoming requests/replies with
        # _handle_zmq_msg().
        def _loop_over_sockets():
            term = False

            for sock in socks_with_data:
                if sock is zmq_termination_reply_socket:
                    return True

                msg = sock.recv().decode()
                reply = self._handle_zmq_msg(msg)

                # Check if we got a valid reply from the method called.
                if reply is None:
                    log.warning(
                        "No reply generated, replying with error!"
                    )
                    reply = self._encapsulate_reply(self._generate_error())

                sock.send(ElementTree.tostring(reply))

            return term

        # Look at all incoming messages
        while True:
            socks_with_data = dict(zmq_poller.poll())

            if socks_with_data:
                term = _loop_over_sockets()

                if term:
                    break

        # Cleanup ZMQ
        zmq_poller.unregister(zmq_reply_socket)
        zmq_reply_socket.close()

    def _handle_register(self, msg_root):
        """ Send handler params as soon as the renderer has registered. """
        log.debug(
            "Handling register: {}".format(ElementTree.tostring(msg_root))
        )
        token = msg_root.attrib['token']
        renderer = self._lookup_executing_renderer_with_token(token)
        if not renderer:
            lmsg = 'Spoof handler registration attempt: token is {token}'
            log.warning(lmsg.format(token=token))
        else:
            renderer.subprocess.register()

            # Mark the renderer as 'registered'.
            with self._renderers_lock:
                renderer.has_registered = True

            reply = self._encapsulate_reply(
                self._generate_params(renderer.subprocess.handler_params)
            )

            log.debug("Registered handler {}".format(msg_root))

            return reply

    def _stop_renderer(self, renderer_uuid):
        """ Stop the subprocess associated with renderer. """
        renderer = self._get_renderer(renderer_uuid)

        # Stop here if there is no renderer (anymore).
        if not renderer:
            return

        threading.Thread(target=renderer.stop).start()

    def _start_renderer(self, item, position, layout=None):
        """ Find the appropriate renderer for the content item, initialise it
        with an optional layout, find cached path to the content item and start
        the renderer subprocess.
        :param item: Content Item instance to be shown on the screen.
        :param layout: Optional layout attributes (see display_item).
        :param position: Optional position attribute (see display_item).
        :return: subprocess ID.
        """

        # Get initial args and find the right renderer.
        # We also give the renderer a unique ID that it will use to communicate
        # back to Display Manager.
        args = get_initial_args(item.get_content_type())
        module = ARG_RENDER_NAMESPACE + args['module']
        renderer_uuid = str(uuid.uuid4())
        cmd_args = [
            self._get_yarely_module_starter_path(), '-m', module,
            '--uuid', renderer_uuid,
            ZMQ_ADDRESS_LOCALHOST.format(port=ZMQ_RENDERER_REQ_PORT)
        ]

        # We take the first URI from the content item to display.
        item_uri = str(item)

        # Try to get the item from the cache and overwrite its URI.
        if 'precache' in args and args['precache']:
            item_uri = self.cache.file_cached(item, strict=False)

        # Validate item_uri to make sure it can be scheduled at all
        if item_uri is None:
            raise RendererError()

        # Check if item_uri really is a URI. Some renderer don't like local
        # paths and prefer URIs (file://) instead.
        if (
            'param_type' in args and
            args['param_type'] == 'uri' and
            True not in (item_uri.startswith('http'),
                         item_uri.startswith('udp'),
                         item_uri.startswith('file'),
                         item_uri.startswith('rtmp'))
        ):
            item_uri = platform.get_uri_from_local_path(item_uri)

        # Prepare the new renderer and start it
        log.debug('Starting new renderer: {args!s}'.format(args=cmd_args))
        params_over_zmq = {args['param_type']: item_uri}

        # Add the layout
        if layout is not None:
            params_over_zmq.update(layout)

        logging.debug("Send params over ZMQ: {}".format(params_over_zmq))

        subp = SubprocessExecutionWithErrorCapturing(
            cmd_args, params_over_zmq
        )

        # Start the renderer and store the reference in _executing_renderers.
        subprocess_id = subp.start()

        # Save the reference to the new renderer.
        renderer = ExecutingRenderer(subp, position, renderer_uuid, item)

        with self._renderers_lock:
            self._renderers[renderer_uuid] = renderer

        return subprocess_id

    def display_item(self, item, layout=None, position=DEFAULT_POSITION):
        """ Display a Content Item on the screen.

        In addition to the content item, this method also allows setting a
        custom layout (e.g. to place the item only on parts of the screen) and
        use a unique key for this layout/position (allowing multiple items at a
        time to be displayed).

        If an item will be shown at a `position` that was already taken
        previously, this method will take the previous content off the screen
        and replace it with the new content item.

        This method starts a new thread that asynchronously finds appropriate
        renderers, starts and registers these and replaces the previous
        content.

        :param item: ContentItem instance.
        :param layout: Dictionary with the following structure:
        {
            "layout_style": "x_y_width_height",
            "layout_x": str(bottom_left_x),
            "layout_y": str(bottom_left_y),
            "layout_width": str(width),
            "layout_height": str(height)
        }
        :param position: any unique identifier used as a key to a dictionary
        consisting of all currently displayed content items.
        """

        log.debug(
            "Received request to display {item} at position {pos}".format(
                item=str(item), pos=position
            )
        )

        # We don't want to block here to make our app less responsive.
        threading.Thread(
            target=self._display_item, kwargs={
                'item': item, 'layout': layout, 'position': position
            }
        ).start()

    def get_active_item(self, position=DEFAULT_POSITION):
        """ Returns the active item at given position as a tuple:
        (content_item, start_timestamp).

        If no item exists at position, this method will return (None, None).
        """

        renderer = self._get_renderer_at_position(position)

        if not renderer:
            return (None, None)

        return (renderer.content_item, renderer.active_timestamp)

    def get_active_start_timestamp(self, position=DEFAULT_POSITION):
        """ Get the timestamp since when the item is active. """
        renderer = self._get_renderer_at_position(position)
        if not renderer:
            return None
        return renderer.active_timestamp

    def remove_item(self, position=DEFAULT_POSITION):
        """ Taking the item at the specified position off the display. This
        method also clears up the associated renderer subprocess and removes
        the entry from self._active.
        """
        log.debug("Going to remove item from position {}".format(position))
        renderer = self._get_renderer_at_position(position)
        if not renderer:
            log.warning("No renderer found to remove item!")
            return  # Fixme - raise error?

        self._stop_renderer(renderer.renderer_uuid)
        self._remove_renderer(renderer.renderer_uuid)

    def remove_items(self):
        """ Take all items off the screen. """
        renderers_to_remove = list()
        with self._renderers_lock:
            for renderer in self._renderers.values():
                self._stop_renderer(renderer.renderer_uuid)
                renderers_to_remove.append(renderer)

            for renderer_to_remove in renderers_to_remove:
                self._remove_renderer(renderer_to_remove.renderer_uuid)

    def start(self):
        """ Start listening for incoming requests/replies. The mapping from
        request to method is done in _handle_incoming_zmq. Initialise the
        cache (reading in cache directory from config) for determining the
        local path to files to be displayed on the screen.
        """

        self._zmq_display_renderer_reply_thread = threading.Thread(
            target=self._handle_incoming_zmq
        )
        t_name = 'ZMQ Display Renderer Reply Thread'
        self._zmq_display_renderer_reply_thread.name = t_name
        self._zmq_display_renderer_reply_thread.daemon = True
        self._zmq_display_renderer_reply_thread.start()

        # Initialise the cache
        self._initialise_cache()

    def stop(self):
        """ Stop renderer reply thread and all active renderers. """

        self._zmq_display_renderer_reply_thread.stop()

        # Stop all renderer and clear the dictionary.
        self.remove_items()
