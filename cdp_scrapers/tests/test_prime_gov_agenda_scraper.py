from typing import Dict, List

import pytest
from cdp_backend.database.constants import RoleTitle

from cdp_scrapers.prime_gov_utils import (
    Agenda,
    default_role_map,
    get_member_names,
    get_members_table,
    get_minutes_item,
    load_agenda,
    split_name_role,
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
name_texts = [
    [
        "COUNCILMEMBER NITHYA RAMAN, CHAIR",
        "COUNCILMEMBER BOB BLUMENFIELD",
        "COUNCILMEMBER CURREN D. PRICE, JR.",
    ],
]
names = [
    ["NITHYA RAMAN", "BOB BLUMENFIELD", "CURREN D. PRICE, JR."],
]
role_titles = [
    [RoleTitle.CHAIR, RoleTitle.COUNCILMEMBER, RoleTitle.COUNCILMEMBER],
]
role_maps = [
    default_role_map,
]
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


@pytest.mark.parametrize("agenda", agendas)
def test_get_members_table(agenda: Agenda):
    assert get_members_table(agenda) is not None


@pytest.mark.parametrize("agenda, _name_texts", zip(agendas, name_texts))
def test_get_member_names(agenda: Agenda, _name_texts: List[str]):
    assert get_member_names(agenda) == _name_texts


@pytest.mark.parametrize(
    "_name_texts, _names, titles, role_map",
    zip(name_texts, names, role_titles, role_maps),
)
def test_split_name_title(
    _name_texts: List[str],
    _names: List[str],
    titles: List[RoleTitle],
    role_map: Dict[str, RoleTitle],
):
    assert list(map(lambda n: split_name_role(n, role_map), _name_texts)) == list(
        zip(_names, titles)
    )


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
