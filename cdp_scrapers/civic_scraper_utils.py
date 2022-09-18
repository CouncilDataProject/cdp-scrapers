import abc
import enum
from copy import deepcopy
from datetime import datetime
from logging import getLogger
from typing import Dict, Iterable, Optional

from cdp_backend.pipeline.ingestion_models import (
    EventIngestionModel,
    IngestionModel,
    Session,
)
from civic_scraper.base.asset import Asset

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


def merge_ingestion(
    left_ingestion: IngestionModel, right_ingestion: IngestionModel
) -> IngestionModel:
    """
    Return a merged instance of the given ingestion models.

    Parameters
    ----------
    left_ingestion: IngestionModel
        Ingestion model to merge
    right_ingestion: IngestionModel
        Ingestion model to merge

    Returns
    -------
    IngestionModel
        Input ingestion models merged.

    Raises
    ------
    ValueError
        When both ingestion models have different values for the same attribute.
    """
    kwargs = dict()
    for key, left_attr in left_ingestion.__dict__.items():
        right_attr = getattr(right_ingestion, key)
        if left_attr is not None and right_attr is not None and left_attr != right_attr:
            raise ValueError(
                f"Cannot resolve conflict for {key}: {left_attr} and {right_attr}"
            )
        kwargs.update({key: deepcopy(left_attr or right_attr)})

    return left_ingestion.__class__(**kwargs)


def merge_session(session: Session, ingestion: CivicIngestionModel) -> Session:
    """
    Return input session merged with information from the ingested asset.

    Parameters
    ----------
    session: Session
        Merge target session
    ingestion: CivicIngestionModel
        Ingested civic_scraper Asset

    Returns
    -------
    Session
        Input session and asset merged.

    Notes
    -----
    ingestion is ignored if asset_type is not for Session.
    """
    if not ingestion.is_ingestion(Session):
        return session
    return merge_ingestion(session, ingestion.get_session())


def merge_event(
    event: EventIngestionModel, ingestion: CivicIngestionModel
) -> EventIngestionModel:
    """
    Return input event merged with information from the ingested asset.

    Parameters
    ----------
    session: EventIngestionModel
        Merge target event
    ingestion: CivicIngestionModel
        Ingested civic_scraper Asset

    Returns
    -------
    EventIngestionModel
        Input event and asset merged.

    Notes
    -----
    ingestion is ignored if asset_type is not for EventIngestionModel.
    """
    if not ingestion.is_ingestion(EventIngestionModel):
        return event
    return merge_ingestion(event, ingestion.get_event())


def merge_assets(assets: Iterable[Asset]) -> Optional[EventIngestionModel]:
    """
    Create an event from civic_scraper assets.

    Parameters
    ----------
    assets: Iterable[Asset]
        AssetCollection from civic_scraper.

    Returns
    -------
    Optional[EventIngestionModel]
        Event created from input assets.

    Raises
    -----
    ValueError
        If input AssetCollection contains assets for different meetings.
    """
    event = EventIngestionModel(body=None, sessions=None)
    session = Session(session_datetime=None, video_uri=None, session_index=None)

    meeting_id: str = None
    for ingestion in map(CivicIngestionModel, assets):
        event = merge_event(event, ingestion)
        session = merge_session(session, ingestion)

        if meeting_id is None:
            meeting_id = ingestion.asset.meeting_id
        elif (
            ingestion.asset.meeting_id is not None
            and ingestion.asset.meeting_id != meeting_id
        ):
            raise ValueError(
                f"Mixed meetings: {meeting_id} and {ingestion.asset.meeting_id}"
            )

    if session.video_uri is None:
        return None

    event.sessions = [session]

    if event.body is None:
        return None

    return event
