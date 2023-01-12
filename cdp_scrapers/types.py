#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import Callable, Dict, List, NamedTuple, Optional

from bs4 import BeautifulSoup
from cdp_backend.pipeline.ingestion_models import Body, Person, Seat
from dataclasses_json import dataclass_json

###############################################################################


class ContentURIs(NamedTuple):
    video_uri: Optional[str]
    caption_uri: Optional[str] = None


@dataclass_json
@dataclass
class ScraperStaticData:
    seats: Dict[str, Seat] = None
    primary_bodies: Dict[str, Body] = None
    persons: Dict[str, Person] = None


LegistarContentParser = Callable[[str, BeautifulSoup], Optional[List[ContentURIs]]]
"""
Function that returns URLs for videos and captions
from a Legistar/Granicus-hosted video web page

Parameters
----------
client: str
    Which legistar client to target. Ex: "seattle"
video web page: BeautifulSoup
    Video web page loaded into bs4

Returns
-------
uris: Optional[List[ContentURIs]]
    URIs for video and optional caption

See Also
--------
cdp_scrapers.legistar_content_parsers
cdp_scrapers.legistar_utils.get_legistar_content_uris()
"""
