#!/bin/sh

# Start a yarely application by pretending it's a module and passing in the
# path to the yarely configuration file.
# Example (valid on Darwin/Mac OS X):
#   $ ./yarely_application_starter.sh yarely/darwin/facade/facade.py
#
# This is mostly used by various starters that should be called following OS
# startup.

# YARELY_CONFIG will be passed as the last parameter to the application.
# If YARELY_CONFIG is not set in the environment a default value of
# "~/proj/yarely/config/yarely.cfg" will be used.

# It's probably better to alter YARELY_CONFIG in the environment rather
# than overwriting it in this script.  But boys will be boys.
#YARELY_CONFIG="/usr/local/packages/yarely-cfg/yarely.cfg"

### No user serviceable parts contained below ###

if [ -z "$YARELY_CONFIG" ]; then
    YARELY_CONFIG="${HOME}/proj/yarely/config/yarely.cfg"
fi

starters_path="`dirname "$0"`"

"$starters_path/yarely_module_starter.sh" "$@" "$YARELY_CONFIG"
