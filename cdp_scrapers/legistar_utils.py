#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.request import urlopen
from urllib.error import (
    URLError,
    HTTPError,
)

import requests

from cdp_backend.pipeline.ingestion_models import (
    EventIngestionModel,
    Body,
    Session,
    EventMinutesItem,
    MinutesItem,
    Matter,
    SupportingFile,
    Person,
    Vote,
)

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

LEGISTAR_BASE = "http://webapi.legistar.com/v1/{client}"
LEGISTAR_VOTE_BASE = LEGISTAR_BASE + "/EventItems"
LEGISTAR_EVENT_BASE = LEGISTAR_BASE + "/Events"
LEGISTAR_MATTER_BASE = LEGISTAR_BASE + "/Matters"
LEGISTAR_PERSON_BASE = LEGISTAR_BASE + "/Persons"

# e.g. MinutesItem.name =  EventItemEventId from legistar api
LEGISTAR_MINUTE_NAME = "EventItemEventId"
LEGISTAR_SESSION_VIDEO_URI = "EventVideoPath"
LEGISTAR_EV_MINUTE_DECISION = "EventItemPassedFlagName"
LEGISTAR_PERSON_EMAIL = "PersonEmail"
LEGISTAR_PERSON_EXT_ID = "PersonId"
LEGISTAR_PERSON_NAME = "PersonFullName"
LEGISTAR_PERSON_PHONE = "PersonPhone"
LEGISTAR_PERSON_WEBSITE = "PersonWWW"
LEGISTAR_BODY_NAME = "EventBodyName"
LEGISTAR_VOTE_DECISION = "VoteResult"
LEGISTAR_VOTE_EXT_ID = "VoteId"
LEGISTAR_FILE_EXT_ID = "MatterAttachmentId"
LEGISTAR_FILE_NAME = "MatterAttachmentName"
LEGISTAR_FILE_URI = "MatterAttachmentHyperlink"
LEGISTAR_MATTER_EXT_ID = "EventItemMatterId"
LEGISTAR_MATTER_TITLE = "EventItemTitle"
LEGISTAR_MATTER_NAME = "EventItemMatterName"
LEGISTAR_MATTER_TYPE = "EventItemMatterType"
LEGISTAR_MATTER_STATUS = "EventItemMatterStatus"
# Session.session_datetime is a combo of EventDate and EventTime
# TODO: this means same time for all Sessions in a NotImplementedError.
#       some other legistar api data that can be used instead?
LEGISTAR_SESSION_DATE = "EventDate"
LEGISTAR_SESSION_TIME = "EventTime"
LEGISTAR_AGENDA_URI = "EventAgendaFile"

LEGISTAR_EV_ITEMS = "EventItems"
LEGISTAR_EV_ATTACHMENTS = "EventItemMatterAttachments"
LEGISTAR_EV_VOTES = "EventItemVoteInfo"
LEGISTAR_VOTE_PERSONS = "PersonInfo"

CDP_VIDEO_URI = "video_uri"
CDP_CAPTION_URI = "caption_uri"

###############################################################################


def get_legistar_events_for_timespan(
    client: str,
    begin: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> List[Dict]:
    """
    Get all legistar events and each events minutes items, people, and votes, for a
    client for a given timespan.

    Parameters
    ----------
    client: str
        Which legistar client to target. Ex: "seattle"
    begin: Optional[datetime]
        The timespan beginning datetime to query for events after.
        Default: UTC now - 1 day
    end: Optional[datetime]
        The timespan end datetime to query for events before.
        Default: UTC now

    Returns
    -------
    events: List[Dict]
        All legistar events that occur between the datetimes provided for the client
        provided. Additionally, requests and attaches agenda items, minutes items, any
        attachments, called "EventItems", requests votes for any of these "EventItems",
        and requests person information for any vote.
    """
    # Set defaults
    if begin is None:
        begin = datetime.utcnow() - timedelta(days=1)
    if end is None:
        end = datetime.utcnow()

    # The unformatted request parts
    filter_datetime_format = "EventDate+{op}+datetime%27{dt}%27"
    request_format = LEGISTAR_EVENT_BASE + "?$filter={begin}+and+{end}"

    # Get response from formatted request
    log.debug(f"Querying Legistar for events between: {begin} - {end}")
    response = requests.get(
        request_format.format(
            client=client,
            begin=filter_datetime_format.format(
                op="ge",
                dt=str(begin).replace(" ", "T"),
            ),
            end=filter_datetime_format.format(
                op="lt",
                dt=str(end).replace(" ", "T"),
            ),
        )
    ).json()

    # Get all event items for each event
    item_request_format = (
        LEGISTAR_EVENT_BASE
        + "/{event_id}/EventItems?AgendaNote=1&MinutesNote=1&Attachments=1"
    )
    for event in response:
        # Attach the Event Items to the event
        event["EventItems"] = requests.get(
            item_request_format.format(client=client, event_id=event["EventId"])
        ).json()

        # Get vote information
        for event_item in event["EventItems"]:
            vote_request_format = LEGISTAR_VOTE_BASE + "/{event_item_id}/Votes"
            event_item["EventItemVoteInfo"] = requests.get(
                vote_request_format.format(
                    client=client,
                    event_item_id=event_item["EventItemId"],
                )
            ).json()

            # Get person information
            for vote_info in event_item["EventItemVoteInfo"]:
                person_request_format = LEGISTAR_PERSON_BASE + "/{person_id}"
                vote_info["PersonInfo"] = requests.get(
                    person_request_format.format(
                        client=client,
                        person_id=vote_info["VotePersonId"],
                    )
                ).json()

    log.debug(f"Collected {len(response)} Legistar events")
    return response


class LegistarScraper:
    """
    Base class for transforming Legistar API data to CDP IngestionModel
    A given installation must define a derived class and implement get_video_uris()

    Parameters
    ----------
    client: str
        Legistar client name, e.g. "seattle" for Seattle

    Attributes
    ----------
    client_name: str
        Legistar client name

    Methods
    -------
    is_legistar_compatible()
        Check that Legistar API recognizes client name
    check_for_cdp_min_ingestion(check_days=7)
        Test if can obtain at least one minimally defined EventIngestionModel
    get_events(
        begin=datetime.utcnow() - timedelta(days=2),
        end=datetime.utcnow()
    )
        Main get method that returns Legistar API data as List[EventIngestionModel]
    get_video_uris(legistar_ev)
        Must implement in class derived from LegistarScraper
    """

    def __init__(self, client: str):
        self.client_name = client

    @property
    def is_legistar_compatible(self) -> bool:
        """
        Check that Legistar API recognizes client name

        Returns
        -------
        bool
            True if client_name is a valid Legistar client name
        """
        # simplest check, if the GET request works, it is a legistar place
        try:
            resp = urlopen(f"http://webapi.legistar.com/v1/{self.client_name}/bodies")
            return resp.status == 200
        except URLError or HTTPError:
            return False

    def check_for_cdp_min_ingestion(self, check_days: int = 7) -> bool:
        """
        Test if can obtain at least one minimally defined EventIngestionModel

        Parameters
        ----------
        check_days : int, default=7
            Test duration is the past check_days days from now

        Returns
        -------
        bool
            True if got at least one minimally defined EventIngestionModel
        """
        # no point wasting time if the client isn't on legistar at all
        if not self.is_legistar_compatible:
            return False

        now = datetime.utcnow()
        days = range(check_days)

        for d in days:
            begin = now - timedelta(days=d + 1)
            end = now - timedelta(days=d)
            log.debug(
                "Testing for minimal information "
                f"from {begin.isoformat()} to {end.isoformat()}"
            )

            # ev: EventIngestionModel
            for cdp_ev in self.get_events(begin=begin, end=end):
                try:
                    if (
                        len(cdp_ev.body.name) > 0
                        and cdp_ev.sessions[0].session_datetime is not None
                        and len(cdp_ev.sessions[0].video_uri) > 0
                    ):
                        session_time = cdp_ev.sessions[0].session_datetime
                        log.debug(
                            f"Got minimal EventIngestionModel for {self.client_name}: "
                            f"body={cdp_ev.body.name}, "
                            f"session={session_time.isoformat()}, "
                            f"video={cdp_ev.sessions[0].video_uri}"
                        )
                        return True

                # catch None or empty list
                except TypeError or IndexError:
                    pass

        log.debug(
            f"Failed to get minimal EventIngestionModel for {self.client_name} "
            f"in the past {check_days} days from {now.isoformat()}"
        )
        # no event in check_days had enough for minimal ingestion model item
        return False

    @staticmethod
    def get_person(legistar_person: Dict) -> Person:
        """
        Return CDP Person for Legistar Person

        Parameters
        ----------
        legistar_person : Dict
            Legistar API Person

        Returns
        -------
        ingestion_models.Person
        """
        return Person(
            email=legistar_person[LEGISTAR_PERSON_EMAIL],
            external_source_id=legistar_person[LEGISTAR_PERSON_EXT_ID],
            name=legistar_person[LEGISTAR_PERSON_NAME],
            phone=legistar_person[LEGISTAR_PERSON_PHONE],
            website=legistar_person[LEGISTAR_PERSON_WEBSITE],
        )

    @staticmethod
    def get_votes(legistar_votes: List[Dict]) -> List[Vote]:
        """
        Return List[ingestion_models.Vote] for Legistar API Votes

        Parameters
        ----------
        legistar_votes : List[Dict]
            Legistar API Votes

        Returns
        -------
        List[ingestion_models.Vote]
        """
        votes = []

        for vote in legistar_votes:
            votes.append(
                Vote(
                    decision=vote[LEGISTAR_VOTE_DECISION],
                    external_source_id=vote[LEGISTAR_VOTE_EXT_ID],
                    person=LegistarScraper.get_person(vote[LEGISTAR_VOTE_PERSONS]),
                )
            )

        return votes

    @staticmethod
    def get_event_support_files(
        legistar_ev_attachments: List[Dict],
    ) -> List[SupportingFile]:
        """
        Return List[ingestion_models.SupportingFile] for Legistar API MatterAttachments

        Parameters
        ----------
        legistar_ev_attachments : List[Dict]
            Legistar API MatterAttachments

        Returns
        -------
        List[ingestion_models.SupportingFile]
        """
        files = []

        for attachment in legistar_ev_attachments:
            files.append(
                SupportingFile(
                    external_source_id=attachment[LEGISTAR_FILE_EXT_ID],
                    name=attachment[LEGISTAR_FILE_NAME],
                    uri=attachment[LEGISTAR_FILE_URI],
                )
            )

        return files

    @staticmethod
    def get_matter(legistar_ev: Dict) -> Matter:
        """
        Return ingestion_models.Matter from Legistar API EventItem

        Parameters
        ----------
        legistar_ev : Dict
            Legistar API EventItem

        Returns
        -------
        ingestion_models.Matter
        """
        return Matter(
            external_source_id=legistar_ev[LEGISTAR_MATTER_EXT_ID],
            name=legistar_ev[LEGISTAR_MATTER_NAME],
            matter_type=legistar_ev[LEGISTAR_MATTER_TYPE],
            title=legistar_ev[LEGISTAR_MATTER_TITLE],
            result_status=legistar_ev[LEGISTAR_MATTER_STATUS],
        )

    @staticmethod
    def get_event_minutes(legistar_ev_items: List[Dict]) -> List[EventMinutesItem]:
        """
        Return List[ingestion_models.EventMinutesItem] for Legistar API EventItems

        Parameters
        ----------
        legistar_ev_items : List[Dict]
            Legistar API EventItems

        Returns
        -------
        List[ingestion_models.EventMinutesItem]
        """
        minutes = []

        # EventMinutesItem object per member in EventItems
        for item in legistar_ev_items:
            minutes.append(
                EventMinutesItem(
                    decision=item[LEGISTAR_EV_MINUTE_DECISION],
                    # other better choice for name?
                    minutes_item=MinutesItem(name=item[LEGISTAR_MINUTE_NAME]),
                    votes=LegistarScraper.get_votes(item[LEGISTAR_EV_VOTES]),
                    matter=LegistarScraper.get_matter(item),
                    supporting_files=LegistarScraper.get_event_support_files(
                        item[LEGISTAR_EV_ATTACHMENTS]
                    ),
                )
            )

        return minutes

    @staticmethod
    def legistar_ev_date_time(ev_date: str, ev_time: str) -> datetime:
        """
        Return datetime from ev_date and ev_time

        Parameters
        ----------
        ev_date : str
            Formatted as "%Y-%m-%dT%H:%M:%S"
        ev_time : str
            Formatted as "%I:%M %p"

        Returns
        -------
        datetime
            date using ev_date and time using ev_time
        """
        # 2021-07-09T00:00:00
        d = datetime.strptime(ev_date, "%Y-%m-%dT%H:%M:%S")
        # 9:30 AM
        t = datetime.strptime(ev_time, "%I:%M %p")
        return datetime(
            year=d.year,
            month=d.month,
            day=d.day,
            hour=t.hour,
            minute=t.minute,
            second=t.second,
        )

    def get_events(
        self,
        # for the past 2 days
        begin: Optional[datetime] = datetime.utcnow() - timedelta(days=2),
        end: Optional[datetime] = datetime.utcnow(),
    ) -> List[EventIngestionModel]:
        """
        Call get_legistar_events_for_timespan to retrieve Legistar API data
        and return as List[EventIngestionModel]

        Parameters
        ----------
        begin : datetime, default=datetime.utcnow() - timedelta(days=2)
            By default query the past 2 days
        end : datetime, default=datetime.utcnow()

        Returns
        -------
        List[ingestion_models.EventIngestionModel]
            One instance of EventIngestionModel per Legistar API Event

        See Also
        --------
        get_legistar_events_for_timespan
        """
        evs = []

        for legistar_ev in get_legistar_events_for_timespan(
            self.client_name,
            begin=begin,
            end=end,
        ):
            session_time = self.legistar_ev_date_time(
                legistar_ev[LEGISTAR_SESSION_DATE], legistar_ev[LEGISTAR_SESSION_TIME]
            )

            sessions = []

            # prefer video file path in legistar Event.EventVideoPath
            if legistar_ev[LEGISTAR_SESSION_VIDEO_URI] is not None:
                list_uri = [
                    {
                        CDP_VIDEO_URI: legistar_ev[LEGISTAR_SESSION_VIDEO_URI],
                        CDP_CAPTION_URI: None,
                    }
                ]
            else:
                list_uri = self.get_video_uris(legistar_ev) or [
                    {CDP_VIDEO_URI: None, CDP_CAPTION_URI: None}
                ]

            for uri in list_uri:
                sessions.append(
                    Session(
                        session_datetime=session_time,
                        session_index=len(sessions),
                        video_uri=uri[CDP_VIDEO_URI],
                        caption_uri=uri[CDP_CAPTION_URI],
                    )
                )

            evs.append(
                EventIngestionModel(
                    agenda_uri=legistar_ev[LEGISTAR_AGENDA_URI],
                    body=Body(name=legistar_ev[LEGISTAR_BODY_NAME]),
                    sessions=sessions,
                    event_minutes_items=self.get_event_minutes(
                        legistar_ev[LEGISTAR_EV_ITEMS]
                    ),
                )
            )

        return evs

    def get_video_uris(self, legistar_ev: Dict) -> List[Dict]:
        """
        Must implement in class derived from LegistarScraper.
        If Legistar Event.EventVideoPath is used, return an empty list here.

        Parameters
        ----------
        legstar_ev : Dict
            Legistar API Event

        Returns
        -------
        List[Dict]
            List of video and caption URI
            [{"video_uri": ..., "caption_uri": ...}, ...]

        Raises
        ------
        NotImplementedError
            This base implementation does nothing
        """
        log.critical(
            "get_video_uris() is required because "
            f"Legistar Event.EventVideoPath is not used by {self.client_name}"
        )
        raise NotImplementedError
