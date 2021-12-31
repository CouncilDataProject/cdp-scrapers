from datetime import datetime

import pytest

from cdp_scrapers.instances.kingcounty import KingCountyScraper
from cdp_scrapers.instances.seattle import SeattleScraper


@pytest.mark.parametrize(
    "start_date_time, end_date_time, number_of_events,"
    "number_of_sessions_in_first_event, number_of_event_minute_items,"
    "event_with_votes, event_minute_item_with_votes, number_of_votes,"
    "expected_caption_uri_in_first_session, expected_video_uri_in_first_session",
    [
        # Check for 1 event with 2 sessions and 12 event minute items.
        (
            datetime(2021, 10, 15),
            datetime(2021, 10, 16),
            1,
            2,
            12,
            -1,
            -1,
            -1,
            "https://www.seattlechannel.org/documents/seattlechannel/closedcaption/"
            "2021/budget_101521_2062123.vtt",
            "https://video.seattle.gov/media/council/budget_101521_2062123V.mp4",
        ),
        # Check for 2 events, with the first event having 1 session and 1 minute item.
        # In this event, there are 5 votes found in the 15th event minute item of the
        # 2nd event.
        (
            datetime(2021, 12, 6, 10, 0),
            datetime(2021, 12, 7, 1, 0),
            2,
            1,
            8,
            1,
            14,
            5,
            "https://www.seattlechannel.org/documents/seattlechannel/closedcaption/"
            "2021/asset_120721_2642121.vtt",
            "https://video.seattle.gov/media/council/asset_120721_2642121V.mp4",
        ),
    ],
)
def test_seattle_scraper(
    start_date_time: datetime,
    end_date_time: datetime,
    number_of_events: int,
    number_of_sessions_in_first_event: int,
    number_of_event_minute_items: int,
    event_with_votes: int,
    event_minute_item_with_votes: int,
    number_of_votes: int,
    expected_caption_uri_in_first_session: str,
    expected_video_uri_in_first_session: str,
) -> None:
    seattle = SeattleScraper()
    seattle_events = seattle.get_events(start_date_time, end_date_time)
    assert len(seattle_events) == number_of_events
    assert len(seattle_events[0].sessions) == number_of_sessions_in_first_event
    assert len(seattle_events[0].event_minutes_items) == number_of_event_minute_items
    if event_minute_item_with_votes >= 0:
        assert (
            len(
                seattle_events[event_with_votes]
                .event_minutes_items[event_minute_item_with_votes]
                .votes
            )
            == number_of_votes
        )
    assert (
        seattle_events[0].sessions[0].caption_uri
        == expected_caption_uri_in_first_session
    )
    assert (
        seattle_events[0].sessions[0].video_uri == expected_video_uri_in_first_session
    )


@pytest.mark.parametrize(
    "start_date_time, end_date_time, number_of_events, number_of_event_minute_items,"
    "event_with_votes, event_minute_item_with_votes, number_of_votes,"
    "expected_video_uri_in_first_session",
    [
        # Check for 1 event with 10 event minute items.
        (
            datetime(2021, 6, 17),
            datetime(2021, 6, 18),
            1,
            15,
            -1,
            -1,
            -1,
            "http://archive-media.granicus.com:443/OnDemand/king/"
            "king_80aac332-5f77-43b4-9259-79d108cdbff1.mp4",
        ),
        # Check for 6 events, with the first event having 1 minute item.
        # In this event, there are 4 votes found in the 5th event minute item of the
        # 5th event.
        (
            datetime(2021, 6, 16),
            datetime(2021, 6, 23),
            6,
            11,
            4,
            4,
            4,
            "http://archive-media.granicus.com:443/OnDemand/king/"
            "king_b2529fca-1b29-4f3e-b0c5-aa9f4bbb27d9.mp4",
        ),
    ],
)
def test_king_county_scraper(
    start_date_time: datetime,
    end_date_time: datetime,
    number_of_events: int,
    number_of_event_minute_items: int,
    event_with_votes: int,
    event_minute_item_with_votes: int,
    number_of_votes: int,
    expected_video_uri_in_first_session: str,
) -> None:
    king_county = KingCountyScraper()
    king_county_events = king_county.get_events(start_date_time, end_date_time)
    assert len(king_county_events) == number_of_events
    assert (
        len(king_county_events[0].event_minutes_items) == number_of_event_minute_items
    )
    if event_minute_item_with_votes >= 0:
        assert (
            len(
                king_county_events[event_with_votes]
                .event_minutes_items[event_minute_item_with_votes]
                .votes
            )
            == number_of_votes
        )
    assert (
        king_county_events[0].sessions[0].video_uri
        == expected_video_uri_in_first_session
    )
