#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import json
from typing import Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from pathlib import Path

from bs4 import BeautifulSoup

from cdp_backend.pipeline.ingestion_models import Person, Seat
from ..legistar_utils import (
    LEGISTAR_EV_SITE_URL,
    LegistarScraper,
)
from ..scraper_utils import str_simplified
from ..types import ContentURIs

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

STATIC_FILE_KEY_PERSONS = "persons"
STATIC_FILE_DEFAULT_PATH = Path(__file__).parent / "kingcounty-static.json"

# will be passed into LegistarScraper.__init__()
# to inject data into Persons to fill in information missing in Legistar API
known_persons: Optional[Dict[str, Person]] = None

# load long-term static data at file load-time, if file exists
if Path(STATIC_FILE_DEFAULT_PATH).exists():
    with open(STATIC_FILE_DEFAULT_PATH, "rb") as json_file:
        static_data = json.load(json_file)

    known_persons = {}
    for name, person in static_data[STATIC_FILE_KEY_PERSONS].items():
        known_persons[name] = Person.from_dict(person)


if known_persons:
    log.debug(f"loaded static data for {', '.join(known_persons.keys())}")

###############################################################################


class KingCountyScraper(LegistarScraper):
    PYTHON_MUNICIPALITY_SLUG: str = "king_county"

    def __init__(self):
        """
        King County specific implementation of LegistarScraper.
        """
        super().__init__(
            client="kingcounty",
            timezone="America/Los_Angeles",
            ignore_minutes_item_patterns=[
                "This meeting also constitutes a meeting of the City Council",
                "In-person attendance is currently prohibited",
                "Times listed are estimated",
                "has been cancelled",
                "Deputy City Clerk",
                "Paste the following link into the address bar of your web browser",
                "HOW TO WATCH",
                "page break",
                "PUBLIC NOTICE",
                "There will be one public hearing on",
                "Consent Items",
                "SUBJECT TO A MOTION TO SUSPEND THE RULES TO TAKE ACTION WITHOUT REFERRAL TO COMMITTEE PURSUANT",  # noqa: E501
                "If you do not have access to the ZOOM application",
                "Executive Session: For 15 minutes, with action to follow",
                "on the agenda for procedural matters",
                "This is a mandatory referral to the",
                "Watch King County TV Channel 22",
            ],
            known_persons=known_persons,
        )

    def get_content_uris(self, legistar_ev: Dict) -> List[ContentURIs]:
        """
        Return URLs for videos and captions parsed from kingcounty.gov web page

        Parameters
        ----------
        legistar_ev: Dict
            Data for one Legistar Event.

        Returns
        -------
        content_uris: List[ContentURIs]
            List of ContentURIs objects for each session found.

        See Also
        --------
        cdp_scrapers.legistar_utils.get_legistar_events_for_timespan
        """
        try:
            # a td tag with a certain id pattern containing url to video

            with urlopen(legistar_ev[LEGISTAR_EV_SITE_URL]) as resp:
                soup = BeautifulSoup(resp.read(), "html.parser")

        except URLError or HTTPError:
            log.debug(f"Failed to open {legistar_ev[LEGISTAR_EV_SITE_URL]}")
            return []

        try:
            # this gets us the url for the web PAGE containing the video
            # video link is provided in the window.open()command inside onclick event
            # <a id="ctl00_ContentPlaceHolder1_hypVideo"
            # data-event-id="75f1e143-6756-496f-911b-d3abe61d64a5"
            # data-running-text="In&amp;nbsp;progress" class="videolink"
            # onclick="window.open('Video.aspx?
            # Mode=Granicus&amp;ID1=8844&amp;G=D64&amp;Mode2=Video','video');
            # return false;"
            # href="#" style="color:Blue;font-family:Tahoma;font-size:10pt;">Video</a>
            extract_url = soup.find(
                "a",
                id=re.compile(r"ct\S*_ContentPlaceHolder\S*_hypVideo"),
                class_="videolink",
            )["onclick"]
            start = extract_url.find("'") + len("'")
            end = extract_url.find("',")
            video_page_url = "https://kingcounty.legistar.com/" + extract_url[start:end]

        # catch if find() didn't find video web page url (no <a id=... href=.../>)
        except KeyError:
            log.debug("No URL for video page on {legistar_ev[LEGISTAR_EV_SITE_URL]}")
            return []

        log.debug(f"{legistar_ev[LEGISTAR_EV_SITE_URL]} -> {video_page_url}")

        try:
            with urlopen(video_page_url) as resp:
                # now load the page to get the actual video url
                soup = BeautifulSoup(resp.read(), "html.parser")

        except URLError or HTTPError:
            log.error(f"Failed to open {video_page_url}")
            return []

        # source link for the video is embedded in the script of downloadLinks.
        # <script type="text/javascript">
        # var meta_id = '',
        # currentClipIndex = 0,
        # clipList = eval([8844]),
        # downloadLinks = eval([["\/\/69.5.90.100:443\/MediaVault\/Download.aspx?
        # server=king.granicus.com&clip_id=8844",
        # "http:\/\/archive-media.granicus.com:443\/OnDemand\/king\/king_e560cf63-5570-416e-a47d-0e1e13652224.mp4",null]]);
        # </script>

        video_script_text = soup.find(
            "script", text=re.compile(r"downloadLinks")
        ).string
        # Below two lines of code tries to extract video url from downLoadLinks variable
        # "http:\/\/archive-media.granicus.com:443\/OnDemand\/king\/king_e560cf63-5570-416e-a47d-0e1e13652224.mp4"
        downloadLinks = video_script_text.split("[[")[1]
        video_url = downloadLinks.split('",')[1].strip('"')
        # Cleans up the video url to remove backward slash(\)
        video_uri = video_url.replace("\\", "")
        # caption URIs are not found for kingcounty events.
        return [ContentURIs(video_uri=video_uri, caption_uri=None)]

    @staticmethod
    def get_static_person_info() -> Dict[str, Person]:
        """
        Scrape current council members information from kingcounty.gov

        Returns
        -------
        persons: Dict[str, Person]
            keyed by name

        Notes
        -----
        Parse https://kingcounty.gov/council/councilmembers/find_district.aspx
        that contains list of current council members name, position, contact info
        """
        # this page lists current council members
        with urlopen(
            "https://kingcounty.gov/council/councilmembers/find_district.aspx"
        ) as resp:
            soup = BeautifulSoup(resp.read(), "html.parser")

        # keyed by name
        persons: Dict[str, Person] = {}

        # there is a series of council member portrait pictures
        # marked by text "official portrait"

        # <a href="/council/dembowski.aspx"><strong>Rod Dembowski</strong><br/>
        # </a>District 1<br/>
        # 206-477-1001<br/>
        # <a href="mailto:...">rod.dembowski@kingcounty.gov </a><br/>
        # Member since: 2013<br/>
        # Current t<span style="color: rgb(0, 0, 0);">erm: 2018-2021</span><br/>
        # <a href="/~/media/...">Official portrait</a>
        # ...
        # repeat similar blob for the next council person
        # ...
        for picture in soup.find_all(
            "a", text=re.compile(".*official.*portrait.*", re.IGNORECASE)
        ):
            picture_uri = f"https://kingcounty.gov{str_simplified(picture['href'])}"

            # preceding 2 <a> tags have email and website url, in that order
            email_tag = picture.find_previous_sibling("a")
            email = str_simplified(email_tag.text)
            website_tag = email_tag.find_previous_sibling("a")
            website = f"https://kingcounty.gov{str_simplified(website_tag['href'])}"
            name = str_simplified(website_tag.text)

            # this area in plain text contains role and phone for this person
            # Rod Dembowski
            # District 1
            # 206-477-1001
            # rod.dembowski@kingcounty.gov
            parent_tag = picture.find_parent()
            # position number is the trailing number in the line after name
            # and the line after position is the telephone
            match = re.search(
                f".*{name}.*\\s+.*(?P<position>\\d+)\\s+(?P<phone>[\\d\\-\\(\\)]+)",
                parent_tag.text,
                re.IGNORECASE,
            )
            phone = match.group("phone")
            seat = Seat(name=f"Position {match.group('position')}")

            persons[name] = Person(
                name=name,
                picture_uri=picture_uri,
                email=email,
                website=website,
                phone=phone,
                seat=seat,
            )

        return persons

    @staticmethod
    def dump_static_info(file_path: Path) -> None:
        """
        Call this to save current council members information as Persons
        in json format to file_path.
        Intended to be called once every N years when the council changes.

        Parameters
        ----------
        file_path: Path
            output json file path
        """
        static_info_json = {STATIC_FILE_KEY_PERSONS: {}}
        for [name, person] in KingCountyScraper.get_static_person_info().items():
            # to allow for easy future addition of info other than Persons
            # save under top-level key "persons" in the file
            static_info_json[STATIC_FILE_KEY_PERSONS][name] = person.to_dict()

        with open(file_path, "wt") as dump:
            dump.write(json.dumps(static_info_json, indent=4))
