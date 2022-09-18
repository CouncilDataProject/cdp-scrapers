import pytest
from cdp_backend.pipeline.ingestion_models import EventIngestionModel, Session
from civic_scraper.base.asset import Asset, AssetCollection

from cdp_scrapers.civic_scraper_utils import (
    AssetType,
    CivicIngestionModel,
    IngestionType,
    asset_datetime,
    civic_strftime,
    merge_assets,
    merge_event,
    merge_session,
)
from datetime import datetime, time

assets = [
    (
        Asset(
            url="agenda_url",
            committee_name="committee",
            asset_type="agenda",
            meeting_date=datetime(2022, 1, 9, 1, 2, 3),
            meeting_id="meeting 1",
        ),
        AssetType.agenda,
        EventIngestionModel,
    ),
    (
        Asset(
            url="minutes_url",
            committee_name="committee",
            asset_type="minutes",
            meeting_date=datetime(2022, 1, 9, 1, 2, 3),
            meeting_id="meeting 1",
        ),
        AssetType.minutes,
        EventIngestionModel,
    ),
    (
        Asset(
            url="audio_url",
            committee_name="committee",
            asset_type="audio",
            meeting_date=datetime(2022, 9, 3),
            meeting_time=time(2, 3, 4),
        ),
        AssetType.audio,
        None,
    ),
    (
        Asset(
            url="video_url",
            committee_name="committee",
            asset_type="video",
            meeting_date=datetime(2022, 8, 11),
            meeting_time=time(3, 4, 5, 6),
        ),
        AssetType.video,
        Session,
    ),
    (
        Asset(
            url="captions_url",
            committee_name="committee",
            asset_type="captions",
        ),
        AssetType.captions,
        Session,
    ),
]


def test_civic_strftime():
    assert datetime.today().strftime("%Y-%m-%d") == civic_strftime(datetime.today())


@pytest.mark.parametrize("asset", map(lambda i: i[0], assets))
def test_asset_datetime(asset: Asset):
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


@pytest.mark.parametrize("asset, asset_type", map(lambda i: (i[0], i[1]), assets))
def test_is_asset(asset: Asset, asset_type: AssetType):
    assert CivicIngestionModel(asset).is_asset(asset_type)


@pytest.mark.parametrize("asset, ingestion_type", map(lambda i: (i[0], i[2]), assets))
def test_is_ingestion(asset: Asset, ingestion_type: IngestionType):
    assert CivicIngestionModel(asset).is_ingestion(ingestion_type)


@pytest.mark.parametrize("asset, asset_type", map(lambda i: (i[0], i[1]), assets))
def test_asset_uri(asset: Asset, asset_type: AssetType):
    assert CivicIngestionModel(asset).get_asset_uri(asset_type) is not None


@pytest.mark.parametrize("asset", map(lambda i: i[0], assets))
def test_get_event(asset: Asset):
    ingested = CivicIngestionModel(asset)
    assert (ingested.get_event() is not None) == ingested.is_ingestion(
        EventIngestionModel
    )


@pytest.mark.parametrize("asset", map(lambda i: i[0], assets))
def test_get_session(asset: Asset):
    ingested = CivicIngestionModel(asset)
    assert (ingested.get_session() is not None) == ingested.is_ingestion(Session)


@pytest.mark.parametrize(
    "session, asset, merged",
    [
        (
            Session(session_datetime=None, video_uri=None, session_index=None),
            Asset(url=None),
            Session(session_datetime=None, video_uri=None, session_index=None),
        ),
        (
            Session(session_datetime=None, video_uri=None, session_index=None),
            Asset(url="url", asset_type="video"),
            Session(session_datetime=None, video_uri="url", session_index=0),
        ),
        (
            Session(session_datetime=None, video_uri="url", session_index=None),
            Asset(url=None, asset_type="video"),
            Session(session_datetime=None, video_uri="url", session_index=0),
        ),
    ],
)
def test_merge_session(session: Session, asset: Asset, merged: Session):
    assert merge_session(session, CivicIngestionModel(asset)) == merged


@pytest.mark.parametrize(
    "event, asset, merged",
    [
        (
            EventIngestionModel(body=None, sessions=None),
            Asset(url=None),
            EventIngestionModel(body=None, sessions=None),
        ),
        (
            EventIngestionModel(body=None, sessions=None),
            Asset(url="url", asset_type="agenda"),
            EventIngestionModel(body=None, sessions=None, agenda_uri="url"),
        ),
        (
            EventIngestionModel(
                body=None,
                sessions=[
                    Session(session_datetime=None, video_uri="video", session_index=0)
                ],
            ),
            Asset(url=None, committee_name="council", asset_type="agenda"),
            EventIngestionModel(
                body="council",
                sessions=[
                    Session(session_datetime=None, video_uri="video", session_index=0)
                ],
            ),
        ),
    ],
)
def test_merge_event(
    event: EventIngestionModel, asset: Asset, merged: EventIngestionModel
):
    assert merge_event(event, CivicIngestionModel(asset)) == merged


@pytest.mark.parametrize(
    "assets, event",
    [
        (
            [Asset(url=None)],
            None,
        ),
        (
            [
                Asset(
                    url="agenda_url",
                    asset_type="agenda",
                    meeting_date=datetime(2022, 1, 9, 1, 2, 3),
                    meeting_id="meeting 1",
                ),
                Asset(
                    url="minutes_url",
                    committee_name="committee",
                    asset_type="minutes",
                    meeting_id="meeting 1",
                ),
                Asset(
                    url="video_url",
                    asset_type="video",
                    meeting_date=datetime(2022, 1, 9, 1, 2, 3),
                    meeting_id="meeting 1",
                ),
            ],
            EventIngestionModel(
                body="committee",
                sessions=[
                    Session(
                        session_datetime=datetime(2022, 1, 9, 1, 2, 3),
                        video_uri="video_url",
                        external_source_id="meeting 1",
                        session_index=0,
                    )
                ],
                agenda_uri="agenda_url",
                minutes_uri="minutes_url",
                external_source_id="meeting 1",
            ),
        ),
    ],
)
def test_merge_assets(assets: AssetCollection, event: EventIngestionModel):
    assert merge_assets(assets) == event
