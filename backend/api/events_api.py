# backend/api/events_api.py
from flask import Blueprint, jsonify, request

from backend.db import get_cursor
from backend.services.event_service import create_event_with_sessions, EventError

events_bp = Blueprint("events_api", __name__)


@events_bp.get("/health")
def events_health():
    # 健康检查接口：仅用于确认服务存活
    return jsonify(
        {
            "status": "ok",
            "message_zh": "events api 正常运行",
            "message_en": "events api alive",
        }
    )


@events_bp.post("/")
def create_event():
    """
    创建活动 + 场次

    URL:
      POST /api/events/

    请求 JSON 示例：
      {
        "title": "Data Science Talk",
        "description": "Introductory sharing session for undergraduates",
        "location": "Teaching Building A101",
        "status": "published",
        "sessions": [
          {
            "start_time": "2025-12-20T14:00:00",
            "end_time": "2025-12-20T16:00:00",
            "capacity": 50,
            "waiting_list_limit": 10
          },
          ...
        ]
      }
    """
    data = request.get_json(silent=True) or {}

    try:
        result = create_event_with_sessions(data)
        # 创建成功返回 201
        # 这里也补充双语提示，便于前端展示
        result.setdefault("message_zh", "活动创建成功")
        result.setdefault("message_en", "Event created successfully")
        return jsonify(result), 201
    except EventError as e:
        return (
            jsonify(
                {
                    "error": "event_create_failed",
                    "message_zh": str(e),
                    "message_en": "Failed to create event: " + str(e),
                }
            ),
            400,
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "error": "server_error",
                    "message_zh": "服务器内部错误",
                    "message_en": "Internal server error: " + str(e),
                }
            ),
            500,
        )


@events_bp.get("/")
def list_events():
    """
    列出所有已发布的活动（不区分场次）。
    URL: GET /api/events/
    """
    sql = """
    SELECT
        e.eid,
        e.title,
        e.description,
        e.location,
        e.status,
        e.created_at,
        e.updated_at
    FROM EVENT e
    WHERE e.status = 'published'
    ORDER BY e.created_at DESC
    """
    with get_cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
    # 这里返回的是列表数据，本身不需要 message_zh / message_en，
    # 前端一般直接展示数据就行，如有需要可以在外层再包一层。
    return jsonify(rows)


@events_bp.get("/<int:eid>/sessions")
def list_event_sessions(eid: int):
    """
    列出某个活动的所有场次。
    URL: GET /api/events/<eid>/sessions
    """
    sql = """
    SELECT
        s.session_id,
        s.eid,
        s.start_time,
        s.end_time,
        s.capacity,
        s.current_registered,
        s.waiting_list_limit,
        s.status
    FROM EVENT_SESSION s
    WHERE s.eid = %s
    ORDER BY s.start_time ASC
    """
    with get_cursor() as cursor:
        cursor.execute(sql, (eid,))
        rows = cursor.fetchall()
    return jsonify(rows)


@events_bp.get("/<int:eid>/detail")
def get_event_detail(eid: int):
    """
    活动详情：返回活动基本信息 + 该活动下的所有场次。

    URL: GET /api/events/<eid>/detail
    """
    # 1. 查询活动基本信息
    sql_event = """
    SELECT
        e.eid,
        e.title,
        e.description,
        e.location,
        e.status,
        e.type_id,
        e.created_at,
        e.updated_at
    FROM EVENT e
    WHERE e.eid = %s
    """
    with get_cursor() as cursor:
        cursor.execute(sql_event, (eid,))
        event = cursor.fetchone()

        if not event:
            return (
                jsonify(
                    {
                        "error": "not_found",
                        "message_zh": "活动不存在",
                        "message_en": "Event not found",
                    }
                ),
                404,
            )

        # 2. 查询该活动的所有场次
        sql_sessions = """
        SELECT
            s.session_id,
            s.eid,
            s.start_time,
            s.end_time,
            s.capacity,
            s.current_registered,
            s.waiting_list_limit,
            s.status
        FROM EVENT_SESSION s
        WHERE s.eid = %s
        ORDER BY s.start_time ASC
        """
        cursor.execute(sql_sessions, (eid,))
        sessions = cursor.fetchall()

    # 3. 拼出统一结构
    event["sessions"] = sessions
    return jsonify(event)