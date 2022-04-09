#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import json
import requests
import urllib3
import warnings
from typing import Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from urllib.parse import urlsplit, parse_qs, quote_plus
from pathlib import Path
from datetime import datetime

from bs4 import BeautifulSoup

from cdp_backend.pipeline.ingestion_models import Person, Seat

from ..legistar_utils import (
    LEGISTAR_EV_SITE_URL,
    LEGISTAR_SESSION_DATE,
    LegistarScraper,
)
from ..scraper_utils import str_simplified, parse_static_file
from ..types import ContentURIs

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

STATIC_FILE_KEY_PERSONS = "persons"
STATIC_FILE_DEFAULT_PATH = Path(__file__).parent / "seattle-static.json"

# we have discovered the city clerk accidentally entered Daniel Strauss
# instead of the correct Dan Strauss for a few events
PERSON_ALIASES = {"Dan Strauss": set(["Daniel Strauss"])}

###############################################################################


class SeattleScraper(LegistarScraper):
    PYTHON_MUNICIPALITY_SLUG: str = "seattle"

    def __init__(self):
        """
        Seattle specific implementation of LegistarScraper.
        """
        super().__init__(
            client="seattle",
            timezone="America/Los_Angeles",
            ignore_minutes_item_patterns=[
                "This meeting also constitutes a meeting of the City Council",
                "In-person attendance is currently prohibited",
                "Times listed are estimated",
                "has been cancelled",
                "Deputy City Clerk",
                "Executive Sessions are closed to the public",
                # Sometimes will have number after "Session", e.g. "Session I"
                r"Executive Session \S*\s*on Pending, Potential, or Actual Litigation",
                "Items of Business",
                # Common to see "CITY COUNCIL:",
                # Or more generally "{body name}:"
                # Check for last char ":"
                r".+:$",
                "Pursuant to Washington State",
            ],
            static_data=parse_static_file(STATIC_FILE_DEFAULT_PATH),
            person_aliases=PERSON_ALIASES,
        )

        try:
            urlopen("https://seattlechannel.org/")
        except URLError:
            pass
        else:
            raise Exception(
                "seattlechannel.org may have fixed their SSL cert. "
                "Check and fix 'requests.get(*, verify=False)' calls"
            )

    def parse_content_uris(
        self, video_page_url: str, event_short_date: str
    ) -> List[ContentURIs]:
        """
        Return URLs for videos and captions parsed from seattlechannel.org web page

        Parameters
        ----------
        video_page_url: str
            URL to a web page for a particular meeting video

        event_short_date: str
            datetime representing the meeting's date, used for verification m/d/yy

        Returns
        -------
        content_uris: List[ContentURIs]
            List of ContentURIs objects for each session found.

        See Also
        --------
        get_content_uris()
        """
        with warnings.catch_warnings():
            warnings.simplefilter(
                "ignore",
                category=urllib3.exceptions.InsecureRequestWarning,
            )
            # now load the page to get the actual video url
            soup = BeautifulSoup(
                requests.get(video_page_url, verify=False).text,
                "html.parser",
            )

        # <script>
        # ...
        # playerInstance.setup({
        # sources: [
        #     {
        #         file: "//...mp4",
        #         label: "Auto"
        #     }
        # ],
        # ...
        # tracks: [{
        #     file: "documents/seattlechannel/closedcaption/2021/...vtt",
        #     label: "English",
        #     kind: "captions",
        #     "default": true
        # }
        #
        #  ],
        # ...

        # entire script tag text that has the video player setup call
        video_script_block = soup.find(
            "script", text=re.compile(r"playerInstance\.setup")
        )
        if not video_script_block:
            log.warning(
                f"Couldn't find 'playerInstance.setup()' block on {video_page_url}.\n"
                "seattlechannel.org may have changed their video page html"
            )
            return []
        video_script_text = video_script_block.string

        # halt if event date not in video's idstring
        # likely means some change on video web page source / script

        # e.g. idstring:'Select Budget Committee Session II 10/14/21'
        #      idstring:'City Council 10/11/21'
        if not re.search(f"idstring:.+{event_short_date}.+", video_script_text):
            raise ValueError(
                f"event date {event_short_date} not in video idstring.\n"
                f"{video_page_url} may be for a different event's video.\n"
            )

        # playerSetup({...
        #             ^
        player_arg_start = re.search(
            r"playerInstance\.setup\((\{)", video_script_text
        ).start(1)

        # ...});
        #     ^
        # playerInstance... # more playerInstance code
        video_json_blob = video_script_text[
            player_arg_start : player_arg_start
            + re.search(
                r"\)\;\s*\n\s*playerInstance", video_script_text[player_arg_start:]
            ).start(0)
        ]

        # not smart enough to make one-line regex for all the 'file's in 'sources'
        videos_start = video_json_blob.find("sources:")
        videos_end = video_json_blob.find("],", videos_start)
        # as shown above, url will start with // so prepend https:
        video_uris = [
            "https:" + i
            for i in re.findall(
                r"file\:\s*\"([^\"]+)",
                video_json_blob[videos_start:videos_end],
            )
        ]

        captions_start = video_json_blob.find("tracks:")
        captions_end = video_json_blob.find("],", captions_start)
        caption_uris = [
            "https://www.seattlechannel.org/" + i
            for i in re.findall(
                r"file\:\s*\"([^\"]+)",
                video_json_blob[captions_start:captions_end],
            )
        ]

        # use max count between videos and captions
        # so we don't lose any (e.g. caption = None if < # videos)
        iter = range(max(len(video_uris), len(caption_uris)))
        list_uri = []

        for i in iter:
            # just in case # videos != # captions
            try:
                video_uri = video_uris[i]
            except IndexError:
                video_uri = None

            try:
                caption_uri = caption_uris[i]
            except IndexError:
                caption_uri = None

            list_uri.append(ContentURIs(video_uri=video_uri, caption_uri=caption_uri))

        if len(list_uri) == 0:
            log.debug(f"No video URI found on {video_page_url}")
        return list_uri

    @staticmethod
    def roman_to_int(roman: str):
        """
        Roman numeral to an integer

        Parameters
        ----------
        roman: str
            Roman numeral string

        Returns
        -------
        int
            Input roman numeral as integer

        References
        ----------
        https://www.w3resource.com/python-exercises/class-exercises/python-class-exercise-2.php
        """
        rom_val = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
        int_val = 0
        for i in range(len(roman)):
            if i > 0 and rom_val[roman[i]] > rom_val[roman[i - 1]]:
                # subtract twice the i-1 th number since it has already been added
                int_val += rom_val[roman[i]] - 2 * rom_val[roman[i - 1]]
            else:
                int_val += rom_val[roman[i]]
        return int_val

    def get_video_page_urls(
        self, video_list_page_url: str, event_short_date: str
    ) -> List[str]:
        """
        Return URLs to web pages hosting videos for meetings from event_short_date

        Parameters
        ----------
        video_list_page_url: str
            URL to web page listing videos featuring the responsible group/body
            for the event described in legistar_ev.
            e.g. http://www.seattlechannel.org/BudgetCommittee?Mode2=Video

        event_short_date: str
            datetime representing the meeting's date m/d/yy

        Returns
        -------
        video_page_urls: List[str]
            web page URL per video

        See Also
        --------
        get_content_uris()
        """
        with warnings.catch_warnings():
            warnings.simplefilter(
                "ignore",
                category=urllib3.exceptions.InsecureRequestWarning,
            )
            # request list of videos for this group on this event's date
            response = requests.get(
                # this is the query sent by the "filter" button on the web page
                f"{video_list_page_url}&filterTerm={quote_plus(event_short_date)}"
                "&itemsPerPage=25&toggleDisplay=Thumbnail_Excerpt",
                verify=False,
            ).text

        # <div class="paginationContainer">
        #     <div class="row borderBottomNone paginationItem">
        #         <div class="col-xs-12 col-sm-4 col-md-3">
        #                     <a href='/BudgetCommittee?videoid=x132213'... </a>
        #         </div>
        #         <div class="col-xs-12 col-sm-8 col-md-9">
        #             <div class="titleDateContainer">
        #                 <h2 class="paginationTitle">
        #                     <a href="/BudgetCommittee?videoid=x132213" ... </a>
        #             </h2>
        #                     <div class="videoDate">10/14/2021</div>
        #         </div>
        #         <div class="titleExcerptText"><p><em>Pursuant to Washington ... </div>
        #     </div>
        # </div>
        #    <div class="row borderBottomNone paginationItem">

        session_video_page_urls: Dict[int, str] = {}

        # want <a> tag in the <div> with
        # title attribute that contains the event date,
        # onclick attribute that calls loadJWPlayer,
        # href attribute that contains videoid

        soup = BeautifulSoup(response, "html.parser")
        for link in soup.find("div", class_="paginationContainer",).find_all(
            "a",
            href=re.compile("videoid"),
            onclick=re.compile("loadJWPlayer"),
            title=re.compile(event_short_date),
        ):
            # e.g. "Session I m/d/yy"
            match = re.search(
                r"session\s(?P<session_int>\d*)(?P<session_roman>[IVXLCDM]*)",
                link["title"],
                re.IGNORECASE,
            )
            if match:
                if match.group("session_int"):
                    session_video_page_urls[
                        int(match.group("session_int"))
                    ] = f"https://www.seattlechannel.org{link['href']}"
                elif match.group("session_roman"):
                    session_video_page_urls[
                        int(SeattleScraper.roman_to_int(match.group("session_roman")))
                    ] = f"https://www.seattlechannel.org{link['href']}"
                else:
                    session_video_page_urls[
                        len(session_video_page_urls)
                    ] = f"https://www.seattlechannel.org{link['href']}"

        # ordered by session number
        return [
            session_video_page_urls[session]
            for session in sorted(session_video_page_urls.keys())
        ]

    def get_content_uris(self, legistar_ev: Dict) -> List[ContentURIs]:
        """
        Return URLs for videos and captions parsed from seattlechannel.org web page

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
        parse_content_uris()

        Notes
        -----
        get_events() calls get_content_uris() to get video and caption URIs.
        get_content_uris() gets video page URL from EventInSiteURL.
        If "videoid" in video page URL, calls parse_content_uris().
        Else, calls get_video_page_urls() to get proper video page URL with "videoid",
            then calls parse_content_uris().
        get_events()
            -> get_content_uris()
                -> parse_content_uris()
                or
                -> get_video_page_urls(), parse_content_uris()
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
            video_page_url = soup.find(
                "a",
                id=re.compile(r"ct\S*_ContentPlaceHolder\S*_hypVideo"),
                class_="videolink",
            )["href"]
            log.debug(f"{legistar_ev[LEGISTAR_EV_SITE_URL]} -> {video_page_url}")
        # catch if find() didn't find video web page url (no <a id=... href=.../>)
        except KeyError:
            log.debug(f"No URL for video page on {legistar_ev[LEGISTAR_EV_SITE_URL]}")
            return []

        event_short_date = datetime.fromisoformat(legistar_ev[LEGISTAR_SESSION_DATE])
        # want no leading zero for month or day
        event_short_date = (
            f"{event_short_date.month}/"
            f"{event_short_date.day}/"
            f"{event_short_date.strftime('%y')}"
        )

        # Some meetings will have text like "Session II" in "Meeting location".
        # For those, don't bother verifying video page URL.
        # They are multi-session and we need to call get_video_page_urls()
        if (
            "session ii"
            not in soup.find(
                "span", id=re.compile(r"ctl\S*_ContentPlaceHolder\S*_lblLocation$")
            ).text.lower()
        ):
            try:
                if parse_qs(urlsplit(video_page_url).query)["videoid"]:
                    # video link contains specific videoid
                    return self.parse_content_uris(video_page_url, event_short_date)
            except KeyError:
                pass

        # at this point video_page_url points to generic video list page like
        # http://www.seattlechannel.org/BudgetCommittee?Mode2=Video

        return [
            uris
            # 1 web page per session video for this multi-session event
            for page_url in self.get_video_page_urls(video_page_url, event_short_date)
            # video and caption urls on the session video web page
            for uris in self.parse_content_uris(page_url, event_short_date)
        ]

    @staticmethod
    def get_person_picture_url(person_www: str) -> Optional[str]:
        """
        Parse person_www and return banner image used on the web page

        Parameters
        ----------
        person_www: str
            e.g. http://www.seattle.gov/council/pedersen

        Returns
        -------
        Image URL: Optional[str]
            Full URL to banner image displayed on person_www
        """
        try:
            with urlopen(person_www) as resp:
                soup = BeautifulSoup(resp.read(), "html.parser")
        except URLError or HTTPError:
            log.debug("Failed to open {person_www}")
            return None

        # <div class="featureWrapperShort" style="background-image:
        # url('/assets/images/Council/Members/Pedersen/
        # Councilmember-Alex-Pedersen_homepage-banner.jpg')"></div>
        div = soup.find(
            "div", class_="featureWrapperShort", style=re.compile(r"background\-image")
        )
        if not div:
            return None

        try:
            # now get just the image uri '/assets/...'
            return "http://www.seattle.gov/" + re.search(
                r"url\('([^']+)", div["style"]
            ).group(1)
        except AttributeError:
            pass

        return None

    @staticmethod
    def get_static_person_info() -> Optional[List[Person]]:
        """
        Return partial Persons with static long-term information

        Returns
        -------
        persons: Optional[List[Person]]
        """
        try:
            # has table with all council members
            with urlopen("https://seattle.legistar.com/MainBody.aspx") as resp:
                soup = BeautifulSoup(resp.read(), "html.parser")
        except URLError or HTTPError:
            log.debug("Failed to open https://seattle.legistar.com/MainBody.aspx")
            return None

        static_person_info: List[Person] = []

        # <tr id="ctl00_ContentPlaceHolder1_gridPeople_ctl00__0" ...>
        #     <td class="rgSorted" style="white-space:nowrap;">
        #         <a ...>Alex Pedersen</a>
        #     </td>
        #     <td>Councilmember<br /><em>Council Position No. 4</em></td>
        #     <td>1/1/2020</td>
        #     <td style="white-space:nowrap;">
        #         <span ...>12/31/2023</span>
        #     </td>
        #     <td style="white-space:nowrap;">
        #         <a ...>Alex.Pedersen@seattle.gov</a>
        #     </td>
        #     <td style="white-space:nowrap;">
        #         <a ...>http://www.seat...ouncil/pedersen</a>
        #     </td>
        # </tr>
        for tr in soup.find_all(
            "tr",
            # each row with this id in said table is for a council member
            id=re.compile(r"ctl\d+_ContentPlaceHolder\d+_gridPeople_ctl\d+__\d+"),
        ):
            # <a> tag in this row with this id has full name
            try:
                name = str_simplified(
                    tr.find(
                        "a",
                        id=re.compile(
                            r"ctl\d*_ContentPlaceHolder\d*"
                            r"_gridPeople_ctl\d*_ctl\d*_hypPerson"
                        ),
                    ).text
                )
            except AttributeError:
                # find() returned None
                continue

            # <a> tag in this row with this id has url
            # for web page with more info on this person
            try:
                person_picture_url = SeattleScraper.get_person_picture_url(
                    tr.find(
                        "a",
                        id=re.compile(
                            r"ctl\d*_ContentPlaceHolder\d*"
                            r"_gridPeople_ctl\d*_ctl\d*_hypWebSite"
                        ),
                    )["href"]
                )
            except AttributeError:
                # find() returned None
                continue

            # <td> in this row with <br> and <em> has seat name
            # <td>Councilmember<br /><em>Council Position No. 4</em></td>
            # the seat is the <em>-phasized text
            try:
                seat = Seat(
                    name=str_simplified(
                        [
                            td
                            for td in tr.find_all("td")
                            if td.find("br") is not None and td.find("em") is not None
                        ][0].em.text
                    )
                )
            except IndexError:
                # accessed 0-th item in an empty list []
                continue

            # from "Council Position No. 4"
            #     Seat.electoral_area: District 4
            #     Seat.name: Position 4
            # from "At-large Council Position No. 9"
            #     Seat.electoral_area: At-large
            #     Seat.name: Position 9

            match = re.search(
                r"(?P<atlarge>At.*large)?.*position.*(?P<position_num>\d+)",
                seat.name,
                re.IGNORECASE,
            )
            if match:
                seat_number = match.group("position_num")
                seat.electoral_area = f"District {seat_number}"
                if match.group("atlarge"):
                    seat.electoral_area = "Citywide"

                seat.name = f"Position {seat_number}"

            static_person_info.append(
                Person(name=name, picture_uri=person_picture_url, seat=seat)
            )

        return static_person_info

    @staticmethod
    def dump_static_info(file_path: str) -> bool:
        """
        Save static data in json format

        Parameters
        ----------
        file_path: str
            Static data dump file path

        Returns
        -------
        bool
            True if some data was saved in file_path

        See Also
        --------
        LegistarScraper.inject_known_data()
        """
        static_person_info = {}
        for person in SeattleScraper.get_static_person_info():
            # save this Person in json keyed by the name
            static_person_info[person.name] = json.loads(person.to_json())

        if not static_person_info:
            return False

        with open(file_path, "wt") as dump:
            dump.write(
                json.dumps({STATIC_FILE_KEY_PERSONS: static_person_info}, indent=4)
            )
        return True
