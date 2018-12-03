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
    DISPLAY_IS_OFF, DISPLAY_IS_ON, DISPLAY_UNEXPECTED_RESULT,
    DISPLAY_UNRESPONSIVE, SerialControlledPublicDisplay,
    SerialControlledPublicDisplayCommandLineApp
)


log = logging.getLogger(__name__)


class SanyoPublicDisplay(SerialControlledPublicDisplay):
    """Compatible with Sanyo displays and possibly also Sanyo projectors."""
    DEVICE_TYPE = 'Sanyo'

    # Display commands
    _COMMAND_POWER_OFF = bytearray([0x43, 0x30, 0x31, 0x0D])
    _COMMAND_POWER_ON = bytearray([0x43, 0x30, 0x30, 0x0D])
    _ENQUIRY_POWER_STATUS = bytearray([0x43, 0x52, 0x30, 0x0D])

    # Display power state
    _STATE_POWER_OFF = bytearray([0x38, 0x30, 0x0D])
    _STATE_POWER_ON = bytearray([0x30, 0x30, 0x0D])

    # Additional display states that are returned instead of the power state
    _STATE_PROCESSING_COOLING_DOWN = bytearray([0x32, 0x30, 0x0D])
    _STATE_POWER_FAILURE = bytearray([0x31, 0x30, 0x0D])
    _STATE_PROCESSING_COOLING_DOWN_AFTER_ABNORMAL_TEMPERATURE = bytearray(
        [0x32, 0x38, 0x0D]
    )
    _STATE_ABNORMAL_TEMPERATURE = bytearray([0x30, 0x38, 0x0D])
    _STATE_STANDBY_AFTER_ABNORMAL_TEMPERATURE = bytearray([0x38, 0x38, 0x0D])
    _STATE_PROCESSING_POWER_SAVE_COOLING_DOWN = bytearray([0x32, 0x34, 0x0D])
    _STATE_POWER_SAVE = bytearray([0x30, 0x34, 0x0D])
    _STATE_COOLING_DOWN_AFTER_LAMP_FAILURE = bytearray([0x32, 0x31, 0x0D])
    _STATE_STANDBY_AFTER_LAMP_FAILURE = bytearray([0x38, 0x31, 0x0D])

    # All the below states indicate that the display is powered off.
    _LIST_STATE_OFF = [
        _STATE_PROCESSING_COOLING_DOWN,
        _STATE_PROCESSING_COOLING_DOWN_AFTER_ABNORMAL_TEMPERATURE,
        _STATE_STANDBY_AFTER_ABNORMAL_TEMPERATURE,
        _STATE_PROCESSING_POWER_SAVE_COOLING_DOWN,
        _STATE_COOLING_DOWN_AFTER_LAMP_FAILURE,
        _STATE_STANDBY_AFTER_LAMP_FAILURE,
        _STATE_POWER_OFF
    ]

    # Some standard display serial settings
    _BAUDRATE = 19200

    def _parse_power_status(self, response):
        """ Parse the response from display and return DISPLAY_IS_ON or
        DISPLAY_IS_OFF.

        To check if the display is off we see if the return value is in the
        LIST_STATE_OFF as any of these values indicate that the display is in
        standby.

        """
        # Handle the expected states (ON / OFF).
        if response == self._STATE_POWER_ON:
            log.info('Display is on.')
            return DISPLAY_IS_ON
        elif response in self._LIST_STATE_OFF:
            log.info('Display is off.')
            return DISPLAY_IS_OFF

        # If no response or response does not match, display is most
        # likely off but could be in an error state.
        elif not response:
            log.warning('Display is not responding.')
            return DISPLAY_UNRESPONSIVE

        log.warning(
            'Display response "{}" did not match expected values.'.format(
                response
            )
        )
        return DISPLAY_UNEXPECTED_RESULT


if __name__ == '__main__':
    args = sys.argv
    SerialControlledPublicDisplayCommandLineApp.main(SanyoPublicDisplay, args)
