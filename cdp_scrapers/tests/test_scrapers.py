from datetime import datetime

import pytest

from cdp_scrapers.instances.houston import HoustonScraper
from cdp_scrapers.instances.kingcounty import KingCountyScraper
from cdp_scrapers.instances.portland import PortlandScraper
from cdp_scrapers.instances.seattle import SeattleScraper


@pytest.mark.flaky(reruns=3, reruns_delay=15)
@pytest.mark.parametrize(
    "start_date_time, end_date_time, expected_meetings,"
    "expected_minutes_item_in_first_meeting, expected_first_supporting_file",
    [
        (
            datetime(2022, 1, 10),
            datetime(2022, 1, 12),
            1,
            29,
            "https://houston.novusagenda.com/agendapublic/"
            "CoverSheet.aspx?ItemID=24626&MeetingID=522",
        ),
        (
            datetime(2022, 11, 7),
            datetime(2022, 11, 16),
            2,
            33,
            "https://houston.novusagenda.com/agendapublic/"
            "CoverSheet.aspx?ItemID=27102&MeetingID=566",
        ),
    ],
)
def test_houston_scraper(
    start_date_time: datetime,
    end_date_time: datetime,
    expected_meetings,
    expected_minutes_item_in_first_meeting,
    expected_first_supporting_file,
):
    houston = HoustonScraper()
    houston_events = houston.get_events(start_date_time, end_date_time)
    assert len(houston_events) == expected_meetings
    assert (
        len(houston_events[0].event_minutes_items)
        == expected_minutes_item_in_first_meeting
    )
    assert (
        houston_events[0].event_minutes_items[0].supporting_files
        == expected_first_supporting_file
    )


@pytest.mark.flaky(reruns=3, reruns_delay=15)
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


@pytest.mark.flaky(reruns=3, reruns_delay=15)
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
            "https://archive-video.granicus.com/king/"
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
            "https://archive-video.granicus.com/king/"
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


@pytest.mark.flaky(reruns=3, reruns_delay=15)
@pytest.mark.parametrize(
    "start_date_time, end_date_time, number_of_events, number_of_event_minute_items,"
    "number_of_sessions, event_with_votes, event_minute_item_with_votes,"
    "number_of_votes, expected_video_uri_in_first_session, expected_agenda_uri",
    [
        (
            datetime(2021, 8, 19),
            datetime(2021, 8, 31),
            0,
            0,
            0,
            0,
            0,
            0,
            "",
            "",
        ),
        # (
        #     datetime(2021, 8, 18),
        #     datetime(2021, 8, 19),
        #     1,
        #     24,
        #     2,
        #     0,
        #     23,
        #     5,
        #     "https://www.youtube.com/embed/zB5YuC5dz1s",
        #     "https://efiles.portlandoregon.gov/record/14645317/File/Document",
        # ),
        # (
        #     datetime(2021, 12, 22),
        #     datetime(2021, 12, 23),
        #     1,
        #     19,
        #     1,
        #     0,
        #     2,
        #     5,
        #     "https://www.youtube.com/embed/aXKE2u24WKg",
        #     "https://efiles.portlandoregon.gov/record/14778119/File/Document",
        # ),
        # (
        #     datetime(2022, 1, 12),
        #     datetime(2022, 1, 13),
        #     1,
        #     14,
        #     1,
        #     0,
        #     5,
        #     5,
        #     "https://www.youtube.com/embed/TBrJbm08i0g",
        #     "https://efiles.portlandoregon.gov/record/14811424/File/Document",
        # ),
        # (
        #     datetime(2021, 11, 10),
        #     datetime(2021, 11, 11),
        #     1,
        #     17,
        #     2,
        #     0,
        #     6,
        #     5,
        #     "https://www.youtube.com/embed/3mYGdqck_bw",
        #     "https://efiles.portlandoregon.gov/record/14750779/File/Document",
        # ),
    ],
)
def test_portland_scraper(
    start_date_time: datetime,
    end_date_time: datetime,
    number_of_events: int,
    number_of_event_minute_items: int,
    number_of_sessions: int,
    event_with_votes: int,
    event_minute_item_with_votes: int,
    number_of_votes: int,
    expected_video_uri_in_first_session: str,
    expected_agenda_uri: str,
) -> None:
    portland = PortlandScraper()
    portland_events = portland.get_events(start_date_time, end_date_time)
    assert len(portland_events) == number_of_events
    if number_of_events > 0:
        assert (
            len(portland_events[0].event_minutes_items) == number_of_event_minute_items
        )
        assert len(portland_events[0].sessions) == number_of_sessions
        assert (
            portland_events[0].sessions[0].video_uri
            == expected_video_uri_in_first_session
        )
        assert (
            len(
                portland_events[event_with_votes]
                .event_minutes_items[event_minute_item_with_votes]
                .votes
            )
            == number_of_votes
        )
        assert portland_events[0].agenda_uri == expected_agenda_uri
