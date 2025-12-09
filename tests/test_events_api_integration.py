"""针对 events_api 的轻量集成测试，使用打桩避免真实数据库。"""
from http import HTTPStatus

import pytest


def test_search_events_stubbed(monkeypatch, client):
    """搜索接口应返回打桩数据并保持 200。"""
    stubbed = [
        {
            "eid": 123,
            "title": "Stub Event",
            "description": "",
            "location": "Hall A",
            "status": "published",
            "type_id": 1,
            "created_at": None,
            "updated_at": None,
            "tags": ["Art"],
            "sessions": [],
        }
    ]

    monkeypatch.setattr("backend.api.events_api.search_events", lambda **_: stubbed)

    resp = client.get("/api/events/search?limit=2")
    assert resp.status_code == HTTPStatus.OK
    data = resp.get_json()
    assert isinstance(data, list)
    assert data[0]["eid"] == 123


def test_search_events_invalid_limit(client):
    """非法 limit 应导致 400。"""
    resp = client.get("/api/events/search?limit=abc")
    assert resp.status_code == HTTPStatus.BAD_REQUEST
    body = resp.get_json()
    assert body.get("error") == "invalid_request"


def test_create_event_requires_auth(client):
    """缺少 Authorization 时应返回 401。"""
    resp = client.post("/api/events/", json={"title": "No Auth"})
    assert resp.status_code == HTTPStatus.UNAUTHORIZED


def test_create_event_success(monkeypatch, client, auth_header):
    """创建活动走打桩逻辑，确保 201 与双语消息。"""

    def _fake_create(payload):  # pragma: no cover - 直接返回固定数据
        return {"eid": 999, "payload": payload}

    monkeypatch.setattr(
        "backend.api.events_api.create_event_with_sessions", _fake_create
    )

    resp = client.post(
        "/api/events/",
        headers=auth_header,
        json={"title": "Demo", "sessions": []},
    )
    assert resp.status_code == HTTPStatus.CREATED
    data = resp.get_json()
    assert data.get("eid") == 999
    assert "message_zh" in data and "message_en" in data
