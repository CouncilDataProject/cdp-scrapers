from datetime import date, datetime
from logging import getLogger
from optparse import Option
from typing import Any, Dict, Iterable, Optional, Set
from cdp_backend.pipeline.ingestion_models import Session, EventIngestionModel, Body
from civic_scraper.base.asset import Asset
from civic_scraper.platforms.primegov.site import PrimeGovSite
from .scraper_utils import IngestionModelScraper, reduced_list, str_simplified


###############################################################################

log = getLogger(__name__)

###############################################################################

SITE_URL = "https://{client}.primegov.com/"
API_URL = "{base_url}/api/meeting/search?from={start_date}&to={end_date}"

MEETING_DATETIME = "dateTime"
MEETING_DATE = "date"
MEETING_TIME = "time"
MEETING_ID = "id"
BODY_NAME = "title"
VIDEO_URL = "videoUrl"

DATE_FORMAT = "%m/%d/%Y"
TIME_FORMAT = "%I:%M %p"

Meeting = Dict[str, Any]


def primegov_strftime(dt: datetime) -> str:
    return dt.strftime(DATE_FORMAT)


def primegov_strptime(meeting: Meeting) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(meeting[MEETING_DATETIME])
    except ValueError:
        try:
            return datetime.strptime(f"{meeting[MEETING_DATE]} {meeting[MEETING_TIME]}", f"{DATE_FORMAT} {TIME_FORMAT}")
        except ValueError:
            pass
    
    log.debug(f"Error parsing '{meeting[MEETING_DATETIME]}', '{meeting[MEETING_DATE]}', '{meeting[MEETING_TIME]}'")
    return None


class PrimeGovScraper(PrimeGovSite, IngestionModelScraper):
    def __init__(self, client_id: str, timezone: str, person_aliases: Optional[Dict[str, Set[str]]] = None):
        PrimeGovSite.__init__(self, SITE_URL.format(client=client_id))
        IngestionModelScraper.__init__(self, timezone=timezone, person_aliases=person_aliases)

        log.debug(
            f"Created PrimeGovScraper "
            f"for primegov_instance: {self.primegov_instance}, "
            f"in timezone: {self.timezone}, "
            f"at url: {self.url}"
        )

    def get_meetings(self,
        begin: datetime,
        end: datetime,
    ) -> Iterable[Meeting]:
        resp = self.session.get(
            f"{self.base_url}/api/meeting/search?from={primegov_strftime(begin)}&to={primegov_strftime(end)}"
        )
        return filter(lambda m: any(m[VIDEO_URL]), resp.json())

    def get_session(self, meeting: Meeting) -> Optional[Session]:
        return self.get_none_if_empty(
            Session(
                session_datetime=primegov_strptime(meeting),
                video_uri=str_simplified(meeting[VIDEO_URL]),
                session_index=0
            )
        )

    def get_body(self, meeting: Meeting) -> Optional[Body]:
        return self.get_none_if_empty(
            Body(name=str_simplified(meeting[BODY_NAME]))
        )

    def get_event(self, meeting: Meeting) -> Optional[EventIngestionModel]:
        return self.get_none_if_empty(
            EventIngestionModel(
                body=self.get_body(meeting),
                sessions=reduced_list([self.get_session(meeting)]),
                external_source_id=str_simplified(str(meeting[MEETING_ID])),
            )
        )
