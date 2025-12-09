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
def mock_auth(monkeypatch):
    """全局打桩鉴权，避免依赖真实数据库用户。"""
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
