#!/usr/bin/env python
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
from setuptools import setup

# Local imports
import yarely


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

platforms = ["Mac OS X >= 10.6"]
requirements = ['pyserial', 'tornado', 'zmq', 'certifi']
test_requirements = []

setup(
    author=yarely.__author__,
    author_email=yarely.__email__,

    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=sorted([
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Developers",
        "Natural Language :: English",

        # There is no specific classifier for Apache 2.0 right now (Aug 2016)
        # If there were, we could build this using yarely.__license__.
        "License :: OSI Approved :: Apache Software License",

        # OS support -- currently OS X >= 10.6
        # See also the platforms variable (no format defined by setuptools).
        "Environment :: MacOS X :: Cocoa",
        "Operating System :: MacOS :: MacOS X",

        # Supported Python versions
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6"
    ]),

    description=yarely.__shortdescription__,
    include_package_data=True,
    install_requires=requirements,
    keywords="yarely digital signage",
    license=yarely.__license__,
    long_description="{readme}\n\n{changelog}".format(
      readme=readme, changelog=history
    ),
    name="yarely",
    packages=["yarely"],
    platforms=platforms,
    scripts=[],
    tests_require=test_requirements,
    url="https://github.com/opendisplays/yarely",
    version=yarely.__version__,
)
