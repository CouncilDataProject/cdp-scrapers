import enum
from datetime import datetime
from typing import List

import pytest

from cdp_backend.pipeline.ingestion_models import Person
from cdp_scrapers.prime_gov_utils import (
    Meeting,
    PersonName,
    PrimeGovScraper,
    primegov_strftime,
    primegov_strptime,
)
from cdp_scrapers.scraper_utils import reduced_list


class DataItem(enum.IntEnum):
    Begin = 0
    End = enum.auto()
    Scraper = enum.auto()
    NumMeetings = enum.auto()
    Meetings = enum.auto()


test_data = [
    (
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


@pytest.mark.parametrize(
    "name_text, person",
    [
        ("COUNCILMEMBER NITHYA RAMAN, CHAIR", Person(name="NITHYA RAMAN")),
        ("COUNCILMEMBER BOB BLUMENFIELD", Person(name="BOB BLUMENFIELD")),
        ("COUNCILMEMBER CURREN D. PRICE, JR.", Person(name="CURREN D. PRICE, JR.")),
    ],
)
def test_get_person(name_text: PersonName, person: Person):
    assert test_data[0][DataItem.Scraper].get_person(name_text) == person
