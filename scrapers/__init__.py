"""
Módulo de scrapers específicos para cada IIS.
"""

from .ciberisciii import CiberisciiiPlaywrightScraper
from .fimabis import FimabisScraper
from .igtp import IgtpScraper
from .imib import ImibScraper
from .idival import IdivalScraper
from .ibis_sevilla import IbisSevillaScraper
from .ibs_granada import IbsGranadaScraper
from .ibsal import IbsalScraper
from .idibaps import IdibapsScraper
from .puerta_hierro import PuertaHierroScraper
from .idis_santiago import IdisSantiagoScraper
from .iis_la_fe import IisLaFeScraper
from .iis_princesa import IisPrincesaScraper
from .iisgm import IisgmScraper
from .biobizkaia import BiobizkaiaScraper

__all__ = [
    'CiberisciiiPlaywrightScraper',
    'FimabisScraper', 
    'IgtpScraper',
    'ImibScraper',
    'IdivalScraper',
    'IbisSevillaScraper',
    'IbsGranadaScraper',
    'IbsalScraper',
    'IdibapsScraper',
    'PuertaHierroScraper',
    'IdisSantiagoScraper',
    'IisLaFeScraper',
    'IisPrincesaScraper',
    'IisgmScraper',
    'BiobizkaiaScraper'
]
