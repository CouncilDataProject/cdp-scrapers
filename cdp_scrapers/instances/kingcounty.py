#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import json
from typing import Dict
from urllib.request import urlopen
from pathlib import Path

from bs4 import BeautifulSoup

from cdp_backend.pipeline.ingestion_models import Person, Seat
from cdp_backend.database.constants import RoleTitle
from ..legistar_utils import (
    LegistarScraper,
)
from ..scraper_utils import str_simplified, parse_static_file

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

STATIC_FILE_KEY_PERSONS = "persons"
STATIC_FILE_DEFAULT_PATH = Path(__file__).parent / "kingcounty-static.json"

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
            static_data=parse_static_file(STATIC_FILE_DEFAULT_PATH),
            role_replacements={
                "Boardmember": RoleTitle.MEMBER,
                "Mr.": RoleTitle.MEMBER,
                "Councilmemeber DELETE": RoleTitle.COUNCILMEMBER,
                "Vice-Chair": RoleTitle.VICE_CHAIR,
                "Council Member": RoleTitle.COUNCILMEMBER,
                "Policy Chair": RoleTitle.CHAIR,
            },
        )

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
