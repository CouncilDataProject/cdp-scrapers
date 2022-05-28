#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
from typing import Optional, List
from urllib.parse import unquote
from urllib.request import urlopen
from defusedxml import ElementTree
import re

from .types import ContentURIs, LegistarContentParser
from .scraper_utils import str_simplified


def _parse_format_1(client: str, soup: BeautifulSoup) -> Optional[List[ContentURIs]]:
    """
    Works for milwaukee, kingcounty, phoenix

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
    cdp_scrapers.types.LegistarContentParser
    cdp_scrapers.legistar_utils.get_legistar_content_uris()
    """
    # source link for the video is embedded in the script of downloadLinks.
    # <script type="text/javascript">
    # var meta_id = '',
    # currentClipIndex = 0,
    # clipList = eval([8844]),
    # downloadLinks = eval([["\/\/69.5.90.100:443\/MediaVault\/Download.aspx?
    # server=king.granicus.com&clip_id=8844",
    # "http:\/\/archive-media.granicus.com:443\/OnDemand\/king\/king_e560cf63-5570-416e-a47d-0e1e13652224.mp4",null]]);
    # </script>

    video_script_text = soup.find("script", text=re.compile(r"downloadLinks"))
    if video_script_text is None:
        return None

    video_script_text = video_script_text.string
    # Below two lines of code tries to extract video url from downLoadLinks variable
    # "http:\/\/archive-media.granicus.com:443\/OnDemand\/king\/king_e560cf63-5570-416e-a47d-0e1e13652224.mp4"
    try:
        downloadLinks = video_script_text.split("[[")[1]
        video_url = downloadLinks.split('",')[1].strip('"')
    except IndexError:
        # split() did not yield expected # items
        return None
    # Cleans up the video url to remove backward slash(\)
    video_uri = video_url.replace("\\", "")
    # caption URIs are not found for kingcounty events.
    return [ContentURIs(video_uri=video_uri, caption_uri=None)]


def _parse_format_2(client: str, soup: BeautifulSoup) -> Optional[List[ContentURIs]]:
    """
    Works for denver

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
    cdp_scrapers.types.LegistarContentParser
    cdp_scrapers.legistar_utils.get_legistar_content_uris()
    """
    # <div id="download-options">
    # <a href="...mp4">
    video_url = soup.find("div", id="download-options")
    if video_url is None:
        return None
    return [ContentURIs(str_simplified(video_url.a["href"]))]


def _parse_format_3(client: str, soup: BeautifulSoup) -> Optional[List[ContentURIs]]:
    """
    Works for boston, corpuschristi, elpasotexas

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
    cdp_scrapers.types.LegistarContentParser
    cdp_scrapers.legistar_utils.get_legistar_content_uris()
    """
    # <video>
    # <source src="...">
    # <track src="...">
    video_url = soup.find("video")
    if video_url is None:
        return None
    return [
        ContentURIs(
            video_uri=f"https:{str_simplified(video_url.source['src'])}",
            caption_uri=(
                (
                    f"http://{client}.granicus.com/"
                    f"{str_simplified(video_url.track['src'])}"
                )
                # transcript is nice to have but not required
                if video_url.find("track") is not None
                and "src" in video_url.track.attrs
                else None
            ),
        )
    ]


def _parse_format_4(client: str, soup: BeautifulSoup) -> Optional[List[ContentURIs]]:
    """
    Works for longbeach, richmondva

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
    cdp_scrapers.types.LegistarContentParser
    cdp_scrapers.legistar_utils.get_legistar_content_uris()
    """
    # a long <meta content="...VideoUrl=...&..." />
    url_regex = re.compile("VideoUrl=([^&]+)")
    # TODO: Also constains ScriptURL but appears to be invalid.
    # Double-check against more events; scrape if we can.
    player_meta = soup.find("meta", property="og:video", content=url_regex)
    if not player_meta:
        return None
    video_url = f"https:{unquote(url_regex.search(player_meta['content']).group(1))}"
    # this makes the server return an xml-like asx
    # NOTE: changing query from rtmp to http makes it return the video url
    #       in http as opposed to rtmp, e.g. rtmp://...mp4 -> http://...mp4
    video_url = video_url.replace("stream_type=rtmp", "stream_type=http")

    with urlopen(video_url) as resp:
        asx = ElementTree.fromstring(resp.read())
        # one and only one <REF HREF="http://...mp4" />
        ref_tag = asx.find(".//REF")
        return [ContentURIs(ref_tag.get("HREF"))] if ref_tag is not None else None


# TODO: do dynamically using inspect or something similar
all_parsers: List[LegistarContentParser] = [
    _parse_format_1,
    _parse_format_2,
    _parse_format_3,
    _parse_format_4,
]
