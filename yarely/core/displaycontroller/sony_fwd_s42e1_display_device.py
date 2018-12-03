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


class SonyFWDS42E1PublicDisplay(SerialControlledPublicDisplay):
    """Compatible with Sony FWD-S42E1 public displays."""
    DEVICE_TYPE = 'Sony FWD-S42E1'

    # DisplayCommands
    _COMMAND_POWER_OFF = bytearray([0x8c, 0x00, 0x00, 0x02, 0x00, 0x8E])
    _COMMAND_POWER_ON = bytearray([0x8c, 0x00, 0x00, 0x02, 0x01, 0x8F])
    _ENQUIRY_POWER_STATUS = bytearray([0x83, 0x00, 0x00, 0xFF, 0xFF, 0x81])

    _STATE_POWER_OFF = bytearray([0x70, 0x00, 0x02, 0x00, 0x72])
    _STATE_POWER_ON = bytearray([0x70, 0x00, 0x02, 0x01, 0x73])


if __name__ == '__main__':
    args = sys.argv
    SerialControlledPublicDisplayCommandLineApp.main(
        SonyFWDS42E1PublicDisplay, args
    )
