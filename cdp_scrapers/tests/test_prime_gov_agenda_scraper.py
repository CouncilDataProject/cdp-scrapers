from typing import List
import pytest
from cdp_scrapers.prime_gov_utils import PrimeGovAgendaScraper

scrapers = [
    PrimeGovAgendaScraper("https://lacity.primegov.com/Portal/MeetingPreview?compiledMeetingDocumentFileId=40742"),
]
names = [
    ["COUNCILMEMBER NITHYA RAMAN, CHAIR", "COUNCILMEMBER BOB BLUMENFIELD", "COUNCILMEMBER CURREN D. PRICE, JR."]
]


@pytest.mark.parametrize("scraper, names", zip(scrapers, names))
def test_get_member_names(scraper: PrimeGovAgendaScraper, names: List[str]):
    assert scraper.get_member_names() == names
