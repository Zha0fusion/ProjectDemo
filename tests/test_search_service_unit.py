"""search_service 的轻量级单元测试。"""
from datetime import datetime

import pytest

from backend.services import search_service


def test_parse_dt_handles_variants():
    """_parse_dt 应该支持 datetime、本地 ISO 字符串，并对非法输入返回 None。"""
    now = datetime.now()
    assert search_service._parse_dt(now) == now
    iso_str = now.isoformat()
    parsed = search_service._parse_dt(iso_str)
    assert isinstance(parsed, datetime)
    assert search_service._parse_dt("not-a-date") is None
    assert search_service._parse_dt(None) is None


def test_search_events_wraps_errors(monkeypatch):
    """当底层 Session 抛错时，search_events 应该转成 SearchError。"""

    class FakeSession:
        def query(self, *args, **kwargs):  # pragma: no cover - minimal stub
            raise RuntimeError("query failed")

        def close(self):
            pass

    monkeypatch.setattr(search_service, "SessionLocal", lambda: FakeSession())

    with pytest.raises(search_service.SearchError) as exc:
        search_service.search_events()

    assert "query failed" in str(exc.value)
