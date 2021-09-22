#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import json
import os
from typing import Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from bs4 import BeautifulSoup

from cdp_backend.pipeline.ingestion_models import Person, Seat

from ..legistar_utils import LEGISTAR_EV_SITE_URL, LegistarScraper, str_simplified
from ..types import ContentURIs

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

STATIC_FILE_KEY_PERSONS = "persons"
STATIC_FILE_DEFAULT_PATH = "cdp_scrapers/instances/seattle-static.json"

known_persons: Optional[Dict[str, Person]] = None

# load long-term static data at file load-time
if os.path.exists(STATIC_FILE_DEFAULT_PATH):
    with open(STATIC_FILE_DEFAULT_PATH, "rb") as json_file:
        static_data = json.load(json_file)

    known_persons = {}
    for name, person in static_data[STATIC_FILE_KEY_PERSONS].items():
        known_persons[name] = Person.from_dict(person)


if known_persons:
    log.debug(f"loaded static data for {', '.join(known_persons.keys())}")

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
                "Executive Session on Pending, Potential, or Actual Litigation",
                "Items of Business",
                # Common to see "CITY COUNCIL:",
                # Or more generally "{body name}:"
                # Check for last char ":"
                r".+:$",
            ],
            known_persons=known_persons,
        )

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
            video_page_url = soup.find(
                "a",
                id=re.compile(r"ct\S*_ContentPlaceHolder\S*_hypVideo"),
                class_="videolink",
            )["href"]
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
        video_script_text = soup.find(
            "script", text=re.compile(r"playerInstance\.setup")
        ).string

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
    def get_district_image_url() -> Optional[str]:
        """
        Return URL for a district map image used on seattle.gov
        Shows all district boundaries

        Returns
        -------
        Image URL: Optional[str]
            District map image URL
        """
        site_url = "https://www.seattle.gov/"
        url = (
            f"{site_url}cityclerk/agendas-and-legislative-resources/"
            "find-your-council-district"
        )
        try:
            with urlopen(url) as resp:
                soup = BeautifulSoup(resp.read(), "html.parser")
        except (URLError, HTTPError):
            log.debug(f"Failed to open {url}")
            return None

        try:
            # <img alt="District Map" src="Images/Clerk/DistrictsMap.jpg" ...
            return site_url + soup.find("img", alt="District Map")["src"]
        except (TypeError, KeyError):
            pass

        return None

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
        such as picture_uri, seat

        Returns
        -------
        persons: Optional[List[Person]]
        """
        # will be used for all seats. simple district boundaries map
        district_map_url = SeattleScraper.get_district_image_url()

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

            seat_number = str_simplified(seat.name.split()[-1])
            seat.electoral_area = "District " + seat_number
            if re.search("large", seat.name, re.IGNORECASE):
                seat.electoral_area = str_simplified(seat.name.split()[0])

            seat.name = "Position " + seat_number
            seat.image_uri = district_map_url
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
