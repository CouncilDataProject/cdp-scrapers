from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from datetime import datetime, timedelta
from itertools import chain, filterfalse, groupby
from logging import getLogger
from pathlib import Path
from typing import Any, NamedTuple

import cleantext
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

from .types import PersonsComparison, ScraperStaticData

###############################################################################

log = getLogger(__name__)

###############################################################################


def reduced_list(input_list: list[Any], collapse: bool = True) -> list | None:
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
        The string to be cleaned.

    Returns
    -------
    cleaned: str
        input_str stripped if it is a string
    """
    if not isinstance(input_str, str):
        return input_str

    input_str = cleantext.clean(
        input_str, fix_unicode=True, lower=False, to_ascii=False
    )

    # Replace utf-8 char encodings with single utf-8 chars themselves
    input_str = input_str.encode("utf-8").decode("utf-8")

    return input_str


def parse_static_person(  # noqa: C901
    person_json: dict[str, Any],
    all_seats: dict[str, Seat],
    primary_bodies: dict[str, Body],
    timezone: pytz.timezone,
) -> Person:
    """
    Parse Dict[str, Any] for a person in static data file to a Person instance.
    person_json["seat"] and person_json["roles"] are validated against
    all_seats and primary_bodies in static data file.

    Parameters
    ----------
    person_json: Dict[str, Any]
        A dictionary in static data file with info for a Person.

    all_seats: Dict[str, Seat]
        Seats defined as top-level in static data file

    primary_bodies: Dict[str, Body]
        Bodies defined as top-level in static data file.

    timezone: str
        The timezone for the target client.
        i.e. "America/Los_Angeles" or "America/New_York"
        See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones for canonical
        timezones.

    See Also
    --------
    parse_static_file
    sanitize_roles
    """
    log.debug(f"Begin parsing static data for {person_json['name']}")

    # "seat" and "roles" are not direct serializations of Seat/Role
    kwargs = {k: v for k, v in person_json.items() if k != "seat" and k != "roles"}
    person: Person = Person(**kwargs)
    if "seat" not in person_json:
        log.debug("Seat name not given")
        return person

    seat_name: str = person_json["seat"]
    if seat_name not in all_seats:
        log.error(f"{seat_name} is not defined in top-level 'seats'")
        return person

    # Keep all_seats unmodified; we will append Roles to this person.seat below
    person.seat = deepcopy(all_seats[seat_name])
    if "roles" not in person_json:
        log.debug("Roles not given")
        return person

    # Role.title must be a RoleTitle constant so get all allowed values
    role_titles: list[str] = get_all_class_attr_values(RoleTitle)
    for role_json in person_json["roles"]:
        if (
            # if str, it is looked-up in primary_bodies
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
            kwargs = {k: v for k, v in role_json.items() if k != "body"}
            try:
                log.debug(f"{kwargs} -> {Role.from_dict(kwargs)}")
            except Exception:
                pass
            else:
                log.info(f"We can resume using from_dict ({sys.version_info})")

            dt_val = kwargs.get("start_datetime")
            kwargs["start_datetime"] = (
                dt_val
                if dt_val is None
                else timezone.localize(datetime.fromtimestamp(dt_val))
            )
            dt_val = kwargs.get("end_datetime")
            kwargs["end_datetime"] = (
                dt_val
                if dt_val is None
                else timezone.localize(datetime.fromtimestamp(dt_val))
            )

            role: Role = Role(**kwargs)
            if isinstance(role_json["body"], str):
                role.body = primary_bodies[role_json["body"]]
            else:
                # This role.body is a dictionary and defines a non-primary one
                # e.g. like a committee such as Transportation
                # that is not the main/full council
                kwargs = role_json["body"]
                role.body = Body(**kwargs)

            if person.seat.roles is None:
                person.seat.roles = [role]
            else:
                person.seat.roles.append(role)

    return person


def parse_static_file(file_path: Path, timezone: str) -> ScraperStaticData:
    """
    Parse Seats, Bodies and Persons from static data JSON.

    Parameters
    ----------
    file_path: Path
        Path to file containing static data in JSON

    timezone: str
        The timezone for the target client.
        i.e. "America/Los_Angeles" or "America/New_York"
        See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones for canonical
        timezones.

    Returns
    -------
    ScraperStaticData:
        Tuple[Dict[str, Seat], Dict[str, Body], Dict[str, Person]]

    See Also
    --------
    parse_static_person
    sanitize_roles

    Notes
    -----
    Function looks for "seats", "primary_bodies", "persons" top-level keys
    """
    with open(file_path) as static_file:
        static_json: dict[str, dict[str, Any]] = json.load(static_file)

        if "seats" not in static_json:
            seats: dict[str, Seat] = {}
        else:
            seats: dict[str, Seat] = {
                seat_name: Seat(**seat)
                for seat_name, seat in static_json["seats"].items()
            }

        if "primary_bodies" not in static_json:
            primary_bodies: dict[str, Body] = {}
        else:
            primary_bodies: dict[str, Body] = {
                body_name: Body(**body)
                for body_name, body in static_json["primary_bodies"].items()
            }

        if "persons" not in static_json:
            known_persons: dict[str, Person] = {}
        else:
            timezone = pytz.timezone(timezone)
            known_persons: dict[str, Person] = {
                person_name: parse_static_person(
                    person, seats, primary_bodies, timezone
                )
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


def sanitize_roles(  # noqa: C901
    person_name: str,
    roles: list[Role] | None = None,
    static_data: ScraperStaticData | None = None,
    council_pres_patterns: list[str] | None = None,
    chair_patterns: list[str] | None = None,
) -> list[Role] | None:
    """
    1. Standardize roles[i].title to RoleTitle constants
    2. Ensure only 1 councilmember Role per term.

    Parameters
    ----------
    person_name: str
        Sanitization target Person.name

    roles: Optional[List[Role]] = None
        target Person's Roles to sanitize

    static_data: Optional[ScraperStaticData]
        Static data defining primary council bodies and predefined Person.seat.roles.
        See Notes.

    council_pres_patterns: List[str]
        Set roles[i].title as "Council President" if match
        and roles[i].body is a primary body like City Council
    chair_patterns: List[str]
        Set roles[i].title as "Chair" if match
        and roles[i].body is not a primary body

    Notes
    -----
    Remove roles[#] if roles[#].body in static_data.primary_bodies.
    Use static_data.persons[#].seat.roles instead.

    If roles[i].body not in static_data.primary_bodies,
    roles[i].title cannot be "Councilmember" or "Council President".

    Use "City Council" and "Council Briefing"
    if static_data.primary_bodies is empty.
    """
    if roles is None:
        roles = []
    if council_pres_patterns is None:
        council_pres_patterns = ["chair", "pres", "super"]
    if chair_patterns is None:
        chair_patterns = ["chair", "pres"]

    if not static_data or not static_data.primary_bodies:
        # Primary/full council not defined in static data file.
        # these are reasonably good defaults for most municipalities.
        primary_body_names = ["city council", "council briefing"]
    else:
        primary_body_names = [
            body_name.lower() for body_name in static_data.primary_bodies.keys()
        ]

    try:
        have_primary_roles = len(static_data.persons[person_name].seat.roles) > 0
    except (KeyError, AttributeError, TypeError):
        have_primary_roles = False

    def _is_role_period_ok(role: Role) -> bool:
        """Test that role.[start | end]_datetime is acceptable."""
        if role.start_datetime is None or role.end_datetime is None:
            return False
        if not have_primary_roles:
            # no roles in static data; accept if this this role is current
            return role.start_datetime.astimezone(
                pytz.utc
            ) <= datetime.today().astimezone(pytz.utc) and datetime.today().astimezone(
                pytz.utc
            ) <= role.end_datetime.astimezone(
                pytz.utc
            )
        # accept if role coincides with one given in static data
        for static_role in static_data.persons[person_name].seat.roles:
            if (
                static_role.start_datetime <= role.start_datetime
                and role.end_datetime <= static_role.end_datetime
            ):
                return True
        return False

    def _is_primary_body(role: Role) -> bool:
        """Is role.body one of primary_bodies in static data file."""
        return (
            role.body is not None
            and role.body.name is not None
            and str_simplified(role.body.name).lower() in primary_body_names
        )

    def _fix_primary_title(role: Role) -> str:
        """Council president or Councilmember."""
        if (
            role.title is None
            or re.search(
                "|".join(council_pres_patterns), str_simplified(role.title), re.I
            )
            is None
        ):
            return RoleTitle.COUNCILMEMBER
        return RoleTitle.COUNCILPRESIDENT

    def _fix_nonprimary_title(role: Role) -> str:
        """Not council president or councilmember."""
        if role.title is None:
            return RoleTitle.MEMBER

        role_title = str_simplified(role.title).lower()
        # Role is not for a primary/full council
        # Role.title cannot be Councilmember or Council President
        if "vice" in role_title:
            return RoleTitle.VICE_CHAIR
        if "alt" in role_title:
            return RoleTitle.ALTERNATE
        if "super" in role_title:
            return RoleTitle.SUPERVISOR
        if re.search("|".join(chair_patterns), role_title, re.I) is not None:
            return RoleTitle.CHAIR
        return RoleTitle.MEMBER

    def _is_councilmember_term(role: Role) -> bool:
        return (
            role.title == RoleTitle.COUNCILMEMBER
            and role.start_datetime is not None
            and role.end_datetime is not None
        )

    roles = list(
        # drop dynamically scraped primary roles
        # if primary roles are given in static data
        filterfalse(
            lambda role: have_primary_roles and _is_primary_body(role),
            # filter out bad start_datetime, end_datetime
            filter(_is_role_period_ok, roles),
        )
    )
    # standardize titles
    for role in filter(_is_primary_body, roles):
        role.title = _fix_primary_title(role)
    for role in filterfalse(_is_primary_body, roles):
        role.title = _fix_nonprimary_title(role)

    class CouncilMemberTerm(NamedTuple):
        start_datetime: datetime
        end_datetime: datetime
        index_in_roles: int

    # when checking for overlapping terms, we should do so per body.
    # e.g. simultaneous councilmember roles in city council and in council briefing
    # are completely acceptable and common.

    scraped_member_roles_by_body: list[list[Role]] = [
        list(roles_for_body)
        for body_name, roles_for_body in groupby(
            sorted(
                filter(
                    # get all dynamically scraped councilmember terms
                    lambda role: not have_primary_roles
                    and _is_councilmember_term(role),
                    roles,
                ),
                # sort from old to new role
                key=lambda role: (
                    role.body.name,
                    role.start_datetime,
                    role.end_datetime,
                ),
            ),
            # group by body
            key=lambda role: role.body.name,
        )
    ]

    if have_primary_roles:
        # don't forget to include info from the static data file
        roles.extend(static_data.persons[person_name].seat.roles)
    if len(scraped_member_roles_by_body) == 0:
        # no Councilmember roles dynamically scraped
        # nothing more to do
        return roles

    for roles_for_body in scraped_member_roles_by_body:
        for i in [i for i, role in enumerate(roles_for_body) if i > 0]:
            prev_role = roles_for_body[i - 1]
            this_role = roles_for_body[i]
            # if member role i overlaps with member role j, end i before j
            if prev_role.end_datetime > this_role.start_datetime:
                roles[
                    roles.index(prev_role)
                ].end_datetime = this_role.start_datetime - timedelta(days=1)

    return roles


def extract_persons(events):
    """
    Get all sponsors and voters across all events.

    Parameters
    ----------
    events: list[EventIngestionModel]
        Scraped events

    Returns
    -------
    list[Person]
        Unique list of all sponsors and voters found
    """

    def extract_sponsors(event_item):
        sponsors = event_item.matter.sponsors if event_item.matter else []
        sponsors = sponsors or []
        sponsors = reduced_list(sponsors, collapse=False)
        return sponsors

    def extract_voters(event_item):
        votes = event_item.votes or []
        voters = [v.person for v in votes]
        voters = reduced_list(voters, collapse=False)
        return voters

    events = reduced_list(events, collapse=False)
    items = [e.event_minutes_items or [] for e in events]
    items = chain.from_iterable(items)
    items = reduced_list(items, collapse=False)

    sponsors = map(extract_sponsors, items)
    sponsors = chain.from_iterable(sponsors)
    voters = map(extract_voters, items)
    voters = chain.from_iterable(voters)

    persons = chain(sponsors, voters)
    persons = {p.name: p for p in persons}
    persons = list(persons.values())
    return persons


def compare_persons(
    scraped_persons, known_persons, primary_bodies
) -> PersonsComparison:
    """
    Look for old and new councilmembers.

    Parameters
    ----------
    scraped_persons: list[Person]
        e.g. from extract_persons
    known_persons: list[Person]
        e.g. from ScraperStaticData
    primary_bodies: list[Body]
        e.g. from ScraperStaticData

    Returns
    -------
    PersonsComparison
        Old and new councilmember names
    """

    def holds_primary_role(person):
        roles = person.seat.roles if person.seat and person.seat.roles else []
        active_roles = filter(
            lambda r: r.end_datetime is None
            or datetime.today().date() <= r.end_datetime.date(),
            roles,
        )

        body_names = [r.body.name if r.body else None for r in active_roles]
        body_names = reduced_list(body_names, collapse=False)
        primary_body_names = filter(lambda b: b.name in body_names, primary_bodies)
        return any(primary_body_names)

    active_persons = list(filter(lambda p: p and p.is_active, scraped_persons))
    primary_persons = list(filter(holds_primary_role, active_persons))
    names = {p.name for p in primary_persons}

    known_names = {p.name for p in known_persons}
    old_names = list(known_names - names)
    new_names = list(names - known_names)
    return PersonsComparison(old_names, new_names)


class IngestionModelScraper:
    """
    Base class for events scrapers providing IngestionModels for cdp-backend pipeline.

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
        person_aliases: dict[str, set[str]] | None = None,
    ):
        self.timezone: pytz.timezone = pytz.timezone(timezone)
        self.person_aliases = person_aliases

    @staticmethod
    def find_time_zone() -> str:
        """
        Return name for a US time zone matching UTC
        offset calculated from OS clock.
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
    def get_required_attrs(model: IngestionModel) -> list[str]:
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

    def get_none_if_empty(self, model: IngestionModel) -> IngestionModel | None:
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

    def handle_old_new_council(
        self, old_names: list[str], new_names: list[str]
    ) -> None:
        """
        Override to handle old and new councilmember information.

        Parameters
        ----------
        old_names: list[str]
            e.g. from scraper_utils.compare_persons
        new_names: list[str]
            e.g. from scraper_utils.compare_persons

        Notes
        -----
        Base implementation simply logs
        """
        if any(old_names):
            log.info(f"{old_names} are no longer found in scraped data")
        if any(new_names):
            log.warning(f"{new_names} are new. Update self.static_data.persons.")
