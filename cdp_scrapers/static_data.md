## Motivation

Certain types of information may change much less frequently, relative to those that are specific to a given meeting.
List of councilmembers and their biographical data are some examples.
Let's call them "static data." Given this context,
`scraper_utils.parse_static_file()` and a static data file can be used

1. As source of biographical (e.g. e-mail address) and professional (e.g. seats held) information for councilmembers.
This may be useful in situations when scraping such information is not trivial.

2. To provide correct information for the councilmembers.
We have often observed invalid or incorrect information provided by the municipalities for the councilmembers.
They are mostly simple mistakes, or inconsistencies in the data.
A static data file can be used to provide consistent, correct and updated councilmember information.

## Example

```Python
import pprint
from cdp_scrapers.scraper_utils import parse_static_file, sanitize_roles

static_data = parse_static_file("cdp_scrapers/instances/seattle-static.json")
pprint.pp(static_data.seats, indent=4)

# {
#     'Position 1': Seat(name='Position 1',
#     ...,
#     'Position 2': Seat(name='Position 2',
#     ...,
# }

pprint.pp(static_data.primary_bodies, indent=4)

# {
#     'City Council': Body(name='City Council',
#     ...,
#     'Council Briefing': Body(name='Council Briefing',
#     ...,
# }

pprint.pp(static_data.persons, indent=4)

# {
#     'Alex Pedersen': Person(name='Alex Pedersen',
#     ...,
#                             seat=Seat(name='Position 4',
#     ...,
#                             roles=[   Role(title='Councilmember',
#                                            body=Body(name='City Countil',
#     ...,
#     'Andrew Lewis': Person(name='Andrew Lewis',
#     ...,
# }

# councilmember is cdp_backend.pipeline.ingestion_models.Person
# Augment, clean up and update scraped list of roles for this councilmember
councilmember.seat.roles = sanitize_roles(councilmember.name, scraped_roles, static_data)
```

### `LegistarScraper`

If your scraper inherits from [`LegistarSCraper`](./legistar_utils.py),
you could pass the return value from the function into the constructor.

```Python
# instances/my_municipality.py

from ..legistar_utils import LegistarScraper
from ..scraper_utils import parse_static_file

class MyScraper(LegistarScraper):
    PYTHON_MUNICIPALITY_SLUG: str = "mymunicipality"

    def __init__(self):
        super().__init__(
            client="municipality_legistar_client_id",
            timezone="America/My_TimeZone",
            #
            static_data=parse_static_file("municipality_static_data.json"),
            #
            ...,
```

The information read from the static data file will be used automatically during [post-processing](./legistar_utils.py#L1560) of the scraped data.

## Static Data File

See [`instances/*static*.json`](./instances/seattle-static.json) for examples.

### `seats`

Seats on the local council defined as [`ingestion_models.Seat`](https://councildataproject.org/cdp-backend/cdp_backend.pipeline.html#cdp_backend.pipeline.ingestion_models.Seat) in JSON.
Used as a look-up table for `Person.seat` in the `persons` section of the static data file.

### `primary_bodies`

The primary council bodies defined as [`ingestion_models.Body`](https://councildataproject.org/cdp-backend/cdp_backend.pipeline.html#cdp_backend.pipeline.ingestion_models.Body) in JSON.
A councilmember's [roles](https://councildataproject.org/cdp-backend/cdp_backend.pipeline.html#cdp_backend.pipeline.ingestion_models.Seat.roles) in any of the `primary_bodies` are used to determine the person's terms served.

### `persons`

Provide information here to augment scraped data for [councilmembers](https://councildataproject.org/cdp-backend/cdp_backend.pipeline.html#cdp_backend.pipeline.ingestion_models.Person)
at run time.

For example, if the scraping yieled the following `Person` instance,

```Python
councilmember = Person(
    name="Some Council Member",
    phone="bad number", # or None
)
```

and the following is given in the static data file,

```Json
"persons": {
    "Some Council Member": {
        "name": "Some Council Member",
        "phone": "123-123-1234",
        ...,
    },
    ...,
}
```

In the data set returned by `get_events()`, `councilmember` will be like,

```Python
Person(
    name="Some Council Member",
    phone="123-123-1234",
```

#### `roles`

The recommendation is to provide the councilmember's terms here,
using the information given in the `primary_bodies` section.

```Json
...
"primary_bodies": {
    "City Council": {
        "name": "City Council"
...
"persons": {
    "Some Council Member": {
        ...,
        "roles": [
            {
                "body": "City Council",
                "start_datetime": 1577865600,
                "end_datetime": 1704009600,
                "title": "Councilmember"
            },
...
```

This role with the city council will be added at run time
to this person's `Person.seat.roles` list.


## Notes

In [`inject_known_data()`](./legistar_utils.py#L1560) and
[`sanitize_roles()`](./scraper_utils.py#L228),
information given in the static data file is prioritized over dynamically scraped data.
