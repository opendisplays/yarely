# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


class Struct:
    """A base-class for C-style structs -- it's just a dictionary
    with class-style attribute access.

    """
    def __init__(self, **kwargs):
        """
        :param dict kwargs: a dict of key-value pairs to initialise the
            :class:`Struct` with.

        """
        # We could do this in a single line:
        #     self.__dict__.update(**kwargs)
        # BUT we don't because doing it this way allows subclasses to
        # override __setattr__().
        for key, value in kwargs.items():
            self.__setattr__(key, value)
