from datetime import datetime, time

import pytest
from civic_scraper.base.asset import Asset

from cdp_scrapers.civic_scraper_utils import (
    AssetType,
    CivicIngestionModel,
    asset_datetime,
    civic_strftime,
)

assets = [
    (
        Asset(
            url="agenda_url",
            committee_name="agenda committee",
            asset_type="agenda",
            meeting_date=datetime(2022, 9, 1),
        ),
        AssetType.agenda,
    ),
    (
        Asset(
            url="minutes_url",
            committee_name="minutes committee",
            asset_type="minutes",
            meeting_date=datetime(2022, 1, 9, 1, 2, 3),
        ),
        AssetType.minutes,
    ),
    (
        Asset(
            url="audio_url",
            committee_name="audio committee",
            asset_type="audio",
            meeting_date=datetime(2022, 9, 3),
            meeting_time=time(2, 3, 4),
        ),
        AssetType.audio,
    ),
    (
        Asset(
            url="video_url",
            committee_name="video committee",
            asset_type="video",
            meeting_date=datetime(2022, 8, 11),
            meeting_time=time(3, 4, 5, 6),
        ),
        AssetType.video,
    ),
    (
        Asset(
            url="captions_url",
            committee_name="captions committee",
            asset_type="captions",
        ),
        AssetType.captions,
    ),
]


def test_civic_strftime():
    assert datetime.today().strftime("%Y-%m-%d") == civic_strftime(datetime.today())


@pytest.mark.parametrize("asset, asset_type", assets)
def test_asset_datetime(asset: Asset, asset_type: AssetType):
    meeting_datetime = asset.meeting_date
    if meeting_datetime is not None and asset.meeting_time is not None:
        meeting_datetime = datetime(
            meeting_datetime.year,
            meeting_datetime.month,
            meeting_datetime.day,
            asset.meeting_time.hour,
            asset.meeting_time.minute,
            asset.meeting_time.second,
            asset.meeting_time.microsecond,
        )
    assert asset_datetime(asset) == meeting_datetime


@pytest.mark.parametrize("asset, asset_type", assets)
def test_is_asset(asset: Asset, asset_type: AssetType):
    assert CivicIngestionModel(asset).is_asset(asset_type)


@pytest.mark.parametrize("asset, asset_type", assets)
def test_asset_uri(asset: Asset, asset_type: AssetType):
    assert CivicIngestionModel(asset).get_asset_uri(asset_type) is not None


@pytest.mark.parametrize("asset, asset_type", assets)
def test_get_event(asset: Asset, asset_type: AssetType):
    ingested = CivicIngestionModel(asset)
    assert (ingested.get_event() is not None) == (
        ingested.is_asset(AssetType.agenda) or ingested.is_asset(AssetType.minutes)
    )


@pytest.mark.parametrize("asset, asset_type", assets)
def test_get_session(asset: Asset, asset_type: AssetType):
    ingested = CivicIngestionModel(asset)
    assert (ingested.get_session() is not None) == (
        ingested.is_asset(AssetType.captions) or ingested.is_asset(AssetType.video)
    )


@pytest.mark.parametrize("asset, asset_type", assets)
def test_get_ingested(asset: Asset, asset_type: AssetType):
    ingested = CivicIngestionModel(asset)
    assert (ingested.get_ingested() is None) == ingested.is_asset(AssetType.audio)
