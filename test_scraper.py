import sys
import json
from argparse import ArgumentParser
from datetime import (datetime, timedelta)
from functools import partial
from typing import (List, Optional)
from cdp_scrapers import instances
from cdp_scrapers.legistar_utils import LEGISTAR_DATETIME_FORMAT
from cdp_backend.pipeline.ingestion_models import EventIngestionModel


def iso_strptime(dt: str) -> Optional[datetime]:
    try:
        return datetime.strptime(dt, LEGISTAR_DATETIME_FORMAT)
    except (TypeError, ValueError):
        try:
            # try with fractional second
            return datetime.strptime(dt, LEGISTAR_DATETIME_FORMAT + ".%f")
        except (TypeError, ValueError):
            pass

    return None


if __name__ == "__main__":
    argp = ArgumentParser()
    argp.add_argument(
        "municipality_slug",
        help="Municipality slug as defined in your scraper",
    )
    argp.add_argument(
        "--from_dt",
        help=(
            "The timespan beginning ISO-formatted datetime str to query for events "
            "after. Default is 2 days from today."
        ),
    )
    argp.add_argument(
        "--to_dt",
        help=(
            "The timespan end ISO-formatted datetime str to query for events before."
            "Default is today."
        ),
    )
    args = argp.parse_args()

    from_dt = iso_strptime(args.from_dt)
    if not from_dt:
        from_dt = datetime.utcnow() - timedelta(days=2)

    to_dt = iso_strptime(args.to_dt)
    if not to_dt:
        to_dt = datetime.utcnow()

    try:
        # in __init__.py we add get_{slug}_events() as an attribute to the module
        get_events: partial = getattr(instances, f"get_{args.municipality_slug}_events")
    except AttributeError:
        # exit after printing an empty json
        sys.exit("[]")

    ingestions: List[EventIngestionModel] = get_events(from_dt=from_dt, to_dt=to_dt)
    print(
        json.dumps(
            [json.loads(ingestion.to_json()) for ingestion in ingestions],
            indent="    ",
        )
    )
