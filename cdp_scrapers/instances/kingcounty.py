#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Dict, List
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

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

LEGISTAR_EV_SITE_URL = "EventInSiteURL"

###############################################################################


class KingCountyScraper(LegistarScraper):
    def __init__(self):
        """
        kingcounty-specific implementation of LegistarScraper
        """
        super().__init__("kingcounty")

    def get_video_uris(self, legistar_ev: Dict) -> List[Dict]:
        """
        Return URLs for videos and captions parsed from kingcounty.gov web page

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
            
            extract_video_url = soup.find(
                "a",
                id=re.compile(r"ct\S*_ContentPlaceHolder\S*_hypVideo"),
                class_="videolink",
            )["onclick"]
            start= extract_video_url.find("'")+len("'")
            end= extract_video_url.find("',")
            video_page_url='https://kingcounty.legistar.com/'+extract_video_url[start:end]

            
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
        video_script_text = soup.find(
            "script", text=re.compile(r"downloadLinks")
        ).string
        downloadLinks = video_script_text.split("[[")[1]
        video_url_extract=downloadLinks.split(",\"")[1]
        video_url=downloadLinks.split("\",")[1].strip('"')
        video_url = video_url.replace("\\","")
        
        video_uris=[]
        video_uris.append(video_url)
        # caption URIs are not found for kingcounty events. keeping it to maintain the return format.
        caption_uri=[]
        iter = range(len(video_uris))
        list_uri = []

        for i in iter:
            try:
                video_uri = video_uris[i]
            except IndexError:
                video_uri = None

            list_uri.append({CDP_VIDEO_URI: video_uri, CDP_CAPTION_URI: caption_uri})

        if len(list_uri) == 0:
            log.debug(f"No video URI found on {video_page_url}")
        return list_uri
