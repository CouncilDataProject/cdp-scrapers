import pytest
from cdp_backend.pipeline.ingestion_models import Matter, MinutesItem

from cdp_scrapers.prime_gov_utils import (
    Agenda,
    get_matter,
    get_minutes_item,
    get_minutes_tables,
    get_support_files,
    load_agenda,
)

urls = [
    (
        "https://lacity.primegov.com/Portal/MeetingPreview"
        "?compiledMeetingDocumentFileId=41088"
    ),
]
agendas = list(map(load_agenda, urls))
minutes_counts = [8]
support_file_counts = [4]
first_minutes_items = [
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
        matter_type="report",
        title=(
            "Information Technology Agency (ITA) report, "
            "in response to a 2022-23 Budget Recommendation, "
            "relative to the status on the implementation of permanent Wi-Fi hotspots."
        ),
        result_status="APPROVED",
        sponsors=None,
        external_source_id=None,
    )
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
    minutes_item: MinutesItem,
):
    assert get_minutes_item(next(get_minutes_tables(agenda))) == minutes_item


@pytest.mark.parametrize(
    "agenda, num_files",
    zip(agendas, support_file_counts),
)
def test_get_support_files(agenda: Agenda, num_files: int):
    assert len(list(get_support_files(next(get_minutes_tables(agenda))))) == num_files


@pytest.mark.parametrize(
    "agenda, matter",
    zip(agendas, matters),
)
def test_get_matter(agenda: Agenda, matter: Matter):
    minutes_table = next(get_minutes_tables(agenda))
    minutes_item = get_minutes_item(minutes_table)
    assert get_matter(minutes_table, minutes_item) == matter
