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


class SamsungPublicDisplay(SerialControlledPublicDisplay):
    """Compatible with Samsung 400MX and Samsung 460MX. """
    DEVICE_TPYE = "Samsung 400MX and Samsung 460MX"

    # According to the doc this is a special case where 0xFF is ID=0.
    DISPLAY_ID = 0xFF
    HEADER = 0xAA

    # DisplayCommands
    _COMMAND_POWER_OFF = bytearray([0x11, DISPLAY_ID, 1, 0])
    _COMMAND_POWER_ON = bytearray([0x11, DISPLAY_ID, 1, 1])
    _ENQUIRY_POWER_STATUS = bytearray([0x11, DISPLAY_ID, 0])

    # 65 = A
    _STATE_POWER_OFF = bytearray(
        [HEADER, 0xFF, DISPLAY_ID, 3, 65, 0x11, 0, 83]
    )
    _STATE_POWER_ON = bytearray([HEADER, 0xFF, DISPLAY_ID, 3, 65, 0x11, 1, 84])

    @staticmethod
    def _get_checksum(cmd_array):
        # The checksum is the sum of all parameters without the header.
        # The check sum should be always 2 hex digits (i.e. not over 0xFF).

        cmd_sum = sum(cmd_array)

        return cmd_sum % 256

    def _send_cmd(self, cmd):
        """This method builds the complete command that is going to be sent
        to the display. Gets the checksum first and appends it to the end of
        the bytearray. And prepends the header.

        """
        checksum = self._get_checksum(cmd)
        cmd.insert(0, self.HEADER)
        cmd.append(checksum)

        self._send_raw_cmd(cmd)


if __name__ == '__main__':
    args = sys.argv
    SerialControlledPublicDisplayCommandLineApp.main(
        SamsungPublicDisplay, args
    )
