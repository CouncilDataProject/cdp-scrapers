#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Dict, List
from bs4 import BeautifulSoup
from urllib.request import urlopen
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
from cdp_scrapers.legistar_utils import get_legistar_events_for_timespan

###############################################################################


def get_event_minutes(legistar_ev_items: List[Dict]) -> List[EventMinutesItem]:
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
                minutes_item = MinutesItem(name = item['EventItemEventId']),

                matter = Matter(
                    name = item['EventItemMatterName'],
                    matter_type = item['EventItemMatterType'],
                    title = item['EventItemTitle'],
                    # other better choice for result?
                    result_status = item['EventItemMatterStatus'],
                )
            )
        )

    return minutes


def get_event_video(ev_site_url: str) -> str:
    '''
    parse web page at ev_site_url and return url for video if found
    ev_site_url is EventInSiteURL
    '''
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

        # use this pattern to get the script tag containing the video url
        # and to also get the url itself from the script tag text
        video_url_regex = re.compile(r'playerInstance\.setup\s*\(\s*\{\s*sources\:\s*\[\s*\{\s*file\:\s*\"([^\"\n]+)')
        return 'https:' + video_url_regex.search(soup.find('script', text = video_url_regex).string).group(1)

        # TODO: get transcript (subtitles)

    except:
        return None


def get_events() -> List[EventIngestionModel]:
    client_name = 'seattle'
    evs = []

    for legistar_ev in get_legistar_events_for_timespan(
        client_name,
        # for the past 2 days
        # will address duplicates later
        begin = datetime.datetime.utcnow() - datetime.timedelta(days = 2),
        end = datetime.datetime.utcnow(),
        # NOTE: use the range below to retrieve events with 1 containing video
        #begin = datetime.datetime(year = 2021, month = 7, day = 9),
        #end = datetime.datetime(year = 2021, month = 7, day = 10),
    ):
        try:
            session_time = datetime.datetime.strptime(legistar_ev['EventAgendaLastPublishedUTC'], '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError:
            session_time = datetime.datetime.strptime(legistar_ev['EventAgendaLastPublishedUTC'], '%Y-%m-%dT%H:%M:%S')
        except:
            session_time = None

        evs.append(
            EventIngestionModel(
                body = Body(name = legistar_ev['EventBodyName']),
                event_minutes_items = get_event_minutes(legistar_ev['EventItems']),

                sessions = [Session(
                    session_datetime = session_time,
                    session_index = 0,
                    video_uri = get_event_video(legistar_ev['EventInSiteURL']),
                )],
            )
        )

    return evs
