from datetime import datetime
from typing import List

import pytest

from bs4 import Tag
from cdp_backend.database.constants import MatterStatusDecision
from cdp_backend.pipeline.ingestion_models import EventMinutesItem, Matter, MinutesItem
from cdp_scrapers.prime_gov_utils import (
    Meeting,
    get_minutes_tables,
    load_agenda,
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

urls = [
    (
        "https://lacity.primegov.com/Portal/MeetingPreview"
        "?compiledMeetingDocumentFileId=41088"
    ),
]
agendas = list(map(load_agenda, urls))
minutes_tables = list(map(lambda agenda: list(get_minutes_tables(agenda)), agendas))
minutes_items = [
    MinutesItem(
        name="22-0600-S29",
        description=(
            "Information Technology Agency (ITA) report, "
            "in response to a 2022-23 Budget Recommendation, "
            "relative to the status on the implementation of permanent Wi-Fi hotspots."
        ),
    ),
]
matters = [
    Matter(
        name="Information Technology Agency report",
        matter_type="Report",
        title=(
            "Information Technology Agency (ITA) report, "
            "in response to a 2022-23 Budget Recommendation, "
            "relative to the status on the implementation of permanent Wi-Fi hotspots."
        ),
        result_status=MatterStatusDecision.ADOPTED,
        sponsors=None,
        external_source_id=None,
    )
]
event_minutes_items = [
    # Will be filled in the respective test cases using input data defined above
    EventMinutesItem(minutes_item=None, index=1),
]
support_file_counts = [4]


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
    "scraper, minutes_tbls, minutes_item",
    zip(scrapers, minutes_tables, minutes_items),
)
def test_get_minutes_item(
    scraper: PrimeGovScraper, minutes_tbls: List[Tag], minutes_item: MinutesItem
):
    assert scraper.get_minutes_item(minutes_tbls[0]) == minutes_item


@pytest.mark.parametrize(
    "scraper, minutes_tbls, minutes_item, matter",
    zip(scrapers, minutes_tables, minutes_items, matters),
)
def test_get_matter(
    scraper: PrimeGovScraper,
    minutes_tbls: List[Tag],
    minutes_item: MinutesItem,
    matter: Matter,
):
    assert scraper.get_matter(minutes_tbls[0], minutes_item) == matter


@pytest.mark.parametrize(
    "scraper, minutes_tbls, minutes_item, matter, num_support_files, expected_item",
    zip(
        scrapers,
        minutes_tables,
        minutes_items,
        matters,
        support_file_counts,
        event_minutes_items,
    ),
)
def test_get_event_minutes_item(
    scraper: PrimeGovScraper,
    minutes_tbls: List[Tag],
    minutes_item: MinutesItem,
    matter: Matter,
    num_support_files: int,
    expected_item: EventMinutesItem,
):
    expected_item.minutes_item = minutes_item
    expected_item.matter = matter
    event_minutes_item = scraper.get_event_minutes_item(minutes_tbls[0])

    assert event_minutes_item.index == expected_item.index
    assert event_minutes_item.matter == expected_item.matter
    assert event_minutes_item.minutes_item == expected_item.minutes_item
    assert len(event_minutes_item.supporting_files) == num_support_files


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


@pytest.mark.parametrize(
    "scraper, meetings, num_event_minutes_items",
    zip(scrapers, all_meetings, [[13, 8]]),
)
def test_get_event_minutes_items(
    scraper: PrimeGovScraper,
    meetings: List[Meeting],
    num_event_minutes_items: List[int],
):
    for meeting, num_items in zip(meetings, num_event_minutes_items):
        assert len(scraper.get_event_minutes_items(meeting)) == num_items
