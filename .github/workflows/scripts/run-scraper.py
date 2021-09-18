import sys
import json
import logging
import argparse
import traceback
from datetime import (datetime, timedelta)
from functools import partial
from typing import (List, Optional)
from cdp_scrapers import instances


###############################################################################

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)4s: %(module)s:%(lineno)4s %(asctime)s] %(message)s",
)
log = logging.getLogger(__name__)

###############################################################################

PARAMS_FILE = "scraper-params.txt"
RESULTS_FILE = "scraper-results.json"

###############################################################################


def iso_strptime(dt: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(dt)
    except (TypeError, ValueError):
        pass

    return None


class Args(argparse.Namespace):
    def __init__(self, args: Optional[List[str]]) -> None:
        self.__parse(args)

    def __parse(self, args: Optional[List[str]]) -> None:
        p = argparse.ArgumentParser(
            prog="run-scraper",
            description=(
                f"Run events scraper and save results to {RESULTS_FILE}."
            ),
        )
        p.add_argument(
            "get_events_name",
            help="get_{your_municipality_slug}_events",
        )
        p.add_argument(
            "--from_dt",
            help=(
                "The timespan beginning ISO-formatted datetime str to query for events "
                "after. Default is 2 days from today."
            ),
        )
        p.add_argument(
            "--to_dt",
            help=(
                "The timespan end ISO-formatted datetime str to query for events before"
                "Default is today."
            ),
        )
        p.parse_args(namespace=self, args=args)


def save_events(get_events_name: str, from_dt_str: str, to_dt_str: str) -> None:
    from_dt = iso_strptime(from_dt_str)
    if not from_dt:
        from_dt = datetime.utcnow() - timedelta(days=2)

    to_dt = iso_strptime(to_dt_str)
    if not to_dt:
        to_dt = datetime.utcnow()

    get_events: partial = getattr(instances, f"{get_events_name}")

    with open(PARAMS_FILE, "wt") as params_file:
        params_file.write(
            f"--from_dt={from_dt.isoformat()} "
            f"--to_dt={to_dt.isoformat()} "
            f"{get_events_name}\n"
        )
    with open(RESULTS_FILE, "wt") as results_file:
        results_file.write(
            json.dumps(
                [
                    json.loads(ingestion.to_json())
                    for ingestion in get_events(from_dt=from_dt, to_dt=to_dt)
                ],
                indent=4,
            )
        )


def main() -> None:
    try:
        # skip the first arg "/test-scraper" which would be included if called
        # from github issue/pull request comment
        args = Args(" ".join(sys.argv[1:]).replace("/test-scraper", "").split())
        save_events(
            get_events_name=args.get_events_name,
            from_dt_str=args.from_dt,
            to_dt_str=args.to_dt
        )
    except Exception as e:
        log.error("=============================================")
        log.error("\n\n" + traceback.format_exc())
        log.error("=============================================")
        log.error("\n\n" + str(e) + "\n")
        log.error("=============================================")
        sys.exit(1)


###############################################################################
# Allow caller to directly run this module (usually in development scenarios)

if __name__ == "__main__":
    main()
