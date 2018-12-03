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
import sys

# Local (Yarely) imports
from yarely.core.displaycontroller.serial_display_device import (
    SerialControlledPublicDisplay, SerialControlledPublicDisplayCommandLineApp
)


log = logging.getLogger(__name__)


class LGPublicDisplay(SerialControlledPublicDisplay):
    """Compatible with LG displays."""
    DEVICE_TYPE = 'LG Display'

    # DisplayCommands
    _COMMAND_POWER_OFF = b'ka 00 00\r'
    _COMMAND_POWER_ON = b'ka 00 01\r'
    _ENQUIRY_POWER_STATUS = b'ka 00 ff\r'

    _STATE_POWER_OFF = b'a 01 OK00x'
    _STATE_POWER_ON = b'a 01 OK01x'

    # DISPLAY VOLUME COMMANDS
    LG_COMMAND_SET_MUTE_OFF = b'ke 00 01\r'
    LG_COMMAND_SET_MUTE_ON = b'ke 00 00\r'
    LG_COMMAND_SET_VOLUME = b'kf 00 {}\r'

    # VALID VOLUME VALUES
    LG_MIN_VOLUME = 0
    LG_MAX_VOLUME = 64


if __name__ == '__main__':
    args = sys.argv
    SerialControlledPublicDisplayCommandLineApp.main(LGPublicDisplay, args)
