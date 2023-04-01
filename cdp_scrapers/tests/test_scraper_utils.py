from itertools import chain
import random

from cdp_backend.pipeline.ingestion_models import Matter, Person, Vote, EventMinutesItem, MinutesItem
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
    def make_persons(self, num_persons):
        return [Person(name=f"person_{i}") for i in range(num_persons)]

    def make_sponsored_matters(self, num_matters, sponsors):
        num_sponsors = len(sponsors)
        num_sponsors_list = [random.randrange(num_sponsors + 1) for _ in range(num_matters)]
        matter_sponsors = [random.choices(sponsors, k=k) for k in num_sponsors_list]

        # Making sure at least one matter with all sponsors
        if num_matters:
            matter_sponsors[random.randrange(num_matters)] = sponsors

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

    @pytest.mark.parametrize("num_persons", [0, 1, 3])
    @pytest.mark.parametrize("num_matters", [0, 1, 3])
    def test_helpers(self, num_persons, num_matters):
        persons = self.make_persons(num_persons)
        assert len(persons) == num_persons

        matters = self.make_sponsored_matters(num_matters, persons)
        matter_sponsors = [matter.sponsors or [] for matter in matters]
        for sponsors in matter_sponsors:
            assert len(sponsors) <= num_persons
            for sponsor in sponsors:
                assert sponsor in persons

        matter_sponsors = chain.from_iterable(matter_sponsors)
        sponsor_names = set([p.name for p in matter_sponsors])
        person_names = set([p.name for p in persons])

        try:
            assert sponsor_names == person_names
        except AssertionError:
            assert len(sponsor_names) == 0 and num_matters == 0