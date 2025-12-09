"""Pytest fixtures for Flask app with auth mocking.
中文注释说明测试支架的用途，其余代码保持英文。
"""
import sys
from pathlib import Path

import pytest

# 将项目根目录加入 sys.path，避免找不到 backend 包
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app import create_app
from tests.db_utils import reset_and_seed, check_db_connection


@pytest.fixture(scope="session")
def app():
    """创建测试模式的 Flask 应用，避免真实服务器启动。"""
    flask_app = create_app("testing")
    flask_app.config.update(TESTING=True)
    return flask_app


@pytest.fixture()
def client(app):
    """提供 test_client，方便进行 API 调用。"""
    return app.test_client()


@pytest.fixture(autouse=True)
def mock_auth(monkeypatch, request):
    """全局打桩鉴权，除非标记 real_auth。"""
    if request.node.get_closest_marker("real_auth"):
        yield
        return

    def _fake_get_user(token):
        if token == "test-token":
            return {
                "user_id": 1,
                "name": "Test User",
                "email": "test@example.com",
                "role": "staff",
                "blocked_until": None,
            }
        return None

    monkeypatch.setattr("backend.auth_decorators.get_user_by_token", _fake_get_user)
    yield


@pytest.fixture()
def auth_header():
    """默认的 Bearer 头，用于通过 login_required/roles_required。"""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture()
def real_auth_header(db_ready, client):
    """从 /api/auth/login 获取真实 JWT，用于需要 real_auth 的测试。"""
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "password_admin"},
    )
    data = resp.get_json()
    token = data.get("token")
    return {"Authorization": f"Bearer {token}"}


# ===== 数据库相关的标记与基线准备 =====


def pytest_configure(config):
    config.addinivalue_line("markers", "requires_db: 依赖真实数据库的测试")
    config.addinivalue_line("markers", "real_auth: 使用真实鉴权，禁用打桩")
    config.addinivalue_line("markers", "perf: 性能/效率类测试")


@pytest.fixture(scope="session")
def db_ready():
    """探测数据库并重建 schema，失败则 skip。"""
    try:
        check_db_connection()
        reset_and_seed()
    except Exception as exc:  # pragma: no cover - 仅在 CI 无 DB 时触发
        pytest.skip(f"requires real DB: {exc}")
    return True
