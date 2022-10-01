from datetime import datetime
from logging import getLogger
from pathlib import Path
import re
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup, Tag
from cdp_backend.database.constants import MatterStatusDecision
from cdp_backend.pipeline.ingestion_models import (
    Body,
    EventIngestionModel,
    Matter,
    MinutesItem,
    Session,
    SupportingFile,
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


def get_minutes_item(minutes_table: Tag) -> MinutesItem:
    """
    Extract minutes item name and description.

    Parameters
    ----------
    minutes_table: Tag
        <table> for a minutes item on agenda web page

    Returns
    -------
    MinutesItem
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

    return MinutesItem(name=str_simplified(name), description=str_simplified(desc))


def get_support_files_div(minutes_table: Tag) -> Tag:
    """
    Find the <div> containing a minutes item's support document URLs

    Parameters
    ----------
    minutes_table: Tag
        <table> for a minutes item on agenda web page

    Returns
    -------
    Tag
        <div> with support documents for the minutes item
    """
    # go up from the <table> for this minutes item
    # then find the next <div> that contains the associated support files.
    return minutes_table.parent.find_next_sibling("div", class_="item_contents")


def get_support_files(minutes_table: Tag) -> Iterator[SupportingFile]:
    """
    Extract the minutes item's support file URLs

    Parameters
    ----------
    minutes_table: Tag
        <table> for a minutes item on agenda web page

    Returns
    -------
    Iterator[SupportingFile]
        List of support file information for the input minutes item

    Raises
    ------
    ValueError
        If the <table> HTML structure is not as expected

    See Also
    --------
    get_minutes_tables()
    """

    def extract_file(file_div: Tag) -> SupportingFile:
        try:
            # the second <a> tag in each file <div> has the file url.
            url_tag = file_div.find_all("a")[1]
        except IndexError:
            # if here, we found <div> with correct class
            # so if we didn't find expected <a>, probably means HTML changed
            raise ValueError(f"Support file <div> is no longer recognized: {file_div}")

        # they sometimes include file suffix in the document title
        # e.g. Budget Recommendation dated 5-18-22.pdf
        # get rid of the suffix .pdf from the descriptive name for the file
        name = re.sub(r"\.\S{2,4}\s*$", "", url_tag.text)

        url: str = url_tag["href"]
        # don't need all the query after the file suffix
        # e.g. ...pdf?name=...
        url = url[: url.find("?")]

        # use as id if file name is just a number
        id = Path(url).stem
        if re.match(r"\d+", id) is None:
            id = None

        return SupportingFile(
            external_source_id=id, name=str_simplified(name), uri=str_simplified(url)
        )

    contents_div = get_support_files_div(minutes_table)
    file_divs = contents_div.find_all("div", class_="attachment-holder")
    return map(extract_file, file_divs)


def get_matter(
    minutes_table: Tag, minutes_item: Optional[MinutesItem] = None
) -> Optional[Matter]:
    """
    Extract matter info from a minutes item <table>

    Parameters
    ----------
    minutes_table: Tag
        <table> for a minutes item on agenda web page
    minutes_item: Optional[MinutesItem] = None
        Associated minutes item that will be used to fill in some info.
        e.g. matter title is taken from it if available.

    Returns
    -------
    Matter
        A Matter instance associated with a minutes item.

    Notes
    -----
    Only basic string clean-up is applied, e.g. simplify whitespace.
    Caller is expect to clean up the data as appropriate.

    See Also
    --------
    get_minutes_tables()
    """
    # ex 1. APPROVED Information Technology Agency report dated July 26, 2022
    #       - (3) Yes; (0) No
    # ex 2. APPROVED Motion (Buscaino - Lee) - (3) Yes; (0) No

    def _get_matter_text(minutes_table: Tag) -> Optional[str]:
        """
        Matter text blob from minutes item <table>
        """
        this_div = minutes_table.parent
        matter_div = this_div.next_sibling
        files_div = get_support_files_div(minutes_table)

        # If there is a <div> between current <table>
        # and the <div> with the support documents,
        # that <div> will contain matter information
        if matter_div == files_div:
            return None
        return str_simplified(matter_div.text)

    def _extract_status(text: str) -> Tuple[str, Optional[str]]:
        """
        (matter text blob, result status)
        """
        uppercase_word = re.search(r"^\s*([A-Z]+)", text)
        if uppercase_word is None:
            return text, None

        result_status = uppercase_word.group(1)
        return str_simplified(text[uppercase_word.end() :]), str_simplified(
            result_status
        )

    def _get_name(text: str) -> str:
        """
        Keep just the name in the matter text blob
        """
        name_end = text.rfind(" dated")
        if name_end < 0:
            name_end = text.rfind(" - (")

        if name_end < 0:
            return text
        return str_simplified(text[:name_end])

    def _get_type(matter_name: str) -> Optional[str]:
        """
        Last word seems to be appropriate to use as type
        e.g. report, motion
        """
        type_end = matter_name.rfind("(")
        if type_end < 0:
            type_end = None

        type_start = matter_name.rfind(" ", None, type_end)
        if type_start < 0:
            return None
        return str_simplified(matter_name[type_start:type_end])

    matter_text = _get_matter_text(minutes_table)
    if matter_text is None:
        return None

    matter_text, result_status = _extract_status(matter_text)
    matter_name = _get_name(matter_text)
    matter_type = _get_type(matter_name)
    matter_title = matter_text if minutes_item is None else minutes_item.description

    return Matter(
        matter_type=matter_type,
        name=matter_name,
        result_status=result_status,
        title=matter_title,
    )


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
        matter_adopted_pattern: str = (
            r"approved|confirmed|passed|adopted|consent|(?:voted.*com+it+ee)"
        ),
        matter_in_progress_pattern: str = r"heard|read|filed|held|(?:in.*com+it+ee)",
        matter_rejected_pattern: str = r"rejected|dropped",
        person_aliases: Optional[Dict[str, Set[str]]] = None,
    ):
        """
        Parameters
        ----------
        client_id: str
            primegov api instance id, e.g. lacity for Los Angeles, CA
        timezone: str
            Local time zone
        matter_adopted_pattern: str
            Regex pattern used to convert matter was adopted to CDP constant value.
            Default: "approved|confirmed|passed|adopted"
        matter_in_progess_pattern: str
            Regex pattern used to convert matter is in-progress to CDP constant value.
            Default: "heard|ready|filed|held|(?:in\\s*committee)"
        matter_rejected_pattern: str
            Regex pattern used to convert matter was rejected to CDP constant value.
            Default: "rejected|dropped"
        person_aliases: Optional[Dict[str, Set[str]]] = None
            Dictionary used to catch name aliases
            and resolve improperly different Persons to the one correct Person.
        """
        PrimeGovSite.__init__(self, SITE_URL.format(client=client_id))
        IngestionModelScraper.__init__(
            self, timezone=timezone, person_aliases=person_aliases
        )

        self.matter_adopted_pattern = matter_adopted_pattern
        self.matter_in_progress_pattern = matter_in_progress_pattern
        self.matter_rejected_patten = matter_rejected_pattern

        # {"pattern_for_adopted": ADOPTED, ...}
        self.matter_status_pattern_map: Dict[str, MatterStatusDecision] = dict(
            zip(
                [
                    self.matter_adopted_pattern,
                    self.matter_in_progress_pattern,
                    self.matter_rejected_patten,
                ],
                [
                    MatterStatusDecision.ADOPTED,
                    MatterStatusDecision.IN_PROGRESS,
                    MatterStatusDecision.REJECTED,
                ],
            )
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
        return self.get_none_if_empty(get_minutes_item(minutes_table))

    def get_matter(
        self, minutes_table: Tag, minutes_item: Optional[MinutesItem] = None
    ) -> Optional[Matter]:
        """
        Extract matter info from a minutes item <table> on agenda web page

        Parameters
        ----------
        minutes_table: Tag
            <table> tag on agenda web page for a minutes item.
        minutes_item: Optional[MinutesItem] = None
            Associated minutes item that will be used to fill in some info.

        Returns
        -------
        Matter
            A Matter instance associated with a minutes item.

        Notes
        -----
        self.matter_status_pattern_map is used to standardize result_status
        to one of the CDP ingetion model constants.

        See Also
        --------
        matter_status_pattern_map
        get_matter()
        """

        def _standardize_type(matter: Matter) -> Matter:
            if matter.matter_type is not None:
                # First letter uppercased
                matter.matter_type = re.sub(
                    r"^\s*([a-z])", lambda m: m.group(1).upper(), matter.matter_type
                )
            return matter

        def _standarize_status(matter: Matter) -> Matter:
            for pattern, status in self.matter_status_pattern_map.items():
                match = re.search(pattern, matter.result_status, re.I)
                if match is not None:
                    matter.result_status = status
                    break
            return matter

        matter = get_matter(minutes_table, minutes_item)
        if matter is None:
            return None

        matter = _standardize_type(matter)
        matter = _standarize_status(matter)
        return self.get_none_if_empty(matter)

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
