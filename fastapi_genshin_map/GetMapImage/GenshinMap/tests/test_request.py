import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

import pytest

DIR = Path(__file__).parent

if TYPE_CHECKING:
    from httpx import Response


@pytest.mark.asyncio
async def test_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    with open(DIR / "labels.json", encoding="utf-8") as f:
        data = json.load(f)

    async def _fake_request(endpoint: str) -> Dict[str, Any]:
        return data

    monkeypatch.setattr("genshinmap.request._request", _fake_request)

    from genshinmap.models import Tree
    from genshinmap.request import MapID, get_labels

    assert await get_labels(MapID.teyvat) == [
        Tree.parse_obj(i) for i in data["tree"]
    ]


@pytest.mark.asyncio
async def test_points(monkeypatch: pytest.MonkeyPatch) -> None:
    with open(DIR / "points.json", encoding="utf-8") as f:
        data = json.load(f)

    async def _fake_request(endpoint: str) -> Dict[str, Any]:
        return data

    monkeypatch.setattr("genshinmap.request._request", _fake_request)

    from genshinmap.models import Point
    from genshinmap.request import MapID, get_points

    assert await get_points(MapID.teyvat) == [
        Point.parse_obj(i) for i in data["point_list"]
    ]


@pytest.mark.asyncio
async def test_maps(monkeypatch: pytest.MonkeyPatch) -> None:
    with open(DIR / "maps.json", encoding="utf-8") as f:
        data = json.load(f)

    async def _fake_request(endpoint: str) -> Dict[str, Any]:
        return data

    monkeypatch.setattr("genshinmap.request._request", _fake_request)

    from genshinmap.models import MapInfo
    from genshinmap.request import MapID, get_maps

    assert await get_maps(MapID.teyvat) == MapInfo.parse_obj(data["info"])


@pytest.mark.asyncio
async def test_page_label(monkeypatch: pytest.MonkeyPatch) -> None:
    with open(DIR / "page.json", encoding="utf-8") as f:
        data = json.load(f)

    async def _fake_request(endpoint: str) -> Dict[str, Any]:
        return data

    monkeypatch.setattr("genshinmap.request._request", _fake_request)

    from genshinmap.models import PageLabel
    from genshinmap.request import MapID, get_page_label

    assert await get_page_label(MapID.teyvat) == [
        PageLabel.parse_obj(i) for i in data["list"]
    ]


@pytest.mark.asyncio
async def test_anchor(monkeypatch: pytest.MonkeyPatch) -> None:
    with open(DIR / "anchors.json", encoding="utf-8") as f:
        data = json.load(f)

    async def _fake_request(endpoint: str) -> Dict[str, Any]:
        return data

    monkeypatch.setattr("genshinmap.request._request", _fake_request)

    from genshinmap.models import Anchor
    from genshinmap.request import MapID, get_anchors

    assert await get_anchors(MapID.teyvat) == [
        Anchor.parse_obj(i) for i in data["list"]
    ]


@pytest.mark.asyncio
async def test_get_spot_from_game(monkeypatch: pytest.MonkeyPatch) -> None:
    with open(DIR / "spots" / "spots.json", encoding="utf-8") as f:
        spots = f.read()
    with open(DIR / "spots" / "kinds.json", encoding="utf-8") as f:
        kinds = f.read()

    async def _post(
        self,
        url: str,
        json: Dict[str, Any],
        headers: Optional[Dict[str, Any]] = None,
    ) -> "Response":
        from httpx import Request, Response

        if url == "/spot_kind/sync_game_spot":
            # 1. 申请刷新
            return Response(
                200,
                text='{"retcode":0,"message":"OK","data":{}}',
                request=Request("POST", url),
            )
        else:
            # 3.获取坐标
            return Response(200, text=spots, request=Request("POST", url))

    async def _get(self, url: str, headers: Dict[str, Any]) -> "Response":
        from httpx import Request, Response

        return Response(200, text=kinds, request=Request("GET", url))

    monkeypatch.setattr("httpx._client.AsyncClient.post", _post)
    monkeypatch.setattr("httpx._client.AsyncClient.get", _get)

    from genshinmap.models import SpotKinds
    from genshinmap.request import MapID, get_spot_from_game

    spot, kind = await get_spot_from_game(MapID.teyvat, "")
    assert spot == {
        581061: [
            {
                "id": 2267179,
                "name": "",
                "content": "",
                "kind_id": 581061,
                "spot_icon": "",
                "x_pos": 416.3067626953125,
                "y_pos": 57.92724609375,
                "nick_name": "MingxuanGame1",
                "avatar_url": (
                    "https://img-static.mihoyo.com/avatar/avatar40004.png"
                ),
                "status": 1,
            }
        ]
    }
    assert kind == SpotKinds.parse_obj(json.loads(kinds)["data"])


@pytest.mark.asyncio
async def test_spot_status_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _post(
        self,
        url: str,
        json: Dict[str, Any],
        headers: Optional[Dict[str, Any]] = None,
    ) -> "Response":
        from httpx import Request, Response

        return Response(
            200,
            text='{"data":null,"message":"10分钟内只能操作一次","retcode":-2000}',
            request=Request("POST", url),
        )

    monkeypatch.setattr("httpx._client.AsyncClient.post", _post)
    from genshinmap.exc import StatusError
    from genshinmap.request import MapID, get_spot_from_game

    with pytest.raises(StatusError) as exc_info:
        await get_spot_from_game(MapID.teyvat, "")
        exc = exc_info.value
        assert exc.status == -2000
        assert exc.message == "10分钟内只能操作一次"


@pytest.mark.asyncio
async def test_internal_request_status_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _get(self, url: str) -> "Response":
        from httpx import Request, Response

        return Response(
            200,
            text='{"retcode":0,"message":"OK","data":{"test": 1}}',
            request=Request("GET", url),
        )

    monkeypatch.setattr("httpx._client.AsyncClient.get", _get)
    from genshinmap.request import _request

    assert await _request("") == {"test": 1}


@pytest.mark.asyncio
async def test_internal_request(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _get(self, url: str) -> "Response":
        from httpx import Request, Response

        return Response(
            200,
            text='{"retcode":1,"message":"err","data":null}',
            request=Request("GET", url),
        )

    monkeypatch.setattr("httpx._client.AsyncClient.get", _get)
    from genshinmap.exc import StatusError
    from genshinmap.request import _request

    with pytest.raises(StatusError) as exc_info:
        await _request("")
        exc = exc_info.value
        assert exc.status == 1
        assert exc.message == "err"


@pytest.mark.asyncio
@pytest.mark.parametrize(argnames="map_id", argvalues=[2, 7, 9])
async def test_connection(map_id) -> None:
    from genshinmap.request import (
        get_maps,
        get_labels,
        get_points,
        get_anchors,
        get_page_label,
    )

    assert await get_labels(map_id)
    assert await get_anchors(map_id)
    assert await get_page_label(map_id)
    assert await get_maps(map_id)
    assert await get_points(map_id)
