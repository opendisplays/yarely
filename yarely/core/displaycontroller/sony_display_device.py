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


class SonyPublicDisplay(SerialControlledPublicDisplay):
    """Compatible with Sony FWD-40LX1."""

    DEVICE_TYPE = 'Sony FWD-40LX1'

    # Display commands and return values
    _COMMAND_POWER_ON = bytearray([0x8c, 0x00, 0x00, 0x02, 0x01])
    _COMMAND_POWER_OFF = bytearray([0x8c, 0x00, 0x00, 0x02, 0x00])
    _COMMAND_SET_INPUT_INPUT2_RGB = bytearray([0x8c, 0x00, 0x01, 0x02, 0x0a])
    _COMMAND_SET_INPUT_INPUT2_COMPONENT = bytearray(
        [0x8c, 0x00, 0x01, 0x02, 0x0b]
    )
    _COMMAND_SET_INPUT_OPTION1_VIDEO = bytearray(
        [0x8c, 0x00, 0x01, 0x02, 0x0c]
    )
    _COMMAND_SET_INPUT_OPTION1_S_VIDEO = bytearray(
        [0x8c, 0x00, 0x01, 0x02, 0x0d]
    )
    _COMMAND_SET_INPUT_OPTION1_RGB = bytearray([0x8c, 0x00, 0x01, 0x02, 0x0e])
    _COMMAND_SET_INPUT_OPTION1_COMPONENT = bytearray(
        [0x8c, 0x00, 0x01, 0x02, 0x0f]
    )
    _COMMAND_SET_INPUT_OPTION2_VIDEO = bytearray(
        [0x8c, 0x00, 0x01, 0x02, 0x10]
    )
    _COMMAND_SET_INPUT_OPTION2_S_VIDEO = bytearray(
        [0x8c, 0x00, 0x01, 0x02, 0x11]
    )
    _COMMAND_SET_INPUT_OPTION2_RGB = bytearray([0x8c, 0x00, 0x01, 0x02, 0x12])
    _COMMAND_SET_INPUT_OPTION2_COMPONENT = bytearray(
        [0x8c, 0x00, 0x01, 0x02, 0x13]
    )
    _COMMAND_SET_INPUT_INPUT1_DVI = bytearray([0x8c, 0x00, 0x01, 0x02, 0x20])
    _COMMAND_GET_INPUT_STATUS = bytearray([0x83, 0x00, 0x01, 0xff, 0xff])
    _COMMAND_SET_MUTE_OFF = bytearray([0x8c, 0x00, 0x03, 0x02, 0x00])
    _COMMAND_SET_MUTE_ON = bytearray([0x8c, 0x00, 0x03, 0x02, 0x01])
    _COMMAND_SET_VOLUME = bytearray([0x8c, 0x10, 0x30, 0x02])
    _ENQUIRY_POWER_STATUS = [0x83, 0x00, 0x00, 0xFF, 0xFF]
    _STATE_POWER_ON = bytearray([0x70, 0x00, 0x02, 0x01, 0x73])
    _STATE_POWER_OFF = bytearray([0x70, 0x00, 0x02, 0x00, 0x72])

    # Volume settings
    _MIN_VOLUME = 0
    _MAX_VOLUME = 64

    def _get_volume_code(self, volume_percentage):
        code = self._COMMAND_SET_VOLUME[:]
        volume = int((self._MAX_VOLUME / 100.0) * volume_percentage)
        code.append(volume)
        log.debug("Volume code is {volume_code}".format(volume_code=code))
        return code

    @staticmethod
    def _calculate_checksum(buf, length):
        checksum = 0
        for pos in range(length):
            checksum += buf[pos]

        checksum &= ~0xff00
        log.debug("Checksum is %x" % checksum)
        return checksum

    def _send_cmd(self, cmd):
        chksum = self._calculate_checksum(cmd, len(cmd))
        cmd_with_chksum = cmd[:]
        cmd_with_chksum.append(chksum)
        self._send_raw_cmd(cmd_with_chksum)


if __name__ == '__main__':
    args = sys.argv
    SerialControlledPublicDisplayCommandLineApp.main(SonyPublicDisplay, args)
