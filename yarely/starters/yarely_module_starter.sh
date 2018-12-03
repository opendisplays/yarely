#!/bin/sh


# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


# Start a yarely module with the appropriate paths configured.
#
# This is mostly called internally from yarely - yarely_application_starter.sh
# is the main culprit.

# YARELY_PARENT will be appended to PYTHONPATH and will become the started
# module's working directory.  If YARELY_PARENT is not set in the environment
# a default value of "~/proj" will be used.

# It's probably better to alter YARELY_PARENT in the environment rather
# than overwriting it in this script, but I'll leave this temptation here
# just in case...

### No user serviceable parts contained below ###

if [ -z "$YARELY_PARENT" ]; then
    YARELY_PARENT="${HOME}/proj"
fi

cd "$YARELY_PARENT"

PYTHONPATH="${PYTHONPATH}:${YARELY_PARENT}"
export PYTHONPATH

#echo "**********"
#echo "Deprecated"
#echo "**********"
#echo "The shell-based starters are deprecated.  Why not try the wonderful new"
#echo "Python-based starters?"

exec python3 "$@"
