#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from typing import Any, Dict, List
from bs4 import BeautifulSoup
import re
import logging
from urllib.request import urlopen
from urllib.error import (
    URLError,
    HTTPError,
)

from ..legistar_utils import (
    LegistarScraper,
    CDP_VIDEO_URI,
    CDP_CAPTION_URI,
)

from cdp_backend.pipeline.ingestion_models import EventIngestionModel

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

LEGISTAR_EV_SITE_URL = "EventInSiteURL"

###############################################################################


class SeattleScraper(LegistarScraper):
    def __init__(self):
        """
        Seattle-specific implementation of LegistarScraper
        """
        super().__init__("seattle")

    def get_video_uris(self, legistar_ev: Dict) -> List[Dict]:
        """
        Return URLs for videos and captions parsed from seattlechannel.org web page

        Parameters
        ----------
        legistar_ev : Dict
            Data for one Legistar Event obtained from
            ..legistar_utils.get_legistar_events_for_timespan()

        Returns
        -------
        List[Dict]
            List of video and caption URI
            [{"video_uri": ..., "caption_uri": ...}, ...]
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

            list_uri.append({CDP_VIDEO_URI: video_uri, CDP_CAPTION_URI: caption_uri})

        if len(list_uri) == 0:
            log.debug(f"No video URI found on {video_page_url}")
        return list_uri

    def get_time_zone(self) -> str:
        """
        Return US Pacific time zone name.
        Can call find_time_zone() to find dynamically.

        Returns
        -------
        time zone name : str
            "US/Pacific"
        """
        return "US/Pacific"


def get_events(
    from_dt: datetime,
    to_dt: datetime,
    **kwargs: Any,
) -> List[EventIngestionModel]:
    """
    Implimentation of the Seattle Scrapper to provide to a cookiecutter or for testing.
    """
    return SeattleScraper().get_events(begin=from_dt, end=to_dt)
