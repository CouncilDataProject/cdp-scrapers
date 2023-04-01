import random

from cdp_backend.pipeline.ingestion_models import Matter, Person, Vote
import pytest

from cdp_scrapers.scraper_utils import str_simplified


@pytest.mark.parametrize(
    "input_string, expected_output",
    [
        (
            "   test   ",
            "test",
        ),
        ("    test", "test"),
        ("test     ", "test"),
        ("test\r\n\ftest", "test\ntest"),
        ("test \t\vtest", "test test"),
        ("M. Lorena Gonz\u00e1lez", "M. Lorena González"),
        (5, 5),
    ],
)
def test_str_simplifed(input_string: str, expected_output: str):
    # Validate that both methods work the same
    assert str_simplified(input_string) == expected_output


class TestExtractPersons:
    @pytest.fixture
    def make_persons(self):
        def _make(num_persons):
            return [Person(name=f"person_{i}") for i in range(num_persons)]
        return _make

    @pytest.fixture
    def make_sponsored_matters(self):
        def _make(num_matters, sponsors):
            num_sponsors = len(sponsors)
            num_sponsors_list = [random.randrange(num_sponsors + 1) for _ in range(num_matters)]
            # Making sure at least one matter with all sponsors
            if num_matters:
                num_sponsors_list[random.randrange(num_matters)] = num_sponsors
            matter_sponsors = [random.choices(sponsors, k=k) for k in num_sponsors_list]

            matters = [
                Matter(
                    name=f"matter_{i}",
                    matter_type=f"type_{i}",
                    title=f"title_{i}",
                    sponsors=_sponsors,
                )
                for i, _sponsors in enumerate(matter_sponsors)
            ]
            return matters
        return _make

    @pytest.mark.parametrize("num_persons", [0, 1, 3])
    @pytest.mark.parametrize("num_matters", [0, 1, 3])
    def test_fixtures(self, num_persons, num_matters, make_persons, make_sponsored_matters):
        persons = make_persons(num_persons)
        assert len(persons) == num_persons

        matters = make_sponsored_matters(num_matters, persons)
        matter_sponsors = [matter.sponsors or [] for matter in matters]
        for sponsors in matter_sponsors:
            assert len(sponsors) <= num_persons
            for sponsor in sponsors:
                assert sponsor in persons
