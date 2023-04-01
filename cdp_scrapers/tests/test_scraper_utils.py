from itertools import chain
import random

from cdp_backend.pipeline.ingestion_models import Matter, Person, Vote, EventMinutesItem, EventIngestionModel, MinutesItem
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

    def make_matters(self, num_matters, sponsors):
        if num_matters:
            num_sponsors = [random.randrange(len(sponsors) + 1) for _ in range(num_matters)]
            # At least one matter has all sponsors
            num_sponsors[random.randrange(num_matters)] = len(sponsors)

            for i, k in enumerate(num_sponsors):
                matter = Matter(
                        name=f"matter_{i}",
                        matter_type=f"type_{i}",
                        title=f"title_{i}",
                        sponsors=random.sample(sponsors, k),
                    )
                yield matter

    def make_votes(self, num_items, voters):
        if num_items:
            num_voters = [random.randrange(len(voters) + 1) for _ in range(num_items)]
            # At least one minutes item has all voters
            num_voters[random.randrange(num_items)] = len(voters)

            for i, k in enumerate(num_voters):
                item_voters = random.sample(voters, k)
                votes = [Vote(person=p, decision="Approve") for p in item_voters]
                yield votes

    def make_events(self, matters, votes):
        matters_votes = zip(matters, votes)
        items = [
            EventMinutesItem(
                minutes_item=None,
                matter=matter,
                votes=_votes,
            )
            for matter, _votes in matters_votes
        ]

        while len(items):
            num_items = random.randrange(len(items) + 1)
            event_items = random.sample(items, num_items)
            event = EventIngestionModel(
                body=None,
                sessions=[],
                event_minutes_items=event_items
            )
            yield event

            for item in event_items:
                items.remove(item)

    @pytest.mark.parametrize("num_persons", [0, 1, 3])
    @pytest.mark.parametrize("num_matters", [0, 1, 3])
    @pytest.mark.parametrize("num_sponsors", [0, 1, 3])
    @pytest.mark.parametrize("num_voters", [0, 1, 3])
    def test_helpers(self, num_persons, num_matters, num_sponsors, num_voters):
        persons = self.make_persons(num_persons)
        assert len(persons) == num_persons

        num_sponsors = min(num_sponsors, num_persons)
        num_voters = min(num_voters, num_persons)
        _matters = [] if num_persons == 0 else self.make_matters(num_matters, random.sample(persons, num_sponsors))
        _votes = [] if num_persons == 0 else self.make_votes(num_matters, random.sample(persons, num_voters))
        events = self.make_events(_matters, _votes)

        items = [e.event_minutes_items for e in events]
        items = list(chain.from_iterable(items))
        matters = [i.matter for i in items]

        sponsors = [m.sponsors for m in matters]
        sponsors = chain.from_iterable(sponsors)
        names = set([p.name for p in sponsors])

        try:
            assert len(names) == num_sponsors
        except AssertionError:
            assert len(names) == 0 and num_matters == 0

        for sponsor in sponsors:
            assert sponsor in persons

        votes = [i.votes for i in items]
        votes = chain.from_iterable(votes)
        voters = [v.person for v in votes]
        names = set([p.name for p in voters])

        try:
            assert len(names) == num_voters
        except AssertionError:
            assert len(names) == 0 and num_matters == 0

        for voter in voters:
            assert voter in persons
