# -*- coding: utf-8 -*-

"""
Individual scratchpad and maybe up-to-date CDP instance scrapers.
"""

import importlib
import inspect
import sys
from datetime import datetime
from functools import partial
from pkgutil import iter_modules
from typing import Any, Callable, Dict, List, Type

from cdp_backend.pipeline.ingestion_models import EventIngestionModel
from cdp_backend.pipeline.mock_get_events import (
    get_events as get_test_deployment_events,
)

from cdp_scrapers.legistar_utils import LegistarScraper
from cdp_scrapers.instances.portland import get_portland_events

###############################################################################


def _init_and_run_get_events(
    from_dt: datetime,
    to_dt: datetime,
    legistar_scraper: Type[LegistarScraper],
    **kwargs: Any,
) -> List[EventIngestionModel]:
    scraper = legistar_scraper()
    return scraper.get_events(begin=from_dt, end=to_dt, **kwargs)


SCRAPER_FUNCTIONS: Dict[str, Callable] = {}
for submodule in iter_modules(__path__):
    # Import the submodule
    mod = importlib.import_module(f"{__name__}.{submodule.name}")

    # Get the scraper from the module
    for a, member_cls in inspect.getmembers(mod, inspect.isclass):
        if (
            issubclass(member_cls, LegistarScraper)
            and member_cls is not LegistarScraper
        ):
            scraper_get_events = partial(
                _init_and_run_get_events,
                legistar_scraper=member_cls,
            )
            # Attach the partial function to the scraper functions dict
            SCRAPER_FUNCTIONS[member_cls.PYTHON_MUNICIPALITY_SLUG] = scraper_get_events

# Not inhereting from the LegistarScraper?
# Add your scraper function here
# SCRAPER_FUNCTIONS[{python_municipality_slug}] = {function_callable}
SCRAPER_FUNCTIONS["test_deployment"] = get_test_deployment_events
SCRAPER_FUNCTIONS["portland"] = get_portland_events

# Set all scraper functions as exports of this module
for python_municipality_slug, func in SCRAPER_FUNCTIONS.items():
    setattr(sys.modules[__name__], f"get_{python_municipality_slug}_events", func)
