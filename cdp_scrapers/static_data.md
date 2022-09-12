## Motivation

Certain types of information may change much less frequently, relative to those that are specific to a given meeting.
List of councilmembers and their biographical data are some examples.
Let's call them "static data." Given this context,
`scraper_utils.parse_static_file()` is an utility function that can be used

1. As source of biographical (e.g. e-mail address) and professional (e.g. seats held) information for councilmembers.
This may be useful in situations when scraping such information is not trivial.

2. To provide correct information for the councilmembers.
We have often observed invalid or incorrect information provided by the municipalities for the councilmembers.
They are mostly simple mistakes, or inconsistencies in the data.
A static data file can be used to provide consistent, correct and updated councilmember information.

## Example

```Python
import pprint
from cdp_scrapers.scraper_utils import parse_static_file

seats, primary_bodies, persons = parse_static_file("cdp_scrapers/instances/seattle-static.json")
pprint.pp(seats, indent=4)

# {
#     'Position 1': Seat(name='Position 1',
#     ...,
#     'Position 2': Seat(name='Position 2',
#     ...,
# }

pprint.pp(primary_bodies, indent=4)

# {
#     'City Council': Body(name='City Council',
#     ...,
#     'Council Briefing': Body(name='Council Briefing',
#     ...,
# }

pprint.pp(primary_bodies, indent=4)

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
            static_data=parse_static_file("municipality_static_data.json"),
            ...,
```

The information read from the static data file will be used automatically during post-processing of the scraped data.

## Sections

### `seats`

`cdp_backend.pipeline.ingestion_models.Seat` serialized as JSON
