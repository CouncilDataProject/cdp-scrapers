import pytest
from cdp_scrapers.instances.seattle import SeattleScraper
from datetime import datetime


@pytest.mark.parametrize(
    "start_date_time, end_date_time, number_of_events,"
    "number_of_sessions_in_first_event, expected_caption_uri_in_first_session,"
    "expected_video_uri_in_first_session",
    [
        (datetime(2021, 6, 16), datetime(2021, 6, 18), 1, 1,
         "https://www.seattlechannel.org/documents/seattlechannel/closedcaption/2021/"
         "tran_061621_2672121.vtt",
         "https://video.seattle.gov/media/council/tran_061621_2672121V.mp4"),
        (datetime(2021, 6, 16), datetime(2021, 6, 30), 9, 1,
         "https://www.seattlechannel.org/documents/seattlechannel/closedcaption/2021/"
         "tran_061621_2672121.vtt",
         "https://video.seattle.gov/media/council/tran_061621_2672121V.mp4"),
        (datetime(2021, 10, 26), datetime(2021, 10, 28), 9, 1,
         "https://www.seattlechannel.org/documents/seattlechannel/closedcaption/2021/"
         "tran_061621_2672121.vtt",
         "https://video.seattle.gov/media/council/tran_061621_2672121V.mp4")
    ],
)
def test_seattle_scraper(
    start_date_time: datetime,
    end_date_time: datetime,
    number_of_events: int,
    number_of_sessions_in_first_event: int,
    expected_caption_uri_in_first_session: str,
    expected_video_uri_in_first_session: str
) -> None:
    print("test")
    seattle = SeattleScraper()
    seattle_events = seattle.get_events(start_date_time, end_date_time)
    assert len(seattle_events) == number_of_events
    assert len(seattle_events[0].sessions) == number_of_sessions_in_first_event
    assert seattle_events[0].sessions[0].caption_uri ==\
           expected_caption_uri_in_first_session
    assert seattle_events[0].sessions[0].video_uri ==\
           expected_video_uri_in_first_session
