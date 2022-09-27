from datetime import datetime
from typing import List

import pytest

from cdp_scrapers.prime_gov_utils import (
    Meeting,
    PrimeGovScraper,
    primegov_strftime,
    primegov_strptime,
)
from cdp_scrapers.scraper_utils import reduced_list


begin_dates = [datetime(2022, 9, 1)]
end_dates = [datetime(2022, 9, 1)]
scrapers = [PrimeGovScraper(client_id="lacity", timezone="America/Los_Angeles")]
all_meetings = [
    list(s.get_meetings(begin_dates[i], end_dates[i])) for i, s in enumerate(scrapers)
]
meeting_counts = [2]


@pytest.mark.parametrize(
    "meeting, date_time",
    [
        (
            {"dateTime": "2022-09-06T10:00:00", "date": "", "time": ""},
            datetime(2022, 9, 6, 10),
        ),
        (
            {"dateTime": "", "date": "09/06/2022", "time": "10:00 AM"},
            datetime(2022, 9, 6, 10),
        ),
        ({"dateTime": "2022-09-06", "date": "", "time": ""}, datetime(2022, 9, 6)),
        ({"dateTime": "", "date": "09/06/2022", "time": ""}, datetime(2022, 9, 6)),
    ],
)
def test_strptime(meeting: Meeting, date_time: datetime):
    assert primegov_strptime(meeting) == date_time


@pytest.mark.parametrize(
    "date_time",
    [
        (datetime(2022, 9, 1, 10)),
    ],
)
def test_strftime(date_time: datetime):
    assert date_time.strftime("%m/%d/%Y") == primegov_strftime(date_time)


@pytest.mark.parametrize(
    "num_meetings, meetings",
    zip(meeting_counts, all_meetings),
)
def test_get_meetings(num_meetings: int, meetings: List[Meeting]):
    assert len(meetings) == num_meetings


@pytest.mark.parametrize(
    "scraper, meetings",
    zip(scrapers, all_meetings),
)
def test_get_session(scraper: PrimeGovScraper, meetings: List[Meeting]):
    sessions = reduced_list(map(scraper.get_session, meetings))
    assert len(sessions) == len(meetings)


@pytest.mark.parametrize(
    "scraper, meetings",
    zip(scrapers, all_meetings),
)
def test_get_body(scraper: PrimeGovScraper, meetings: List[Meeting]):
    bodies = reduced_list(map(scraper.get_body, meetings))
    assert len(bodies) == len(meetings)


@pytest.mark.parametrize(
    "scraper, meetings",
    zip(scrapers, all_meetings),
)
def test_get_event(scraper: PrimeGovScraper, meetings: List[Meeting]):
    events = reduced_list(map(scraper.get_event, meetings))
    assert len(events) == len(meetings)


@pytest.mark.parametrize(
    "scraper, begin, end, num_meetings",
    zip(scrapers, begin_dates, end_dates, meeting_counts),
)
def test_get_events(
    scraper: PrimeGovScraper, begin: datetime, end: datetime, num_meetings: int
):
    events = scraper.get_events(begin, end)
    assert len(events) == num_meetings
