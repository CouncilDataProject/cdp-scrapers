#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from typing import Dict, List
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from bs4 import BeautifulSoup

from ..legistar_utils import LEGISTAR_EV_SITE_URL, LegistarScraper, str_simplified
from ..types import ContentURIs

###############################################################################

log = logging.getLogger(__name__)

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
            ],
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
    def get_person_urls() -> Dict[str, str]:
        # this page lists current council members with urls to personal pages
        with urlopen(
            "https://kingcounty.gov/council/councilmembers/find_district.aspx"
        ) as resp:
            soup = BeautifulSoup(resp.read(), "html.parser")

        # look for <map> tag. it'll have <area> per district/person
        # <map name="rade_img_map_1339527544713" id="rade_img_map_1339527544713">
        # <area alt="Rod Dembowski" shape="RECT" href="/Dembowski.aspx" />
        person_urls: Dict[str, str] = {}
        for i in soup.find("map").find_all("area", href=re.compile(r"\S")):
            person_urls[str_simplified(i["alt"])] = f"https://kingcounty.gov{i['href']}"

        return person_urls
