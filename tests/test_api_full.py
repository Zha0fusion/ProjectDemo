"""覆盖主要 API 的真连集成测试。
中文注释描述接口预期。
"""
from http import HTTPStatus

import pytest


@pytest.mark.requires_db
@pytest.mark.real_auth
def test_registration_api_create_and_cancel(client, db_ready, real_auth_header):
    """使用真实 JWT 完成报名与取消。"""
    resp = client.post("/api/registrations/", headers=real_auth_header, json={"session_id": 1})
    assert resp.status_code in (HTTPStatus.OK, HTTPStatus.BAD_REQUEST)
    if resp.status_code == HTTPStatus.OK:
        data = resp.get_json()
        assert data.get("status") in {"registered", "waiting"}

        cancel = client.post(
            "/api/registrations/cancel",
            headers=real_auth_header,
            json={"session_id": 1},
        )
        assert cancel.status_code == HTTPStatus.OK


@pytest.mark.requires_db
@pytest.mark.real_auth
def test_groups_api_list_and_create(client, db_ready, real_auth_header):
    """管理员可以列出并创建观众群组。"""
    list_resp = client.get("/api/groups", headers=real_auth_header)
    assert list_resp.status_code == HTTPStatus.OK

    create_resp = client.post(
        "/api/groups",
        headers=real_auth_header,
        json={"group_name": "VIP-Auto", "description": "auto group"},
    )
    assert create_resp.status_code in (HTTPStatus.CREATED, HTTPStatus.CONFLICT)


@pytest.mark.requires_db
@pytest.mark.real_auth
def test_analytics_overview_api(client, db_ready, real_auth_header):
    """analytics 概览接口应返回 200。"""
    resp = client.get("/api/analytics/events/1/overview", headers=real_auth_header)
    assert resp.status_code == HTTPStatus.OK
    body = resp.get_json()
    assert body.get("eid") == 1
