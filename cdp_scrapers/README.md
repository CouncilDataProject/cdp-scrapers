# Notes on `LegistarScraper`s

## Filtering

1. Unimportant `EventMinutesItem`


`EventMinutesItem(minutes_item=MinutesItem(name="This meeting 
also constitutes a meeting of the City Council, provided ...", ...), ...)`

`minutes_item.name` comes from Legistar EventItem["EventItemTitle"]. Legistar 
EventItems wil often contain unimportant information, as shown above, that we 
want to exclude from ingesting into CDP. The `IGNORED_MINUTE_ITEMS` attribute in 
`LegistarScraper` 
defies a `List[str]` that we want to filter out. 
`IGNORED_MINUTE_ITEMS` is used in `filter_event_minutes()`, case-insensitively.

In your LegistarScraper-derived class' `__init__()`, overwrite or append to 
`self.IGNORED_MINUTE_ITEMS`. e.g.

```
class MyScraper(LegistarScraper):
    def __init__(self):
        super().__init__("my_city")

        self.IGNORED_MINUTE_ITEMS[MinutesItem].append("This meeting also constitutes a meeting")
```

With that filter in place, this entire `EventMinutesItem` becomes `None`.

2. Empty models

Consider another example such as

`EventMinutesItem(decision=None, matter=None, minutes_item=None, supporting_files=[], ...)`

which means nothing. `get_required_attrs()` returns attributes in a given 
`IngestionModel` without default values as defined in the respective `class` 
definitions. As this is "expensive" dynamic checking, the string lists are cached 
in `min_ingestion_keys`. i.e. `get_required_attrs()` is called just once per 
`IngestionModel` type.

For example, because `minutes_item` is `None` in the above 
`EventMinutesItem`, `get_none_if_empty()` will return `None`, instead of the 
given `EventMinutesItem` instance as-is.

This filtering is applied bottom-up. e.g.
```
# this is not exactly how the code is written
# but a representation of the call path

# reduced_list() simply removes None from the list
votes = reduced_list(
    [
        # return None if this Vote is empty
        get_none_if_empty(
            Vote(
                # return None if this Person is empty,
                # instead of Person(email=None, ...)
                person=get_none_if_empty(
                    Person(
                        email=...,
                        ...
                    )
                ),
                ...
            )
        )
        for vote in legistar_votes # Legistar "EventItemVoteInfo"
    ]
)
```

## Legistar -> CDP Ingestion

Some collection of notes from development phase on what Legistar API fields to 
use for what `IngestionModel` fields.

- For example "Public Comment" isn't a matter, its a minutes item. Minutes items 
are: "something that happened or was discussed during the meeting" while matters 
are usually the "things that were discussed" which is why minutes can link to 
matters. "Approval of Agenda" is a minutes item and links to the Matter "Agenda 
for 2021-07-28" for example.

## Instance-specific scraping

Base `LegistarScraper` was written such that ideally, an installation needs to 
define a derived class with just `__init__()` defined where Legistar client name 
is provided by calling `super().__init__("my_city")`, as in the above example.

You can override and implement your own methods as necessary. For example, the base
implementation for `get_event_support_files()` uses "MatterAttachmentId", 
"MatterAttachmentName", "MatterAttachmentHyperlink" from Legistar for 
`external_source_id`, `name`, `uri` for `SupportingFile`, respectively. You can 
define and implement `get_event_support_files()` in your LegistarScraper-derived 
class to use a completely different mapping for `SupportingFile`.

### Scraping for `Session.video_uri`

The "big" scraping that an instance will probably have to provide is 
`get_video_uris()`. The base class will try to use Legistar "EventVideoPath" but 
it is likely that information is not filled. In these situations Legistar might 
point to some external resource, such as a web page hosted somewhere else, that 
does have video URI for the given event. See `SeattleScraper.get_video_uris()`

See SeattleScraperGetVideoUris.ipynb for a walkthrough of how the method was 
implemented for Seattle. Keep in mind your implementation will most likely vary 
from this example.

## Minor notes

- `strip()` string fields to prevent passing values with garbage 
leading/trailing whitespace characters.
