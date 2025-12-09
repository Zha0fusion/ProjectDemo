"""数据库真连的基础覆盖。
中文注释描述每个步骤，其余代码保持英文。
"""
from http import HTTPStatus
from datetime import datetime

import pytest

from backend.services.registration_service import register_for_session, cancel_registration
from tests.db_utils import create_event_with_session, insert_users


@pytest.mark.requires_db
@pytest.mark.real_auth
def test_auth_login_and_token(client, db_ready):
    """验证 /api/auth/login 能返回 token。"""
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "password_admin"},
    )
    assert resp.status_code == HTTPStatus.OK
    data = resp.get_json()
    assert data.get("token")
    assert data.get("user", {}).get("role") == "admin"


@pytest.mark.requires_db
def test_register_and_cancel_flow_db(db_ready):
    """直接调用 service，确保容量更新与取消逻辑在真实 DB 生效。"""
    insert_users(10)
    session_info = create_event_with_session(capacity=2, waiting=3)
    sid = session_info["session_id"]

    # 首次报名 -> registered
    first = register_for_session(user_id=1, session_id=sid)
    assert first["status"] == "registered"

    # 第二次报名 -> registered, capacity 达到 2
    second = register_for_session(user_id=2, session_id=sid)
    assert second["status"] == "registered"

    # 第三次报名 -> waiting
    third = register_for_session(user_id=3, session_id=sid)
    assert third["status"] == "waiting"
    assert third["queue_position"] == 1

    # 取消第二个用户，等待转正
    cancel_res = cancel_registration(user_id=2, session_id=sid)
    assert cancel_res["message_en"].startswith("Cancellation")

    # 转正后检查 waiting 队列重新计算
    promoted = register_for_session(user_id=4, session_id=sid)
    assert promoted["status"] == "waiting"
    # 取消操作会让原候补转正，因此新的候补应从 1 开始
    assert promoted["queue_position"] == 1


@pytest.mark.requires_db
def test_event_detail_api(client, db_ready):
    """事件详情 API 应能返回基础字段。"""
    resp = client.get("/api/events/1/detail")
    assert resp.status_code == HTTPStatus.OK
    body = resp.get_json()
    assert body.get("eid") == 1
    assert isinstance(body.get("sessions"), list)
