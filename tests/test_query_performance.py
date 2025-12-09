"""查询效率与可扩展性简单基准。
中文注释描述性能阈值。
"""
from time import perf_counter

import pytest

from backend.services import search_service
from backend.services.analytic_service import get_event_overview


@pytest.mark.requires_db
@pytest.mark.perf
def test_search_events_perf(db_ready):
    """search_events 在示例数据下应在 1s 内返回。"""
    start = perf_counter()
    res = search_service.search_events(limit=100, offset=0)
    elapsed = perf_counter() - start
    assert isinstance(res, list)
    assert elapsed < 1.0


@pytest.mark.requires_db
@pytest.mark.perf
def test_analytics_overview_perf(db_ready):
    """get_event_overview 计算应在 1s 内完成。"""
    start = perf_counter()
    data = get_event_overview(1)
    elapsed = perf_counter() - start
    assert data.get("eid") == 1
    assert elapsed < 1.0
