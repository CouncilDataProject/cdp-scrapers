import abc
from copy import deepcopy
import enum
from datetime import datetime
from itertools import groupby
from logging import getLogger
from typing import Dict, Iterable, List, Optional, Tuple

from cdp_backend.pipeline.ingestion_models import (
    EventIngestionModel,
    IngestionModel,
    Session,
)
from civic_scraper.base.asset import Asset
from civic_scraper.runner import Runner

###############################################################################

log = getLogger(__name__)

###############################################################################

DATE_FORMAT = "%Y-%m-%d"
IngestionType = abc.ABCMeta


class AssetType(enum.IntFlag):
    """
    See Also
    --------
    civic_scraper.base.constants.SUPPORTED_ASSET_TYPES
    """

    agenda = 0
    minutes = enum.auto()
    audio = enum.auto()
    video = enum.auto()
    agenda_packet = enum.auto()
    captions = enum.auto()


def asset_datetime(asset: Asset) -> Optional[datetime]:
    """
    Return the associated meeting's datetime

    Parameters
    ----------
    asset: Asset
        The civic_scraper Asset

    Returns
    -------
    datetime
        datetime for the asset's associated meeting
    """
    meeting_datetime = asset.meeting_date
    if meeting_datetime is None or asset.meeting_time is None:
        return meeting_datetime

    return datetime(
        meeting_datetime.year,
        meeting_datetime.month,
        meeting_datetime.day,
        asset.meeting_time.hour,
        asset.meeting_time.minute,
        asset.meeting_time.second,
        asset.meeting_time.microsecond,
    )


def civic_strftime(dt: datetime) -> str:
    """
    String representation of the given datetime object,
    in format accepted by civic_scraper.

    Parameters
    ----------
    dt: datetime
        The datetime object to convert to string

    Returns
    -------
    str
        Input datetime converted to string

    See Also
    --------
    civic_scraper.runner.Runner.scrape()
    """
    return datetime.strftime(dt, DATE_FORMAT)


class CivicIngestionModel:
    """
    Converter for civic_scraper Asset to IngestionModel

    See Also
    --------
    civic_scraper.base.asset.Asset
    """

    type_map: Dict[str, IngestionModel] = {
        AssetType.agenda.name: EventIngestionModel,
        AssetType.minutes.name: EventIngestionModel,
        AssetType.video.name: Session,
        AssetType.captions.name: Session,
    }

    def __init__(self, asset: Asset):
        """
        Parameters
        ----------
        asset: Asset
            The Asset object to ingest
        """
        self.asset = asset

    def is_asset(self, asset_type: AssetType) -> bool:
        """
        Test if the ingested asset is of a certain asset type.

        Parameters
        ----------
        asset_type: AssetType
            Target asset type

        Returns
        -------
        bool
        """
        return self.asset.asset_type == asset_type.name

    def is_ingestion(self, ingestion_type: IngestionType) -> bool:
        return (
            CivicIngestionModel.type_map.get(self.asset.asset_type, None)
            is ingestion_type
        )

    def get_asset_uri(self, asset_type: AssetType) -> Optional[str]:
        """
        Get url of given type from ingested asset.

        Parameters
        ----------
        asset_type: AssetType
            Target asset type

        Returns
        -------
        Optional[str]
            Asset URL; None if asset type mismatch
        """
        return self.asset.url if self.is_asset(asset_type) else None

    def ingest(self, **kwargs) -> Optional[IngestionModel]:
        """
        Call the constructor for the matching IngestionModel.

        Parameters
        ----------
        kwargs: Any
            The keyword arguments passed to IngestionModel.__init__()

        Returns
        -------
        Optional[IngestionModel]
            Instance of the IngestionModel that matches the Asset.
        """
        try:
            return CivicIngestionModel.type_map[self.asset.asset_type](**kwargs)
        except (KeyError, TypeError):
            return None

    def get_event(self) -> Optional[EventIngestionModel]:
        """
        civic_scraper Asset to EventIngestionModel

        Returns
        -------
        Optional[EventIngestionModel]
            The asset converted to EventIngestionModel; None if asset type mismatch
        """
        return self.ingest(
            body=self.asset.committee_name,
            sessions=None,
            agenda_uri=self.get_asset_uri(AssetType.agenda),
            minutes_uri=self.get_asset_uri(AssetType.minutes),
            external_source_id=self.asset.meeting_id,
        )

    def get_session(self) -> Optional[Session]:
        """
        civic_scraper Asset to Session

        Returns
        -------
        Optional[Session]
            The asset converted to Session; None if asset type mismatch
        """
        return self.ingest(
            session_datetime=asset_datetime(self.asset),
            session_index=0,
            video_uri=self.get_asset_uri(AssetType.video),
            caption_uri=self.get_asset_uri(AssetType.captions),
            external_source_id=self.asset.meeting_id,
        )


def merge_ingestion(old: IngestionModel, new: IngestionModel) -> IngestionModel:
    kwargs = {
        k: deepcopy(getattr(new, k) if v is None else v)
        for k, v in old.__dict__.items()
    }
    return old.__class__(**kwargs)


def merge_session(session: Session, ingestion: CivicIngestionModel) -> Session:
    if not ingestion.is_ingestion(Session):
        return session
    return merge_ingestion(session, ingestion.get_session())


def merge_event(
    event: EventIngestionModel, ingestion: CivicIngestionModel
) -> EventIngestionModel:
    if not ingestion.is_ingestion(EventIngestionModel):
        return event
    return merge_ingestion(event, ingestion.get_event())


def merge_assets(assets: Iterable[Asset]) -> Tuple[EventIngestionModel, Session]:
    event = EventIngestionModel(body=None, sessions=None)
    session = Session(session_datetime=None, video_uri=None, session_index=None)
    for asset in assets:
        ingestion = CivicIngestionModel(asset)
        event = merge_event(event, ingestion)
        session = merge_session(session, ingestion)

    return event, session


def get_events(site_url: str, begin: datetime, end: datetime):
    assets = Runner().scrape(start_date=begin, end_date=end, site_urls=[site_url])
    events: List[EventIngestionModel] = list()

    for meeting_id, meeting_assets in groupby(assets, key=lambda a: a.meeting_id):
        event, session = merge_assets(meeting_assets)

        if session.video_uri is None:
            continue

        event.sessions = [session]
        if event.body is None:
            continue

        events.append(event)

    return events
