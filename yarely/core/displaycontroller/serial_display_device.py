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
import os
import serial
import subprocess
import sys
import time

log = logging.getLogger(__name__)


# Return values for the rest of Yarely to use
DISPLAY_IS_ON = 'IS_ON'
"""Represents the state in which a display is powered on."""
DISPLAY_IS_OFF = 'IS_OFF'
"""Represents the state in which a display is powered off."""
DISPLAY_UNRESPONSIVE = 'UNRESPONSIVE'
"""Represents the state in which a display does not respond to status
requests.

"""
DISPLAY_UNEXPECTED_RESULT = 'UNKNOWN'
"""Represents the state in which a display responds to status requests but
with a result that does not match the known ON / OFF responses.

"""


class SerialControlledPublicDisplay(object):
    """Base class for communicating with serial controlled display hardware."""

    DEVICE_TYPE = None    # Subclasses to provide something sensible
    """A human-readable description of this display device (e.g.,
    manufacturer, device series).
    """

    # Typical location of the USB serial devices on Mac OS
    _USB_SERIAL = '/dev/tty.usbserial-'

    # Some standard display serial settings
    _BAUDRATE = 9600
    _PARITY = serial.PARITY_NONE
    _STOPBITS = serial.STOPBITS_ONE
    _BYTESIZE = serial.EIGHTBITS

    # Display commands and return values
    #
    # Subclasses to provide some non-empty bytearrays here.
    _COMMAND_POWER_ON = bytearray()
    _COMMAND_POWER_OFF = bytearray()
    _ENQUIRY_POWER_STATUS = bytearray()
    _STATE_POWER_ON = bytearray()
    _STATE_POWER_OFF = bytearray()

    def __init__(self, port):
        self.serial_connection = self._open_serial(port)

    def _close_serial(self):
        """Closes this object's serial connection."""

        log.debug("Close serial <<<{serial}>>>".format(
            serial=self.serial_connection)
        )
        self.serial_connection.close()

    def _flush_buffer(self):
        self.serial_connection.flush()

    def _open_serial(self, port):
        """Opens and returns a serial connection."""

        # Build a full device name based on the fact that this will be a
        # USB->serial device.
        full_path_to_port = self._USB_SERIAL + port
        log.debug("Open serial: {full_path_to_port}".format(
            full_path_to_port=full_path_to_port)
        )

        # Open the serial connection
        try:
            serial_connection = serial.Serial(
                port=full_path_to_port, baudrate=self._BAUDRATE,
                parity=self._PARITY, stopbits=self._STOPBITS,
                bytesize=self._BYTESIZE
            )

        # Handle any errors (e.g. if port is incorrect)
        except OSError as err:
            log.error("Cannot open serial connection: {}".format(err))
            sys.exit(1)  # Exit out of script with an error status.

        # Return the result
        log.debug(
            "Opened serial <<<{serial}>>>".format(serial=serial_connection)
        )
        return serial_connection

    def _read_raw_response(self):
        log.debug("Reading serial...")

        # Sleep for 1 sec to give device time to answer
        time.sleep(1)

        # Grab a byte stream from the serial connection
        output_list = list()

        while self.serial_connection.inWaiting() > 0:
            raw_output = self.serial_connection.read(1)
            int_output = ord(raw_output)
            output_list.append(int_output)

        # Return the output as a bytearray if it isn't already
        if not isinstance(output_list, bytearray):
            output_list = bytearray(output_list)

        log.debug("Response from serial: {response}".format(
            response=output_list)
        )
        return output_list

    def _send_raw_cmd(self, cmd):
        """Sends a raw command over the serial connection.

        :param cmd: the command to be sent.
        :type cmd: byte, OR bytearray.

        """
        log.debug(
            "Send raw cmd <<<{cmd}>>> to <<<{ser}>>>".format(
                cmd=cmd, ser=self.serial_connection
            )
        )

        # Clear the buffer first.
        self._flush_buffer()

        # And then send the command.
        response = self.serial_connection.write(cmd)
        log.debug("<<<{response}>>> bytes written.".format(response=response))

    def _send_cmd(self, cmd):
        # Some subclasses may need to calculate checksums etc.
        #     _send_raw_cmd()      just sends the command over serial
        #     _send_cmd()          will send the command plus any checksum
        self._send_raw_cmd(cmd)

    def _parse_power_status(self, response):
        """Parse the response from display and return the appropriate values,
        such as DISPLAY_IS_ON, DISPLAY_IS_OFF, DISPLAY_UNRESPONSIVE and
        DISPLAY_UNEXPECTED_RESULT.

        Extend this method if the display supports additional state values.

        """
        # Handle the expected states (ON / OFF).
        if response == self._STATE_POWER_ON:
            log.info('Display is on.')
            return DISPLAY_IS_ON
        elif response == self._STATE_POWER_OFF:
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

    def get_power_status(self):
        """Request and return the power status of this display.

        rtype: string
        return: a description of the power state of this display. Should be
            one of the constants provided by this class (i.e.,
            DISPLAY_IS_ON, DISPLAY_IS_OFF, DISPLAY_UNRESPONSIVE,
            DISPLAY_UNEXPECTED_RESULT).

        """

        # Send a status request over the serial connection
        log.debug("Requesting display power status")

        self._send_cmd(self._ENQUIRY_POWER_STATUS)

        # Read back the response data
        response = self._read_raw_response()

        return self._parse_power_status(response)

    def turn_off(self):
        """Send a serial command designed to turn the display off. """
        self._send_cmd(self._COMMAND_POWER_OFF)

        # We have to read out the response or the display won't turn off.
        log.debug("Response: {}".format(self._read_raw_response()))

    def turn_on(self):
        """Send a serial command designed to turn the display on. """
        self._send_cmd(self._COMMAND_POWER_ON)

        # We have to read out the response or the display won't turn on.
        log.debug("Response: {}".format(self._read_raw_response()))


# Version of the command line app with no reboot backdoor :)
class _SerialControlledPublicDisplayCommandLineApp(object):

    # Default commands and helptext for when this class is executed in the
    # most typical/expected way.
    COMMAND_POWER_ON = 'ON'
    """Command-line argument to turn the the display on."""
    COMMAND_POWER_OFF = 'OFF'
    """Command-line argument to turn the the display off."""
    ENQUIRY_POWER_STATUS = 'GET_POWER_STATUS'
    """Command-line argument to check the power state of the display."""
    VALID_COMMANDS = (
        COMMAND_POWER_ON, COMMAND_POWER_OFF, ENQUIRY_POWER_STATUS
    )
    """The complete set of valid values for the command-line argument
    `command`.

    """
    HELPTEXT = (
        "Script to control and check a {{device_type}} display's power state "
        "via serial.\n\nusage: python3 {{filename}} [command] [serial_device]"
        "\n\ncommands:\n\n\t{commands}\n\nserial_device should be a "
        "{usbserial}-serial_device\n\nexample: python3 {{filename}} ON"
        "FTCY4Z0L"
    ).format(
        usbserial=SerialControlledPublicDisplay._USB_SERIAL,
        commands="\n\t".join(VALID_COMMANDS)
    )
    """Helptext to be printed if command-line arguments are not correct."""

    @classmethod
    def main(cls, serial_controlled_pd_cls, args):
        """Main entry point for most executions.

        :param serial_controlled_pd_cls: FIXME.
        :type serial_controlled_pd_cls: FIXME.
        :param list args: FIXME.

        """
        # Check validity of arguments
        command = None
        if len(args) is 3:
            command = args[1].upper()
            serial_device = args[2]
        if command not in cls.VALID_COMMANDS:
            print(cls.HELPTEXT.format(
                filename=args[0], device_type=cls.DEVICE_TYPE
            ))
            sys.exit()

        # Create new instance of a subclass of SerialControlledPublicDisplay.
        #
        # This will try and open the serial device -- this can raise an
        # OSError but the message is fairly self-explanatory so we'll just let
        # that bubble up to the user as it is.
        display = serial_controlled_pd_cls(serial_device)

        # Execute the command (parsed out of args).
        if command == cls.COMMAND_POWER_ON:
            display.turn_on()
        elif command == cls.COMMAND_POWER_OFF:
            display.turn_off()
        elif command == cls.ENQUIRY_POWER_STATUS:
            print(display.get_power_status())

        # Cleanup the serial device before we exit
        display._close_serial()


class _SerialControlledPublicDisplayCommandLineAppWithRebootBackdoor(
    _SerialControlledPublicDisplayCommandLineApp
):

    REBOOT_TRIGGER_FILES = [
        "/Users/ecampus/proj/yarely-local/restart.txt",
        "/Users/pdnet/proj/yarely-local/restart.txt"
    ]

    @staticmethod
    def _cleanup_reboot_trigger_files(reboot_trigger_files):
        success = True
        for f in reboot_trigger_files:
            try:
                log.debug("Removing file {}".format(f))
                os.remove(f)
            except OSError:
                log.error("Could not remove file {}".format(f))
                success = False
        return success

    @staticmethod
    def _reboot():
        # Wait for the dust to settle, this should give someone a hope of a
        # chance of fixing stuff (quickly) if we've screwed this script up.
        time.sleep(10)

        # Actually do the reboot
        try:
            log.debug("Rebooting machine")
            subprocess.call(["sudo", "reboot", "now"])
        except OSError:
            log.error("Could not reboot")

    @classmethod
    def _reboot_check(cls):
        reboot = False

        # Check for reboot files
        reboot_triggers = [
            f for f in cls.REBOOT_TRIGGER_FILES if os.path.exists(f)
        ]
        if reboot_triggers:
            log.debug('Found reboot trigger files: {}'.format(reboot_triggers))

            # If there's a reboot file, make sure to remove it before
            # rebooting ;)
            # If we can't successfully cleanup the files then we won't reboot!
            reboot = cls._cleanup_reboot_trigger_files(reboot_triggers)

        # Return True if we should reboot, False otherwise :)
        return reboot

    @classmethod
    def main(cls, serial_controlled_pd_cls, args):

        # This script has a bit of a funky side-effect, as well as powering
        # the displays on and off, we also provide a backdoor for rebooting
        # the OS itself.
        if cls._reboot_check():
            cls._reboot()
            sys.exit()    # The machine will reboot now anyway :)

        super().main(serial_controlled_pd_cls, args)

SerialControlledPublicDisplayCommandLineApp = (
    _SerialControlledPublicDisplayCommandLineAppWithRebootBackdoor
)
