import logging
import re
import unicodedata
from datetime import datetime
from metaphone import doublemetaphone
from thefuzz import fuzz
from typing import Any, List, Optional, Set
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import pytz
from bs4 import BeautifulSoup
from cdp_backend.pipeline.ingestion_models import IngestionModel

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

# fuzzy matching must score greater than or equal to this number
# to be decided as being aliases of each other
NAME_ALIAS_THRESHOLD = 90

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


def name_variants(name: str) -> Set[str]:
    name = name.lower()
    try:
        # this web page lists most name variations
        # e.g. querying with Tom returns names like Tomas, Thomas
        with urlopen(f"https://www.behindthename.com/name/{name}/related") as resp:
            soup = BeautifulSoup(resp.read(), "html.parser")
    except URLError or HTTPError:
        if not re.search(r"-\d+$", name):
            # try e.g. tom-1 for tom
            return name_variants(f"{name}-1")
        return set()

    # all such <a> tags
    # <a href="/name/thomas" class="nlc">Thomas</a>
    full_forms = set([i.string for i in soup.find_all("a", class_="nlc")])
    if not full_forms:
        # found no names; probably because name (tom) needs further specifications
        # like tom-1 (English) and tom-2 (Hebrew).
        # see if there is <a> tag like
        # <a href="/name/tom-1/related" class="nll">
        if soup.find("a", class_="nll", href=re.compile(f".*{name}-\\d+.*")):
            # e.g. try tom-1
            return name_variants(f"{name}-1")

    trail_num = re.search(r"-(\d+)$", name)
    if not trail_num:
        return full_forms

    # we queried something like tom-1, try tom-2
    return full_forms | name_variants(
        f"{name[:trail_num.start(1)]}{int(trail_num.group(1)) + 1}"
    )


def alphabets_only(input_str: str) -> str:
    # clean up whitespace
    return str_simplified(
        re.sub(
            # no punctuations, numbers, etc.
            r"[^a-zA-Z\s]",
            "",
            # canonical unicode
            unicodedata.normalize("NFKC", input_str)
            # drop all non-ascii chars
            .encode("ascii", "ignore").decode("ascii")
        )
    )


def is_same_person(name: str, query_name: str) -> bool:
    # for better fuzzy logic, keep just lowercase alphabets and single whitespaces
    name = alphabets_only(name).lower()
    query_name = alphabets_only(query_name).lower()

    # don't waste time if obvious
    if name == query_name:
        return True
    if len(name) == 0 or len(query_name) == 0:
        return False

    # can't always use the first substring as first name
    # e.g. first_initial middle_name last_name
    name_parts = name.split()
    for i in range(len(name_parts)):
        if len(name_parts[i]) < 2:
            # not going to do anything with initials
            continue
        # Bob, Bobby, Robert, ...
        for part_variant in (name_variants(name_parts[i]) | set([name_parts[i]])):
            # deep copy so we keep name_parts untouched
            name_variant = list(name_parts)
            # ["Bob", "Doe"] -> ["Bobby", "Doe"]
            name_variant[i] = part_variant
            # ["Bobby", "Doe"] -> "Bobby Doe"
            name_variant = " ".join(name_variant)

            if (
                fuzz.token_sort_ratio(name_variant, query_name)
                >= NAME_ALIAS_THRESHOLD
            ):
                return True

            # try comparing pronunciations
            # but sort to take care of sitautions like first, last and last, first
            syllables = doublemetaphone("".join(sorted(name_variant.split())))
            query_syllables = doublemetaphone("".join(sorted(query_name.split())))
            if (
                # primary == primary -> best
                syllables[0] == query_syllables[0]
                # primary == secondary -> good
                or syllables[0] == query_syllables[1]
                or syllables[1] == query_syllables[0]
            ):
                return True

    return False


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
    """

    def __init__(
        self,
        timezone: str,
    ):
        self.timezone: pytz.timezone = pytz.timezone(timezone)

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
