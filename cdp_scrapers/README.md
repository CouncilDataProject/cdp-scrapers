# Notes on writing LegistarScrapers

## Filtering

`EventMinutesItem(minutes_item=MinutesItem(name="123", description="This meeting 
also constitutes a meeting of the City Council, provided ...", external_source_id
=123), index=None, matter=None, result_status=None, sponsors=None, 
external_source_id=None), supporting_files=[], decision=None, votes=[])`

There are 2 levels of filtering we want to apply on the above example.

1. Unimportant minutes_item

MinutesItem.description comes from Legistar EventItem.EventItemTitle. Legistar 
EventItems wil often contain unimportant information, as shown above, that we 
want to exclude from ingesting into CDP. The `IGNORED_MINUTE_ITEMS` attribute in 
`LegistarScraper` 
defies a `List[str]` per `IngestionModel` class that we want to filter out. 
`IGNORED_MINUTE_ITEMS` is used in `filter_event_minutes()`, case-insensitively.

In your LegistarScraper-derived class' `__init__()`, overwrite or append to 
`self.IGNORED_MINUTE_ITEMS`. e.g.

```
class MyScraper(LegistarScraper):
    def __init__(self):
        super().__init__("my_city")

        self.IGNORED_MINUTE_ITEMS[MinutesItem].append("This meeting also constitutes a meeting")
```

With that filter in place, this `MinutesItem.description` becomes `None`.

2. Empty models

If `description` is set to `None`, the example `MinutesItem` is like

`MinutesItem(name="123", description=None, external_source_id=123)`

which means nothing. `MIN_INGESTION_KEYS` is the LegistarScraper attribute used 
to return `None` for such "empty" models. Like `IGNORED_MINUTE_ITEMS`, it defines a `List[str]` 
per `IngestionModel` class. Here, each string in the `List[str]` is a key in the 
corresponding model. For example, the base `LegistarScraper` class defines

```
self.MIN_INGESTION_KEYS = {
    ...
    MinutesItem: ["description"],
    ...
}
```

`get_none_if_empty(self, model)` will test if any key in 
`self.MIN_INGESTION_KEYS[model.__class__]` in `model` has a nonempty value like 
`if model.__dict__[key]: ...`.

For example, we have just `"description"` listed for `MinutesItem`. The test will 
fail because `model.__dict__["description"] is None`. `get_none_if_empty()` will 
therefore return `None`, instead of the argument `model` as-is.

This works recursively. i.e. `get_none_if_empty()` is called on the parent 
`EventMinutesItem`, which now contains a bunch of `None` for its fields like 
`minutes_item`, `matter`, etc. The base definition of `self.MIN_INGESTION_KEYS[EventMinutesItem]` is `["matter", "minutes_item"]`. Since this `EventMinutesItem` has None for its `matter` and `minutes_item`, 
`get_none_if_empty()` returne `None` for this `EventMinutesItem`, and the main 
`get_events()` excludes it from the returned `List[EventMinutesItem]`.

Modify `MIN_INGESTION_KEYS` in your `__init()__` like `IGNORED_MINUTE_ITEMS` as desired.

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
does have URI for the given event. See `SeattleScraper.get_video_uris()`

TODO: upload notebook to demonstrate how we arrived at `SeattleScraper.
get_video_uris()` from Legistar EventItem.

## Minor notes

- `strip()` string fields
