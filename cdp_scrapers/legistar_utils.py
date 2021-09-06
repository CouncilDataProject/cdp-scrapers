#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import requests
from cdp_backend.database.constants import (
    EventMinutesItemDecision,
    MatterStatusDecision,
    VoteDecision,
)
from cdp_backend.pipeline.ingestion_models import (
    Body,
    EventIngestionModel,
    EventMinutesItem,
    IngestionModel,
    Matter,
    MinutesItem,
    Person,
    Session,
    SupportingFile,
    Vote,
    Role,
)
import pytz

from .types import ContentURIs

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

LEGISTAR_BASE = "http://webapi.legistar.com/v1/{client}"
LEGISTAR_VOTE_BASE = LEGISTAR_BASE + "/EventItems"
LEGISTAR_EVENT_BASE = LEGISTAR_BASE + "/Events"
LEGISTAR_MATTER_BASE = LEGISTAR_BASE + "/Matters"
LEGISTAR_PERSON_BASE = LEGISTAR_BASE + "/Persons"
LEGISTAR_BODY_BASE = LEGISTAR_BASE + "/Bodies"

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
LEGISTAR_PERSON_ROLES = "OfficeRecordInfo"
LEGISTAR_BODY_NAME = "BodyName"
LEGISTAR_BODY_EXT_ID = "BodyId"
LEGISTAR_BODY_ACTIVE = "BodyActiveFlag"
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
LEGISTAR_MATTER_SPONSORS = "MatterSponsorInfo"
LEGISTAR_SPONSOR_ID = "MatterSponsorNameId"
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
LEGISTAR_ROLE_BODY = "OfficeRecordBodyInfo"
LEGISTAR_ROLE_START = "OfficeRecordStartDate"
LEGISTAR_ROLE_END = "OfficeRecordEndDate"
LEGISTAR_ROLE_EXT_ID = "OfficeRecordId"
LEGISTAR_ROLE_TITLE = "OfficeRecordTitle"

LEGISTAR_EV_ITEMS = "EventItems"
LEGISTAR_EV_ATTACHMENTS = "EventItemMatterAttachments"
LEGISTAR_EV_VOTES = "EventItemVoteInfo"
LEGISTAR_VOTE_PERSONS = "PersonInfo"
LEGISTAR_EV_SITE_URL = "EventInSiteURL"
LEGISTAR_EV_EXT_ID = "EventId"
LEGISTAR_EV_BODY = "EventBodyInfo"

LEGISTAR_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
###############################################################################


known_persons: Dict[int, Dict[str, Any]] = {}
known_bodies: Dict[int, Dict[str, Any]] = {}


def get_legistar_body(
    client: str,
    body_id: int,
    use_cache: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Return information for a single legistar body in JSON.

    Parameters
    ----------
    client: str
        Which legistar client to target. Ex: "seattle"
    body_id: int
        Unique ID for this body in the legistar municipality
    use_cache: bool
        True: Store result to prevent querying repeatedly for same body_id

    Returns
    -------
    body: Dict[str, Any]
        legistar API body

    Notes
    -----
    known_bodies cache is cleared for every LegistarScraper.get_events() call
    """
    if use_cache:
        try:
            return known_bodies[body_id]
        except KeyError:
            # new body
            pass

    body_request_format = LEGISTAR_BODY_BASE + "/{body_id}"
    response = requests.get(
        body_request_format.format(
            client=client,
            body_id=body_id,
        )
    )

    if response.status_code == 200:
        body = response.json()
    else:
        body = None

    if use_cache:
        known_bodies[body_id] = body
    return body


def get_legistar_person(
    client: str,
    person_id: int,
    use_cache: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Return information for a single legistar person in JSON.

    Parameters
    ----------
    client: str
        Which legistar client to target. Ex: "seattle"
    person_id: int
        Unique ID for this person in the legistar municipality
    use_cache: bool
        True: Store result to prevent querying repeatedly for same person_id

    Returns
    -------
    person: Dict[str, Any]
        legistar API person

    Notes
    -----
    known_persons cache is cleared for every LegistarScraper.get_events() call
    """
    if use_cache:
        try:
            return known_persons[person_id]
        except KeyError:
            # new person
            pass

    person_request_format = LEGISTAR_PERSON_BASE + "/{person_id}"
    response = requests.get(
        person_request_format.format(
            client=client,
            person_id=person_id,
        )
    )

    if response.status_code != 200:
        if use_cache:
            known_persons[person_id] = None
        return None

    person = response.json()

    # all known OfficeRecords (roles) for this person
    response = requests.get(
        (person_request_format + "/OfficeRecords").format(
            client=client,
            person_id=person_id,
        )
    )

    if response.status_code != 200:
        person[LEGISTAR_PERSON_ROLES] = None
        if use_cache:
            known_persons[person_id] = person
        return person

    office_records: List[Dict[str, Any]] = response.json()
    for record in office_records:
        # body for this role
        record[LEGISTAR_ROLE_BODY] = get_legistar_body(
            client=client, body_id=record["OfficeRecordBodyId"], use_cache=use_cache
        )

    person[LEGISTAR_PERSON_ROLES] = office_records
    if use_cache:
        known_persons[person_id] = person
    return person


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
    cache_persons_bodies: bool
        True: Store responses to prevent duplicate queries for a person or a body

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

    # a given person and/or body's information being updated
    # during the lifetime of this single call is miniscule.
    # use a cache to prevent 10s-100s of web requests
    # for the same person/body
    global known_persons, known_bodies
    # See Also
    # get_legistar_person()
    known_persons.clear()
    # See Also
    # get_legistar_body()
    known_bodies.clear()

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

        # Attach info for the body responsible for this event
        event[LEGISTAR_EV_BODY] = get_legistar_body(
            client=client, body_id=event["EventBodyId"], use_cache=True
        )

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
                vote_info["PersonInfo"] = get_legistar_person(
                    client=client,
                    person_id=vote_info["VotePersonId"],
                    use_cache=True,
                )

            if (
                not isinstance(event_item["EventItemMatterId"], int)
                or event_item["EventItemMatterId"] < 0
            ):
                event_item[LEGISTAR_MATTER_SPONSORS] = None
            else:
                # this person's sponsor
                sponsor_request_format = (
                    LEGISTAR_MATTER_BASE + "/{event_item_matter_id}/Sponsors"
                )
                event_item[LEGISTAR_MATTER_SPONSORS] = requests.get(
                    sponsor_request_format.format(
                        client=client,
                        event_item_matter_id=event_item["EventItemMatterId"],
                    )
                ).json()

    log.debug(f"Collected {len(response)} Legistar events")
    return response


def str_simplified(input_str: str) -> str:
    """
    Remove leading and trailing whitespaces, simplify multiple whitespaces, unify
    newline characters.

    Parameters
    ----------
    input_str: str

    Returns
    -------
    cleaned: str
        input_str stripped if it is a string
    """
    if not isinstance(input_str, str):
        return input_str

    input_str = input_str.strip()
    # unify newline to \n
    input_str = re.sub(r"[\r\n\f]+", r"\n", input_str)
    # multiple spaces and tabs to 1 space
    input_str = re.sub(r"[ \t\v]+", " ", input_str)

    # Replace utf-8 char encodings with single utf-8 chars themselves
    input_str = input_str.encode("utf-8").decode("utf-8")

    return input_str


def reduced_list(input_list: List[Any], collapse: bool = True) -> Optional[List]:
    """
    Remove all None items from input_list.

    Parameters
    ----------
    input_list: List[Any]
        Input list from which to filter out items that are None
    collapse: bool, default = True
        If True, return None in place of an empty list

    Returns
    -------
    reduced_list: Optional[List]
        All items in the original list except for None values.
        None if all items were None and collapse is True.
    """
    filtered = [item for item in input_list if item is not None]
    if collapse and len(filtered) == 0:
        filtered = None

    return filtered


class LegistarScraper:
    """
    Base class for transforming Legistar API data to CDP IngestionModel.

    If get_events() naively fails and raises an error, a given installation must define
    a derived class and implement the get_content_uris() function.

    Parameters
    ----------
    client: str
        Legistar client name, e.g. "seattle" for Seattle, "kingcounty" for King County.
    timezone: str
        The timezone for the target client.
        i.e. "America/Los_Angeles" or "America/New_York"
        See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones for canonical
        timezones.
    ignore_minutes_item_patterns: List[str]
        A list of string patterns or substrings to act as a minutes item filter.
        Any item in the provided list will be compiled as a regex string and any
        minute's item that contains the compiled pattern will be filtered out of the
        produced CDP minutes item list.
        Default: [] (do not filter any minutes items)
    vote_approve_pattern: str
        Regex pattern used to convert Legistar instance's votes in approval value to CDP
        constant value.
        Default: "approve|favor|yes"
    vote_abstain_pattern: str
        Regex pattern used to convert Legistar instance's abstension value to CDP
        constant value. Note, this is a pure abstension, not an "approval by
        abstention" or "rejection by abstension" value. Those should be places in
        vote_approve_pattern and vote_reject_pattern respectively.
        Default: "abstain|refuse|refrain"
    vote_reject_pattern: str
        Regex pattern used to convert Legistar instance's votes in rejection value to
        CDP constant value.
        Default: "reject|oppose|no"
    vote_absent_pattern: str
        Regex pattern used to convert Legistar instance's excused absense value to CDP
        constant value.
        Default: "absent"
    vote_nonvoting_pattern: str
        Regex pattern used to convert Legistar instance's non-voting value to CDP
        constant value.
        Default: "nv|(?:non.*voting)"
    matter_adopted_pattern: str
        Regex pattern used to convert Legistar instance's matter was adopted to CDP
        constant value.
        Default: "approved|confirmed|passed|adopted"
    matter_in_progess_pattern: str
        Regex pattern used to convert Legistar instance's matter is in-progress to
        CDP constant value.
        Default: "heard|ready|filed|held|(?:in\s*committee)"
    matter_rejected_pattern: str
        Regex pattern used to convert Legistar instance's matter was rejected to CDP
        constant value.
        Default: "rejected|dropped"
    minutes_item_decision_passed_pattern: str
        Regex pattern used to convert Legistar instance's minutes item passage to CDP
        constant value.
        Default: "pass"
    minutes_item_decision_failed_pattern: str
        Regex pattern used to convert Legistar instance's minutes item failure to CDP
        constant value.
        Default: "not|fail"

    See Also
    --------
    cdp_scrapers.legistar_utils.LegistarScraper.get_content_uris
    cdp_scrapers.instances.seattle.SeattleScraper
    """  # noqa: W605

    def __init__(
        self,
        client: str,
        timezone: str,
        ignore_minutes_item_patterns: List[str] = [],
        vote_approve_pattern: str = r"approve|favor|yes",
        vote_abstain_pattern: str = r"abstain|refuse|refrain",
        vote_reject_pattern: str = r"reject|oppose|no",
        vote_absent_pattern: str = r"absent",
        vote_nonvoting_pattern: str = r"nv|(?:non.*voting)",
        matter_adopted_pattern: str = (
            r"approved|confirmed|passed|adopted|consent|(?:voted.*com+it+ee)"
        ),
        matter_in_progress_pattern: str = r"heard|read|filed|held|(?:in.*com+it+ee)",
        matter_rejected_pattern: str = r"rejected|dropped",
        minutes_item_decision_passed_pattern: str = r"pass",
        minutes_item_decision_failed_pattern: str = r"not|fail",
    ):
        self.client_name: str = client
        self.timezone: pytz.timezone = pytz.timezone(timezone)
        self.ignore_minutes_item_patterns: List[str] = ignore_minutes_item_patterns

        # regex patterns used to infer cdp_backend.database.constants
        # from Legistar string fields
        self.vote_approve_pattern: str = vote_approve_pattern
        self.vote_abstain_pattern: str = vote_abstain_pattern
        self.vote_reject_pattern: str = vote_reject_pattern
        # TODO: need to debug these using real examples
        self.vote_absent_pattern: str = vote_absent_pattern
        self.vote_nonvoting_pattern: str = vote_nonvoting_pattern

        self.matter_adopted_pattern: str = matter_adopted_pattern
        self.matter_in_progress_pattern: str = matter_in_progress_pattern
        self.matter_rejected_patten: str = matter_rejected_pattern

        self.minutes_item_decision_passed_pattern: str = (
            minutes_item_decision_passed_pattern
        )
        self.minutes_item_decision_failed_pattern: str = (
            minutes_item_decision_failed_pattern
        )

    @staticmethod
    def get_required_attrs(model: IngestionModel) -> List[str]:
        """
        Return list of keys required in model as specified in IngestionModel class
        definition.

        Parameters
        ----------
        model: IngestionModel
            Person, MinutesItem, etc.

        Returns
        -------
        attr_keys: List[str]
            List of keys (attributes) in model without default value in class
            definition.
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

    def get_none_if_empty(self, model: IngestionModel) -> Optional[IngestionModel]:
        """
        Check required keys in model, return None if any such key has no value.
        i.e. If all required keys have valid value, return as-is.

        Parameters
        ----------
        model: IngestionModel
            Person, MinutesItem, etc.

        Returns
        -------
        model: Optional[IngestionModel]
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
            min_keys = LegistarScraper.get_required_attrs(model)
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

    def get_matter_status(self, legistar_matter_status: str) -> Optional[str]:
        """
        Return appropriate MatterStatusDecision constant from EventItemMatterStatus.

        Parameters
        ----------
        legistar_matter_status: str
            Legistar API EventItemMatterStatus.

        Returns
        -------
        matter_status: Optional[str]
            A constant from CDP allowed matter status decisions.
            None if missing information or if matter status decision parameter patterns
            are not inclusive to the Legistar matter status value.

        See Also
        --------
        cdp_backend.database.constants.MatterStatusDecision
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

        log.debug(f"no MatterStatusDecision filter for {legistar_matter_status}")
        return None

    def get_minutes_item_decision(
        self,
        legistar_item_passed_name: str,
    ) -> Optional[str]:
        """
        Return appropriate EventMinutesItemDecision constant from
        EventItemPassedFlagName.

        Parameters
        ----------
        legistar_item_passed_name: str
            Legistar API EventItemPassedFlagName

        Returns
        -------
        emi_decision: Optional[str]
            A constant from CDP allowed minutes item decisions.
            None if missing information or if minutes item decision parameter
            patterns are no inclusive of the Legistar minutes item decision value.

        See Also
        --------
        cdp_backend.database.constants.EventMinutesItemDecision
        """
        if not legistar_item_passed_name:
            return None

        if (
            re.search(
                self.minutes_item_decision_passed_pattern,
                legistar_item_passed_name,
                re.IGNORECASE,
            )
            is not None
        ):
            return EventMinutesItemDecision.PASSED

        if (
            re.search(
                self.minutes_item_decision_failed_pattern,
                legistar_item_passed_name,
                re.IGNORECASE,
            )
            is not None
        ):
            return EventMinutesItemDecision.FAILED

        log.debug(f"no EventMinutesItemDecision filter for {legistar_item_passed_name}")
        return None

    def get_vote_decision(self, legistar_vote: Dict) -> Optional[str]:
        """
        Return appropriate VoteDecision constant based on Legistar Vote.

        Parameters
        ----------
        legistar_vote: Dict
            Legistar API Vote

        Returns
        -------
        vote_decision: Optional[str]
            A constant from CDP allowed vote decisions.
            None if missing vote information or if vote decision parameter patterns are
            not inclusive of the Legistar vote value.

        See Also
        --------
        cdp_backend.database.constants.VoteDecision
        """
        vote_value = legistar_vote[LEGISTAR_VOTE_VAL_NAME]
        # don't want to make assumption about VoteValueId = 0 meaning here
        # so treating VoteValueId as null only when None
        if not vote_value and legistar_vote[LEGISTAR_VOTE_VAL_ID] is None:
            return None

        # NOTE: The required integer VoteValueId = 16 seems to be "in favor".
        #       But don't know what other values would be e.g. "opposed to", etc.
        #       Therefore deciding VoteDecision based on the string VoteValueName.

        decision = None

        if (
            re.search(
                self.vote_approve_pattern,
                vote_value,
                re.IGNORECASE,
            )
            is not None
        ):
            decision = VoteDecision.APPROVE
        elif (
            re.search(
                self.vote_reject_pattern,
                vote_value,
                re.IGNORECASE,
            )
            is not None
        ):
            decision = VoteDecision.REJECT

        nonvoting = (
            re.search(
                self.vote_nonvoting_pattern,
                vote_value,
                re.IGNORECASE,
            )
            is not None
        )

        # determine qualifer like absent, abstain
        if (
            re.search(
                self.vote_absent_pattern,
                vote_value,
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
                vote_value,
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

        if not decision:
            log.debug(f"no VoteDecision filter for {vote_value}")
        return decision

    def get_body(self, legistar_body: Dict[str, Any]) -> Optional[Body]:
        """
        Return CDP Body for Legistar body.

        Parameters
        ----------
        legistar_body: Dict
            Legistar API body

        Returns
        -------
        body: Optional[body]
            The Legistar body converted to a CDP body ingestion model.
            None if missing required information.

        See Also
        --------
        get_legistar_body()
        """
        if not legistar_body:
            return None

        return self.get_none_if_empty(
            Body(
                external_source_id=legistar_body[LEGISTAR_BODY_EXT_ID],
                is_active=bool(legistar_body[LEGISTAR_BODY_ACTIVE]),
                name=str_simplified(legistar_body[LEGISTAR_BODY_NAME]),
            )
        )

    def get_roles(
        self, legistar_office_records: List[Dict[str, Any]]
    ) -> Optional[List[Role]]:
        """
        Return list of CDP Role from list of legistar OfficeRecord

        Parameters
        ----------
        legistar_office_records: List[Dict]
            Legistar API OfficeRecords

        Returns
        -------
        roles: Optional[List[Role]]
            From Legistar OfficeRecords. None if missing information.
        """
        if not legistar_office_records:
            return None

        return reduced_list(
            [
                self.get_none_if_empty(
                    Role(
                        body=self.get_body(record[LEGISTAR_ROLE_BODY]),
                        # e.g. 2017-11-30T00:00:00
                        start_datetime=self.localize_datetime(
                            datetime.strptime(
                                record[LEGISTAR_ROLE_START],
                                LEGISTAR_DATETIME_FORMAT,
                            )
                        ),
                        end_datetime=self.localize_datetime(
                            datetime.strptime(
                                record[LEGISTAR_ROLE_END], LEGISTAR_DATETIME_FORMAT
                            )
                        ),
                        external_source_id=record[LEGISTAR_ROLE_EXT_ID],
                        title=str_simplified(record[LEGISTAR_ROLE_TITLE]),
                    )
                )
                for record in legistar_office_records
            ]
        )

    def get_person(self, legistar_person: Dict) -> Optional[Person]:
        """
        Return CDP Person for Legistar Person.

        Parameters
        ----------
        legistar_person: Dict
            Legistar API Person

        Returns
        -------
        person: Optional[Person]
            The Legistar Person converted to a CDP person ingestion model.
            None if missing information.

        See Also
        --------
        get_legistar_person()
        """
        if not legistar_person:
            return None

        phone = str_simplified(legistar_person[LEGISTAR_PERSON_PHONE])
        if phone:
            # (123)456... -> 123-456...
            phone = phone.replace("(", "").replace(")", "-")

        return self.get_none_if_empty(
            Person(
                email=str_simplified(legistar_person[LEGISTAR_PERSON_EMAIL]),
                external_source_id=legistar_person[LEGISTAR_PERSON_EXT_ID],
                name=str_simplified(legistar_person[LEGISTAR_PERSON_NAME]),
                phone=phone,
                website=str_simplified(legistar_person[LEGISTAR_PERSON_WEBSITE]),
                is_active=bool(legistar_person[LEGISTAR_PERSON_ACTIVE]),
                roles=self.get_roles(legistar_person[LEGISTAR_PERSON_ROLES]),
            )
        )

    def get_votes(self, legistar_votes: List[Dict]) -> Optional[List[Vote]]:
        """
        Return List[Vote] for Legistar API Votes.

        Parameters
        ----------
        legistar_votes: List[Dict]
            Legistar votes as CDP Vote ingestion models.

        Returns
        -------
        votes: Optional[List[Vote]]
            List of votes if any were provided.
            None if empty list or missing information.
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

    def get_event_supporting_files(
        self,
        legistar_ev_attachments: List[Dict],
    ) -> Optional[List[SupportingFile]]:
        """
        Return List[SupportingFile] for Legistar API MatterAttachments.

        Parameters
        ----------
        legistar_ev_attachments: List[Dict]
            Legistar API MatterAttachments

        Returns
        -------
        files: Optional[List[SupportingFile]]
            List of supporting files if provided.
            None if empty list or missing information.
        """
        return reduced_list(
            [
                self.get_none_if_empty(
                    SupportingFile(
                        external_source_id=attachment[LEGISTAR_FILE_EXT_ID],
                        name=str_simplified(attachment[LEGISTAR_FILE_NAME]),
                        uri=str_simplified(attachment[LEGISTAR_FILE_URI]),
                    )
                )
                for attachment in legistar_ev_attachments
            ]
        )

    def get_sponsors(self, legistar_sponsors: List[Dict]) -> Optional[List[Person]]:
        if not legistar_sponsors:
            return None

        return reduced_list(
            [
                self.get_person(
                    get_legistar_person(
                        client=self.client_name,
                        person_id=sponsor[LEGISTAR_SPONSOR_ID],
                        use_cache=True,
                    )
                )
                for sponsor in legistar_sponsors
            ]
        )

    def get_matter(self, legistar_ev: Dict) -> Optional[Matter]:
        """
        Return Matter from Legistar API EventItem.

        Parameters
        ----------
        legistar_ev: Dict
            Legistar API EventItem

        Returns
        -------
        matter: Optional[Matter]
            List of converted Legistar matter details to CDP matter objects.
            None if missing information.
        """
        return self.get_none_if_empty(
            Matter(
                external_source_id=legistar_ev[LEGISTAR_MATTER_EXT_ID],
                # Too often EventItemMatterName is not filled
                # but EventItemMatterFile is
                name=str_simplified(legistar_ev[LEGISTAR_MATTER_NAME])
                or str_simplified(legistar_ev[LEGISTAR_MATTER_TITLE]),
                matter_type=str_simplified(legistar_ev[LEGISTAR_MATTER_TYPE]),
                sponsors=self.get_sponsors(legistar_ev[LEGISTAR_MATTER_SPONSORS]),
                title=str_simplified(legistar_ev[LEGISTAR_MATTER_TITLE]),
                result_status=self.get_matter_status(
                    legistar_ev[LEGISTAR_MATTER_STATUS]
                ),
            )
        )

    def get_minutes_item(self, legistar_ev_item: Dict) -> Optional[MinutesItem]:
        """
        Return MinutesItem from parts of Legistar API EventItem.

        Parameters
        ----------
        legistar_ev_item: Dict
            Legistar API EventItem

        Returns
        -------
        minutes_item: Optional[MinutesItem]
            None if could not get nonempty MinutesItem.name from EventItem.
        """

        return self.get_none_if_empty(
            MinutesItem(
                external_source_id=legistar_ev_item[LEGISTAR_MINUTE_EXT_ID],
                name=str_simplified(legistar_ev_item[LEGISTAR_MINUTE_NAME]),
            )
        )

    def fix_event_minutes(
        self, ev_minutes_item: Optional[EventMinutesItem], legistar_ev_item: Dict
    ) -> Optional[EventMinutesItem]:
        """
        Inspect the MinutesItem and Matter in ev_minutes_item.
        - Move some fields between them to make the information more meaningful.
        - Enforce matter.result_status when appropriate.

        Parameters
        ----------
        ev_minutes_item: Optional[EventMinutesItem]
            The specific event minutes item to clean.
            Or None if running this function in a loop with multiple event minutes
            items and you don't want to clean / the emi was filtered out.
        legistar_ev_item: Dict
            The original Legistar EventItem.

        Returns
        -------
        cleaned_emi: Optional[EventMinutesItem]
            The cleaned event minutes item. This can clean both the event minutes item
            and the attached matter information.
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
    ) -> Optional[EventMinutesItem]:
        """
        Return None if minutes_item.name contains unimportant text
        that we want to ignore

        Parameters
        ----------
        ev_minutes_item: EventMinutesItem

        Returns
        -------
        filtered_event_minutes_items: Optional[EventMinutesItem]
            The allowed minutes item or None is filtered out.
        """
        if not ev_minutes_item.minutes_item or not ev_minutes_item.minutes_item.name:
            return ev_minutes_item
        for filter in self.ignore_minutes_item_patterns:
            if re.search(filter, ev_minutes_item.minutes_item.name, re.IGNORECASE):
                return None
        return ev_minutes_item

    def get_event_minutes(
        self, legistar_ev_items: List[Dict]
    ) -> Optional[List[EventMinutesItem]]:
        """
        Return List[EventMinutesItem] for Legistar API EventItems.

        Parameters
        ----------
        legistar_ev_items: List[Dict]
            Legistar API EventItems

        Returns
        -------
        event_minutes_items: Optional[List[EventMinutesItem]]
            Filtered set of event minutes items.
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
                                supporting_files=self.get_event_supporting_files(
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

    @staticmethod
    def find_time_zone() -> str:
        """
        Return name for a US time zone matching UTC offset calculated from OS clock.
        """
        utc_now = pytz.utc.localize(datetime.utcnow())
        local_now = datetime.now()

        for zone_name in pytz.country_timezones("us"):
            zone = pytz.timezone(zone_name)
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

    def localize_datetime(self, local_time: datetime) -> datetime:
        """
        Return input datetime with time zone information.
        This allows for nonambiguous conversions to other zones including UTC.

        Parameters
        ----------
        local_time: datetime
            The datetime to attached timezone information to.

        Returns
        -------
        local_time: datetime
            The date and time attributes (year, month, day, hour, ...) remain unchanged.
            tzinfo is now provided.
        """
        try:
            return self.timezone.localize(local_time)
        except (AttributeError, ValueError):
            # AttributeError: time_zone or local_time is None
            # ValueError: local_time is not navie (has time zone info)
            return local_time

    @staticmethod
    def date_and_time_to_datetime(ev_date: str, ev_time: Optional[str]) -> datetime:
        """
        Return datetime from ev_date and ev_time

        Parameters
        ----------
        ev_date: str
            Formatted as "%Y-%m-%dT%H:%M:%S"
        ev_time: Optional[str]
            Formatted as "%I:%M %p"
            Or None and do not attach time to date.

        Returns
        -------
        datetime
            date using ev_date and time using ev_time
        """
        # 2021-07-09T00:00:00
        d = datetime.strptime(ev_date, LEGISTAR_DATETIME_FORMAT)
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

    def get_content_uris(self, legistar_ev: Dict) -> List[ContentURIs]:
        """
        Must implement in class derived from LegistarScraper.
        If Legistar Event.EventVideoPath is used, return an empty list in the override.

        Parameters
        ----------
        legistar_ev: Dict
            Data for one Legistar Event.

        Returns
        -------
        event_content_uris: List[ContentURIs]
            List of ContentURIs objects for each session found.

        Raises
        ------
        NotImplementedError
            This base implementation does nothing

        See Also
        --------
        cdp_scrapers.legistar_utils.get_legistar_events_for_timespan
        """
        log.critical(
            "get_content_uris() is required because "
            f"Legistar Event.EventVideoPath is not used by {self.client_name}"
        )
        raise NotImplementedError

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
        begin: datetime, optional
            The timespan beginning datetime to query for events after.
            Default is 2 days from UTC now
        end: datetime, optional
            The timespan end datetime to query for events before.
            Default is UTC now

        Returns
        -------
        events: List[EventIngestionModel]
            One instance of EventIngestionModel per Legistar Event

        See Also
        --------
        cdp_scrapers.legistar_utils.get_legistar_events_for_timespan
        """
        if begin is None:
            begin = datetime.utcnow() - timedelta(days=2)
        if end is None:
            end = datetime.utcnow()

        ingestion_models = []

        for legistar_ev in get_legistar_events_for_timespan(
            self.client_name, begin=begin, end=end
        ):
            # better to return time as local time with time zone info,
            # rather than as utc time.
            # this way the calling pipeline can find out what is the local zone.
            session_time = self.localize_datetime(
                self.date_and_time_to_datetime(
                    legistar_ev[LEGISTAR_SESSION_DATE],
                    legistar_ev[LEGISTAR_SESSION_TIME],
                )
            )
            # prefer video file path in legistar Event.EventVideoPath
            if legistar_ev[LEGISTAR_SESSION_VIDEO_URI]:
                list_uri = [
                    ContentURIs(
                        video_uri=str_simplified(
                            legistar_ev[LEGISTAR_SESSION_VIDEO_URI]
                        ),
                        caption_uri=None,
                    )
                ]
            else:
                list_uri = self.get_content_uris(legistar_ev) or [
                    ContentURIs(video_uri=None, caption_uri=None)
                ]

            sessions = []
            sessions = reduced_list(
                [
                    self.get_none_if_empty(
                        Session(
                            session_datetime=session_time,
                            session_index=len(sessions),
                            video_uri=content_uris.video_uri,
                            caption_uri=content_uris.caption_uri,
                        )
                    )
                    # Session per video
                    for content_uris in list_uri
                ]
            )
            ingestion_models.append(
                self.get_none_if_empty(
                    EventIngestionModel(
                        external_source_id=legistar_ev[LEGISTAR_EV_EXT_ID],
                        agenda_uri=str_simplified(legistar_ev[LEGISTAR_AGENDA_URI]),
                        minutes_uri=str_simplified(legistar_ev[LEGISTAR_MINUTES_URI]),
                        sessions=sessions,
                        event_minutes_items=self.get_event_minutes(
                            legistar_ev[LEGISTAR_EV_ITEMS]
                        ),
                        body=self.get_body(legistar_ev[LEGISTAR_EV_BODY]),
                    )
                )
            )

        # easier for calling pipeline to handle an empty list rather than None
        # so request reduced_list() to give me [], not None
        return reduced_list(ingestion_models, collapse=False)

    @property
    def is_legistar_compatible(self) -> bool:
        """
        Check that Legistar API recognizes client name.

        Returns
        -------
        compatible: bool
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
        check_days: int, default=7
            Test duration is the past check_days days from now

        Returns
        -------
        minimum_ingestion_data_available: bool
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
