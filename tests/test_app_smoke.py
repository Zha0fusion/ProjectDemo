"""最小化 smoke 测试：确保应用可启动并返回基础健康信息。"""
from http import HTTPStatus


def test_index_returns_running_message(client):
    """GET / 应该返回后端存活提示。"""
    resp = client.get("/")
    assert resp.status_code == HTTPStatus.OK
    data = resp.get_json()
    assert data == {"message": "Event Registration System backend is running."}


def test_events_health_endpoint(client):
    """GET /api/events/health 应该返回 OK 状态。"""
    resp = client.get("/api/events/health")
    assert resp.status_code == HTTPStatus.OK
    data = resp.get_json()
    assert data.get("status") == "ok"
    assert "events api" in (data.get("message_en") or "")
