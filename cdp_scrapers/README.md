# Notes on writing LegistarScrapers

## Filtering

1. Unimportant `EventMinutesItem`


`EventMinutesItem(minutes_item=MinutesItem(name="123", description="This meeting 
also constitutes a meeting of the City Council, provided ...", ...), ...)`

`minutes_item.description` comes from Legistar EventItem["EventItemTitle"]. Legistar 
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

which means nothing. `MIN_INGESTION_KEYS` is the LegistarScraper attribute used 
to return `None` for such "empty" models. Like `IGNORED_MINUTE_ITEMS` it defines a `List[str]`, 
per `IngestionModel` class. Here, each string in the `List[str]` is a key in the 
corresponding model. For example, the base `LegistarScraper` class defines

```
self.MIN_INGESTION_KEYS = {
    ...
    EventMinutesItem: ["matter", "minutes_item"],
    ...
}
```

`get_none_if_empty(self, model)` will test if any key in 
`self.MIN_INGESTION_KEYS[model.__class__]` in `model` has a nonempty value; 
`if model.__dict__[key]: ...`.

For example, because `matter` and `minutes_item` are both `None` in the above 
`EventMinutesItem`, `get_none_if_empty()` will return `None`, instead of the 
given `EventMinutesItem` instance as-is.

This filtering is applied bottom-up. e.g.
```
# this is not exactly how the code is written
# but a representation of the call path

# reduced_list() simply removes None from the list
votes = reducsed_list(
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

Modify `MIN_INGESTION_KEYS` in your `__init()__` like `IGNORED_MINUTE_ITEMS` to 
adjust to how your municipality provides information through Legistar.

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

TODO: upload notebook to demonstrate how we arrived at `SeattleScraper.
get_video_uris()` from Legistar EventItem.

## Minor notes

- `strip()` string fields
