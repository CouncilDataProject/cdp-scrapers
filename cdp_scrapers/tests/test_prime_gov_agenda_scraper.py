import pytest

from cdp_scrapers.prime_gov_utils import (
    Agenda,
    get_minutes_item,
    load_agenda,
    get_minutes_tables,
    MinutesItemInfo,
)

urls = [
    (
        "https://lacity.primegov.com/Portal/MeetingPreview"
        "?compiledMeetingDocumentFileId=41088"
    ),
]
agendas = list(map(load_agenda, urls))
minutes_counts = [8]
first_minutes_items = [
    MinutesItemInfo(
        name="22-0600-S29",
        desc=(
            "Information Technology Agency (ITA) report, "
            "in response to a 2022-23 Budget Recommendation, "
            "relative to the status on the implementation of permanent Wi-Fi hotspots."
        ),
    ),
]


@pytest.mark.parametrize("url", urls)
def test_load_agenda(url: str):
    assert load_agenda(url) is not None


@pytest.mark.parametrize(
    "agenda, num_minutes",
    zip(agendas, minutes_counts),
)
def test_get_minutes_tables(
    agenda: Agenda,
    num_minutes: int,
):
    assert len(list(get_minutes_tables(agenda))) == num_minutes


@pytest.mark.parametrize(
    "agenda, minutes_item",
    zip(agendas, first_minutes_items),
)
def test_get_minutes_item(
    agenda: Agenda,
    minutes_item: MinutesItemInfo,
):
    assert get_minutes_item(next(get_minutes_tables(agenda))) == minutes_item
