import json
import re
from copy import deepcopy
from datetime import datetime, timedelta
from logging import getLogger
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Set

import pytz
from cdp_backend.database.constants import RoleTitle
from cdp_backend.pipeline.ingestion_models import (
    Body,
    IngestionModel,
    Person,
    Role,
    Seat,
)
from cdp_backend.utils.constants_utils import get_all_class_attr_values
from .types import ScraperStaticData

###############################################################################

log = getLogger(__name__)

###############################################################################


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


def parse_static_person(
    person_json: Dict[str, Any],
    all_seats: Dict[str, Seat],
    primary_bodies: Dict[str, Body],
) -> Person:
    log.debug(f"Begin parsing static data for {person_json['name']}")

    person: Person = Person.from_dict(
        {k: v for k, v in person_json.items() if k != "seat" and k != "roles"}
    )
    if "seat" not in person_json:
        log.debug("Seat name not given")
        return person

    seat_name: str = person_json["seat"]
    if seat_name not in all_seats:
        log.error(f"{seat_name} is not defined in top-level 'seats'")
        return person

    person.seat = deepcopy(all_seats[seat_name])
    if "roles" not in person_json:
        log.debug("Roles not given")
        return person

    role_titles: List[str] = get_all_class_attr_values(RoleTitle)
    person.seat.roles = []

    for role_json in person_json["roles"]:
        if (
            isinstance(role_json["body"], str)
            and role_json["body"] not in primary_bodies
        ):
            log.error(
                f"{role_json} is ignored. "
                f"{role_json['body']} is not defined in top-level 'primary_bodies'"
            )
        elif role_json["title"] not in role_titles:
            log.error(
                f"{role_json} is ignored. "
                f"{role_json['title']} is not a RoleTitle constant."
            )
        else:
            role: Role = Role.from_dict(
                {k: v for k, v in role_json.items() if k != "body"}
            )
            if isinstance(role_json["body"], str):
                role.body = primary_bodies[role_json["body"]]
            else:
                role.body = Body.from_dict(role_json["body"])

            person.seat.roles.append(role)

    return person


def parse_static_file(file_path: Path) -> ScraperStaticData:
    with open(file_path) as static_file:
        static_json: Dict[str, Dict[str, Any]] = json.load(static_file)

        if "seats" not in static_json:
            seats: Dict[str, Seat] = {}
        else:
            seats: Dict[str, Seat] = {
                seat_name: Seat.from_dict(seat)
                for seat_name, seat in static_json["seats"].items()
            }

        if "primary_bodies" not in static_json:
            primary_bodies: Dict[str, Body] = {}
        else:
            primary_bodies: Dict[str, Body] = {
                body_name: Body.from_dict(body)
                for body_name, body in static_json["primary_bodies"].items()
            }

        if "persons" not in static_json:
            known_persons: Dict[str, Person] = {}
        else:
            known_persons: Dict[str, Person] = {
                person_name: parse_static_person(person, seats, primary_bodies)
                for person_name, person in static_json["persons"].items()
            }

        log.debug(
            f"ScraperStaticData parsed from {file_path}:\n"
            f"    seats: {list(seats.keys())}\n"
            f"    primary_bodies: {list(primary_bodies.keys())}\n"
            f"    persons: {list(known_persons.keys())}\n"
        )
        return ScraperStaticData(
            seats=seats, primary_bodies=primary_bodies, persons=known_persons
        )


def sanitize_roles(
    person_name: str,
    roles: Optional[List[Role]] = None,
    known_static_data: Optional[ScraperStaticData] = None,
    president_patterns: List[str] = ["chair", "pres", "super"],
) -> Optional[List[Role]]:
    """
    1. Standardize roles[i].title to RoleTitle constants
    2. Ensure only 1 councilmember Role per term

    Parameters
    ----------
    person_name: str
        Sanitization target Person.name

    roles: Optional[List[Role]] = None
        target Person's Roles to sanitize

    known_static_data: Optional[ScraperStaticData]
        Static data defining primary council bodies and predefined Person.seat.roles.
        See Notes.

    president_patterns: List[str]
        roles[i].title = "Council President" or "Chair" if match

    Notes
    -----
    Remove roles[#] if roles[#].body in static_data.primary_bodies.
    Use known_static_data.persons[#].seat.roles instead.

    If roles[i].body not in static_data.primary_bodies,
    roles[i].title cannot be "Councilmember" or "Council President".

    Use "City Council" and "Council Briefing"
    if known_static_data.primary_bodies is empty.
    """
    if roles is None:
        roles = []

    if not known_static_data or not known_static_data.primary_bodies:
        primary_body_names = ["city council", "city briefing"]
    else:
        primary_body_names = [
            body_name.lower() for body_name in known_static_data.primary_bodies.keys()
        ]

    try:
        have_primary_roles = len(known_static_data.persons[person_name].seat.roles) > 0
    except (KeyError, AttributeError, TypeError):
        have_primary_roles = False

    class CouncilMemberTerm(NamedTuple):
        start_datetime: datetime
        end_datetime: datetime
        roles_index: int

    terms: List[CouncilMemberTerm] = []

    for i, role in enumerate(roles):
        role_title = str_simplified(role.title).lower()

        if (
            role.body is not None
            and role.body.name is not None
            and str_simplified(role.body.name).lower() in primary_body_names
        ):
            if have_primary_roles:
                roles[i] = None
            elif re.search("|".join(president_patterns), role_title, re.I) is not None:
                role.title = RoleTitle.COUNCILPRESIDENT
            else:
                role.title = RoleTitle.COUNCILMEMBER
                # get all councilmember terms
                if role.start_datetime is not None and role.end_datetime is not None:
                    terms.append(
                        CouncilMemberTerm(role.start_datetime, role.end_datetime, i)
                    )
        elif "vice" in role_title:
            role.title = RoleTitle.VICE_CHAIR
        elif re.search("|".join(president_patterns), role_title, re.I) is not None:
            role.title = RoleTitle.CHAIR
        elif "alt" in role_title:
            role.title = RoleTitle.ALTERNATE
        else:
            role.title = RoleTitle.MEMBER

    if have_primary_roles:
        roles.extend(known_static_data.persons[person_name].seat.roles)
    if len(terms) == 0:
        return reduced_list(roles)

    # sort in asc order of start_datetime and end_datetime.
    terms.sort()
    # if term i overlaps with term j, end term i before term j
    for i, term in enumerate(terms[:-1]):
        if terms[i].end_datetime > terms[i + 1].start_datetime:
            # reflect adjusted role end date in the actual roles list
            roles[terms[i].roles_index].end_datetime = terms[
                i + 1
            ].start_datetime - timedelta(days=1)

    return reduced_list(roles)


class IngestionModelScraper:
    """
    Base class for events scrapers providing IngestionModels for cdp-backend pipeline

    Parameters
    ----------
    timezone: str
        The timezone for the target client.
        i.e. "America/Los_Angeles" or "America/New_York"
        See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones for canonical
        timezones.
    person_aliases: Optional[Dict[str, Set[str]]]
        Dictionary used to catch name aliases
        and resolve improperly different Persons to the one correct Person.
        Default: None
    """

    def __init__(
        self,
        timezone: str,
        person_aliases: Optional[Dict[str, Set[str]]] = None,
    ):
        self.timezone: pytz.timezone = pytz.timezone(timezone)
        self.person_aliases = person_aliases

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
            min_keys = IngestionModelScraper.get_required_attrs(model)
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

    def resolve_person_alias(self, person: Person) -> Person:
        """
        If input person is in fact an alias of a reference known person,
        return the reference person instead.
        Else return person as-is.

        Parameters
        ----------
        person: Person
            Person to check whether is an alias or a real unique Person

        Returns
        -------
        Person
            input person, or the correct reference Person if input person is an alias.
            This base implementation always returns person as-is.

        See Also
        --------
        instances.seattle.person_aliases
        """
        return person
