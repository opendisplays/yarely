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
import re
from logging.handlers import TimedRotatingFileHandler

# Importing __main__ is a bit magic, but it seems to work ok
import __main__

CLEAN_FILENAME_RE = re.compile('[^a-zA-Z0-9.]')


class TimedRotatingFileHandlerWithApplicationName(TimedRotatingFileHandler):
    """A TimedRotatingFileHandler that is aware of the main application's name.

    Useful when the same logging configuration should be used by multiple
    processes which are started with different main module names.

    Arguments are identical to TimedRotatingFileHandler, save that
    filename is run through str.format to replace 'application_name' with
    the application name.

    """

    def __init__(self, filename, *args, **kwargs):
        # Small bodge to make sure we get different filenames for processes
        # within the same package
        application_name = CLEAN_FILENAME_RE.sub('_', __main__.__file__)

        # Little cleanup to shorten names a bit
        usual_path_start_string = '_yarely_'
        index_of_usual_path_start_string = application_name.rfind(
          usual_path_start_string
        )
        if index_of_usual_path_start_string >= 0:
            application_name = application_name[
              index_of_usual_path_start_string+1:
            ]

        # Coerce the names to strings because in some odd cases one of them
        # ends up as None
        # 13 Nov 2013 -- do we need this anymore??
        filename = filename.format(application_name=application_name)

        super().__init__(filename, *args, **kwargs)
