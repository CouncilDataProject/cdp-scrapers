# -*- coding: utf-8 -*-

"""
Individual scratchpad and maybe up-to-date CDP instance scrapers.
"""

from pkgutil import iter_modules
import importlib
import inspect
from typing import Dict, Type

from cdp_scrapers.legistar_utils import LegistarScraper

###############################################################################


SCRAPERS: Dict[str, Type[LegistarScraper]] = {}
for submodule in iter_modules(__path__):
    # Import the submodule
    mod = importlib.import_module(f"{__name__}.{submodule.name}")

    # Get the scraper from the module
    for a, member_cls in inspect.getmembers(mod, inspect.isclass):
        if (
            issubclass(member_cls, LegistarScraper)
            and member_cls is not LegistarScraper
        ):
            # Attach the class to scrapers with it's municipality name
            SCRAPERS[member_cls.MUNICIPALITY_SLUG] = member_cls

# Not inhereting from the LegistarScraper?
# Add your scraper class here
# SCRAPERS[{municipality_slug}] = {class_def}
