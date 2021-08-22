#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import NamedTuple, Optional

###############################################################################


class ContentURIs(NamedTuple):
    video_uri: Optional[str]
    caption_uri: Optional[str] = None
