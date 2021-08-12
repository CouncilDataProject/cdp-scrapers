# cdp-scrapers

[![Build Status](https://github.com/CouncilDataProject/cdp-scrapers/workflows/Build%20Main/badge.svg)](https://github.com/CouncilDataProject/cdp-scrapers/actions)
[![Documentation](https://github.com/CouncilDataProject/cdp-scrapers/workflows/Documentation/badge.svg)](https://CouncilDataProject.github.io/cdp-scrapers/)

Scratchpad for scraper development and general utilities.

---

## Council Data Project

Council Data Project is an open-source project dedicated to providing journalists,
activists, researchers, and all members of each community we serve with the tools they
need to stay informed and hold their Council Members accountable.

For more information about Council Data Project, please visit
[our website](https://councildataproject.org/).

## About

`cdp-scrapers` is a collection of utilities and in-progress or actively maintained
CDP instance event scrapers. The purpose of this library is to help new CDP instance
maintainers have a quick plethora of examples for getting started on developing their
event scraper functions.

## Quick Start

### Legistar

General Legistar utility functions.

```python
from cdp_scrapers.legistar_utils import get_legistar_events_for_timespan
from datetime import datetime

# Get all events (and minutes item and voting details)
# for a provided timespan for a legistar client
# Returns List[Dict]
events = get_legistar_events_for_timespan(
    client="seattle",
    start=datetime(2021, 7, 12),
    end=datetime(2021, 7, 14),
)

# Futher processing
# ...
```

### Scrapers

In-progress or completed scrapers.

```python
from cdp_scrapers.instances.seattle import get_events

# This is an in-progress or completed scraper
# Returns List[cdp_backend.pipeline.ingestion_models.EventIngestionModel]
events = get_events()
```

## Installation

**Stable Release:** `pip install cdp-scrapers`<br>
**Development Head:** `pip install git+https://github.com/CouncilDataProject/cdp-scrapers.git`

## Documentation

For full package documentation please visit [councildataproject.org/cdp-scrapers](https://councildataproject.org/cdp-scrapers).

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for information related to developing the code.

**MIT license**
