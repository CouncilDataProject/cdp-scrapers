import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import re
from typing import Dict, List, NamedTuple, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from cdp_backend.pipeline.ingestion_models import (
    Body,
    EventIngestionModel,
    EventMinutesItem,
    Matter,
    MinutesItem,
    Person,
    Session,
    SupportingFile,
    Vote,
)
from ..scraper_utils import IngestionModelScraper, reduced_list

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

STATIC_FILE_KEY_PERSONS = "persons"
STATIC_FILE_DEFAULT_PATH = Path(__file__).parent / "portland-static.json"

known_persons: Dict[str, Person] = {}

# load long-term static data at file load-time
if Path(STATIC_FILE_DEFAULT_PATH).exists():
    with open(STATIC_FILE_DEFAULT_PATH, "rb") as json_file:
        static_data = json.load(json_file)

    for name, person in static_data[STATIC_FILE_KEY_PERSONS].items():
        known_persons[name] = Person.from_dict(person)


if len(known_persons) > 0:
    log.debug(f"loaded static data for {', '.join(known_persons.keys())}")

###############################################################################


class WebPageSoup(NamedTuple):
    status: bool
    soup: Optional[BeautifulSoup]


def load_web_page(url: Union[str, Request]) -> WebPageSoup:
    """
    Load web page at url and return content soupified

    Parameters
    ----------
    url: str | urllib.request.Request
        Web page to load

    Returns
    -------
    result: WebPageSoup
        WebPageSoup.status = False if web page at url could not be loaded

    """
    try:
        with urlopen(url) as resp:
            return WebPageSoup(True, BeautifulSoup(resp.read(), "html.parser"))
    except URLError or HTTPError as e:
        log.error(f"Failed to open {url}: {str(e)}")

    return WebPageSoup(False)


class PortlandScraper(IngestionModelScraper):
    def __init__(self):
        super().__init__(timezone="America/Los_Angeles")

    def get_person(self, name: str) -> Optional[Person]:
        global known_persons
        try:
            return known_persons[name]
        except KeyError:
            pass

        # TODO: If here means we have incomplete portland-static.json.
        #       Get information from the bottom of
        #       https://www.portland.gov/council-clerk/engage.
        #       Should add to known_persons so we don't query this same person again.
        return None

    def get_matter(self, event_page: BeautifulSoup) -> Optional[Matter]:
        # TODO:
        # matter_type:
        #   Each item listed on agenda page begins with a descriptive phrase,
        #   and at the end of this description its type is listed within parentheses.
        #   e.g. “Request of the … (Communication)” -> matter_type = “communication”
        # name:
        #   1. “Document number” if listed. Or, if not listed
        #   2. Type + item number? e.g. “Ordinance 862”
        # result_status:
        #   From same information as for EventMinutesItem.decision, i.e. “Disposition”.
        #   e.g. “Passed to second reading” -> IN_PROGRESS
        # sponsors:
        #   Some items listed on agenda page has “Introduced by” field with name.
        # title:
        #   The first description phrase in each item on agenda page.
        #   This is usually hyperlinked to another page with more details.

        return self.get_none_if_empty(
            Matter(matter_type=None, name=None, sponsors=None, title=None),
        )

    def get_supporting_files(
        self, event_page: BeautifulSoup
    ) -> Optional[List[SupportingFile]]:
        # TODO:
        # When we follow the link for any item on agenda page,
        # there are various documents under “Documents and Exhibits,”
        # “Impact Statement,” and others.
        # May be simpler to just get all linked pdf files on those web pages.

        return reduced_list(
            [self.get_none_if_empty(SupportingFile(name=None, uri=None))],
        )

    def get_votes(self, event_page: BeautifulSoup) -> Optional[List[Vote]]:
        # TODO:
        # Voting results are listed on agenda page for some items, like
        # Votes: Commissioner Mingus Mapps Yea
        #        Commissioner Carmen Rubio Yea
        #        Commissioner Dan Ryan Yea
        #        Commissioner Jo Ann Hardesty Yea
        #        Mayor Ted Wheeler Yea.
        # Have only seen “Yea”. We have several constants for Vote.decision.
        # Clearly “Yea” -> VoteDecision.APPROVE, but we don’t have enough information
        # for what words to map to other constants.

        return reduced_list(
            [
                self.get_none_if_empty(
                    Vote(decision=None, person=self.get_person(None))
                ),
            ],
        )

    def get_event_minutes(
        self, event_page: BeautifulSoup
    ) -> Optional[List[EventMinutesItem]]:
        # TODO:
        # decision:
        # Some items listed on agenda page have “Disposition” like “passed”.
        # Have not yet found what they use to mean “failed.”

        # think we will let MinutesItem.name = Matter.name
        #                   MinutesItem.description = Matter.title
        return reduced_list(
            [
                self.get_none_if_empty(
                    EventMinutesItem(
                        decision=None,
                        index=0,
                        matter=self.get_matter(event_page),
                        minutes_item=MinutesItem(name=None, description=None),
                        supporting_files=self.get_supporting_files(event_page),
                        votes=self.get_votes(event_page),
                    ),
                ),
            ],
        )

    def get_sessions(self, event_page: BeautifulSoup) -> Optional[List[Session]]:
        # each session's meta data is given in <div class="session-meta">
        # including youtube video url for the session, if available
        # <div class="session-meta">
        # ...
        # <time class="datetime">Wednesday, December 15, 2021 9:30 am</time>
        # ...
        # <iframe src="https://www.youtube.com/...">

        sessions: List[Session] = []
        session_index = 0

        for session_div in event_page.find_all("div", class_="session-meta"):
            session_time = session_div.find("time", class_="datetime")
            # plenty of sessions have no video listed so must check.
            # recall we require video_uri for a valid Session.
            video_iframe = session_div.find("iframe", src=re.compile(".*youtube.*"))
            if session_time and video_iframe:

                sessions.append(
                    self.get_none_if_empty(
                        Session(
                            session_datetime=self.localize_datetime(
                                datetime.strptime(
                                    session_time.string,
                                    "%A, %B %d, %Y %I:%M %p",
                                )
                            ),
                            session_index=session_index,
                            video_uri=video_iframe["src"],
                        )
                    )
                )

            session_index += 1

        return reduced_list(sessions)

    def get_event(self, event_time: datetime) -> Optional[EventIngestionModel]:
        """
        Information for council meeting on given date if available
        """
        # try to load https://www.portland.gov/council/agenda/yyyy/mm/dd
        event_page = load_web_page(
            f"https://www.portland.gov/council/agenda/{event_time.strftime('%Y/%m/%d')}"
        )
        if not event_page.status:
            # no meeting on requested day
            return None

        # TODO:
        # agenda_uri:
        # 1. URL to *agenda*pdf near the top of agenda page. Or,
        # 2. First, follow URL in “disposition agenda” link button near the top
        #    page (e.g. https://efiles.portlandoregon.gov/record/14654925).
        #    Then get the URL from the “Download” button on that subsequent web page.

        return self.get_none_if_empty(
            EventIngestionModel(
                agenda_uri=None,
                # NOTE: have not seen any specific body/bureau named on any agenda page
                body=Body(name="City Council"),
                event_minutes_items=self.get_event_minutes(event_page.soup),
                minutes_uri=None,
                sessions=self.get_sessions(event_page.soup),
            ),
        )

    def get_events(
        self,
        begin: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[EventIngestionModel]:
        """
        Portland, OR city council meeting information over given time span
        as List[EventIngestionModel]

        Parameters
        ----------
        begin: datetime, optional
            The timespan beginning datetime to query for events after.
            Default is 2 days from UTC now
        end: datetime, optional
            The timespan end datetime to query for events before.
            Default is UTC now

        Returns
        -------
        events: List[EventIngestionModel]

        References
        ----------
        https://www.portland.gov/council/agenda/all
        """
        if begin is None:
            begin = datetime.utcnow() - timedelta(days=2)
        if end is None:
            end = datetime.utcnow()

        return reduced_list(
            [
                self.get_event(begin + timedelta(days=day))
                for day in range((end - begin).days)
            ],
            # prefer to return [] over None to backend pipeline
            # for easier iterate there
            collapse=False,
        )
