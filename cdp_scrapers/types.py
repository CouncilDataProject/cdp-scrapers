#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Dict, NamedTuple, Optional
from cdp_backend.pipeline.ingestion_models import (
    Body,
    Person,
    Seat,
)

###############################################################################


class ContentURIs(NamedTuple):
    video_uri: Optional[str]
    caption_uri: Optional[str] = None


class ScraperStaticData(NamedTuple):
    seats: Dict[str, Seat] = None
    primary_bodies: Dict[str, Body] = None
    persons: Dict[str, Person] = None
