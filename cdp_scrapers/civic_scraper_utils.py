import enum
from datetime import datetime
from logging import getLogger
from typing import Dict, Optional

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

    def get_event(self) -> Optional[EventIngestionModel]:
        """
        civic_scraper Asset to EventIngestionModel

        Returns
        -------
        Optional[EventIngestionModel]
            The asset converted to EventIngestionModel; None if asset type mismatch
        """
        try:
            return CivicIngestionModel.type_map[self.asset.asset_type](
                body=self.asset.committee_name,
                sessions=None,
                agenda_uri=self.get_asset_uri(AssetType.agenda),
                minutes_uri=self.get_asset_uri(AssetType.minutes),
            )
        except (KeyError, TypeError):
            # type_map[asset_type] != EventIngestionModel
            return None

    def get_session(self) -> Optional[Session]:
        """
        civic_scraper Asset to Session

        Returns
        -------
        Optional[Session]
            The asset converted to Session; None if asset type mismatch
        """
        try:
            return CivicIngestionModel.type_map[self.asset.asset_type](
                session_datetime=asset_datetime(self.asset),
                session_index=0,
                video_uri=self.get_asset_uri(AssetType.video),
                caption_uri=self.get_asset_uri(AssetType.captions),
            )
        except (KeyError, TypeError):
            return None

    def get_ingested(self) -> IngestionModel:
        """
        civic_scraper Asset to IngestionModel

        Returns
        -------
        Optional[IngestionModel]
            The asset converted to some IngestionSession.
            None if no conversion exists for this asset type.
        """
        for ingestion in [
            self.get_event,
            self.get_session,
        ]:
            ingested = ingestion()
            if ingested is not None:
                return ingested

        return None
