#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from datetime import datetime, timedelta
from itertools import groupby
from logging import getLogger
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import quote_plus, urljoin

from cdp_backend.pipeline.ingestion_models import Body, EventIngestionModel, Session
from yt_dlp import YoutubeDL

from .scraper_utils import IngestionModelScraper, reduced_list

log = getLogger(__name__)


def urljoin_search_query(
    channel_name: str,
    search_terms: str,
    begin: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> str:
    """
    Return search URL https://www.youtube.com/@channel/search?query=...

    Parameters
    ----------
    channel_name: str
        YouTube channel hosting the videos
    search_terms: str
        Search terms, e.g. "city council meeting"
    begin: Optional[datetime]
        The timespan beginning datetime to query for events after.
    end: Optional[datetime]
        The timespan end datetime to query for events before.

    Returns
    -------
    str
        Full HTTPS URL for searching channel videos
        e.g. https://www.youtube.com/@chanel/search?...

    Raises
    ------
    ValueError
        - If both begin and end are None
        - If search term + date range is empty
    """
    begin_term = "" if begin is None else begin.strftime("after:%Y-%m-%d")
    end_term = "" if end is None else end.strftime("before:%Y-%m-%d")
    date_term = f" {begin_term} {end_term}".strip()

    if not any(date_term):
        raise ValueError("Searching without date range filter is not allowed.")

    search_term = f"{search_terms} {date_term}"
    search_term = quote_plus(search_term.strip())

    if not any(search_term):
        raise ValueError("Empty search terms")

    channel_url = urljoin("https://www.youtube.com", f"@{channel_name}")
    query = f"search?query={search_term}"
    url = f"{channel_url}/{query}"
    return url


def get_video_info(query_url: str) -> List[Dict[str, Any]]:
    """
    Return dictionaries of search hit video meta data

    Parameters
    ----------
    query_url: str
        Full YouTube URL including the query parameters

    Returns
    -------
    List[Dict[str, Any]]
        Dictionary containing information for each search hit YouTube video
    """
    with YoutubeDL(
        params={
            "sleep_interval_requests": 0.5,
            "noplaylist": True,
            "forcejson": True,
        },
    ) as ydl:
        info = ydl.extract_info(url=query_url, download=False)
        return info.get("entries", [])


class YoutubeIngestionScraper(IngestionModelScraper):
    """
    Base class for scraping CDP event ingestion models from YouTube videos.
    """

    def __init__(
        self, channel_name: str, body_search_terms: Dict[str, str], **kwargs: Any
    ) -> None:
        """
        Parameters
        ----------
        channel_name: str
            YouTube channel name where the municipality meeting videos are hosted
        body_search_terms: Dict[str, str]
            e.g. {"City Council": "city council meeting"}
        kwargs: Any
            Passed to base class constructor
        """
        super().__init__(**kwargs)

        self.channel_name = channel_name
        self.body_search_terms = body_search_terms

    def parse_datetime(self, title: str) -> datetime:
        """
        Parse video datetime from title text

        Parameters
        ----------
        title: str
            YouTube video title

        Returns
        -------
        datetime
            datetime instance for the video.

        Notes
        -----
        Override for custom parsing.
        Default expects month_name day, year
        e.g. January 1, 1960
        """
        date_match = re.search(r"[a-z]+ \d{1,2}, \d{4}", title, re.I)
        return datetime.strptime(date_match.group(), "%B %d, %Y")

    def get_session(self, video_info: Dict[str, Any]) -> Optional[Session]:
        """
        Parse a CDP Session from YouTube video information

        Parameters
        ----------
        video_info: Dict[str, Any]
            YouTube video information from yt-dlp

        Returns
        -------
        Optional[Session]
            None if required information is missing
        """
        session_index = video_info.get("playlist_index", 0)
        video_id = video_info.get("id")

        video_title = video_info["title"]
        video_datetime = self.parse_datetime(video_title)
        video_uri = video_info["webpage_url"]

        log.debug(f"{video_title} -> {video_uri}")

        session = Session(
            session_datetime=video_datetime,
            video_uri=video_uri,
            session_index=session_index,
            external_source_id=video_id,
        )
        session = self.get_none_if_empty(session)
        return session

    def iter_events(
        self, begin: datetime, end: datetime
    ) -> Iterator[EventIngestionModel]:
        """
        Return iterator over events from given date range,
        for all known bodies in this municipality.

        Parameters
        ----------
        begin: datetime
            The timespan beginning datetime to query for events after.
        end: datetime
            The timespan end datetime to query for events before.

        Yields
        ------
        EventIngestionModel

        Notes
        -----
        If multiple videos are found for a given body on the same day,
        they are treated to be sessions of the same event.
        """
        for body_name, search_terms in self.body_search_terms.items():
            body = Body(name=body_name)
            body = self.get_none_if_empty(body)
            url = urljoin_search_query(
                channel_name=self.channel_name,
                search_terms=search_terms,
                begin=begin,
                end=end,
            )

            video_info_list = get_video_info(query_url=url)
            video_info_list = filter(
                lambda info: re.search(search_terms, info["title"], re.I) is not None,
                video_info_list,
            )

            sessions = map(self.get_session, video_info_list)
            sessions = reduced_list(sessions, collapse=False)
            sessions = filter(
                lambda s: s.session_datetime >= begin and s.session_datetime <= end,
                sessions,
            )
            sessions = list(sessions)

            for _, _sessions in groupby(
                sessions, key=lambda s: s.session_datetime.date()
            ):
                event = EventIngestionModel(
                    body=body,
                    sessions=list(_sessions),
                )
                event = self.get_none_if_empty(event)
                yield event

    def get_events(
        self,
        begin: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[EventIngestionModel]:
        """
        Scrape CDP events from the meeting videos
        hosted on this municipality YouTube channel.

        Parameters
        ----------
        begin: Optional[datetime]
            The timespan beginning datetime to query for events after.
            Default is 2 days from UTC now
        end: Optional[datetime]
            The timespan end datetime to query for events before.
            Default is UTC now

        Returns
        -------
        events: List[EventIngestionModel]
            One instance of EventIngestionModel per Legistar Event
        """
        if begin is None:
            begin = datetime.utcnow() - timedelta(days=2)
        if end is None:
            end = datetime.utcnow()

        events = self.iter_events(begin=begin, end=end)
        events = reduced_list(events, collapse=False)
        return events
