"""
Módulo de scrapers específicos para cada IIS.
"""

from .ciberisciii import CiberisciiiPlaywrightScraper
from .fimabis import FimabisScraper
from .igtp import IgtpScraper

__all__ = [
    'CiberisciiiPlaywrightScraper',
    'FimabisScraper', 
    'IgtpScraper'
]
