#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from typing import Dict, List, Optional, NamedTuple
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from bs4 import BeautifulSoup

from cdp_backend.pipeline.ingestion_models import Person, Seat

from ..legistar_utils import LEGISTAR_EV_SITE_URL, LegistarScraper
from ..types import ContentURIs

###############################################################################

log = logging.getLogger(__name__)

###############################################################################


class PersonSeat(NamedTuple):
    name: str
    seat: str


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
    def get_static_person_info() -> List[Person]:
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
            name = tr.find(
                "a",
                id=re.compile(
                    r"ctl\d*_ContentPlaceHolder\d*_gridPeople_ctl\d*_ctl\d*_hypPerson"
                ),
            ).string

            # <td> in this row with <br> and <em> has seat name
            # row has the member's name, e.g.
            # <td>Councilmember<br /><em>Council Position No. 4</em></td>
            # the seat is the <em>-phasized text
            seat = [
                td
                for td in tr.find_all("td")
                if td.find("br") is not None and td.find("em") is not None
            ][0].em.text

            static_person_info.append(Person(name=name, seat=Seat(name=seat)))

        return static_person_info

    @staticmethod
    def get_district_image_url() -> Optional[str]:
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
