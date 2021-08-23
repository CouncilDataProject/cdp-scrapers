# Notes on `LegistarScraper`

## Filtering

- Unimportant `EventMinutesItem`

```python
EventMinutesItem(
    minutes_item=MinutesItem(
        name="This meeting also constitutes a meeting of the City Council, provided ...",
        ...
    ),
    ...
)
```

`minutes_item.name` comes from Legistar EventItem["EventItemTitle"]. Legistar 
EventItems will often contain unimportant information, as shown above, that we 
want to exclude from ingesting into CDP. The `ignore_minutes_item_patterns` attribute in 
`LegistarScraper` 
defines a `List[str]` that we want to filter out. 
`ignore_minutes_item_patterns` is used in `filter_event_minutes()`, case-insensitively.

Set the list of filter strings in `__init__()` of your class derived from LegistarScraper. e.g.

```python
class MyScraper(LegistarScraper):
    def __init__(self):
        super().__init__(
            client="my_municipality",
            timezone="America/Los_Angeles",
            ignore_minutes_item_patterns=[
                "This meeting also constitutes a meeting of the City Council",
                # Common to see "CITY COUNCIL:",
                # Or more generally "{body name}:"
                # Check for last char ":"
                r".+:$",
            ],
        )
```

With that filter in place, this entire `EventMinutesItem` becomes `None`.

- Empty models

Consider another example such as

```python
EventMinutesItem(decision=None, matter=None, minutes_item=None, supporting_files=[], ...)
```

which means nothing. `get_required_attrs()` returns attributes in a given 
`IngestionModel` without default values as defined in the respective `class` 
definitions. As this is "expensive" dynamic checking, the string lists are cached 
in `min_ingestion_keys`. i.e. `get_required_attrs()` is called just once per 
`IngestionModel` type.

For example, because `minutes_item` is `None` in the above 
`EventMinutesItem`, `get_none_if_empty()` will return `None`, instead of the 
given `EventMinutesItem` instance as-is.

This filtering is applied bottom-up. e.g.

```python
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

## Legistar to CDP `IngestionModel`

Here are some notes on what Legistar API fields to use for `IngestionModel` fields.

- "Public Comment" isn't a matter, it is a minutes item. Minutes items 
are: "something that happened or was discussed during the meeting" while matters 
are usually the "things that were discussed" which is why minutes can link to 
matters. "Approval of Agenda" is a minutes item and links to the Matter "Agenda 
for 2021-07-28", for example.

## Instance-specific scraping

In an ideal situation, in your `LegistarScraper` class you need to provide just 
the municipality's Legistar client ID and the time zone. See the `MyScraper` example above.

You can override and implement your own methods as necessary. For example, the base
implementation for `get_event_support_files()` uses `"MatterAttachmentId"`, 
`"MatterAttachmentName"`, `"MatterAttachmentHyperlink"` from Legistar:

```python
[
    SupportingFile(
        external_source_id=attachment["MatterAttachmentId"],
        name=attachment["MatterAttachmentName"],
        uri=attachment["MatterAttachmentHyperlink"],
    )
    # Legistar "MatterAttachments"
    for attachment in legistar_ev_attachments
]
```

You can define and implement `get_event_support_files()` in your 
`LegistarScraper`-derived class to use a completely different mapping for 
`SupportingFile`.

### Scraping for `Session.video_uri`

The "big" scraping that an instance will probably have to provide is 
`get_content_uris()`. The base class will try to use Legistar "EventVideoPath" but 
it is likely that information is not filled. In these situations Legistar might 
point to some external resource, such as a web page hosted somewhere else, that 
does have URI for the video from the given event. See `SeattleScraper.get_content_uris()`.

### Other notes

- Recommend calling `legistar_utils.str_simplified()` on string fields to remove 
leading/trailing whitespace and simplify consecutive whitespace.
