import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from cdp_backend.database.constants import MatterStatusDecision, VoteDecision
from cdp_backend.pipeline.ingestion_models import (Body, EventIngestionModel,
                                                   EventMinutesItem, Matter,
                                                   MinutesItem, Person,
                                                   Session, SupportingFile,
                                                   Vote)

from ..scraper_utils import IngestionModelScraper, reduced_list, str_simplified

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

    def separate_name_from_title(self, title_and_name: str):
        # title_and_name:
        #   The title (Mayor of Commissioner) and name of a Portland City Commission
        #   member.
        #   e.g., Mayor Ted Wheeler, Commissioner Carmen Rubio

        name_index = title_and_name.index(" ")
        return title_and_name[name_index + 1 :]

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

        # Find document number
        doc_number_element_sibling = event_page.find(
            "div", text=re.compile("Document number"), attrs={"class": "field__label"}
        )

        # If there is no document number, skip this minute item
        if doc_number_element_sibling is None:
            return None
        doc_number_element = doc_number_element_sibling.next_sibling
        doc_number = doc_number_element.find("div", class_="field__item").text.strip()

        # Find title
        title_div = event_page.find("div", class_="council-document__title")
        matter_title = title_div.find("a").text.strip()

        # Find type
        title_div.find("a").clear()
        matter_type = title_div.text.strip()
        if matter_type[0] == "(" and matter_type[-1] == ")":
            matter_type = matter_type[1:-1]

        # Find result status
        result_status_element_sibling = event_page.find(
            "div", text=re.compile("Disposition"), attrs={"class": "field__label"}
        )
        result_status_element = result_status_element_sibling.next_sibling
        result_status = result_status_element.text
        if result_status in ["Accepted", "Passed"]:
            result_status = MatterStatusDecision.ADOPTED
        elif "Passed to" in result_status:
            result_status = MatterStatusDecision.IN_PROGRESS
        else:
            result_status = None

        # Find the sponsors
        sponsor_element_uncle = event_page.find(
            "div", text=re.compile("Introduced by"), attrs={"class": "field__label"}
        )
        sponsor_list = None
        if sponsor_element_uncle is not None:
            sponsor_element_parent = sponsor_element_uncle.next_sibling
            sponsor_elements = sponsor_element_parent.findAll(
                "div", class_="field__item"
            )
            sponsor_list = []
            for sponsor_element in sponsor_elements:
                sponsor = sponsor_element.text.strip()
                sponsor_list.append(
                    self.get_person(self.separate_name_from_title(sponsor))
                )

        return self.get_none_if_empty(
            Matter(
                matter_type=matter_type,
                name=doc_number,
                sponsors=sponsor_list,
                title=matter_title,
                result_status=result_status,
            ),
        )

    def get_supporting_files(
        self, event_page: BeautifulSoup, minutes_item_index: int
    ) -> Optional[List[SupportingFile]]:
        """
        Return SupportingFiles for a given EventMinutesItems

        # Find title
        title_div = event_page.find("div", class_="council-document__title")

        # Find related document
        href = title_div.find("a")["href"]

        return reduced_list(
            [
                self.get_none_if_empty(
                    SupportingFile(name="Details", uri="https://portland.gov" + href)
                )
            ],

        Parameters
        ----------
        event_page: BeautifulSoup
            Event web page e.g. https://www.portland.gov/council/agenda/yyyy/m/d
            loaded in BeautifulSoup

        minutes_item_index: int
            EventMinutesItem index on event_page

        Returns
        -------
        supporting files: Optional[List[SupportingFile]]
            Supporting files listed on the event minutes item's details page
        """
        try:
            # on the event page, event minute item titles are listed
            # in <div> with a particular class attribute.
            # so look for the minute_item_index-th such <div> on the event page
            div = event_page.find_all(
                "div", class_="field--label-hidden council-document__title"
            )[minutes_item_index]
            # <a href="/council/documents/communication/placed-file/295-2021">
            details_url = f'https://www.portland.gov{div.find("a")["href"]}'
        except (IndexError, TypeError):
            # find_all() returned list with size <= minutes_item_index
            # or find("a") did not succeed
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

        vote_element_uncle = event_page.find(
            "div", text=re.compile("Votes"), attrs={"class": "field__label"}
        )
        if vote_element_uncle is None:
            return None
        vote_element_parent = vote_element_uncle.next_sibling
        vote_elements = vote_element_parent.findAll("div", class_="relation--type-")
        vote_list = []
        for vote_element in vote_elements:
            vote = vote_element.text.strip()

            i = vote.rfind(" ")
            decision = vote[i:].strip()
            if decision == "Yea":
                decision = VoteDecision.APPROVE
            elif decision == "Nay":
                decision = VoteDecision.REJECT
            elif decision == "Absent":
                decision = VoteDecision.ABSENT_NON_VOTING
            else:
                decision = None
            name = self.separate_name_from_title(vote[0:i].strip())
            vote_list.append(
                self.get_none_if_empty(
                    Vote(decision=decision, person=self.get_person(name))
                )
            )

        return vote_list

    def get_event_minutes(
        self, event_page: BeautifulSoup
    ) -> Optional[List[EventMinutesItem]]:
        # TODO:
        # decision:
        # Some items listed on agenda page have “Disposition” like “passed”.
        # Have not yet found what they use to mean “failed.”

        # think we will let MinutesItem.name = Matter.name
        #                   MinutesItem.description = Matter.title

        minute_sections = event_page.find_all(
            "div", class_="relation--type-agenda-item"
        )
        event_minute_items = []
        for minute_section in minute_sections:
            title_div = minute_section.find("div", class_="council-document__title")
            matter_title = title_div.find("a").text.strip()
            index = int(minute_section.find("h4").text.strip())
            event_minute_item = EventMinutesItem(
                decision=None,
                index=index,
                matter=self.get_matter(minute_section),
                minutes_item=MinutesItem(name=None, description=matter_title),
                supporting_files=self.get_supporting_files(minute_section, index),
                votes=self.get_votes(minute_section),
            )
            event_minute_items.append(event_minute_item)

        return reduced_list(
            [event_minute_items],
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

    def get_agenda_uri(self, event_page: BeautifulSoup) -> str:
        """
        Find the uri for the file containing the agenda at each Portland, OR city
        council meeting

        Parameters
        ----------
        event_page: The page for the meeting

        Returns
        -------
        agenda_uri: The uri for the file containing the meeting's agenda
        """
        agenda_uri_element = event_page.find(
            "a", text=re.compile("Disposition Agenda"), attrs={"class": "btn-cta"}
        )
        if agenda_uri_element is not None:
            return agenda_uri_element["href"] + "/File/Document"
        parent_agenda_uri_element = event_page.find("div", {"class": "inline-flex"})
        agenda_uri_element = parent_agenda_uri_element.find("a")
        if agenda_uri_element is not None:
            return "https://www.portland.gov" + agenda_uri_element["href"]
        return None

    def get_event(self, event_time: datetime) -> Optional[EventIngestionModel]:
        """
        Information for council meeting on given date if available
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

        # TODO:
        # agenda_uri:
        # 1. URL to *agenda*pdf near the top of agenda page. Or,
        # 2. First, follow URL in “disposition agenda” link button near the top
        #    page (e.g. https://efiles.portlandoregon.gov/record/14654925).
        #    Then get the URL from the “Download” button on that subsequent web page.

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
