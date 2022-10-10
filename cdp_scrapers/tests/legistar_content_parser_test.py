import pytest

from cdp_scrapers.legistar_utils import parse_video_page_url


@pytest.mark.parametrize(
    "video_page_url, client, expected_caption_uri, expected_video_uri",
    [
        (
            # parser1
            "https://kingcounty.legistar.com/Video.aspx?Mode=Granicus&ID1=8825&G="
                + "D64F10C7-C196-4013-ABF6-0DA49839DE59&Mode2=Video",
            "kingcounty",
            None,
            "http://archive-media.granicus.com:443/OnDemand/king/king_80aac332-5f77"
                + "-43b4-9259-79d108cdbff1.mp4",
        ),
        (
            # parser1
            "https://milwaukee.granicus.com/player/clip/3338?view_id=2&"
                + "redirect=true&h=554d836741a2ef17c85f81f393fdd2a0",
            "milwaukee",
            None,
            "https://archive-media2.granicus.com/OnDemand/milwaukee/"
                + "milwaukee_ab8846f8-7591-4c06-bffe-8f3953346af2.mp4",
        ),
        (
            # parser2
            "https://denver.granicus.com/player/clip/15076?view_id=180&"
                + "redirect=true&h=061d42ee62c77b4008bd1841ecd023ad",
            "denver",
            None,
            "http://archive-media.granicus.com:443/OnDemand/denver/"
                + "denver_7f5b308a-1a82-48dc-8f1b-ce7767ee2e9b.mp4",
        ),
        (
            # parser3
            "http://boston.granicus.com/player/clip/324?view_id=1&redirect=true&"
                + "h=09f2d7e09d3f0ebcdb959f089e3f922a",
            "boston",
            "http://boston.granicus.com//videos/324/captions.vtt",
            "https://archive-stream.granicus.com/OnDemand/_definst_/mp4:boston/"
                + "boston_3260c449-dba9-4b54-8cdd-38bf31147d98.mp4/playlist.m3u8",
        ),
        (
            # parser3
            "https://corpuschristi.granicus.com/player/clip/1694?view_id=2&"
                + "redirect=true&h=a22666c178424e903474d594dde1fe3a",
            "corpuschristi",
            "http://corpuschristi.granicus.com//videos/1694/captions.vtt",
            "https://archive-stream.granicus.com/OnDemand/_definst_/mp4:"
                + "corpuschristi/corpuschristi_f91b021b-b5da-45bb-b5fc"
                + "-ec7c7d8c2d32.mp4/playlist.m3u8",
        ),
        (
            # parser3
            "http://elpasotexas.granicus.com/player/clip/224?view_id=1"
                + "&redirect=true&h=0a4363d1c34a910f97dfc42636b53cf1",
            "elpasotexas",
            "http://elpasotexas.granicus.com//videos/224/captions.vtt",
            "https://archive-stream.granicus.com/OnDemand/_definst_/mp4"
                + ":elpasotexas/elpasotexas_c654bf29-2d1b-4de3-826d-9c5746511f6a"
                + ".mp4/playlist.m3u8",
        ),
        (
            # parser4
            "https://longbeach.granicus.com/MediaPlayer.php?view_id=84&clip_id=13404",
            "longbeach",
            None,
            "http://archive-media.granicus.com:443/OnDemand/longbeach/"
                + "longbeach_cf37b162-9817-428a-9fcd-b72daca8062a.mp4",
        ),
        (
            # parser4
            "https://richmondva.granicus.com/MediaPlayer.php?view_id=1&clip_id=3271",
            "richmondva",
            None,
            "http://archive-media.granicus.com:443/OnDemand/richmondva/"
                + "richmondva_870c84ae-9614-44a3-a65b-a3e79c56426d.mp4",
        ),
    ],
)
def test_str_simplifed(
    video_page_url: str, client: str, expected_caption_uri: str, expected_video_uri: str
):
    assert (
        parse_video_page_url(video_page_url, client)[0].caption_uri
        == expected_caption_uri
    )
    assert (
        parse_video_page_url(video_page_url, client)[0].video_uri == expected_video_uri
    )
