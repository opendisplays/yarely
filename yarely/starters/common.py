# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


import os
import sys
from pprint import pprint

"""A selection of helper methods to launch Yarely components safely on
all platforms.

Starters should use the launch_application() method.

Configuration is through setting environment variables:
    YARELY_PYTHON32_BIN - Path to the Python interpreter
        See the python_version_platform_map dictionary for default values.
    YARELY_CONFIG - Path to the yarely.cfg file.
        See get_yarely_config().
    YARELY_PARENT - Directory to change into before launching.
        This path will be appended to PYTHONPATH so that the Yarely package
        can be found. It can also be used to allow the consistent use of
        relative paths to (and within) yarely.cfg.
        See get_yarely_parent().
    YARELY_STARTER_VERBOSE - If set, be verbose about command being launched.

"""

# Key is sys.platform, value is file path
# File path may be a filename (PATH will be searched), or an absolute or
# relative path.
python_platform_map = {
    "darwin": "python3",
    "linux": "python3",
    "win32": "c:\\python3\\python.exe",
}

# Environment template for path to Python binary.
YARELY_PYTHON3_BIN_ENVIRONMENT_KEY = "YARELY_PYTHON3_BIN"

# requirements specifications
# (there aren't any yet!)

# module_name_template replacement fields
module_name_fields = {
    "platform": sys.platform
}

verbose = ("YARELY_STARTER_VERBOSE" in os.environ)


class StarterError(Exception):
    pass


def launch_application(module_name_template, requirements):
    """Launch (replacing this process) the module specified
    using a suitable (per the requirements list) Python interpreter.

    The path to yarely.cfg is passed as the single argument to the module.
    See get_yarely_config().

    module_name_template - a string specifying the module name to launch.
        See exec_module().

    requirements - a list of requirements classes that help guide
        the selection of a suitable Python interpreter.  See exec_module().

    """

    yarely_config = get_yarely_config()

    arguments = [yarely_config]

    exec_module(module_name_template, requirements, arguments)


def exec_module(module_name_template, requirements, arguments):
    """Launch (replacing this process) the module specified using a
    suitable (per the requirements list) Python interpreter.

    Change into the Yarely parent directory before launching.
    See get_yarely_parent().

    module_name_template - a string specifying the module name to launch.
        str.format() is called to replace based on the following:
            platform -> sys.platform

    requirements - a list of requirements classes that help guide
        the selection of a suitable Python interpreter.

    arguments - a list of arguments passed to the launched module.

    """

    module_name = module_name_template.format(**module_name_fields)
    python_binary = get_python_binary(requirements)

    python_arguments = [python_binary, "-m", module_name]
    python_arguments.extend(arguments)
    python_arguments.extend(sys.argv[1:])

    yarely_parent = get_yarely_parent()

    if verbose:
        msg = "Changing into Yarely parent directory '{yarely_parent}'"
        print(msg.format(yarely_parent=yarely_parent))

    try:
        os.chdir(yarely_parent)
    except Exception as e:
        msg = "Unable to change into Yarely parent directory '{yarely_parent}'"
        raise StarterError(msg.format(yarely_parent=yarely_parent)) from e

    environment = os.environ.copy()

    if "PYTHONPATH" in environment:
        existing_python_path = environment["PYTHONPATH"]
        python_path_template = "{existing_python_path}:{yarely_parent}"
        python_path = python_path_template.format(
                existing_python_path=existing_python_path,
                yarely_parent=yarely_parent)
    else:
        python_path = yarely_parent

    environment["PYTHONPATH"] = python_path

    if verbose:
        msg = "Executing Python interpreter '{python_binary}' " \
              "with arguments '{python_arguments!r}' in environment"
        print(msg.format(
            python_binary=python_binary, python_arguments=python_arguments
        ))
        pprint(environment)

    try:
        os.execvpe(python_binary, python_arguments, environment)
    except Exception as e:
        msg = "Failed to execute Python interpreter '{python_binary}' " \
              "with arguments '{python_arguments!r}' in environment " \
              "'{environment!r}'"
        raise StarterError(msg.format(
            python_binary=python_binary,
            python_arguments=python_arguments,
            environment=environment
        )) from e


def get_python_binary(requirements):
    """Return a string indicating the path to the Python interpreter on
    this platform.

    The default values may be overridden by setting the environment variable
    YARELY_PYTHON32_BIN.

    """

    # Check the environment for overrides.
    if YARELY_PYTHON3_BIN_ENVIRONMENT_KEY in os.environ:
        return os.environ[YARELY_PYTHON3_BIN_ENVIRONMENT_KEY]

    python_binary = python_platform_map.get(sys.platform)

    if python_binary is None:
        raise StarterError("Unexpected platform '{platform}'".format(
            platform=sys.platform))

    return python_binary


def get_yarely_config():
    """Return a string indicating the path to the yarely.cfg file.
    Default: 'yarely-local/config/yarely.cfg'

    The default value may be overridden by setting the environment variable
    YARELY_CONFIG.

    """

    if "YARELY_CONFIG" in os.environ:
        return os.environ["YARELY_CONFIG"]

    return "yarely-local/config/yarely.cfg"


def get_yarely_parent():
    """Return a string indicating the directory to change into.
    Default: '$HOME/proj'

    The default value may be overridden by setting the environment variable
    YARELY_PARENT.

    """

    if "YARELY_PARENT" in os.environ:
        return os.environ["YARELY_PARENT"]

    user_home = os.environ.get("HOME")
    if user_home is None:
        msg = "YARELY_PARENT not set and unable to concoct default value"
        raise StarterError(msg)

    return os.path.join(user_home, "proj")
