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
import configparser
import logging
import logging.config
import re
from functools import wraps

# Local imports
from yarely.core.helpers import conversions
from yarely.core.helpers import Singleton
from yarely.core.helpers.colour import RGBColour, ColourError

log = logging.getLogger(__name__)


class ConfigError(Exception):
    """Base class for configuration errors."""
    pass


class ConfigNotInitialisedError(ConfigError):
    """Raised when a method requiring the config is called prior to the
    config being successfully initialised.

    """
    pass


class ConfigInitialisationError(ConfigError):
    """Raised when the initialise() method of :class:`YarelyConfig` fails to
    complete correctly.

    """
    pass


class ConfigParsingError(ConfigError):
    """Base class for configuration parsing errors."""
    pass


class LogInitialisationError(ConfigError):
    """Raised when the initialise() method of :class:`YarelyConfig` fails
    to process the logging configuration based on values found in the root
    config file.

    """
    pass


class ConfigValidationError(ConfigError):
    """Raised when the validate() method of :class:`YarelyConfig` fails to
    complete correctly.

    """
    pass


class FacadeConfigInvalid(ConfigValidationError):
    """Raised when the :class:`YarelyConfig` class determines that the
    Facade configuration is invalid.

    Possible causes include an invalid background colour format and use of a
    coordinate-based background colour when no image path has been set.

    """
    pass


class _YarelyConfig(object, metaclass=Singleton):
    """Provide a representation of the data described in a
    Microsoft Windows INI style config file.

    Singleton class - all parts of a given Yarely instance
    will share the same configuration.

    Sample usage:
        >>> from yarely.core.config import YarelyConfig  # doctest: +SKIP
        >>> conf = YarelyConfig()                        # doctest: +SKIP
        >>> conf.initialise(path_to_file)                # doctest: +SKIP #NOQA
        >>> conf.get('ContentSources', 'ContentRoot')    # doctest: +SKIP

    """

    def __init__(self, filename=None):
        """Default constructor - create a new :class:`YarelyConfig` object.

        :param string filename: an optional string or bytes object giving
            the pathname (absolute or relative to the current working
            directory) of the config file to be used to intialise values in
            this object.

        If a filename is specified the configuration is immediately
        initialised based on the specified ini-style config file.

        This is a singleton class. The __init__ method is only called if no
        previous instance exists - in the event that an instance already
        exists, calls to create a new instance will not result in the
        execution of this constructor but will simply result in the previous
        instance being returned.

        Example:
            >>> from yarely.core.config import YarelyConfig
            >>> a = YarelyConfig()
            >>> b = YarelyConfig()
            >>> id(a) == id(b)
            True

        Note that the above behaviour pattern has particular significance
        for the filename argument as it will ONLY be processed if this is
        the first attempt to create an instance. In subsequent calls the
        constuctor is not called so the filename argument will not be
        processed.

        Example:
            >>> from yarely.core.config import YarelyConfig
            >>> a = YarelyConfig()
            >>> b = YarelyConfig('/samples/yarely.cfg')
            >>> b.items()
            Traceback (most recent call last):
              File "<stdin>", line 1, in <module>
              File "/yarely/core/config/parse_config.py", line 206, \
              in check
                raise ConfigNotInitialisedError()
            yarely.core.config.parse_config.ConfigNotInitialisedError

        """
        self.config = None
        self.colours = {}
        self.tuples = {}
        if filename:
            self.initialise(filename)

    def _read_file(self, filename, required=True):
        try:
            with open(filename) as configfile:
                self.config.read_file(configfile)
        except Exception as error:
            if required:
                raise error
            msg = 'Failed to read optional file {filename} - {error}'
            log.warning(msg.format(filename=filename, error=error))

    def initialise(self, filename):
        """Prepare the :class:`YarelyConfig` object for option retrieval
        based on a specified config file.

        :param string filename: a string or bytes object giving the pathname
            (absolute or relative to the current working directory) of the
            config file to be opened.

        """
        self.config = configparser.ConfigParser()
        try:
            # Load the root config
            self._read_file(filename)

            # Cool, now we know where the logging should be - let's get logging
            try:
                logging_config = self.get('Logging', 'ConfigFile')
                logging.config.fileConfig(
                  logging_config, disable_existing_loggers=False
                )
                log.debug('Logging initialised')
            except Exception as error:
                msg = 'Failed to initialise log'
                log.exception(msg)
                raise LogInitialisationError(msg) from error

            # Load any extra config files (required & optional)
            for (label, value) in self.items('RequiredConfig'):
                self._read_file(value)
            for (label, value) in self.items('OptionalConfig'):
                self._read_file(value, False)
        except Exception as e:
            self.config = None
            msg = 'Failed to read config at path: {filename}'
            msg = msg.format(filename=filename)
            raise ConfigInitialisationError(msg) from e
        self.validate()

    def check_config_initialised(fn):
        """A decorator function that ensures a
        :class:`ConfigNotInitialisedError` will be raised if the decorated
        method is called prior to successful config initialisation.

        To initialise config, call self.initialise(). Note that the config
        will be initialised automatically if the filename param was supplied
        when this object was created.

        :param function fn: the function to be decorated.
        :raises ConfigNotInitialisedError: raised if self.config has
            not been been successfully intialised.

        """
        @wraps(fn)
        def check(*args, **kwargs):
            _self = args[0]
            if not _self.config:
                raise ConfigNotInitialisedError()
            return fn(*args, **kwargs)
        return check

    @check_config_initialised
    def validate(self):
        """Apply Yarely-specific config validation rules (e.g. checks that
        specific config items are present, of a given type etc.)

        :raises ConfigNotInitialisedError: raised if self.config has
            not been been successfully intialised.

        """
        # Facade config validation
        bg_colour = self.get('Facade', 'BackgroundColour')
        if ',' in bg_colour:
            try:
                # Check string contains a tuple of length two (spaces and
                # brackets optional).
                match = re.match('^\(?\s*(\d+)\s*,\s*(\d+)\s*\)?$', bg_colour)
                if match:
                    coords = match.group(1, 2)
                    coords = tuple([int(val) for val in coords])
                    self.set('Facade', 'BackgroundColour', coords)
                else:
                    msg = 'Expected tuple of size 2 (read {val})'
                    msg = msg.format(val=bg_colour)
                    raise ValueError(msg)

                # To specify a tuple (coordinate set) ImagePath must be set.
                try:
                    self.get('Facade', 'ImagePath')
                except configparser.NoOptionError as e:
                    msg = 'Coordinate-based background colour requires \
ImagePath to be set.'
                    raise ValueError(msg) from e
            except Exception as e:
                msg = 'Failed to parse colour from config tuple (read {val})'
                msg = msg.format(val=bg_colour)
                raise FacadeConfigInvalid(msg) from e
        else:
            try:
                colour = RGBColour(bg_colour)
                self.set('Facade', 'BackgroundColour', colour)
            except ColourError as e:
                msg = 'Failed to parse colour from config (read {val})'
                msg = msg.format(val=bg_colour)
                raise FacadeConfigInvalid(msg) from e

    @check_config_initialised
    def __getattr__(self, name):
        if hasattr(self.config, name):
            return getattr(self.config, name)
        else:
            raise NameError('Name \'{name}\' is not defined'.format(name=name))

    @check_config_initialised
    def set(self, section, option, value):
        """If the given section exists, set the given option to the
        specified value; otherwise raise :class:`configparser.NoSectionError`.

        :param string section: the section to set the option in.
        :param string option: the option to be set.
        :param string value: the value to set the option to.
        :raises ConfigNotInitialisedError: raised if self.config has
            not been been successfully intialised.
        :raises configparser.NoSectionError: raised if the specified section
            does not exist.

        """
        if isinstance(value, RGBColour):
            if section not in self.colours:
                self.colours[section] = {}
            self.colours[section][option] = value
            value = value.as_string()
        elif isinstance(value, tuple):
            if section not in self.tuples:
                self.tuples[section] = {}
            self.tuples[section][option] = value
            value = str(value)
        self.config.set(section, option, value)

    @check_config_initialised
    def getcolour(self, section, option, raw=False, vars=None, **kwargs):
        """A convenience method which coerces the configparser option in the
        specified section to a :class:`RGBColor` instance. Note that the
        accepted formats for the option are look something like this (for
        an RGB colour where all values are 255): 'F', '#F', 'FFF', '#FFF',
        'FFFFFF' and '#FFFFFF'. These string values are checked in a
        case-insensitive manner.

        FIXME: Do raw, vars and fallback do the right thing?

        :param string section: the section to get the option from.
        :param string option: the option to be fetched.
        :param raw: See :func:`configparser.ConfigParser.get` for
            documentation of the raw parameter.
        :param vars: See :func:`configparser.ConfigParser.get` for
            documentation of the vars parameter.
        :param kwargs: See :func:`configparser.ConfigParser.get` for
            additional keyword arguments.
        :raises ConfigNotInitialisedError: raised if self.config has
            not been been successfully intialised.
        :raises configparser.NoSectionError: raised if the specified section
            does not exist.

        """
        # Check vars (FIXME - does this behave as configparse.get() does?)
        if vars and option in vars:
            if isinstance(vars[option], RGBColour):
                return vars[option]
            msg = 'Option \'{opt}\' in vars is not an RGBColour instance.'
            msg = msg.format(opt=option)
            raise ValueError(msg)

        # Check self.colours (a dict of colours within this config)
        elif section in self.colours and option in self.colours[section]:
            return self.colours[section][option]

        # Check for an existing option of wrong type
        try:
            self.get(section, option, raw=raw)
            msg = 'Option \'{opt}\' in section \'{sect}\' cannot be retrieved \
as a colour'
            raise ValueError(msg.format(opt=option, sect=section))

        # Raise NoSectionError or NoOptionError as applicable
        except Exception:
            if 'fallback' in kwargs:
                return kwargs['fallback']
            raise

    @check_config_initialised
    def getfloat(self, *args, **kwargs):
        """A convenience method which coerces the configparser option in the
        specified section to a floating point number. This method
        will also convert a percentage value (e.g. 50%) to the corresponding
        floating point value (e.g. 0.5).

        :param string section: the section to get the option from.
        :param string option: the option to be fetched.
        :param args: See :func:`configparser.ConfigParser.get` for
            documentation of additional arguments.
        :param kwargs: See :func:`configparser.ConfigParser.get` for
            additional keyword arguments.
        :raises ConfigNotInitialisedError: raised if self.config has
            not been been successfully intialised.
        :raises configparser.NoSectionError: raised if the specified section
            does not exist.

        """
        try:
            return self.config.getfloat(*args, **kwargs)
        except Exception:
            str_val = self.config.get(*args, **kwargs)
            if str_val[-1] == '%':
                return float(str_val[:-1]) / 100
            raise

    @check_config_initialised
    def getint(self, *args, **kwargs):
        """A convenience method which coerces the configparser option in the
        specified section to an integer. This method will also convert a
        byte-descriptive string (e.g. '20KiB') to the integer value
        representing the number of bytes (20480).

        :param string section: the section to get the option from.
        :param string option: the option to be fetched.
        :param args: See :func:`configparser.ConfigParser.get` for
            documentation of additional arguments.
        :param kwargs: See :func:`configparser.ConfigParser.get` for
            additional keyword arguments.
        :raises ConfigNotInitialisedError: raised if self.config has
            not been been successfully intialised.
        :raises configparser.NoSectionError: raised if the specified section
            does not exist.

        """
        try:
            return self.config.getint(*args, **kwargs)
        except Exception as e:
            str_val = self.config.get(*args, **kwargs)
            try:
                return conversions.unit_of_information_in_bytes(str_val)

            # If byte conversion fails, maybe this is just a
            # 'normal' string - raise the original exception.
            except conversions.UnitOfInformationConversionError:
                raise e

    @check_config_initialised
    def gettuple(self, section, option, raw=False, vars=None, **kwargs):
        """A convenience method which coerces the configparser option in the
        specified section to a tuple instance. Note that the accepted
        formats for the option are look something like this (for a tuple
        containing the items 0 and 1): '(0, 1)' brackets and spacing are
        optional. These string values are checked in a case-insensitive
        manner.

        FIXME: Do raw, vars and fallback do the right thing?

        :param string section: the section to get the option from.
        :param string option: the option to be fetched.
        :param args: See :func:`configparser.ConfigParser.get` for
            documentation of additional arguments.
        :param kwargs: See :func:`configparser.ConfigParser.get` for
            additional keyword arguments.
        :raises ValueError: raised if the string value of the specificed
            option is not an accepted tuple format.
        :raises ConfigNotInitialisedError: raised if self.config has
            not been been successfully intialised.
        :raises configparser.NoSectionError: raised if the specified section
            does not exist.

        """
        # Check vars (FIXME - does this behave as configparse.get() does?)
        if vars and option in vars:
            if isinstance(vars[option], tuple):
                return vars[option]
            msg = "Option '{opt}' in vars is not an tuple."
            msg = msg.format(opt=option)
            raise ValueError(msg)

        # Check self.colours (a dict of colours within this config)
        elif section in self.tuples and option in self.tuples[section]:
            return self.tuples[section][option]

        # Check for an existing option of wrong type
        try:
            self.get(section, option, raw=raw)
            msg = (
                "Option '{opt}' in section '{sect}' cannot be retrieved "
                "as a tuple"
            )
            raise ValueError(msg.format(opt=option, sect=section))

        # Raise NoSectionError or NoOptionError as applicable
        except Exception:
            if 'fallback' in kwargs:
                return kwargs['fallback']
            raise
