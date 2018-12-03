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
import platform
import sys
from argparse import ArgumentParser

# Local (Yarely) imports
from yarely.core.config import YarelyConfig

log = logging.getLogger(__name__)


class ApplicationError(Exception):
    """Base class for application errors."""
    pass


class ApplicationConfigurationError(ApplicationError):
    """Raised when loading the configuration fails."""
    pass


class Application:
    """A base class for applications. Provides dummy methods for
    handling command line arguments.

    Subclasses can handle command line arguments by overriding
    Application._add_arguments() and Application._handle_arguments()
    which are both called by Application.process_arguments().

    Sample Usage:

        >>> a = Application('A Sample Application')
        >>> a.process_arguments()

    """
    def __init__(self, description):
        """
        :param string description: a text description that will be used
            by :meth:`Application.process_arguments()` if an alternative is
            not directly supplied to the method.

        """
        super().__init__()
        self.description = description

    def _add_arguments(self, arg_parser):
        """Add arguments to the argument parser.

        For implementation by subclasses.

        :param arg_parser: FIXME.
        :type arg_parser: a :class:`argparse.ArgumentParser` instance.

        """
        pass

    def _handle_arguments(self, args):
        """Handle arguments received from the argument parser.

        For implementation by subclasses.

        :param args: the result of
            :meth:`argparse.ArgumentParser.parse_args()`.
        :type args: FIXME.

        """
        pass

    def process_arguments(self, *args, **kwargs):
        """Read in and act upon arguments from the command line.

        args and kwargs are passed directly to argparse.ArgumentParser's
        constructor.

        Customisation of the ArgumentParser is available through the delegate
        methods self._add_arguments and self._handle_arguments.

        """
        if 'description' not in kwargs:
            kwargs['description'] = self.description
        arg_parser = ArgumentParser(*args, **kwargs)
        self._add_arguments(arg_parser)
        args = arg_parser.parse_args()
        self._handle_arguments(args)

    def start(self):
        """The main execution method for this application.

        :raises NotImplementedError: always.

        """
        raise NotImplementedError

    def stop(self):
        """Termination of the main execution method for this application."""
        pass


class ApplicationWithBasicLogging(Application):
    """A base class for applications that use logging.basicConfig to
    log to stderr.

    """

    def __init__(self, description):
        """
        :param string description: a text description that will be used
            by :meth:`Application.process_arguments()` if an alternative is
            not directly supplied to the method.

        """
        # Basic config uses a StreamHandler to stderr by default
        logging_format = '%(levelname)s: %(message)s'
        logging.basicConfig(level=logging.DEBUG, format=logging_format)
        super().__init__(description)


class ApplicationWithConfig(Application):
    """A base class for applications expecting the path to the
    configuration file as a command line argument.

    """

    def __init__(self, description):
        """
        :param string description: a text description that will be used
            by :meth:`Application.process_arguments()` if an alternative is
            not directly supplied to the method.

        """
        self.config = None
        super().__init__(description)

    def _add_arguments(self, arg_parser):  # Overrides method in superclass
        super()._add_arguments(arg_parser)
        arg_parser.add_argument(
          "config_path", help="path to yarely configuration file"
        )

    def _handle_arguments(self, args):     # Overrides method in superclass
        super()._handle_arguments(args)
        self._read_config(args.config_path)

    def _read_config(self, path):
        """Intialise a config object

        :param string path: a string or bytes object giving the pathname
            (absolute or relative to the current working directory) of the
            config file to be used to intialise values in this object.

        """
        try:
            self.config = YarelyConfig(path)
        except Exception as e:
            msg = "Error initialising configuration from '{path}'"
            msg = msg.format(path=path)
            log.exception(msg)
            raise ApplicationConfigurationError(msg) from e

        logging.captureWarnings(True)
        version_template = "Python version: {version!r}"
        uname_template = "Host details: {uname!r}"
        argv_template = "Command line: {argv!r}"
        log.info(version_template.format(version=sys.version))
        log.info(uname_template.format(uname=platform.uname()))
        log.info(argv_template.format(argv=sys.argv))
