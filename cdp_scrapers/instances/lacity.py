#!/usr/bin/env python

import logging
from datetime import datetime
from typing import Any, List, Optional

from cdp_backend.pipeline.ingestion_models import EventIngestionModel

from ..prime_gov_utils import PrimeGovScraper

###############################################################################

log = logging.getLogger(__name__)

###############################################################################


class LosAngelesScraper(PrimeGovScraper):
    PYTHON_MUNICIPALITY_SLUG: str = "lacity"

    def __init__(self):
        """LA, CA specific implementation of PrimeGovScraper."""
        super().__init__(
            client_id="lacity",
            timezone="America/Los_Angeles",
        )


def get_lacity_events(
    from_dt: Optional[datetime] = None,
    to_dt: Optional[datetime] = None,
    **kwargs: Any,
) -> List[EventIngestionModel]:
    """
    Public API for use in instances.__init__ so that this func can be attached
    as an attribute to cdp_scrapers.instances module.
    Thus the outside world like cdp-backend can get at this by asking for
    "get_lacity_events".

    Parameters
    ----------
    from_dt: datetime, optional
        The timespan beginning datetime to query for events after.
        Default is 2 days from UTC now
    to_dt: datetime, optional
        The timespan end datetime to query for events before.
        Default is UTC now
    kwargs: Any
        Any extra keyword arguments to pass to the get events function.

    Returns
    -------
    events: List[EventIngestionModel]

    See Also
    --------
    cdp_scrapers.instances.__init__.py
    """
    scraper = LosAngelesScraper()
    return scraper.get_events(begin=from_dt, end=to_dt, **kwargs)
