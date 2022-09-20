import re
from datetime import datetime
from logging import getLogger
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup, Tag
from cdp_backend.database.constants import RoleTitle
from cdp_backend.pipeline.ingestion_models import (
    Body,
    EventIngestionModel,
    Person,
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

MEMBERS_TBL_KEYWORD = "MEMBERS:"

Meeting = Dict[str, Any]
PersonName = str
Agenda = BeautifulSoup

default_role_map: Dict[str, RoleTitle] = {
    "CHAIR": RoleTitle.CHAIR,
    "COUNCILMEMBER": RoleTitle.COUNCILMEMBER,
}


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

    log.warning(f"{url} responed {resp.status_code} {resp.reason} {resp.text}")
    return None


def get_members_table(agenda: Agenda) -> Optional[Tag]:
    """
    Get the <table> on the agenda web page that contains councilmember names.

    Parameters
    ----------
    agenda: Agenda
        Agenda web page loaded into BeautifulSoup

    Returns
    -------
    Optional[Tag]
        <table> for councilmember names
    """

    def _contains_members_row(tag: Tag) -> bool:
        return tag.find("span", string=MEMBERS_TBL_KEYWORD) is not None

    def _is_members_table(table: Tag) -> bool:
        return (
            table.name == "table"
            and _contains_members_row(table)
            and any(table.find_all("tr"))
        )

    return agenda.find(_is_members_table)


def get_member_names(agenda: Agenda) -> List[PersonName]:
    """
    Get names of councilmembers listed on the agenda.

    Parameters
    ----------
    agenda: Agenda
        Agenda web page loaded into BeautifulSoup

    Returns
    -------
    List[PersonName]
        Names of councilmembers on the agenda.
    """
    table = get_members_table(agenda)
    if not table:
        return list()

    def _get_name(row: Tag) -> PersonName:
        # Last column in the members table has the name
        return row.find_all("td")[-1].string

    return reduced_list(map(_get_name, table.find_all("tr")), collapse=False)


def split_name_role(
    name_text: PersonName, role_map: Dict[str, RoleTitle]
) -> Tuple[PersonName, RoleTitle]:
    """
    Split councilmember name text blob into name and role title.

    Parameters
    ----------
    name_text: PersonName
        Name as listed on agenda web page
    role_map: Dict[str, RoleTitle]
        Map titles on agenda to CDP std role titles

    Returns
    -------
    PersonName, RoleTitle
        The person's name and std role title

    See Also
    --------
    cdp_backend.database.constants.RoleTitle
    """

    def _pop_lead_title() -> Tuple[PersonName, Optional[RoleTitle]]:
        """
        Pop any role title in the beginning of name blob
        """
        for match, std_title in map(
            lambda title: (
                re.search(f"^\\s*{title[0]}", name_text, re.I),
                title[1],
            ),
            role_map.items(),
        ):
            if match is not None:
                # Remove title from name blob
                return name_text[match.end() :], std_title
        return name_text, None

    def _pop_trail_title() -> Tuple[PersonName, Optional[RoleTitle]]:
        """
        Pop any role title at the end of name blob
        """
        for match, std_title in map(
            lambda title: (
                re.search(f",\\s*{title[0]}\\s*$", name_text, re.I),
                title[1],
            ),
            role_map.items(),
        ):
            if match is not None:
                # Remove title from name blob
                return name_text[: match.start()], std_title
        return name_text, None

    name_text, lead_title = _pop_lead_title()
    name_text, trail_title = _pop_trail_title()
    # trailing title is more "important"; they are titles like chair.
    # leading title is usually councilmember.
    title = trail_title or lead_title
    title = title or RoleTitle.MEMBER

    return str_simplified(name_text), title


def get_minutes_tables(agenda: Agenda) -> List[Tag]:
    def _is_minutes_item(tag):
        return tag.name == "table" and tag.find_parent("div", class_="agenda-item") is not None
    return agenda.find_all(_is_minutes_item)


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
        role_map: Dict[str, RoleTitle] = None,
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
        role_map: Dict[str, RoleTitle] = None
            Dictionary used to replace role titles with CDP standard role titles.
            The keys should be titles you want to replace and the values should be a
            CDP standard role.
        """
        PrimeGovSite.__init__(self, SITE_URL.format(client=client_id))
        IngestionModelScraper.__init__(
            self, timezone=timezone, person_aliases=person_aliases
        )
        self.role_map = role_map or default_role_map

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

    def get_person(self, name_text: PersonName) -> Optional[Person]:
        """
        Convert a councilmember name text blob from an agenda page
        to a Person instance

        Parameters
        ----------
        name_text: PersonName
            Name as listed on agenda web page

        Returns
        -------
        Optional[Person]
            Person from given name text blob

        Notes
        -----
        For now role title in the text blob is ignored.

        See Also
        --------
        split_name_role()
        """
        name, _ = split_name_role(name_text, self.role_map)
        return self.get_none_if_empty(self.resolve_person_alias(Person(name=name)))

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
    ) -> Iterable[Meeting]:
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
        Optional[Iterable[Meeting]]
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
