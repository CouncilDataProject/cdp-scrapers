#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Dict, List
from bs4 import BeautifulSoup
import re
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

LEGISTAR_EV_SITE_URL = 'EventInSiteURL'

###############################################################################


# TODO: add logging
class SeattleScraper(LegistarScraper):
    def __init__(self):
        super().__init__('seattle')

    def get_video_uris(self, legistar_ev: Dict) -> List[Dict]:
        try:
            # EventInSiteURL (= MeetingDetail.aspx) has a td tag
            # with a certain id pattern containing url to video
            with urlopen(legistar_ev[LEGISTAR_EV_SITE_URL]) as resp:
                soup = BeautifulSoup(resp.read(), 'html.parser')
        except URLError or HTTPError:
            return []

        try:
            # this gets us the url for the web PAGE containing the video
            video_page_url = soup.find(
                'a',
                id=re.compile(r'ct\S*_ContentPlaceHolder\S*_hypVideo'),
                class_='videolink'
            )['href']
        # catch if find() didn't find video web page url (no <a id=... href=.../>)
        except KeyError:
            return []

        try:
            with urlopen(video_page_url) as resp:
                # now load the page to get the actual video url
                soup = BeautifulSoup(resp.read(), 'html.parser')
        except URLError or HTTPError:
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
            'script',
            text=re.compile(r'playerInstance\.setup')
        ).string

        # playerSetup({...
        #             ^
        player_arg_start = re.search(
            r'playerInstance\.setup\((\{)',
            video_script_text
        ).start(1)

        # ...});
        #     ^
        # playerInstance... # more playerInstance code
        video_json_blob = video_script_text[
            player_arg_start :
            player_arg_start + re.search(
                r'\)\;\s*\n\s*playerInstance',
                video_script_text[player_arg_start:]
            ).start(0)
        ]

        # not smart enough to make one-line regex for all the 'file's in 'sources'
        videos_start = video_json_blob.find('sources:')
        videos_end = video_json_blob.find('],', videos_start)
        # as shown above, url will start with // so prepend https:
        video_uris = [
            'https:' + i for i in re.findall(
                r'file\:\s*\"([^\"]+)',
                video_json_blob[videos_start : videos_end],
            )
        ]

        captions_start = video_json_blob.find('tracks:')
        captions_end = video_json_blob.find('],', captions_start)
        caption_uris = [
            'https://www.seattlechannel.org/' + i for i in re.findall(
                r'file\:\s*\"([^\"]+)',
                video_json_blob[captions_start : captions_end],
            )
        ]

        iter = range(len(video_uris))
        list_uri = []

        for i in iter:
            # TODO: ok to assume # video_uris == # caption_uris
            #       on a meeting details web page on seattlechannel.org ?
            list_uri.append({
                CDP_VIDEO_URI : video_uris[i],
                CDP_CAPTION_URI : caption_uris[i]
            })

        return list_uri
