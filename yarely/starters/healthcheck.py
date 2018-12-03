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


import configparser
import logging
import os
import re
import subprocess
import sys
from importlib import import_module
from urllib.error import URLError
from urllib.request import urlopen

HOME = os.environ['HOME']
YARELY_DIR = os.path.join(HOME, 'proj', 'yarely')
YARELY_LOCAL = os.path.join(HOME, 'proj', 'yarely-local')
LOGGING_PATH = os.path.join(YARELY_LOCAL, "logs", "healthcheck.log")
YARELY_CONFIG = os.path.join(YARELY_LOCAL, "config", "yarely.cfg")

# If no version specified we do not enforce a specific version of the package.
PACKAGES_TO_BE_CHECKED = {
    "IxionAnalytics": "1.6", "pkg_resources": None, "serial": None
}
HOSTS_TO_BE_CHECKED = [
    'http://scc-schools-opendisplays.lancs.ac.uk',
    'http://mercury.lancs.ac.uk'
]

DISPLAY_DEVICE_DRIVER_SUFFIX = '_display_device.py'
SERIAL_PREFIX = 'tty.usbserial-'

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger_handlers = {
    # handler: format string
    logging.StreamHandler(sys.stdout): '%(levelname)s - %(message)s',
}

# Logging into the same directory as Yarely does. If that path does not exist
# we won't log to a file.
if os.path.exists(YARELY_CONFIG):
    logger_handlers[logging.FileHandler(LOGGING_PATH)] = (
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

for logger_handler, format_str in logger_handlers.items():
    logger_handler.setLevel(logging.INFO)
    logger_handler.setFormatter(logging.Formatter(format_str))
    logger.addHandler(logger_handler)


def _urlopen_check(host):
    try:
        response = urlopen(host, timeout=1)  # timeout in seconds
        response_code = response.getcode()

        # Check for 2xx response codes.
        if 200 <= response_code < 300:
            return True
        logger.warning("Host {host} returned status code {code}".format(
            host=host, code=response_code
        ))

    except URLError:
        pass

    # If the response code is other than 2xx or the page was not reachable at
    # all we return false.
    return False


def check_network():
    logger.info("Checking network status...")

    # Check if Google DNS is online (by IP)
    if _urlopen_check('http://8.8.8.8'):
        logger.info("Network seems to be OK.")
    else:
        logger.error('NETWORK NOT WORKING!')


def check_dns():
    logger.info("Checking DNS status...")
    if _urlopen_check('http://google.com'):
        logger.info("DNS seems to be OK.")
    else:
        logger.error("DNS NOT WORKING!")


def _check_website_reachable(host):
    logger.info("Checking status of {}".format(host))
    if _urlopen_check(host):
        logger.info("{} is reachable.".format(host))
        return True

    logger.error('{} OFFLINE?!'.format(host))
    return False


def _check_ping_time(host):
    # http://stackoverflow.com/a/316974/3628578
    logger.info("Checking response time for {}...".format(host))

    # remove http:// or https:// from the host
    host = host.replace('http://', '').replace('https://', '')

    try:
        ping = subprocess.Popen(
            ["ping", "-c", "4", host],  # ping four times.
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, error = ping.communicate()
        out_decode = out.decode("utf-8")

    except ValueError as err:
        logger.error("Error while calling ping: {}".format(err))
        return  # SANTA! STOP HERE!!!

    out_list = out_decode.split("\n")

    try:
        # there is an empty line at the end
        last_line = out_list[len(out_list)-2]
        matcher = re.compile(
            "round-trip min/avg/max/stddev = (\d+.\d+)/(\d+.\d+)/(\d+.\d+)/"
            "(\d+.\d+)"
        )
        avg = matcher.match(last_line).groups()[1]

    except IndexError as err:
        logger.error("Invalid response received from ping for {}".format(
            host
        ))
        return

    # Attribute error when we don't find the matching pattern, probably because
    # the network is down.
    except AttributeError as err:
        logger.error("Network down? {}".format(str(error)))
        return

    logger.info('Average response time for {} is: {}ms'.format(host, avg))


def check_website_availability(host):
    # Only ping the website if it is reachable.
    if _check_website_reachable(host):
        _check_ping_time(host)


def _package_exists(package):
    try:
        import_module(package)
        return True
    except ImportError:
        return False


def check_package(package):
    logger.info("Checking {}...".format(package))

    # Check if the package is installed at all
    if not _package_exists(package):
        logger.error("CAN NOT FIND {}".format(package))
        return

    logger.info("{} is available on this machine".format(package))

    # Check the version (only if the version number was specified, otherwise
    # we are not interested in a specific version.
    if PACKAGES_TO_BE_CHECKED[package] is not None:
        check_package_version(package)

    # Special case for our analytics library
    if package == "IxionAnalytics":
        _check_ixion_analytics_version()


def check_package_version(package):
    logger.info("Checking {} version...".format(package))

    if not _package_exists('pkg_resources'):
        logger.error("pkg_resources package not installed.")
        return

    import pkg_resources

    try:
        # Get the version of the package installed by setuptools. Note: This
        # might not match the version that is actually used.
        installed = pkg_resources.get_distribution(package).version

        if installed == PACKAGES_TO_BE_CHECKED[package]:
            logger.info("Version {} installed and used.".format(installed))

        else:
            logger.error('OLD VERSION USED?!')

    except pkg_resources.DistributionNotFound:
        logger.warning("CAN NOT VERIFY THE VERSION OF {}.".format(package))


def _check_ixion_analytics_version():
    logger.info("Checking IxionAnalyitcs version specific...")

    if not _package_exists("IxionAnalytics"):
        logger.error("IxionAnalytics does not exist.")
        return

    import IxionAnalytics

    # double check if the newest version is also the default version (in
    # case it got messed up with different Python versions). If it is an
    # old version the method 'track_interaction' won't exist. In future I
    # will add a __version__ flag to the analytics library to make that
    # more clear and clean.
    newest_version_used = 'track_interaction' in dir(IxionAnalytics)

    if newest_version_used:
        logger.info("Newest version of IxionAnalyitcs used.")

    else:
        logger.error('Old version of IxionAnalyitcs used.')


def _check_if_yarely_config_exists():
    return os.path.exists(YARELY_CONFIG)


def _get_config_item(section, option, fallback):
    cfg = configparser.ConfigParser()
    cfg.read(YARELY_CONFIG)
    return cfg.get(section, option, fallback=fallback)


def _get_display_type():
    return _get_config_item('DisplayDevice', 'devicetype', fallback='sony')


def _get_serial_name():
    return _get_config_item(
        'DisplayDevicess', 'displaydeviceserialusbname', fallback=None
    )


def check_display_power_status():
    logger.info("Checking display power status...")

    if not _package_exists("serial"):
        logger.warning(
            "CAN NOT CHECK DISPLAY STATUS BECAUSE serial PACKAGE IS MISSING."
        )
        return

    logger.info("Checking if Yarely config exists...")
    if not _check_if_yarely_config_exists():
        logger.error("CAN NOT FIND YARELY CONFIG!")
        return

    display = _get_display_type()   # sony, lg, projector, etc.
    logger.info("Using display type: {}".format(display))
    script_name = display + DISPLAY_DEVICE_DRIVER_SUFFIX
    path_to_script = os.path.join(
        YARELY_DIR, 'core', 'scheduler', script_name
    )

    logger.info("Trying to find the display script...")
    if not os.path.exists(path_to_script):
        logger.error(
            "CAN NOT FIND DISPLAY SCRIPT. CHECK YARELY INSTALLATION!"
        )
        return

    logger.info("Requesting display power status...")
    serial_name = _get_serial_name()
    args = [
        'python3', path_to_script, 'GET_POWER_STATUS', serial_name
    ]
    try:
        process_output = subprocess.check_output(args)
    except OSError as err:
        logger.error("OSError: {}".format(err))
        return
    except TypeError as err:
        # This will be raised when check_output returns NoneType
        logger.error("TypeError: {}".format(err))
        return
    except subprocess.CalledProcessError as err:
        logger.error("Error calling the script: {}".format(err))
        return

    process_output = process_output.decode("utf-8").rstrip()
    if process_output not in ["IS_ON", "IS_OFF"]:
        logger.error(
            "DISPLAY IS NOT RESPONDING."
            "CHECK SERIAL CONNECTION!"
        )
    else:
        logger.info("Display status: {}".format(
            process_output
        ))


if __name__ == "__main__":
    print("=============================================")
    print("==   YARELY HEALTH CHECK STARTING          ==")
    print("=============================================")

    check_network()
    check_dns()

    for host in HOSTS_TO_BE_CHECKED:
        check_website_availability(host)

    for package in PACKAGES_TO_BE_CHECKED:
        check_package(package)

    check_display_power_status()

    print("=============================================")
    print("==   YARELY HEALTH CHECK COMPLETE          ==")
    print("=============================================")
