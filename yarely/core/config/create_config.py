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
import os.path

YARLEY_ROOT = '/tmp'
CONTENT_ROOT = os.path.join(YARLEY_ROOT, 'subscriptions')
CONFIG_ROOT = os.path.join(YARLEY_ROOT, 'config', 'samples')
CONFIG_PATH = os.path.join(CONFIG_ROOT, 'yarely.cfg')


class ConfigCreator(object):
    """Generates a sample Yarely configuration file (Microsoft Windows INI
    style).

    """

    def create_config(self):
        """Write a sample Yarely configuration to the CONFIG_PATH file.
        Any existing file at CONFIG_PATH will be overwritten.

        """

        self.config = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation()
        )

        # Each of the following methods adds one or more sections to the
        # config file
        self._content_sources_config()
        self._logging_config()
        self._supplementary_config()
        self._facade_config()
        self._cache_config()
        self._display_device_controller_config()
        self._scheduler_config()

        # All set up - let's write the config file!
        with open(CONFIG_PATH, 'w') as configfile:
            self.config.write(configfile)

    def _content_sources_config(self):
        # We'd like to specify a root content source that will give a
        # list of all the content this machine is subscribed to. We'll
        # expect this at a common file system location.
        # For the first pass, the File handler that reads from this
        # content source will pull at the given refresh rate.
        self.config.add_section('SubscriptionManagement')
        self.config.set('SubscriptionManagement', 'SubscriptionRoot',
                        os.path.join(CONTENT_ROOT, 'root.xml'))
        self.config.set('SubscriptionManagement', 'RefreshRate', '1 HOUR')
        self.config.set('SubscriptionManagement', 'PersistTo',
                        os.path.join(CONTENT_ROOT, 'yarely_subscriptions.db'))

    def _display_device_controller_config(self):
        # Where possible display hardware will be turned off when no content is
        # available to be shown. If  DisplayDeviceSerialUSBName is set then the
        # Display Controller will attempt to power the display on/off as
        # required. This is currently achieved through serial communication
        # from within the scheduler. The display timeout is the time in seconds
        # the display turns off if no content is available.

        self.config.add_section('DisplayDevice')
        self.config.set('DisplayDevice', 'DisplayDeviceSerialUSBName',
                        'FTCY5YSZ')
        self.config.set('DisplayDevice', 'DisplayTimeout', '300')

    def _logging_config(self):
        # Path to the logging configuration file.
        self.config.add_section('Logging')
        self.config.set('Logging', 'ConfigFile',
                        os.path.join(CONFIG_ROOT, 'logging.cfg'))

    def _supplementary_config(self):
        # FIXME - Add required configuration file paths here.
        # The config parser will error if any of these files cannot be
        # found.
        self.config.add_section('RequiredConfig')

        # Optional extra configuration file paths.
        # The config parser will try and load these files but will not
        # error if they cannot be found/processed (a warning will be
        # issued).
        self.config.add_section('OptionalConfig')
        self.config.set('OptionalConfig', 'LocalConfig',
                        os.path.join(CONFIG_ROOT, 'local.cfg'))

    def _cache_config(self):
        # The CacheManager mantains an index of all files stored in its
        # cache. This SQLite database is stored in a local file whose
        # name and location is determined by CacheDatabase. IndexTable
        # determines the tablename to be used for this index.
        self.config.add_section('CacheMetaStorage')
        self.config.set('CacheMetaStorage', 'MetaStorePath',
                        os.path.join(YARLEY_ROOT, 'content.db'))
        self.config.set('CacheMetaStorage', 'IndexTable', 'CacheIndex')

        # The CacheManager maintains a copy of all fetched files in the
        # CacheLocation. The maximum size of the CacheLocation is determined
        # by the MaxCacheSize, which can be can be specified as:
        # a value of '1B' means 1 byte
        # a value of '1KB' means 1000 bytes
        # a value of '1KiB' means 1024 bytes
        # a value of '1MB': means 1000 * 1000 bytes
        # a value of '1MiB': means 1024 * 1024 bytes
        # a value of '1GB': means 1000 * 1000 * 1000 bytes
        # a value of '1GiB': means 1024 * 1024 * 1024 bytes
        # a value of '1TB': means 1000 * 1000 * 1000 * 1000 bytes
        # a value of '1TiB': means 1024 * 1024 * 1024 * 1024 bytes
        # Once the maxcachesize is reached the CacheManager uses the
        # Least Recently Used (LRU) algorithm, to remove least recently
        # used files from the CacheLocation.
        self.config.add_section('CacheFileStorage')
        self.config.set('CacheFileStorage', 'CacheLocation', YARLEY_ROOT)
        self.config.set('CacheFileStorage', 'MaxCacheSize', '20MiB')

    def _facade_config(self):
        self.config.add_section('Facade')

        # Optional path to image
        self.config.set('Facade', 'ImagePath',
                        os.path.join(CONFIG_ROOT, 'facade', 'logo.png'))

        # Optional image scale factor (read as a float - 100% == 1)
        # a value of '1' means 'fill the screen without loosing any image'
        # a value of '0.5' means 'pad with 25% background to each side on the
        # longest side.
        # a value of '0' or lower means do not scale at all - show the image
        # at it's native resolution.
        self.config.set('Facade', 'ImageScale', '100%')

        # Required background colour.  Either hex (#0000FF) or (if an
        # imagepath has been set) a tuple of (x,y) co-ords for the pixel
        # to pick from the image.
        # Accepted value styles:
        # #0000FF 	-> Interpreted as an rgb colour (0 red, 0 green, 255 blue)
        # (1,10)		-> Interpreted as a pixel coordinate (x = 1, y = 10)
        self.config.set('Facade', 'BackgroundColour', '(10,32)')

    def _scheduler_config(self):
        # The scheduler will use the DefaultContentDuration as the default
        # duration for each content item (in seconds). A content item will be
        # shown for the default period only if no preferred-duration constraint
        # is given in the content descriptor set.
        self.config.add_section('Scheduling')
        self.config.set('Scheduling', 'DefaultContentDuration', '15')


# Main entry point.
if __name__ == '__main__':
    conf_writer = ConfigCreator()
    conf_writer.create_config()
