#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

import requests

from cdp_backend.pipeline.ingestion_models import (
    EventIngestionModel,
    Body,
    IngestionModel,
    Session,
    EventMinutesItem,
    MinutesItem,
    Matter,
    SupportingFile,
    Person,
    Vote,
)

from cdp_backend.database.constants import (
    EventMinutesItemDecision,
    MatterStatusDecision,
    VoteDecision,
)

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

LEGISTAR_BASE = "http://webapi.legistar.com/v1/{client}"
LEGISTAR_VOTE_BASE = LEGISTAR_BASE + "/EventItems"
LEGISTAR_EVENT_BASE = LEGISTAR_BASE + "/Events"
LEGISTAR_MATTER_BASE = LEGISTAR_BASE + "/Matters"
LEGISTAR_PERSON_BASE = LEGISTAR_BASE + "/Persons"

# e.g. Session.video_uri =  EventVideoPath from legistar api
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
LEGISTAR_MATTER_TITLE = "EventItemMatterFile"
LEGISTAR_MATTER_NAME = "EventItemMatterName"
LEGISTAR_MATTER_TYPE = "EventItemMatterType"
LEGISTAR_MATTER_STATUS = "EventItemMatterStatus"
# Session.session_datetime is a combo of EventDate and EventTime
# TODO: this means same time for all Sessions in a NotImplementedError.
#       some other legistar api data that can be used instead?
LEGISTAR_SESSION_DATE = "EventDate"
LEGISTAR_SESSION_TIME = "EventTime"
LEGISTAR_AGENDA_URI = "EventAgendaFile"
LEGISTAR_MINUTES_URI = "EventMinutesFile"
LEGISTAR_MINUTE_ITEM_DESC = "EventItemTitle"
LEGISTAR_MINUTE_EXT_ID = "EventItemId"
# NOTE: just don't see any other field that is unique and short-ish
#       that is appropriate for MinutesItem.name, a required field.
#       LEGISTAR_MINUTE_ITEM_DESC tend to be VERY lengthy
LEGISTAR_MINUTE_NAME = LEGISTAR_MINUTE_EXT_ID
LEGISTAR_VOTE_VAL_ID = "VoteValueId"
LEGISTAR_VOTE_VAL_NAME = "VoteValueName"

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


def stripped(in_str) -> str:
    """
    Return leading and trailing whitespace removed if it is a string

    Parameters
    ----------
    in_str: str

    Returns
    -------
    str or Any
        in_str stripped if it is a string
    """
    if isinstance(in_str, str):
        return in_str.strip()
    return in_str


def reduced_list(in_list: List) -> List:
    """
    Remove all None items from in_list
    Return None if in_list is empty

    Parameters
    ----------
    in_list : List

    Returns
    -------
    List | None
    """
    for i in range(len(in_list) - 1, -1, -1):
        if not in_list[i]:
            del in_list[i]

    if len(in_list) == 0:
        in_list = None

    return in_list


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
    MIN_INGESTION_KEYS: Dict[type, List[str]]
        keys per IngestionModel used to decide if the given model is empty
    *_pattern: Pattern
        regex patterns to decide CDP constant from Legistar information

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

        # NOTE: if all the keys are None that item should be None
        self.MIN_INGESTION_KEYS = {
            Session: ["external_source_id", "video_uri", "caption_uri"],
            Person: ["name", "external_source_id"],
            Vote: ["person"],
            SupportingFile: ["external_source_id", "name", "uri"],
            Matter: ["external_source_id", "name", "title"],
            MinutesItem: ["description"],
            EventMinutesItem: ["matter", "minutes_item"],
            EventIngestionModel: [
                "agenda_uri",
                "body",
                "event_minutes_items",
                "minutes_uri",
                "sessions",
            ],
        }

        self.FILTERS = {
            # i.e. MinutesItem deemed irrelevant (filtered out)
            # if description contains this
            MinutesItem: [
                "CALL TO ORDER",
                "ROLL CALL",
                "APPROVAL OF THE JOURNAL",
                "REFERRAL CALENDAR",
                "APPROVAL OF THE AGENDA",
                "This meeting also constitutes a meeting of the City Council",
                "In-person attendance is currently prohibited",
                "Times listed are estimated",
                "Items of Business",
                "PUBLIC COMMENT",
                "PAYMENT OF BILLS",
                "COMMITTEE REPORTS",
                "OTHER BUSINESS",
                "ADJOURNMENT",
                "has been cancelled",
                "PRESENTATIONS",
                "ADOPTION OF OTHER RESOLUTIONS",
                "Deputy City Clerk",
            ]
        }

        # e.g. for VoteDecision.APPROVE
        self.vote_approve_pattern = "approve|favor"
        self.vote_abstain_pattern = "abstain|refuse|refrain"
        self.vote_reject_pattern = "reject|oppose"

        self.matter_adopted_pattern = "approved|confirmed|passed|adopted"
        self.matter_in_progress_pattern = "heard|ready|filed|held"
        self.matter_rejected_patten = "rejected|dropped"

        self.decision_passed_pattern = "pass"
        self.decision_failed_pattern = "not|fail"

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
        List[EventIngestionModel]
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
            session_time = self.date_time_to_datetime(
                legistar_ev[LEGISTAR_SESSION_DATE], legistar_ev[LEGISTAR_SESSION_TIME]
            )

            # prefer video file path in legistar Event.EventVideoPath
            if legistar_ev[LEGISTAR_SESSION_VIDEO_URI] is not None:
                list_uri = [
                    {
                        CDP_VIDEO_URI: stripped(
                            legistar_ev[LEGISTAR_SESSION_VIDEO_URI]
                        ),
                        CDP_CAPTION_URI: None,
                    }
                ]
            else:
                list_uri = self.get_video_uris(legistar_ev) or [
                    {CDP_VIDEO_URI: None, CDP_CAPTION_URI: None}
                ]

            sessions = []
            sessions = reduced_list(
                [
                    self.get_none_if_empty(
                        Session(
                            session_datetime=session_time,
                            session_index=len(sessions),
                            video_uri=uri[CDP_VIDEO_URI],
                            caption_uri=uri[CDP_CAPTION_URI],
                        )
                    )
                    # Session per video
                    for uri in list_uri
                ]
            )

            ingested = self.get_none_if_empty(
                EventIngestionModel(
                    agenda_uri=stripped(legistar_ev[LEGISTAR_AGENDA_URI]),
                    minutes_uri=stripped(legistar_ev[LEGISTAR_MINUTES_URI]),
                    body=Body(name=stripped(legistar_ev[LEGISTAR_BODY_NAME])),
                    sessions=sessions,
                    event_minutes_items=self.get_event_minutes(
                        legistar_ev[LEGISTAR_EV_ITEMS]
                    ),
                )
            )
            # let's not include None in the returned list
            if ingested:
                evs.append(ingested)

        # TODO: better to return None if evs == [] ?
        # return reduced_list(evs)
        return evs

    def get_video_uris(self, legistar_ev: Dict) -> List[Dict]:
        """
        Must implement in class derived from LegistarScraper.
        If Legistar Event.EventVideoPath is used, return an empty list in the override.

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

    def get_matter_status(self, legistar_matter_status: str) -> MatterStatusDecision:
        """
        Return appropriate MatterStatusDecision constant from EventItemMatterStatus

        Parameters
        ----------
        legistar_matter_status : str
            Legistar API EventItemMatterStatus

        Returns
        -------
        MatterStatusDecision
            ADOPTED | IN_PROGRESS | REJECTED | None

        See Also
        --------
        matter_<adopted|rejected|in_progress>_pattern
        """
        if not legistar_matter_status:
            return None

        if (
            re.search(
                self.matter_adopted_pattern, legistar_matter_status, re.IGNORECASE
            )
            is not None
        ):
            return MatterStatusDecision.ADOPTED

        if (
            re.search(
                self.matter_in_progress_pattern,
                legistar_matter_status,
                re.IGNORECASE,
            )
            is not None
        ):
            return MatterStatusDecision.IN_PROGRESS

        if (
            re.search(
                self.matter_rejected_patten, legistar_matter_status, re.IGNORECASE
            )
            is not None
        ):
            return MatterStatusDecision.REJECTED

        return None

    def get_minutes_item_decision(
        self,
        legistar_item_passed_name: str,
    ) -> EventMinutesItemDecision:
        """
        Return appropriate EventMinutesItemDecision constant
            from EventItemPassedFlagName

        Parameters
        ----------
        legistar_item_passed_name : str
            Legistar API EventItemPassedFlagName

        Returns
        -------
        MatterStatusDecision
            PASSED | FAILED | None

        See Also
        --------
        decision_<passed|failed>_pattern
        """
        if not legistar_item_passed_name:
            return None

        if (
            re.search(
                self.decision_passed_pattern, legistar_item_passed_name, re.IGNORECASE
            )
            is not None
        ):
            return EventMinutesItemDecision.PASSED

        if (
            re.search(
                self.decision_failed_pattern, legistar_item_passed_name, re.IGNORECASE
            )
            is not None
        ):
            return EventMinutesItemDecision.FAILED

        return None

    def get_vote_decision(self, legistar_vote: Dict) -> VoteDecision:
        """
        Return appropriate VoteDecision constant based on Legistar Vote

        Parameters
        ----------
        legistar_vote : Dict
            Legistar API Vote

        Returns
        -------
        VoteDecision
            APPROVE | REJECT | ABSTAIN | None

        See Also
        --------
        vote_<approve|abstain|reject>_pattern
        """
        if (
            not legistar_vote[LEGISTAR_VOTE_VAL_NAME]
            # don't want to make assumption about VoteValueId = 0 meaning here
            # so treating VoteValueId as null only when None
            and legistar_vote[LEGISTAR_VOTE_VAL_ID] is None
        ):
            return None

        # NOTE: The required integer VoteValueId = 16 seems to be "in favor".
        #       But don't know what other values would be e.g. "opposed to", etc.
        #       Therefore deciding VoteDecision based on the string VoteValueName.

        if (
            re.search(
                self.vote_approve_pattern,
                legistar_vote[LEGISTAR_VOTE_VAL_NAME],
                re.IGNORECASE,
            )
            is not None
        ):
            return VoteDecision.APPROVE

        if (
            re.search(
                self.vote_abstain_pattern,
                legistar_vote[LEGISTAR_VOTE_VAL_NAME],
                re.IGNORECASE,
            )
            is not None
        ):
            return VoteDecision.ABSTAIN

        if (
            re.search(
                self.vote_reject_pattern,
                legistar_vote[LEGISTAR_VOTE_VAL_NAME],
                re.IGNORECASE,
            )
            is not None
        ):
            return VoteDecision.REJECT

        return None

    def get_person(self, legistar_person: Dict) -> Person:
        """
        Return CDP Person for Legistar Person

        Parameters
        ----------
        legistar_person : Dict
            Legistar API Person

        Returns
        -------
        Person | None
        """
        return self.get_none_if_empty(
            Person(
                email=stripped(legistar_person[LEGISTAR_PERSON_EMAIL]),
                external_source_id=legistar_person[LEGISTAR_PERSON_EXT_ID],
                name=stripped(legistar_person[LEGISTAR_PERSON_NAME]),
                phone=stripped(legistar_person[LEGISTAR_PERSON_PHONE]),
                website=stripped(legistar_person[LEGISTAR_PERSON_WEBSITE]),
            )
        )

    def get_votes(self, legistar_votes: List[Dict]) -> List[Vote]:
        """
        Return List[Vote] for Legistar API Votes

        Parameters
        ----------
        legistar_votes : List[Dict]
            Legistar API Votes

        Returns
        -------
        List[Vote] | None
        """
        return reduced_list(
            [
                self.get_none_if_empty(
                    Vote(
                        decision=self.get_vote_decision(vote),
                        external_source_id=vote[LEGISTAR_VOTE_EXT_ID],
                        person=self.get_person(vote[LEGISTAR_VOTE_PERSONS]),
                    )
                )
                for vote in legistar_votes
            ]
        )

    def get_event_support_files(
        self,
        legistar_ev_attachments: List[Dict],
    ) -> List[SupportingFile]:
        """
        Return List[SupportingFile] for Legistar API MatterAttachments

        Parameters
        ----------
        legistar_ev_attachments : List[Dict]
            Legistar API MatterAttachments

        Returns
        -------
        List[SupportingFile] | None
        """
        return reduced_list(
            [
                self.get_none_if_empty(
                    SupportingFile(
                        external_source_id=attachment[LEGISTAR_FILE_EXT_ID],
                        name=stripped(attachment[LEGISTAR_FILE_NAME]),
                        uri=stripped(attachment[LEGISTAR_FILE_URI]),
                    )
                )
                for attachment in legistar_ev_attachments
            ]
        )

    def get_matter(self, legistar_ev: Dict) -> Matter:
        """
        Return Matter from Legistar API EventItem

        Parameters
        ----------
        legistar_ev : Dict
            Legistar API EventItem

        Returns
        -------
        Matter | None
        """
        return self.get_none_if_empty(
            Matter(
                external_source_id=legistar_ev[LEGISTAR_MATTER_EXT_ID],
                # Too often EventItemMatterName is not filled
                # but EventItemMatterFile is
                name=stripped(legistar_ev[LEGISTAR_MATTER_NAME])
                or stripped(legistar_ev[LEGISTAR_MATTER_TITLE]),
                matter_type=stripped(legistar_ev[LEGISTAR_MATTER_TYPE]),
                title=stripped(legistar_ev[LEGISTAR_MATTER_TITLE]),
                result_status=self.get_matter_status(
                    legistar_ev[LEGISTAR_MATTER_STATUS]
                ),
            )
        )

    def get_minutes_item(self, legistar_ev_item: Dict) -> MinutesItem:
        """
        Return MinutesItem from parts of Legistar API EventItem

        Parameters
        ----------
        legistar_ev_item : Dict
            Legistar API EventItem

        Returns
        -------
        MinutesItem | None
            None if could not get nonempty MinutesItem.name from EventItem
        """
        minutes_item = MinutesItem(
            external_source_id=legistar_ev_item[LEGISTAR_MINUTE_EXT_ID],
            description=stripped(legistar_ev_item[LEGISTAR_MINUTE_ITEM_DESC]),
            name=None,
        )

        # NOTE: for time being this is LEGISTAR_MINUTE_EXT_ID
        name = legistar_ev_item[LEGISTAR_MINUTE_NAME]
        if isinstance(name, int):
            name = str(name)

        minutes_item.name = stripped(name)

        return self.get_none_if_empty(minutes_item)

    def get_event_minutes(
        self, legistar_ev_items: List[Dict]
    ) -> List[EventMinutesItem]:
        """
        Return List[EventMinutesItem] for Legistar API EventItems

        Parameters
        ----------
        legistar_ev_items : List[Dict]
            Legistar API EventItems

        Returns
        -------
        List[EventMinutesItem] | None
        """
        return reduced_list(
            [
                self.get_none_if_empty(
                    self.filter_event_minutes(
                        EventMinutesItem(
                            decision=self.get_minutes_item_decision(
                                item[LEGISTAR_EV_MINUTE_DECISION]
                            ),
                            minutes_item=self.get_minutes_item(item),
                            votes=self.get_votes(item[LEGISTAR_EV_VOTES]),
                            matter=self.get_matter(item),
                            supporting_files=self.get_event_support_files(
                                item[LEGISTAR_EV_ATTACHMENTS]
                            ),
                        )
                    )
                )
                # EventMinutesItem object per member in EventItems
                for item in legistar_ev_items
            ]
        )

    def filter_event_minutes(
        self, ev_minutes_item: EventMinutesItem
    ) -> EventMinutesItem:
        """
        ev_minutes_item.minutes_item = None
        if ev_minutes_item.minutes_item.description is not important
        and ev_minutes_item is otherwise empty

        Parameters
        ----------
        ev_minutes_item : EventMinutesItem

        Returns
        -------
        EventMinutesItem
            ev_minutes_item.minutes_item may be modified to None

        See Also
        --------
        FILTERS
        """
        if (
            not ev_minutes_item.minutes_item
            or not ev_minutes_item.minutes_item.description
        ):
            return ev_minutes_item

        # do not even check MinutesItem.description if we have any of this
        if (
            ev_minutes_item.supporting_files
            or ev_minutes_item.votes
            or ev_minutes_item.matter
        ):
            return ev_minutes_item

        for filter in self.FILTERS[MinutesItem]:
            # e.g. contains MinutesItem is "call to order"
            # in this otherwise empty EventMinutesItem?
            if filter.lower() in ev_minutes_item.minutes_item.description.lower():
                ev_minutes_item.minutes_item = None
                break

        return ev_minutes_item

    def get_none_if_empty(self, model: IngestionModel) -> IngestionModel:
        """
        Check required keys in model, return None if all keys have no value.
        i.e. If any required key has value, return as-is

        Parameters
        ----------
        model :
            Person, MinutesItem, etc.

        Returns
        -------
        IngestionModel | None
            None or model as-is

        See Also
        --------
        MIN_INGESTION_KEYS
            Required keys per IngestionModel class
        """
        try:
            keys = self.MIN_INGESTION_KEYS[model.__class__]
        except KeyError:
            keys = None

        if not keys:
            # no min keys defined
            log.debug(
                f"Consider defining minimum required keys for {model.__class__}"
                " in MIN_INGESTION_KEYS to filter out empty instances"
            )
            return model

        for k in keys:
            try:
                if model.__dict__[k]:
                    # some value for this key in this model
                    return model
            except KeyError:
                pass

        return None

    @staticmethod
    def date_time_to_datetime(ev_date: str, ev_time: str) -> datetime:
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
