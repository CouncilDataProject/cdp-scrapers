import enum
from datetime import datetime
from typing import List

import pytest

from cdp_scrapers.prime_gov_utils import Meeting, PrimeGovScraper
from cdp_scrapers.scraper_utils import reduced_list


class DataItem(enum.IntEnum):
    ClientId = 0
    TimeZone = enum.auto()
    Begin = enum.auto()
    End = enum.auto()
    Scraper = enum.auto()
    NumMeetings = enum.auto()
    Meetings = enum.auto()


test_data = [
    (
        "lacity",
        "America/Los_Angeles",
        datetime(2022, 9, 1),
        datetime(2022, 9, 1),
        PrimeGovScraper(client_id="lacity", timezone="America/Los_Angeles"),
        2,
    ),
]
# append scraped meetings to each test input data set
test_data = list(
    map(
        lambda d: (
            *d,
            list(
                d[DataItem.Scraper].get_meetings(
                    begin=d[DataItem.Begin], end=d[DataItem.End]
                )
            ),
        ),
        test_data,
    )
)


@pytest.mark.parametrize(
    "num_meetings, meetings",
    [(d[DataItem.NumMeetings], d[DataItem.Meetings]) for d in test_data],
)
def test_get_meetings(num_meetings: int, meetings: List[Meeting]):
    assert len(meetings) == num_meetings


@pytest.mark.parametrize(
    "scraper, meetings",
    [(d[DataItem.Scraper], d[DataItem.Meetings]) for d in test_data],
)
def test_get_session(scraper: PrimeGovScraper, meetings: List[Meeting]):
    sessions = reduced_list(map(scraper.get_session, meetings))
    assert len(sessions) == len(meetings)


@pytest.mark.parametrize(
    "scraper, meetings",
    [(d[DataItem.Scraper], d[DataItem.Meetings]) for d in test_data],
)
def test_get_body(scraper: PrimeGovScraper, meetings: List[Meeting]):
    bodies = reduced_list(map(scraper.get_body, meetings))
    assert len(bodies) == len(meetings)


@pytest.mark.parametrize(
    "scraper, meetings",
    [(d[DataItem.Scraper], d[DataItem.Meetings]) for d in test_data],
)
def test_get_event(scraper: PrimeGovScraper, meetings: List[Meeting]):
    events = reduced_list(map(scraper.get_event, meetings))
    assert len(events) == len(meetings)


@pytest.mark.parametrize(
    "scraper, begin, end, num_meetings",
    [
        (
            d[DataItem.Scraper],
            d[DataItem.Begin],
            d[DataItem.End],
            d[DataItem.NumMeetings],
        )
        for d in test_data
    ],
)
def test_get_events(
    scraper: PrimeGovScraper, begin: datetime, end: datetime, num_meetings: int
):
    events = scraper.get_events(begin, end)
    assert len(events) == num_meetings
