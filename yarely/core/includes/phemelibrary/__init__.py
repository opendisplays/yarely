# -*- coding: utf-8 -*-

__author__ = 'Lancaster University'
__email__ = 'ecampus@lancaster.ac.uk'
__version__ = '0.1.0'


# keeping import statements short :)
from .phemelibrary import PhemeAnalytics
from . import IAexceptions
from .APIWrapper import APIWrapper


__all__ = [
    'PhemeAnalytics', 'IAexceptions', 'APIWrapper'
]
