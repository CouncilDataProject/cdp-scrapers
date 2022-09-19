from typing import List
import pytest
from cdp_backend.database.constants import RoleTitle
from cdp_scrapers.prime_gov_utils import PrimeGovAgendaScraper

scrapers = [
    PrimeGovAgendaScraper(
        "https://lacity.primegov.com/Portal/MeetingPreview"
        "?compiledMeetingDocumentFileId=40742"
    ),
]
name_texts = [
    [
        "COUNCILMEMBER NITHYA RAMAN, CHAIR",
        "COUNCILMEMBER BOB BLUMENFIELD",
        "COUNCILMEMBER CURREN D. PRICE, JR.",
    ],
]
names = [
    [
        "NITHYA RAMAN", "BOB BLUMENFIELD", "CURREN D. PRICE, JR."
    ],
]
role_titles = [
    [
        RoleTitle.CHAIR, RoleTitle.COUNCILMEMBER, RoleTitle.COUNCILMEMBER
    ],
]


@pytest.mark.parametrize("scraper, name_texts", zip(scrapers, name_texts))
def test_get_member_names(scraper: PrimeGovAgendaScraper, name_texts: List[str]):
    assert scraper.get_member_names() == name_texts

@pytest.mark.parametrize("scraper, name_texts, names, role_titles", zip(scrapers, name_texts, names, role_titles))
def test_pop_role_title(scraper: PrimeGovAgendaScraper, name_texts: List[str], names: List[str], role_titles: List[str]):
    for name_text, expected_name, expected_title in zip(name_texts, names, role_titles):
        name, title = scraper.pop_role_title(name_text)
        assert name == expected_name
        assert title == expected_title
