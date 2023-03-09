#!/usr/bin/env python

from datetime import datetime
from typing import Any, List

from cdp_backend.pipeline.ingestion_models import EventIngestionModel

###############################################################################


def get_events(
    from_dt: datetime,
    to_dt: datetime,
    **kwargs: Any,
) -> List[EventIngestionModel]:
    """
    Get all events for the provided timespan.

    Parameters
    ----------
    from_dt: datetime
        Datetime to start event gather from.
    to_dt: datetime
        Datetime to end event gather at.
    kwargs: Any
        Any keyword arguments to provide to downstream functions.

    Returns
    -------
    events: List[EventIngestionModel]
        All events gathered that occured in the provided time range.

    Notes
    -----
    As the implimenter of the get_events function, you can choose to ignore the from_dt
    and to_dt parameters. However, they are useful for manually kicking off pipelines
    from GitHub Actions UI.
    """
    # Your implementation here
    return []
