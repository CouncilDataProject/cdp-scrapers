import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List, NamedTuple, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup, Tag
from cdp_backend.database.constants import (
    EventMinutesItemDecision,
    MatterStatusDecision,
    VoteDecision,
)
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

from ..scraper_utils import (
    IngestionModelScraper,
    reduced_list,
    str_simplified,
    parse_static_file,
)

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

SCRAPER_STATIC_DATA = parse_static_file(Path(__file__).parent / "portland-static.json")

###############################################################################

MATTER_ADOPTED_PATTERNS = [
    "accepted",
    "passed",
    "adopted",
    "confirmed",
]
MATTER_IN_PROG_PATTERNS = [
    "passed to",
    "placed on",
    "continued",
    "referred",
]

MINUTE_ITEM_PASSED_PATTERNS = [
    # NOTE: these words while have positive conotation,
    # does not mean the legistation was passed.
    # it indicates the item (or a report, etc.) was accepted to be discussed and voted.
    # "accepted",
    # "confirmed",
    # "adopted",
    "passed$",
]

###############################################################################


class WebPageSoup(NamedTuple):
    status: bool
    soup: Optional[BeautifulSoup] = None


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


def make_efile_url(efile_page_url: str) -> str:
    """
    Helper function to get file download link
    on a Portland EFile hosting web page

    Parameters
    ----------
    efile_page_url: str
        URL to Portland efile hosting web page
        e.g. https://efiles.portlandoregon.gov/record/14803529

    Returns
    -------
    efile url: str
        URL to the file itself
        e.g. https://efiles.portlandoregon.gov/record/14803529/File/Document
    """
    if not efile_page_url.endswith("/"):
        efile_page_url += "/"
    return f"{efile_page_url}File/Document"


def get_disposition(minute_section: Tag) -> str:
    """
    Return disposition string given within minute_section <div>
    on the event web page

    Parameters
    ----------
    minute_section: Tag
        <div> within event web page for a given event minute item

    Returns
    -------
    disposition: str
        Disposition string for the event minute item
        e.g. Accepted, Passed, Placed on file
    """
    result_status_element_sibling = minute_section.find(
        "div", text=re.compile("Disposition"), attrs={"class": "field__label"}
    )
    result_status_element = result_status_element_sibling.next_sibling
    return result_status_element.text


def disposition_to_minute_decision(
    disposition: str,
) -> Optional[EventMinutesItemDecision]:
    """
    Decide EventMinutesItemDecision constant from event minute item disposition

    Parameters
    ----------
    disposition: str
        Disposition event web page for a given item
        e.g. Passed, Continued

    Returns
    -------
    decision: Optional[EventMinutesItemDecision]

    See Also
    --------
    MINUTE_ITEM_PASSED_PATTERNS
    """
    for pattern in MINUTE_ITEM_PASSED_PATTERNS:
        if re.search(pattern, disposition, re.I):
            return EventMinutesItemDecision.PASSED
    return None


def separate_name_from_title(title_and_name: str) -> str:
    """
    Return just name

    Parameters
    ----------
    title_and_name: str
        e.g. Mayor Ted Wheeler

    Returns
    -------
    name: str
        tile_name_name with first word removed e.g. Ted Wheeler

    Notes
    -----
    first word in title_and_name is presumed to be title
    """
    # title_and_name:
    #   The title (Mayor of Commissioner) and name of a Portland City Commission
    #   member.
    #   e.g., Mayor Ted Wheeler, Commissioner Carmen Rubio

    name_index = title_and_name.find(" ")
    return title_and_name[name_index + 1 :]


class PortlandScraper(IngestionModelScraper):
    def __init__(self):
        super().__init__(timezone="America/Los_Angeles")

    def get_person(self, name: str) -> Person:
        """
        Return matching Person from portland-static.json

        Parameters
        ----------
        name: str
            Person full name

        Returns
        -------
        person: Person
            Matching Person from portland-static.json

        Raises
        ------
        KeyError
            If name does not exist in portland-static.json

        References
        ----------
        portland-static.json
        """
        if name not in SCRAPER_STATIC_DATA.persons:
            raise KeyError(f"{name} is unknown. Please update portland-static.json")

        return SCRAPER_STATIC_DATA.persons[name]

    def get_doc_number(self, minute_section: Tag, event_page: BeautifulSoup) -> str:
        """
        Find the document number in the minute_section.

        Parameters
        ----------
        minute_section: Tag
            <div> within event web page for a given event minute item
        event_page: BeautifulSoup
            The entire page where the event is found

        Returns
        -------
        doc_number: str
            The document number in the minute_section
            If this is null, return the section top number with the year
        """
        # Find document number
        doc_number_element_sibling = minute_section.find(
            "div", text=re.compile("Document number"), attrs={"class": "field__label"}
        )

        # If there is no document number, skip this minute item
        if doc_number_element_sibling is None:
            return self.get_section_top_number(minute_section, event_page)
        doc_number_element = doc_number_element_sibling.next_sibling
        doc_number = doc_number_element.find("div", class_="field__item").text.strip()
        return doc_number

    def get_section_top_number(
        self, minute_section: Tag, event_page: BeautifulSoup
    ) -> str:
        """
        Find the top section number in the minute_section.

        Parameters
        ----------
        minute_section: Tag
            <div> within event web page for a given event minute item
        event_page: BeautifulSoup
            The entire page where the event is found

        Returns
        -------
        doc_number: str
            The top section number in the minute_section, with the year appended at the
            end
        """
        agenda_name = event_page.find("title").text.strip()
        base_minute_section = minute_section.find("h4").text.strip()
        if agenda_name is not None:
            return (
                base_minute_section
                + "-"
                + agenda_name[agenda_name.index(",") + 2 : agenda_name.index(",") + 6]
            )
        return base_minute_section

    def get_matter(
        self, minute_section: Tag, event_page: BeautifulSoup
    ) -> Optional[Matter]:
        """
        Make Matter from information in minute_section

        Parameters
        ----------
        minute_section: Tag
            <div> within event web page for a given event minute item
        event_page: BeautifulSoup
            The entire page where the event is found

        Returns
        -------
        matter: Optional[Matter]
            Matter if required information could be parsed from minute_section
        """

        # Find title
        title_div = minute_section.find("div", class_="council-document__title")

        matter_type = None
        matter_title = None

        if title_div is not None:
            matter_title = title_div.find("a").text.strip()

            # Find type
            title_div.find("a").clear()
            matter_type = title_div.text.strip()
            if matter_type[0] == "(" and matter_type[-1] == ")":
                matter_type = matter_type[1:-1]
        else:
            matter_title = (
                minute_section.find("div", class_="field--name-field-disposition-notes")
                .children.__next__()
                .text.strip()
            )
            matter_type = matter_title[
                matter_title.rindex("(") + 1 : matter_title.rindex(")")
            ]
            matter_title = matter_title[0 : matter_title.rindex("(") - 1]

        # Find result status
        result_status = get_disposition(minute_section)
        # strings like "passed to second reading" is better to catch
        # before searching for "passed".
        # so test for IN_PROGRESS first.
        for pattern in MATTER_IN_PROG_PATTERNS:
            if re.search(pattern, result_status, re.I):
                result_status = MatterStatusDecision.IN_PROGRESS
                break
        else:
            for pattern in MATTER_ADOPTED_PATTERNS:
                if re.search(pattern, result_status, re.I):
                    result_status = MatterStatusDecision.ADOPTED
                    break
            else:
                result_status = None

        # Find the sponsors
        sponsor_element_uncle = minute_section.find(
            "div", text=re.compile("Introduced by"), attrs={"class": "field__label"}
        )
        sponsor_list = None
        if sponsor_element_uncle is not None:
            sponsor_element_parent = sponsor_element_uncle.next_sibling
            sponsor_elements = sponsor_element_parent.find_all(
                "div", class_="field__item"
            )
            sponsor_list = reduced_list(
                [
                    self.get_person(
                        separate_name_from_title(sponsor_element.text.strip())
                    )
                    for sponsor_element in sponsor_elements
                ]
            )

        return self.get_none_if_empty(
            Matter(
                matter_type=matter_type,
                name=self.get_doc_number(minute_section, event_page),
                sponsors=sponsor_list,
                title=matter_title,
                result_status=result_status,
            ),
        )

    def get_supporting_files(
        self, minute_section: Tag
    ) -> Optional[List[SupportingFile]]:
        """
        Return SupportingFiles for a given EventMinutesItem

        Parameters
        ----------
        minute_section: Tag
            <div> within event web page for a given event minute item

        Returns
        -------
        supporting files: Optional[List[SupportingFile]]

        Notes
        -----
        Follow hyperlink to go to minutes item details page.
        On the details page look for directly-linked files
        and externally-hosted efiles.

        See Also
        --------
        make_efile_url()
        """
        try:
            # on the event page, event minute item titles are listed
            # in <div> with a particular class attribute.
            # so look for the minute_item_index-th such <div> on the event page
            div = minute_section.find(
                "div", class_="field--label-hidden council-document__title"
            )
            # <a href="/council/documents/communication/placed-file/295-2021">
            details_url = f'https://www.portland.gov{div.find("a")["href"]}'
        except (AttributeError, TypeError):
            # minute_section.find() or div.find() failed
            return None

        # load the mintues item details page that may have links to supporting files
        details_soup = load_web_page(details_url)
        if not details_soup.status:
            return None

        supporting_files: List[SupportingFile] = []
        # first, try to get Documents and Exhibits and Impact Statement
        # these will contain links to files
        for div in details_soup.soup.find_all(
            "div",
            class_=re.compile(
                "field field--label-above field--name-field-"
                "((documents-and-exhibits)|(file-impact-statement)) field--type-file"
            ),
        ):
            supporting_files.extend(
                [
                    self.get_none_if_empty(
                        SupportingFile(
                            name=str_simplified(
                                re.sub(
                                    r"\s*download\s+file\s*",
                                    "",
                                    link.text,
                                    flags=re.IGNORECASE,
                                )
                            ),
                            uri=f'https://www.portland.gov{link["href"]}',
                        )
                    )
                    # <a href="/sites/...pdf"><span>Download file</span>
                    # <i class="fas fa-file-alt"></i>Exhibit A</a>
                    for link in div.find_all("a")
                ]
            )

        # finally parse for efile links
        # these are hosted yet on another web page; always start with https://efiles
        supporting_files.extend(
            [
                self.get_none_if_empty(
                    SupportingFile(
                        name=str_simplified(link.string),
                        uri=make_efile_url(link["href"]),
                    )
                )
                for link in details_soup.soup.find_all(
                    "a", href=re.compile(r"https:\/\/efiles.+")
                )
            ]
        )

        # remove any Nones
        return reduced_list(supporting_files)

    def get_votes(self, minute_section: Tag) -> Optional[List[Vote]]:
        """
        Look for 'Votes:' in minute_section and
        create a Vote object for each line

        Parameters
        ----------
        minute_section: Tag
            <div> within event web page for a given event minute item

        Returns
        -------
        votes: Optional[List[Vote]]
            Votes for corresponding event minute item if found
        """
        vote_element_uncle = minute_section.find(
            "div", text=re.compile("Votes"), attrs={"class": "field__label"}
        )
        if vote_element_uncle is None:
            return None
        vote_element_parent = vote_element_uncle.next_sibling
        vote_elements = vote_element_parent.find_all("div", class_="relation--type-")
        vote_list = []
        for vote_element in vote_elements:
            vote = vote_element.text.strip()
            # at this point vote string is like
            # Commissioner Jo Ann Hardesty Absent
            # Commissioner Mingus Mapps Yea
            is_absent = "absent" in vote.lower()
            vote = re.sub("absent", "", vote, flags=re.I)

            if "yea" in vote.lower():
                vote = re.sub("yea", "", vote, flags=re.I)
                decision = VoteDecision.APPROVE
                if is_absent:
                    decision = VoteDecision.ABSENT_APPROVE
            elif "nay" in vote.lower():
                vote = re.sub("nay", "", vote, flags=re.I)
                decision = VoteDecision.REJECT
                if is_absent:
                    decision = VoteDecision.ABSENT_REJECT
            elif is_absent:
                decision = VoteDecision.ABSENT_NON_VOTING
            else:
                decision = None

            # at this point any decision token like yea has been removed from vote
            name = separate_name_from_title(vote.strip())
            vote_list.append(
                self.get_none_if_empty(
                    Vote(decision=decision, person=self.get_person(name))
                )
            )

        return reduced_list(vote_list)

    def get_event_minutes(
        self, event_page: BeautifulSoup
    ) -> Optional[List[EventMinutesItem]]:
        """
        Make EventMinutesItem from each relation--type-agenda-item <div>
        on event_page

        Parameters
        ----------
        event_page: BeautifulSoup
            Web page for the meeting loaded as a bs4 object

        Returns
        -------
        event minute items: Optional[List[EventMinutesItem]]
        """
        minute_sections = event_page.find_all(
            "div", class_="relation--type-agenda-item"
        )
        event_minute_items = []
        for minute_section in minute_sections:
            matter = self.get_matter(minute_section, event_page)
            if matter is not None:
                minute_name = self.get_doc_number(minute_section, event_page)
                if minute_name is None:
                    minute_name = self.get_doc_number(minute_section, event_page)
                minutes_item = self.get_none_if_empty(
                    MinutesItem(name=minute_name, description=matter.title)
                )
            else:
                minutes_item = None

            event_minute_items.append(
                self.get_none_if_empty(
                    EventMinutesItem(
                        decision=disposition_to_minute_decision(
                            get_disposition(minute_section)
                        ),
                        matter=matter,
                        minutes_item=minutes_item,
                        supporting_files=self.get_supporting_files(minute_section),
                        votes=self.get_votes(minute_section),
                    )
                )
            )

        return reduced_list(event_minute_items)

    def get_sessions(self, event_page: BeautifulSoup) -> Optional[List[Session]]:
        """
        Parse meeting video URIs from event_page,
        return Session for each video found.

        Parameters
        ----------
        event_page: BeautifulSoup
            Web page for the meeting loaded as a bs4 object

        Returns
        -------
        sessions: Optional[List[Session]]
            Session for each video found on event_page
        """
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
                            video_uri=video_iframe["src"].split("?")[0],
                        )
                    )
                )

            session_index += 1

        return reduced_list(sessions)

    def get_agenda_uri(self, event_page: BeautifulSoup) -> Optional[str]:
        """
        Find the uri for the file containing the agenda for a Portland, OR city
        council meeting

        Parameters
        ----------
        event_page: BeautifulSoup
            Web page for the meeting loaded as a bs4 object

        Returns
        -------
        agenda_uri: Optional[str]
            The uri for the file containing the meeting's agenda
        """
        agenda_uri_element = event_page.find(
            "a", text=re.compile("Disposition Agenda"), attrs={"class": "btn-cta"}
        )
        if agenda_uri_element is not None:
            return make_efile_url(agenda_uri_element["href"])
        parent_agenda_uri_element = event_page.find("div", {"class": "inline-flex"})
        if parent_agenda_uri_element is not None:
            agenda_uri_element = parent_agenda_uri_element.find("a")
        else:
            return None
        if agenda_uri_element is not None:
            return f"https://www.portland.gov{agenda_uri_element['href']}"
        return None

    def get_event(self, event_time: datetime) -> Optional[EventIngestionModel]:
        """
        Portland, OR city council meeting information for a specific date

        Parameters
        ----------
        event_time: datetime
            Meeting date

        Returns
        -------
        Optional[EventIngestionModel]
            None if there was no meeting on event_time
            or information for the meeting did not meet minimal CDP requirements.
        """
        # try to load https://www.portland.gov/council/agenda/yyyy/m/d
        event_page = load_web_page(
            "https://www.portland.gov/council/agenda/"
            # we actually DON'T want to use strftime() because we must not zero-pad
            # e.g. for 2022/01/05, we MUST use 2022/1/5
            f"{event_time.year}/{event_time.month}/{event_time.day}"
        )
        if not event_page.status:
            # no meeting on requested day
            return None

        return self.get_none_if_empty(
            EventIngestionModel(
                agenda_uri=self.get_agenda_uri(event_page.soup),
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


def get_portland_events(
    from_dt: Optional[datetime] = None,
    to_dt: Optional[datetime] = None,
    **kwargs: Any,
) -> List[EventIngestionModel]:
    """
    Public API for use in instances.__init__ so that this func can be attached
    as an attribute to cdp_scrapers.instances module.
    Thus the outside world like cdp-backend can get at this by asking for
    "get_portland_events".

    Parameters
    ----------
    from_dt: datetime, optional
        The timespan beginning datetime to query for events after.
        Default is 2 days from UTC now
    to_dt: datetime, optional
        The timespan end datetime to query for events before.
        Default is UTC now

    Returns
    -------
    events: List[EventIngestionModel]

    See Also
    --------
    cdp_scrapers.instances.__init__.py
    """
    scraper = PortlandScraper()
    return scraper.get_events(begin=from_dt, end=to_dt, **kwargs)
