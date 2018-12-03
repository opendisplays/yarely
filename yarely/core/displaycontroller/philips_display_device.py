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


class PhilipsPublicDisplay(SerialControlledPublicDisplay):
    """Compatible with Philips displays."""
    DEVICE_TYPE = 'Philips'
    DISPLAY_ID = 1

    # Display commands

    # All commands WITHOUT length and checksum. We'll calculate that one.
    _COMMAND_POWER_OFF = bytearray([DISPLAY_ID, 0x18, 0x01])
    _COMMAND_POWER_ON = bytearray([DISPLAY_ID, 0x18, 0x02])
    _ENQUIRY_POWER_STATUS = bytearray([DISPLAY_ID, 0x19])

    # The following two should match exactly the output of the display.
    _STATE_POWER_OFF = bytearray(
        [0x05, DISPLAY_ID, 0x19, 0x01, 0x1C]
    )
    _STATE_POWER_ON = bytearray(
        [0x05, DISPLAY_ID, 0x19, 0x02, 0x1F]
    )

    @staticmethod
    def _get_checksum(cmd_array):
        checksum = 0
        for cmd in cmd_array:
            checksum ^= cmd
        return checksum

    @staticmethod
    def _get_cmd_length(cmd_array, add_to_length=0):
        return len(cmd_array) + add_to_length

    def _send_cmd(self, cmd):
        """Sends command to the display and first automatically prepends the
        length of the command and appends the checksum (according to Philips
        RS-232 specifications).

        """
        # Get length and checksum
        length = self._get_cmd_length(cmd, 2)  # checksum + length = 2 bytes
        cmd.insert(0, length)
        checksum = self._get_checksum(cmd)
        cmd.append(checksum)

        self._send_raw_cmd(cmd)


if __name__ == '__main__':
    args = sys.argv
    SerialControlledPublicDisplayCommandLineApp.main(
        PhilipsPublicDisplay, args
    )
