# -*- coding: utf-8 -*-
#
# Copyright 2011-2016 Lancaster University.
#
#
# This file is part of Yarely.
#
# Licensed under the Apache License, Version 2.0.
# For full licensing information see /LICENSE.


"""Module providing a Singleton type."""


class Singleton(type):
    """Singleton type. Designed to be used as a metaclass by classes that
    want to use the Singleton design pattern.

    Example:
        >>> class MySingleton(object, metaclass=Singleton):
        ...     pass
        >>> a = MySingleton()
        >>> b = MySingleton()
        >>> id(a) == id(b)
        True

    """

    def __init__(cls, *args, **kwargs):
        super(Singleton, cls).__init__(*args, **kwargs)
        cls.__instance = None

    def __call__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super(Singleton, cls).__call__(*args, **kwargs)
        return cls.__instance
