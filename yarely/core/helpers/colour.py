# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


""" Yarely colour module. """

# Standard library imports
import warnings

# Some common error messages
TYPE_ERROR_MSG = 'Expected parameter as {type}'
LEN_ERROR_MSG = "'{value}' is an rgb hex string of invalid length"
HEX_ERROR_MSG = "'{value}' is not hex - contains invaid character"
HEX_PREFIX_ERROR_MSG = (
  "Expected # prefix for rgb hex string of length '{length} "
  "(supplied string was '{value}')"
)


class ColourError(Exception):
    """Base class for colour errors."""
    pass


class ColourFormatError(ColourError):
    """Raised when an unexpected colour format is received or requested."""
    pass


class RGBColour(object):
    """Translate between various RGB (Red, Green, Blue) colour encodings.

    Understands the following formats:
        * a hex representation string of length 3 or 6 (optionally with a
            leading #), case insensitive.

          Example:
              >>> RGBColour("F0F")
              RGBColour('#ff00ff')
              >>> RGBColour("#f0f")
              RGBColour('#ff00ff')
              >>> RGBColour("ff00ff")
              RGBColour('#ff00ff')
              >>> RGBColour("#ff00ff")
              RGBColour('#ff00ff')

              >>> test_colour = RGBColour("F0F")
              >>> print(test_colour.as_string(3))
              f0f

        * an arithmetic triplet (values between 0 and 1).

          Example:
              >>> RGBColour((1.0, 0.0, 1.0))
              RGBColour('#ff00ff')

              >>> test_colour = RGBColour("ff00ff")
              >>> test_colour.as_arithmetic_triplet()
              (1.0, 0.0, 1.0)

        * (output only) a digital 8 bit triplet (values between 0 and 255).

          Example:
              >>> test_colour = RGBColour("ff00ff")
              >>> test_colour.as_digital_8bit_triplet()
              (255, 0, 255)


    The equality of RGBColour instances can be compared.

    Example:

        >>> RGBColour('#ff00ff') == RGBColour((1.0, 0.0, 1.0))
        True
        >>> RGBColour('#ff01ff') == RGBColour((1.0, 0.0, 1.0))
        False

    """

    # Note - self.colour is stored as a digital triplet (8 bit).
    # That is, a tuple of three values from 0-255.

    def __init__(self, colour_in):
        """Default constructor - create a new :class:`RGBColour` object.

        :param colour_in: a colour representation in any of the previously
            described acceptable formats.

        """
        if isinstance(colour_in, str):
            if len(colour_in) in (3, 4, 6, 7):
                self.colour = RGBColour._from_hexstring(colour_in)
            else:
                raise ColourFormatError(LEN_ERROR_MSG.format(value=colour_in))
        elif isinstance(colour_in, (list, tuple)):
            self.colour = RGBColour._from_arithmetic_triplet(colour_in)
        else:
            msg = TYPE_ERROR_MSG.format(type='string or a tuple')
            raise TypeError(msg)

    def __eq__(self, other):
        return (self.as_digital_8bit_triplet() ==
                other.as_digital_8bit_triplet())

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        representation = self.as_string()
        return "RGBColour({value!r})".format(value=representation)

    @staticmethod
    def _from_arithmetic_triplet(triplet):
        # Validate length
        if len(triplet) is not 3:
            ok_types = 'tuple of length 3'
            msg = TYPE_ERROR_MSG.format(type=ok_types)
            raise ValueError(msg)

        # Validate triplet values and convert
        digital_triplet = []
        for val in triplet:
            if val > 1:
                ok_types = 'tuple containing only values less than 1'
                msg = TYPE_ERROR_MSG.format(type=ok_types)
                raise ValueError(msg)
            digital_triplet.append(int(val * 255))
        return tuple(digital_triplet)

    @staticmethod
    def _from_hexstring(val):
        orig_val = val

        # Check for hash prefix and remove
        if len(val) in (4, 7):
            if val[0] != '#':
                msg = HEX_PREFIX_ERROR_MSG.format(value=val, length=len(val))
                raise ColourFormatError(msg)
            val = val[1:]

        # Validate length.
        #
        # NOTE - Not an elif - these values have been rewritten above.
        if len(val) in (3, 6):
            # Validate content is valid hex
            try:
                for hex_char in val:
                    int(hex_char, 16)
            except ValueError as e:
                msg = HEX_ERROR_MSG.format(value=orig_val)
                raise ColourFormatError(msg) from e
        else:
            raise ColourFormatError(LEN_ERROR_MSG.format(value=val))

        # Rewrite all strings to length six
        if len(val) is 3:
            val = ''.join([char * 2 for char in val])
        assert len(val) is 6

        # Extract the value
        try:
            return tuple([int(val[i:i + 2], 16) for i in (0, 2, 4)])
        except ValueError as e:                         # Invalid characters
            raise ColourFormatError(                    # should already have
                HEX_ERROR_MSG.format(value=orig_val)    # been caught. This
            ) from e                                    # should never execute!

    def as_arithmetic_triplet(self):
        """Return an arithmetic triplet representation of this RGBColour
        instance. An arithmetic triplet is an rgb tuple of length three.
        All values within the tuple are floats between 0 and 1.

        :rtype: tuple

        Example:
            >>> r = RGBColour('FF00FF')
            >>> r.as_arithmetic_triplet()
            (1.0, 0.0, 1.0)

        """
        return tuple([i / 255 for i in self.colour])

    def as_digital_triplet(self, bits):
        """Alias for as_digital_8bit_triplet and as_digital_16bit_triplet.

        :param int bits: number of bits to use in the colour representation.
        :rtype: tuple

        Example:
            >>> r = RGBColour('FF00FF')
            >>> r.as_digital_triplet(8)
            (255, 0, 255)

        """
        if bits not in (8, 16):
            msg = 'Invalid number of bits: a digital triplet is 8 or 16 bit'
            raise(ColourFormatError(msg))
        elif bits is 8:
            return self.as_digital_8bit_triplet()
        return self.as_digital_16bit_triplet()

    def as_digital_8bit_triplet(self):
        """Return an 8-bit digital triplet representation of this RGBColour
        instance. An 8-bit digital triplet is an rgb tuple of length three.
        All values within the tuple are integers between 0 and 255.

        :rtype: tuple

        Example:
            >>> r = RGBColour('FF00FF')
            >>> r.as_digital_8bit_triplet()
            (255, 0, 255)

        """
        return self.colour

    def as_digital_16bit_triplet(self):
        """Not implemented.

        :raises NotImplementedError: always.

        """                          # Should return a tuple of three 0-65535
        raise NotImplementedError()  # int values.

    def as_string(self, length=7):
        """Return a string representation of this RGBColour instance. The
        representation will have a length of length (default value is 7
        - acceptable values are 3, 4, 6 and 7) which includes a hash prefix
        if one would be expected for that length.

        :param int length: length of the HTML colour representation to use
            (accepted values: 3, 4, 6 or 7).
        :rtype: string

        Example:
            >>> r = RGBColour('FF00FF')
            >>> print(r.as_string())
            #ff00ff
            >>> print(r.as_string(3))
            f0f
            >>> print(r.as_string(4))
            #f0f
            >>> print(r.as_string(6))
            ff00ff
            >>> print(r.as_string(7))
            #ff00ff

        """
        # Validate length and prefix
        if length not in (3, 4, 6, 7):
            msg = 'Invalid rgb string length.'
            raise ColourFormatError(msg)

        # Generate a tuple of hex strings
        hex_tuple = ['{hex:0>2}'.format(hex=hex(i)[2:]) for i in self.colour]

        # Check to see if we can accurately represent the colour within the
        # specified length and truncate as appropriate. Return the string.
        if length < 6:
            # Truncate - this will log a warning if truncating will result
            # in a loss of precision (i.e. the lower byte is not the same
            # as the upper byte).
            hex_truncated = [val[0] for val in hex_tuple]
            if True in [hex_val[0] != hex_val[1] for hex_val in hex_tuple]:
                msg = (
                    "Loss of precision: value {orig} cannot be accurately "
                    "represented in length {length}, value {new} will be used."
                )
                msg = msg.format(
                  orig=hex_tuple, length=length, new=hex_truncated
                )
                warnings.warn(msg)
            hex_tuple = hex_truncated

        prefix = '#' if length in (4, 7) else ''
        return '{prefix}{val}'.format(prefix=prefix, val=''.join(hex_tuple))
