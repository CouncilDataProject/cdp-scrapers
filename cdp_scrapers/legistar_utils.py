#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
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

from pytz import (
    utc,
    timezone,
    country_timezones,
)

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

LEGISTAR_BASE = "http://webapi.legistar.com/v1/{client}"
LEGISTAR_VOTE_BASE = LEGISTAR_BASE + "/EventItems"
LEGISTAR_EVENT_BASE = LEGISTAR_BASE + "/Events"
LEGISTAR_MATTER_BASE = LEGISTAR_BASE + "/Matters"
LEGISTAR_PERSON_BASE = LEGISTAR_BASE + "/Persons"

# TODO: make these member attributes in LegistarScraper
#       so that instances can use different Legistar keys
#       more easily. i.e. modify one of these in __init__()
#       As opposed to overriding a method that uses these.

# e.g. Session.video_uri =  EventVideoPath from legistar api
LEGISTAR_SESSION_VIDEO_URI = "EventVideoPath"
LEGISTAR_EV_MINUTE_DECISION = "EventItemPassedFlagName"
# NOTE: EventItemAgendaSequence is also a candidate for this
LEGISTAR_EV_INDEX = "EventItemMinutesSequence"
LEGISTAR_PERSON_EMAIL = "PersonEmail"
LEGISTAR_PERSON_EXT_ID = "PersonId"
LEGISTAR_PERSON_NAME = "PersonFullName"
LEGISTAR_PERSON_PHONE = "PersonPhone"
LEGISTAR_PERSON_WEBSITE = "PersonWWW"
LEGISTAR_PERSON_ACTIVE = "PersonActiveFlag"
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
# NOTE: this may not be present
LEGISTAR_MATTER_SPONSOR = "EventItemMatterRequester"
# Session.session_datetime is a combo of EventDate and EventTime
# TODO: this means same time for all Sessions in a EventIngestionModel.
#       some other legistar api data that can be used instead
LEGISTAR_SESSION_DATE = "EventDate"
LEGISTAR_SESSION_TIME = "EventTime"
LEGISTAR_AGENDA_URI = "EventAgendaFile"
LEGISTAR_MINUTES_URI = "EventMinutesFile"
LEGISTAR_MINUTE_EXT_ID = "EventItemId"
LEGISTAR_MINUTE_NAME = "EventItemTitle"
LEGISTAR_VOTE_VAL_ID = "VoteValueId"
LEGISTAR_VOTE_VAL_NAME = "VoteValueName"

LEGISTAR_EV_ITEMS = "EventItems"
LEGISTAR_EV_ATTACHMENTS = "EventItemMatterAttachments"
LEGISTAR_EV_VOTES = "EventItemVoteInfo"
LEGISTAR_VOTE_PERSONS = "PersonInfo"
LEGISTAR_EV_SITE_URL = "EventInSiteURL"
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


def stripped(input_str: str) -> str:
    """
    Return leading and trailing whitespace removed if it is a string

    Parameters
    ----------
    input_str : str

    Returns
    -------
    str
        input_str stripped if it is a string
    """
    if isinstance(input_str, str):
        return input_str.strip()
    return input_str


def reduced_list(input_list: List[Any], collapse: bool = True) -> List:
    """
    Remove all None items from input_list.

    Parameters
    ----------
    input_list : List[Any]
        Input list from which to filter out items that are None
    collapse : bool, default = True
        If True, return None in place of an empty list

    Returns
    -------
    List | None
    """
    filtered = [item for item in input_list if item is not None]
    if collapse and len(filtered) == 0:
        filtered = None

    return filtered


class LegistarScraper:
    """
    Base class for transforming Legistar API data to CDP IngestionModel
    A given installation must define a derived class and implement get_video_uris()
    and get_time_zone() functions.

    Parameters
    ----------
    client: str
        Legistar client name, e.g. "seattle" for Seattle

    See Also
    --------
    instances.SeattleScraper
    """

    def __init__(self, client: str):
        self.client_name: str = client

        # EventMinutesItem is ignored from ingestion if minutes_item contains this
        self.IGNORED_MINUTE_ITEMS: List[str] = [
            "This meeting also constitutes a meeting of the City Council",
            "In-person attendance is currently prohibited",
            "Times listed are estimated",
            "has been cancelled",
            "Deputy City Clerk",
            "Paste the following link into the address bar of your web browser",
            "HOW TO WATCH",
            "page break",
            "PUBLIC NOTICE",
            # "CALL TO ORDER",
            # "ROLL CALL",
            # "APPROVAL OF THE JOURNAL",
            # "REFERRAL CALENDAR",
            # "APPROVAL OF THE AGENDA",
            # "Items of Business",
            # "PUBLIC COMMENT",
            # "PAYMENT OF BILLS",
            # "COMMITTEE REPORTS",
            # "OTHER BUSINESS",
            # "ADJOURNMENT",
            # "PRESENTATIONS",
            # "ADOPTION OF OTHER RESOLUTIONS",
        ]

        # regex patterns used to infer cdp_backend.database.constants
        # from Legistar string fields
        self.vote_approve_pattern: str = "approve|favor|yes"
        self.vote_abstain_pattern: str = "abstain|refuse|refrain"
        self.vote_reject_pattern: str = "reject|oppose|no"
        # TODO: need to debug these using real examples
        self.vote_absent_pattern: str = "absent"
        self.vote_nonvoting_pattern: str = "nv|(?:non.*voting)"

        self.matter_adopted_pattern: str = "approved|confirmed|passed|adopted"
        self.matter_in_progress_pattern: str = (
            r"heard|ready|filed|held|(?:in\s*committee)"
        )
        self.matter_rejected_patten: str = "rejected|dropped"

        self.decision_passed_pattern: str = "pass"
        self.decision_failed_pattern: str = "not|fail"

        # e.g. pytz.timezone("US/Pacific")
        self.time_zone: timezone = timezone(self.get_time_zone())

    @property
    def is_legistar_compatible(self) -> bool:
        """
        Check that Legistar API recognizes client name

        Returns
        -------
        bool
            True if client_name is a valid Legistar client name
        """
        # simplest check, if the GET request works, it is a legistar municipality
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
        begin: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[EventIngestionModel]:
        """
        Calls get_legistar_events_for_timespan to retrieve Legistar API data
        and return as List[EventIngestionModel]

        Parameters
        ----------
        begin : datetime, optional
            The timespan beginning datetime to query for events after.
            Default is 2 days from UTC now
        end : datetime, optional
            The timespan end datetime to query for events before.
            Default is UTC now

        Returns
        -------
        List[EventIngestionModel]
            One instance of EventIngestionModel per Legistar Event

        See Also
        --------
        get_legistar_events_for_timespan
        """
        if begin is None:
            begin = datetime.utcnow() - timedelta(days=2)
        if end is None:
            end = datetime.utcnow()

        ingestion_models = []

        for legistar_ev in get_legistar_events_for_timespan(
            self.client_name,
            begin=begin,
            end=end,
        ):
            session_time = self.date_time_to_datetime(
                legistar_ev[LEGISTAR_SESSION_DATE], legistar_ev[LEGISTAR_SESSION_TIME]
            )
            # prefer video file path in legistar Event.EventVideoPath
            if legistar_ev[LEGISTAR_SESSION_VIDEO_URI]:
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
            ingestion_models.append(
                self.get_none_if_empty(
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
            )

        # easier for calling pipeline to handle an empty list rather than None
        # so request reduced_list() to give me [], not None
        return reduced_list(ingestion_models, collapse=True)

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

    def get_time_zone(self) -> str:

        """
        Return time zone name for CDP instance.
        To use dynamically determined time zone,
        use find_time_zone().
        Returns
        -------
        time zone name : str
            i.e. "America/Los_Angeles" | "America/New_York" ...
        See Also
        --------
        SeattleScraper.get_time_zone()
        Notes
        -----
        List of Timezones: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
        Please only use "Canonical" timezones.
        """
        log.error(
            "Time zone name required for proper event timestamping. "
            "e.g. America/Los_Angeles"
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
        matter_*_pattern
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

        log.debug(
            "not able to decide MatterStatusDecision from "
            f"{legistar_matter_status}. consider updating matter_*_pattern"
        )

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
        decision_*_pattern
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
        VoteDecision | None

        See Also
        --------
        vote_*_pattern
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

        decision = None

        if (
            re.search(
                self.vote_approve_pattern,
                legistar_vote[LEGISTAR_VOTE_VAL_NAME],
                re.IGNORECASE,
            )
            is not None
        ):
            decision = VoteDecision.APPROVE
        elif (
            re.search(
                self.vote_reject_pattern,
                legistar_vote[LEGISTAR_VOTE_VAL_NAME],
                re.IGNORECASE,
            )
            is not None
        ):
            decision = VoteDecision.REJECT

        nonvoting = (
            re.search(
                self.vote_nonvoting_pattern,
                legistar_vote[LEGISTAR_VOTE_VAL_NAME],
                re.IGNORECASE,
            )
            is not None
        )

        # determine qualifer like absent, abstain
        if (
            re.search(
                self.vote_absent_pattern,
                legistar_vote[LEGISTAR_VOTE_VAL_NAME],
                re.IGNORECASE,
            )
            is not None
        ):
            if decision == VoteDecision.APPROVE:
                return VoteDecision.ABSENT_APPROVE
            elif decision == VoteDecision.REJECT:
                return VoteDecision.ABSENT_REJECT
            elif nonvoting:
                return VoteDecision.ABSENT_NON_VOTING
        elif (
            re.search(
                self.vote_abstain_pattern,
                legistar_vote[LEGISTAR_VOTE_VAL_NAME],
                re.IGNORECASE,
            )
            is not None
        ):
            if decision == VoteDecision.APPROVE:
                return VoteDecision.ABSTAIN_APPROVE
            elif decision == VoteDecision.REJECT:
                return VoteDecision.ABSTAIN_REJECT
            elif nonvoting:
                return VoteDecision.ABSTAIN_NON_VOTING

        return decision

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
                is_active=bool(legistar_person[LEGISTAR_PERSON_ACTIVE]),
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
        try:
            sponsors = reduced_list(
                [
                    self.get_none_if_empty(
                        # at least try. this info isn't always filled
                        Person(name=legistar_ev[LEGISTAR_MATTER_SPONSOR])
                    )
                ]
            )
        except KeyError:
            sponsors = None

        return self.get_none_if_empty(
            Matter(
                external_source_id=legistar_ev[LEGISTAR_MATTER_EXT_ID],
                # Too often EventItemMatterName is not filled
                # but EventItemMatterFile is
                name=stripped(legistar_ev[LEGISTAR_MATTER_NAME])
                or stripped(legistar_ev[LEGISTAR_MATTER_TITLE]),
                matter_type=stripped(legistar_ev[LEGISTAR_MATTER_TYPE]),
                sponsors=sponsors,
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

        return self.get_none_if_empty(
            MinutesItem(
                external_source_id=legistar_ev_item[LEGISTAR_MINUTE_EXT_ID],
                name=stripped(legistar_ev_item[LEGISTAR_MINUTE_NAME]),
            )
        )

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
                    self.fix_event_minutes(
                        # if minutes_item contains unimportant data,
                        # just make the entire EventMinutesItem = None
                        self.filter_event_minutes(
                            EventMinutesItem(
                                index=item[LEGISTAR_EV_INDEX],
                                minutes_item=self.get_minutes_item(item),
                                votes=self.get_votes(item[LEGISTAR_EV_VOTES]),
                                matter=self.get_matter(item),
                                decision=self.get_minutes_item_decision(
                                    item[LEGISTAR_EV_MINUTE_DECISION]
                                ),
                                supporting_files=self.get_event_support_files(
                                    item[LEGISTAR_EV_ATTACHMENTS]
                                ),
                            )
                        ),
                        item,
                    )
                )
                # EventMinutesItem object per member in EventItems
                for item in legistar_ev_items
            ]
        )

    def fix_event_minutes(
        self, ev_minutes_item: EventMinutesItem, legistar_ev_item: Dict
    ) -> EventMinutesItem:
        """
        Inspect the MinutesItem and Matter in ev_minutes_item.
        - Move some fields between them to make the information more meaningful.
        - Enforce matter.result_status when appropriate.

        Parameters
        ----------
        ev_minutes_item : EventMinutesItem
        legistar_ev_item : Dict
            Legistar EventItem

        Returns
        -------
        EventMinutesItem
            parts of minutes_item and matter could be modified
        """
        if not ev_minutes_item:
            return ev_minutes_item
        if ev_minutes_item.minutes_item and ev_minutes_item.matter:
            # we have both matter and minutes_item
            # - make minutes_item.name the more concise text e.g. "CB 11111"
            # - make minutes_item.description the more descriptive lengthy text
            #   e.g. "AN ORDINANCE related to the..."
            # - make matter.title the same descriptive lengthy text
            ev_minutes_item.minutes_item.description = ev_minutes_item.minutes_item.name
            ev_minutes_item.minutes_item.name = ev_minutes_item.matter.name
            ev_minutes_item.matter.title = ev_minutes_item.minutes_item.description
        # matter.result_status is allowed to be null
        # only when no votes or Legistar EventItemMatterStatus is null
        if ev_minutes_item.matter and not ev_minutes_item.matter.result_status:
            if ev_minutes_item.votes and legistar_ev_item[LEGISTAR_MATTER_STATUS]:
                # means did not find matter_*_pattern in Legistar EventItemMatterStatus.
                # default to in progress (as opposed to adopted or rejected)
                # NOTE: if our matter_*_patterns ARE "complete",
                #       this clause would hit only because the info from Legistar
                #       is incomplete or malformed
                ev_minutes_item.matter.result_status = MatterStatusDecision.IN_PROGRESS

        return ev_minutes_item

    def filter_event_minutes(
        self, ev_minutes_item: EventMinutesItem
    ) -> EventMinutesItem:
        """
        Return None if minutes_item.name contains unimportant text
        that we want to ignore

        Parameters
        ----------
        ev_minutes_item : EventMinutesItem

        Returns
        -------
        EventMinutesItem | None

        See Also
        --------
        IGNORED_MINUTE_ITEMS
        """
        if not ev_minutes_item.minutes_item or not ev_minutes_item.minutes_item.name:
            return ev_minutes_item
        for filter in self.IGNORED_MINUTE_ITEMS:
            if re.search(filter, ev_minutes_item.minutes_item.name, re.IGNORECASE):
                return None
        return ev_minutes_item

    def get_none_if_empty(self, model: IngestionModel) -> IngestionModel:
        """
        Check required keys in model, return None if any such key has no value.
        i.e. If all required keys have valid value, return as-is

        Parameters
        ----------
        model :
            Person, MinutesItem, etc.

        Returns
        -------
        IngestionModel | None
            None or model as-is
        """
        try:
            min_keys = self.min_ingestion_keys[model.__class__]
        except AttributeError:
            # first time using min_ingestion_keys
            self.min_ingestion_keys = {}
            min_keys = None
        except KeyError:
            # first time checking model.__class__
            min_keys = None

        if min_keys is None:
            min_keys = self.get_required_attrs(model)
            # cache so we don't do expensive dynamic checking
            # again for this IngestionModel
            self.min_ingestion_keys[model.__class__] = min_keys

        if not min_keys:
            # no required keys for this model
            # this probably never happens
            return model

        for key in min_keys:
            try:
                val = getattr(model, key)

                # "if not" test to catch all None and None-like values
                # e.g. empty string, empty list, ...
                # but int(0) is not "empty"
                if not val and not isinstance(val, int):
                    # empty value for this key in model
                    return None
            except AttributeError:
                return None

        # nonempty value for all required keys in model
        return model

    def get_required_attrs(self, model: IngestionModel) -> List[str]:
        """
        Return list of keys required in model as specified
        in IngestionModel class definition

        Parameters
        ----------
        model : IngestionModel
            Person, MinutesItem, etc.

        Returns
        -------
        List[str]
            List of keys (attributes) in model without default value in class definition
        """
        try:
            # create an empty one to have python tell us what keys are required
            model.__class__()
            # all attrs in model have default values
            return []
        except TypeError as e:
            # e.g. __init__() missing 3 required positional arguments:
            # 'session_datetime', 'video_uri', and 'session_index'
            match = re.search(
                r"missing (?P<num_keys>\d+) required.+argument(?:s)?\:\s*(?P<keys>.+)",
                str(e),
            )

        if not match:
            log.debug(f"not able to get required attributes for {model.__class__}")
            return []

        num_keys = int(match.group("num_keys"))

        # 'session_datetime', 'video_uri', and 'session_index'
        # -> ["session_datetime", "video_uri", "session_index"]

        # SHOULD be able to do this more elegantly using re.split()
        # but couldn't quite get the pattern right
        keys = re.sub(
            # TypeError uses
            # , and
            # and
            # ,
            # as delimiters for attribute names
            r"(\s*,\s*and\s*)|(\s*and\s*)|(\s*,\s*)",
            ",",
            match.group("keys").strip().replace("'", ""),
        ).split(",")

        if num_keys != len(keys):
            log.debug(f"{model.__class__} has {num_keys} required keys but got {keys}")

        return keys

    def find_time_zone(self) -> str:
        """
        Return name for a US time zone matching UTC offset calculated from OS clock
        Returns
        -------
        time zone name : str
        """
        utc_now = utc.localize(datetime.utcnow())
        local_now = datetime.now()

        for zone_name in country_timezones("us"):
            zone = timezone(zone_name)
            # if this is my time zone
            # utc_now as local time should be VERY close to local_now
            if (
                abs(
                    (
                        utc_now.astimezone(zone) - zone.localize(local_now)
                    ).total_seconds()
                )
                < 5
            ):
                return zone_name

        return None

    def as_local_time(self, local_time: datetime) -> datetime:
        """
        Return input datetime with time zone information.
        This allows for nonambiguous conversions to other zones including UTC.
        Parameters
        ----------
        local_time : datetime
        Returns
        -------
        local_time : datetime
            The date and time attributes (year, month, day, hour, ...) remain unchanged.
            tzinfo is now provided.
        """
        try:
            return self.time_zone.localize(local_time)
        except (AttributeError, ValueError):
            # AttributeError: time_zone or local_time is None
            # ValueError: local_time is not navie (has time zone info)
            return local_time

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
        # some events may have ev_time =None
        if ev_time is not None:
            t = datetime.strptime(ev_time, "%I:%M %p")
            return datetime(
                year=d.year,
                month=d.month,
                day=d.day,
                hour=t.hour,
                minute=t.minute,
                second=t.second,
            )
        else:
            return datetime(
                year=d.year,
                month=d.month,
                day=d.day,
                hour=0,
                minute=0,
                second=0,
            )
