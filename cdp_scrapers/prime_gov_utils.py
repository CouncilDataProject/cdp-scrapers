from datetime import datetime
from logging import getLogger
from typing import Any, Dict, Iterator, List, NamedTuple, Optional, Set

import requests
from bs4 import BeautifulSoup, Tag
from cdp_backend.pipeline.ingestion_models import (
    Body,
    EventIngestionModel,
    MinutesItem,
    Session,
)
from civic_scraper.platforms.primegov.site import PrimeGovSite

from .scraper_utils import IngestionModelScraper, reduced_list, str_simplified

###############################################################################

log = getLogger(__name__)

###############################################################################

SITE_URL = "https://{client}.primegov.com/"
API_URL = "{base_url}/api/meeting/search?from={begin}&to={end}"

MEETING_DATETIME = "dateTime"
MEETING_DATE = "date"
MEETING_TIME = "time"
MEETING_ID = "id"
BODY_NAME = "title"
VIDEO_URL = "videoUrl"

DATE_FORMAT = "%m/%d/%Y"
TIME_FORMAT = "%I:%M %p"

Meeting = Dict[str, Any]
Agenda = BeautifulSoup


class MinutesItemInfo(NamedTuple):
    name: str
    desc: str


def primegov_strftime(dt: datetime) -> str:
    """
    strftime() in format expected for search by primegov api

    Parameters
    ----------
    dt: datetime
        datetime to convert

    Returns
    -------
    str
        Input datetime in string

    See Also
    --------
    civic_scraper.platforms.primegov.site.PrimeGovSite.scrape()
    """
    return dt.strftime(DATE_FORMAT)


def primegov_strptime(meeting: Meeting) -> Optional[datetime]:
    """
    strptime() on meeting_date_time using expected format commonly used in primegov api

    Parameters
    ----------
    meeting: Meeting
        Target meeting

    Returns
    -------
    Optional[datetime]
        Meeting's date and time
    """
    try:
        return datetime.fromisoformat(meeting[MEETING_DATETIME])
    except ValueError:
        try:
            return datetime.strptime(
                f"{meeting[MEETING_DATE]} {meeting[MEETING_TIME]}",
                f"{DATE_FORMAT} {TIME_FORMAT}",
            )
        except ValueError:
            try:
                return datetime.strptime(
                    meeting[MEETING_DATE],
                    DATE_FORMAT,
                )
            except ValueError:
                pass

    log.debug(
        f"Error parsing '{meeting[MEETING_DATETIME]}', "
        f"'{meeting[MEETING_DATE]}', "
        f"'{meeting[MEETING_TIME]}'"
    )
    return None


def load_agenda(url: str) -> Optional[Agenda]:
    """
    Load the agenda web page.

    Parameters
    ----------
    url: str
        Agenda web page URL

    Returns
    -------
    Optional[Agenda]
        Agenda web page loaded into BeautifulSoup
    """
    resp = requests.get(str_simplified(url))
    if resp.status_code == 200:
        return BeautifulSoup(resp.text, "html.parser")

    log.warning(f"{url} responded {resp.status_code} {resp.reason} {resp.text}")
    return None


def get_minutes_tables(agenda: Agenda) -> Iterator[Tag]:
    """
    Return iterator over tables for minutes items.

    Parameters
    ----------
    agenda: Agenda
        Agenda web page loaded into BeautifulSoup

    Returns
    -------
    Iterator[Tag]
        List of <table> for minutes items
    """
    # look for <div> with certain class then get the <table> inside the <div>
    divs = agenda.find_all("div", class_="agenda-item")
    return map(lambda d: d.find("table"), divs)


def get_minutes_item(minutes_table: Tag) -> MinutesItemInfo:
    """
    Extract minutes item name and description.

    Parameters
    ----------
    minutes_table: Tag
        <table> for a minutes item on agenda web page

    Returns
    -------
    MinutesItemInfo
        Minutes item name and description

    Raises
    ------
    ValueError
        If the <table> HTML structure is not as expected

    See Also
    --------
    get_minutes_tables()
    """
    rows = minutes_table.find_all("tr")

    try:
        # minutes item name in the first row, description in the second row
        name = rows[0].find("td").string
        desc = rows[1].find("div").string
    except (IndexError, AttributeError):
        # rows is empty; find*() returned None
        raise ValueError(
            f"Minutes item <table> is no longer recognized: {minutes_table}"
        )

    return MinutesItemInfo(str_simplified(name), str_simplified(desc))


class PrimeGovScraper(PrimeGovSite, IngestionModelScraper):
    """
    Adapter for civic_scraper PrimeGovSite in cdp-scrapers

    See Also
    --------
    civic_scraper.platforms.primegov.site.PrimeGoveSite
    cdp_screapers.scraper_utils.IngestionModelScraper
    """

    def __init__(
        self,
        client_id: str,
        timezone: str,
        person_aliases: Optional[Dict[str, Set[str]]] = None,
    ):
        """
        Parameters
        ----------
        client_id: str
            primegov api instance id, e.g. lacity for Los Angeles, CA
        timezone: str
            Local time zone
        person_aliases: Optional[Dict[str, Set[str]]] = None
            Dictionary used to catch name aliases
            and resolve improperly different Persons to the one correct Person.
        """
        PrimeGovSite.__init__(self, SITE_URL.format(client=client_id))
        IngestionModelScraper.__init__(
            self, timezone=timezone, person_aliases=person_aliases
        )

        log.debug(
            f"Created PrimeGovScraper "
            f"for primegov_instance: {self.primegov_instance}, "
            f"in timezone: {self.timezone}, "
            f"at url: {self.url}"
        )

    def get_session(self, meeting: Meeting) -> Optional[Session]:
        """
        Extract a Session from a primegov meeting dictionary

        Parameters
        ----------
        meeting: Meeting
            Target meeting

        Returns
        -------
        Optional[Session]
            Session extracted from the meeting
        """
        return self.get_none_if_empty(
            Session(
                session_datetime=primegov_strptime(meeting),
                video_uri=str_simplified(meeting[VIDEO_URL]),
                session_index=0,
            )
        )

    def get_body(self, meeting: Meeting) -> Optional[Body]:
        """
        Extract a Body from a primegov meeting dictionary

        Parameters
        ----------
        meeting: Meeting
            Target meeting

        Returns
        -------
        Optional[Body]
            Body extracted from the meeting
        """
        return self.get_none_if_empty(Body(name=str_simplified(meeting[BODY_NAME])))

    def get_minutes_item(self, minutes_table: Tag) -> Optional[MinutesItem]:
        """
        Extract a minutes item from a <table> on agenda web page

        Parameters
        ----------
        minutes_table: Tag
            <table> tag on agenda web page for a minutes item.

        Returns
        -------
        Optional[MinutesItem]
            MinutesItem from given <table>

        See Also
        --------
        get_minutes_item()
        """
        minutes_info = get_minutes_item(minutes_table)
        return self.get_none_if_empty(
            MinutesItem(name=minutes_info.name, description=minutes_info.desc)
        )

    def get_event(self, meeting: Meeting) -> Optional[EventIngestionModel]:
        """
        Extract a EventIngestionModel from a primegov meeting dictionary

        Parameters
        ----------
        meeting: Meeting
            Target meeting

        Returns
        -------
        Optional[EventIngestionModel]
            EventIngestionModel extracted from the meeting

        See Also
        --------
        get_body()
        get_session()
        """
        return self.get_none_if_empty(
            EventIngestionModel(
                body=self.get_body(meeting),
                sessions=reduced_list([self.get_session(meeting)]),
                external_source_id=str_simplified(str(meeting[MEETING_ID])),
            )
        )

    def get_meetings(
        self,
        begin: datetime,
        end: datetime,
    ) -> Iterator[Meeting]:
        """
        Query meetings from primegov api endpoint

        Parameters
        ----------
        begin: datetime
            The timespan beginning datetime to query for events after.
        end: datetime
            The timespan end datetime to query for events before.

        Returns
        -------
        Optional[Iterator[Meeting]]
            Iterator over list of meeting JSON

        Notes
        -----
        Because of CDP's preference for videos,
        meetings without video URL are filtered out.

        See Also
        --------
        get_events()
        """
        resp = self.session.get(
            API_URL.format(
                base_url=self.base_url,
                begin=primegov_strftime(begin),
                end=primegov_strftime(end),
            )
        )
        return filter(lambda m: any(m[VIDEO_URL]), resp.json())

    def get_events(
        self, begin: Optional[datetime] = None, end: Optional[datetime] = None
    ) -> List[EventIngestionModel]:
        """
        Return list of ingested events for the given time period.

        Parameters
        ----------
        begin: Optional[datetime]
            The timespan beginning datetime to query for events after.
            Default is 2 days from UTC now
        end: Optional[datetime]
            The timespan end datetime to query for events before.
            Default is UTC now

        Returns
        -------
        events: List[EventIngestionModel]
            One instance of EventIngestionModel per primegov api meeting

        See Also
        --------
        get_meetings()
        """
        meetings = self.get_meetings(begin, end)
        return reduced_list(map(self.get_event, meetings), collapse=False)
