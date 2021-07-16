#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Dict, List
from bs4 import BeautifulSoup
from urllib.request import urlopen
from urllib.error import HTTPError
import re
import sys
import datetime

from cdp_backend.pipeline.ingestion_models import (
    EventIngestionModel,
    Body,
    Session,
    EventMinutesItem,
    MinutesItem,
    Matter,
)
from cdp_scrapers.legistar_utils import(
    get_legistar_events_for_timespan,
    LEGISTAR_BASE
)

###############################################################################


# e.g. EventItemEventId from legistar api -> MinutesItem.name
LEGISTAR_MINUTE_NAME   = 'EventItemEventId'
LEGISTAR_MATTER_TITLE  = 'EventItemTitle'
LEGISTAR_MATTER_NAME   = 'EventItemMatterName'
LEGISTAR_MATTER_TYPE   = 'EventItemMatterType'
LEGISTAR_MATTER_STATUS = 'EventItemMatterStatus'
LEGISTAR_SESSION_TIME  = 'EventAgendaLastPublishedUTC'
LEGISTAR_BODY_NAME     = 'EventBodyName'

LEGISTAR_EV_ITEMS      = 'EventItems'
LEGISTAR_EV_SITE_URL   = 'EventInSiteURL'


# base class for scraper to convert legistar api data -> cdp ingestion model data
# TODO: double-check unique class name in cdp to avoid confusion
class LegistarScraper:
    def __init__(self, client: str):
        self.client_name = client


    def is_legistar_compatible(self) -> bool:
        '''
        return True if can get successful legistar api response
        '''
        client = self.client_name

        # simplest check, if the GET request works, it is a legistar place
        try:
            resp = urlopen(f'{LEGISTAR_BASE}/bodies')
            return (resp.status == 200)
        except:
            return False


    # TODO: lol, better name???
    def can_get_min_info(self) -> bool:
        '''
        return True if able to get minimum required data for EventIngestionModel
        '''
        # TODO:  call get_events() to check if ANY event in the past week has body name, time and video_uri
        return True


    def get_event_minutes(self, legistar_ev_items: List[Dict]) -> List[EventMinutesItem]:
        '''
        return legistar 'EventItems' as EventMinutesItems
        '''
        # TODO: create more objects like Vote, SupportingFile, Person with available info

        minutes = []

        # EventMinutesItem object per member in EventItems
        for item in legistar_ev_items:
            minutes.append(
                EventMinutesItem(
                    # other better choice for name?
                    minutes_item = MinutesItem(name = item[LEGISTAR_MINUTE_NAME]),

                    matter = Matter(
                        name = item[LEGISTAR_MATTER_NAME],
                        matter_type = item[LEGISTAR_MATTER_TYPE],
                        title = item[LEGISTAR_MATTER_TITLE],
                        # other better choice for result?
                        result_status = item[LEGISTAR_MATTER_STATUS],
                    )
                )
            )

        return minutes


    def get_event_video(self, ev_site_url: str) -> List[Dict]:
        '''
        parse web page at ev_site_url and return url for video and captions if found
        ev_site_url is EventInSiteURL
        [{'video_uri' : 'https://video.mp4', 'caption_uri' : 'https://caption.vtt'}, ...]
        '''
        return []


    def get_events(self) -> List[EventIngestionModel]:
        '''
        main getter to retrieve legistar data as cdp ingestion model items
        '''
        evs = []

        for legistar_ev in get_legistar_events_for_timespan(
            self.client_name,
            # for the past 2 days
            # will address duplicates later
            begin = datetime.datetime.utcnow() - datetime.timedelta(days = 2),
            end = datetime.datetime.utcnow(),
            # NOTE: use the range below to retrieve events with 1 containing video
            #begin = datetime.datetime(year = 2021, month = 7, day = 9),
            #end = datetime.datetime(year = 2021, month = 7, day = 10),
        ):
            try:
                session_time = datetime.datetime.strptime(legistar_ev[LEGISTAR_SESSION_TIME], '%Y-%m-%dT%H:%M:%S.%f')
            except ValueError:
                session_time = datetime.datetime.strptime(legistar_ev[LEGISTAR_SESSION_TIME], '%Y-%m-%dT%H:%M:%S')
            except:
                session_time = None

            sessions = []

            # TODO: Session per video_uri/caption_uri ok?
            for uri in self.get_event_video(legistar_ev[LEGISTAR_EV_SITE_URL]):
                sessions.append(
                    Session(
                        session_datetime = session_time,
                        session_index = 0,
                        video_uri = uri['video_uri'],
                        caption_uri = uri['caption_uri'],
                    )
                )
            else:
                sessions.append(
                    Session(
                        session_datetime = session_time,
                        session_index = 0,
                        video_uri = None,
                    )
                )

            evs.append(
                EventIngestionModel(
                    body = Body(name = legistar_ev[LEGISTAR_BODY_NAME]),
                    event_minutes_items = self.get_event_minutes(legistar_ev[LEGISTAR_EV_ITEMS]),
                    sessions = sessions,
                )
            )

        return evs


class SeattleScraper(LegistarScraper):
    def __init__(self):
        super().__init__('seattle')


    def get_event_video(self, ev_site_url: str) -> List[Dict]:
        # broad try to simply return None if any statement below fails
        try:
            # EventInSiteURL (= MeetingDetail.aspx) has a td tag with a certain id pattern containing url to video
            with urlopen(ev_site_url) as resp:
                soup = BeautifulSoup(resp.read(), 'html.parser')
                # this gets us the url for the web PAGE containing the video
                video_page_url = soup.find('a', id = re.compile(r'ct\S*_ContentPlaceHolder\S*_hypVideo'), class_ = 'videolink')['href']

            with urlopen(video_page_url) as resp:
                # now load the page to get the actual video url
                soup = BeautifulSoup(resp.read(), 'html.parser')

            # <script>
            # ...
            # playerInstance.setup({
            # sources: [
            #     {
            #         file: "//video.seattle.gov/media/council/fin_070921_2612127V.mp4",
            #         label: "Auto"
            #     }
            # ],
            # ...
            # tracks: [{
            #     file: "documents/seattlechannel/closedcaption/2021/fin_070921_2612127.vtt",
            #     label: "English",
            #     kind: "captions",
            #     "default": true
            # }
            # 
            #  ], 
            # ...

            # entire script tag text that has the video player setup call
            video_script_text = soup.find('script', text = re.compile(r'playerInstance\.setup')).string
            # playerSetup({...
            player_arg_start = re.search(r'playerInstance\.setup\((\{)', video_script_text).start(1)
            # ...});
            video_json_blob = video_script_text[
                player_arg_start :
                player_arg_start + re.search(r'\)\;\s*\n\s*playerInstance', video_script_text[player_arg_start:]).start(0)
            ]

            # not smart enough to make a cool one-time regex to get all the 'file's in 'sources'
            sources_start = video_json_blob.find('sources:')
            sources_end = video_json_blob.find('],', sources_start)
            # as shown above, url will start with // so prepend https:
            video_uris = ['https:' + i for i in re.findall(r'file\:\s+\"([^\"]+)',
                video_json_blob[sources_start : sources_end],
            )]

            captions_start = video_json_blob.find('tracks:')
            captions_end = video_json_blob.find('],', captions_start)
            caption_uris = ['http://seattlechannel.org/' + i for i in re.findall(r'file\:\s+\"([^\"]+)',
                video_json_blob[captions_start : captions_end],
            )]

        except:
            return []

        iter = range(len(video_uris))
        list_uri = []

        for i in iter:
            # TODO: ok to assume # video_uris == # caption_uris on a meeting details web page on seattlechannel.org ?
            list_uri.append({'video_uri' : video_uris[i], 'caption_uri' : caption_uris[i]})

        return list_uri
