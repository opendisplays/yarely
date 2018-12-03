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


class IiyamaProLitePublicDisplay(SerialControlledPublicDisplay):
    """Compatible with Iiyama Pro Lite touch screen display."""
    DEVICE_TYPE = "Iiyama ProLite Public Display"

    # DisplayCommands
    _COMMAND_POWER_OFF = bytearray(
        [0x38, 0x30, 0x31, 0x73, 0x21, 0x30, 0x30, 0x30, 0x0D]
    )
    _COMMAND_POWER_ON = bytearray(
        [0x38, 0x30, 0x31, 0x73, 0x21, 0x30, 0x30, 0x31, 0x0D]
    )
    _ENQUIRY_POWER_STATUS = bytearray(
        [0x38, 0x30, 0x31, 0x67, 0x6C, 0x30, 0x30, 0x30, 0x0D]
    )

    _STATE_POWER_OFF = bytearray(
        [0x38, 0x30, 0x31, 0x72, 0x6C, 0x30, 0x30, 0x30, 0x0D, 0xFF]
    )
    _STATE_POWER_ON = bytearray(
        [0x38, 0x30, 0x31, 0x72, 0x6C, 0x30, 0x30, 0x31, 0x0D]
    )


if __name__ == '__main__':
    args = sys.argv
    SerialControlledPublicDisplayCommandLineApp.main(
        IiyamaProLitePublicDisplay, args
    )
