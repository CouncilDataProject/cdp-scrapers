from copy import deepcopy
from datetime import datetime, timedelta
from itertools import chain
import random

from cdp_backend.pipeline.ingestion_models import Matter, Person, Vote, EventMinutesItem, EventIngestionModel, MinutesItem, Role, Body, Seat
import pytest

from cdp_scrapers.scraper_utils import str_simplified, extract_persons, compare_persons


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
    PRIMARY_BODY = "primary_body"

    def make_persons(self, num_persons):
        end_datetime=datetime.today() + timedelta(days=2)
        roles = [
            Role(title=f"primary_role", body=Body(name=TestExtractPersons.PRIMARY_BODY), end_datetime=end_datetime),
            Role(title=f"role", body=Body(name="body"), end_datetime=end_datetime)
        ]
        seat = Seat(name="seat", roles=roles)
        return [Person(name=f"person_{i}", seat=deepcopy(seat)) for i in range(num_persons)]

    def make_matters(self, num_matters, sponsors):
        """Make N Matters. Sponsors are randomly distributed"""
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
        """Make N Votes. Voters are randomly distributed"""
        if num_items:
            num_voters = [random.randrange(len(voters) + 1) for _ in range(num_items)]
            # At least one minutes item has all voters
            num_voters[random.randrange(num_items)] = len(voters)

            for i, k in enumerate(num_voters):
                item_voters = random.sample(voters, k)
                votes = [Vote(person=p, decision="Approve") for p in item_voters]
                yield votes

    def make_events_from_items(self, matters, votes):
        """Combine Matters and Votes into EventIngestionModels. EventMinutesItems are randomly distributed"""
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

    def make_events(self, persons, num_matters, num_sponsors, num_voters):
        """Make EventIngestionModels. Sponsors and voters are randomly distributed."""
        num_persons = len(persons)

        sponsors = [] if num_persons == 0 else random.sample(persons, num_sponsors)
        matters = self.make_matters(num_matters, sponsors)

        voters = [] if num_persons == 0 else random.sample(persons, num_voters)
        votes = self.make_votes(num_matters, voters)

        events = self.make_events_from_items(matters, votes)
        return events

    @pytest.mark.parametrize("num_persons", [0, 1, 3])
    @pytest.mark.parametrize("num_matters", [0, 1, 3])
    @pytest.mark.parametrize("num_sponsors", [0, 1, 3])
    @pytest.mark.parametrize("num_voters", [0, 1, 3])
    def test_helpers(self, num_persons, num_matters, num_sponsors, num_voters):
        """Sanity tests for the above helper methods"""
        persons = self.make_persons(num_persons)
        assert len(persons) == num_persons

        num_sponsors = min(num_sponsors, num_persons)
        num_voters = min(num_voters, num_persons)
        # Make fake events from sponsors and voters
        events = self.make_events(persons, num_matters, num_sponsors, num_voters)

        items = [e.event_minutes_items for e in events]
        items = list(chain.from_iterable(items))

        # Test that the fake events contain input sponsors
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

        # Test that the fake events contain input voters
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

    @pytest.mark.parametrize("num_persons", [1, 3])
    @pytest.mark.parametrize("num_matters", [1, 3])
    @pytest.mark.parametrize("num_sponsors", [1, 3])
    def test_extract_sponsors(self, num_persons, num_matters, num_sponsors):
        """Test that matter sponsors are extracted from events"""
        persons = self.make_persons(num_persons)
        assert len(persons) == num_persons

        num_sponsors = min(num_sponsors, num_persons)
        events = self.make_events(persons, num_matters, num_sponsors, num_voters=0)

        extracted_persons = extract_persons(events)
        assert len(extracted_persons) == num_sponsors

    @pytest.mark.parametrize("num_persons", [1, 3])
    @pytest.mark.parametrize("num_matters", [1, 3])
    @pytest.mark.parametrize("num_voters", [1, 3])
    def test_extract_voters(self, num_persons, num_matters, num_voters):
        """Test that voters are extractd from events"""
        persons = self.make_persons(num_persons)
        assert len(persons) == num_persons

        num_voters = min(num_voters, num_persons)
        events = self.make_events(persons, num_matters, num_sponsors=0, num_voters=num_voters)

        extracted_persons = extract_persons(events)
        assert len(extracted_persons) == num_voters

    @pytest.mark.parametrize("num_matters", [1, 3])
    @pytest.mark.parametrize("num_sponsors", [0, 1, 3])
    @pytest.mark.parametrize("num_voters", [0, 1, 3])
    def test_extract_persons(self, num_matters, num_sponsors, num_voters):
        """Test that sponsors and voters are extracted from events"""
        num_persons = max(num_sponsors, num_voters)
        persons = self.make_persons(num_persons)
        assert len(persons) == num_persons

        num_sponsors = min(num_sponsors, num_persons)
        num_voters = min(num_voters, num_persons)
        events = self.make_events(persons, num_matters, num_sponsors, num_voters)

        extracted_persons = extract_persons(events)
        assert len(extracted_persons) == num_persons


    def detect_old_new(self, num_persons, num_changed, modifier, is_unmodified):
        persons = self.make_persons(num_persons)

        scraped_persons = deepcopy(persons)
        num_changed = min(num_changed, num_persons)
        if num_changed:
            for i in random.sample(range(num_persons), num_changed):
                scraped_persons[i] = modifier(scraped_persons[i])

        old_new = compare_persons(scraped_persons, persons, [Body(name=TestExtractPersons.PRIMARY_BODY)])

        assert len(old_new.old_names) == num_changed
        for p in scraped_persons:
            assert (not p or p.name in old_new.old_names) or is_unmodified(p)


    @pytest.mark.parametrize("num_persons", [1, 3])
    @pytest.mark.parametrize("num_inactive", [0, 1, 3])
    def test_detect_inactive(self, num_persons, num_inactive):
        """Test that we detect those with is_inactive = False"""
        def make_inactive(person):
            person.is_active = False
            return person

        self.detect_old_new(num_persons, num_inactive, make_inactive, lambda p: p.is_active)

    @pytest.mark.parametrize("num_persons", [1, 3])
    @pytest.mark.parametrize("num_term_end", [0, 1, 3])
    def test_detect_term_end(self, num_persons, num_term_end):
        """Test that we detect those with expired council membership"""
        def make_term_end(person):
            person.seat.roles[0].end_datetime = datetime.today() - timedelta(days=2)
            return person

        self.detect_old_new(num_persons, num_term_end, make_term_end, lambda p: datetime.today().date() <= p.seat.roles[0].end_datetime.date())

    @pytest.mark.parametrize("num_persons", [1, 3])
    @pytest.mark.parametrize("num_not_found", [0, 1, 3])
    def test_detect_not_found(self, num_persons, num_not_found):
        """Test that we detect those not scraped"""
        def make_not_found(person):
            person = None
            return person

        self.detect_old_new(num_persons, num_not_found, make_not_found, lambda p: p is not None)
