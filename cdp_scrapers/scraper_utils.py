import logging
import re
from typing import Any, List, Optional

from cdp_backend.pipeline.ingestion_models import IngestionModel

###############################################################################

log = logging.getLogger(__name__)

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


class IngestionModelScraper:
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
