#!/usr/bin/env python

from datetime import datetime
from itertools import chain

import pytest

from cdp_scrapers.youtube_utils import (
    YoutubeIngestionScraper,
    get_video_info,
    urljoin_search_query,
)


@pytest.mark.parametrize(
    "channel, search_terms, begin, end, expected_url",
    [
        (
            "BellevueTelevision",
            "city council meeting",
            datetime(2023, 2, 5),
            datetime(2023, 2, 10),
            (
                "https://www.youtube.com/@BellevueTelevision/"
                "search?query=city+council+meeting+"
                "after%3A2023-02-05+before%3A2023-02-10"
            ),
        ),
        (
            "BellevueTelevision",
            "city council meeting",
            datetime(2023, 2, 5),
            None,
            (
                "https://www.youtube.com/@BellevueTelevision/"
                "search?query=city+council+meeting+after%3A2023-02-05"
            ),
        ),
        (
            "BellevueTelevision",
            "city council meeting",
            None,
            datetime(2023, 2, 10),
            (
                "https://www.youtube.com/@BellevueTelevision/"
                "search?query=city+council+meeting+before%3A2023-02-10"
            ),
        ),
        ("BellevueTelevision", "city council meeting", None, None, None),
    ],
)
def test_search_url(channel, search_terms, begin, end, expected_url):
    try:
        query_url = urljoin_search_query(
            channel_name=channel, search_terms=search_terms, begin=begin, end=end
        )
    except ValueError:
        query_url = None

    assert query_url == expected_url


# @pytest.mark.parametrize(
#     "query_url, video_ids",
#     [
#         (
#             (
#                 "https://www.youtube.com/@BellevueTelevision/"
#                 "search?query=city+council+meeting+"
#                 "after%3A2023-02-05+before%3A2023-02-10"
#             ),
#             ["axUJRaHfgTc"],
#         ),
#     ],
# )
# def test_get_video_info(query_url, video_ids):
#     video_info_list = get_video_info(query_url=query_url)
#     id_list = [i["id"] for i in video_info_list]

#     assert id_list == video_ids


# @pytest.mark.parametrize(
#     "channel, timezone, body, search_terms, begin, end, video_ids",
#     [
#         (
#             "BellevueTelevision",
#             "America/Los_Angeles",
#             "City Council",
#             "city council meeting",
#             datetime(2023, 2, 5),
#             datetime(2023, 2, 10),
#             ["axUJRaHfgTc"],
#         )
#     ],
# )
# def test_get_events(channel, timezone, body, search_terms, begin, end, video_ids):
#     s = YoutubeIngestionScraper(
#         channel_name=channel, body_search_terms={body: search_terms}, timezone=timezone
#     )
#     assert s.channel_name == channel
#     assert s.body_search_terms[body] == search_terms

#     events = s.get_events(begin=begin, end=end)
#     sessions = [e.sessions for e in events]
#     sessions = chain.from_iterable(sessions)
#     sessions = list(sessions)
#     assert len(sessions) == len(video_ids)

#     session_uris = {s.video_uri for s in sessions}
#     video_uris = {f"https://www.youtube.com/watch?v={i}" for i in video_ids}

#     assert session_uris == video_uris
