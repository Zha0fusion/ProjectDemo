# backend/api/checkin_api.py
from datetime import datetime

from flask import Blueprint, jsonify, request

from backend.auth_decorators import login_required, roles_required

from backend.db import get_cursor

checkin_bp = Blueprint("checkin_api", __name__)


@checkin_bp.post("/")
@login_required
@roles_required("staff", "admin")
def checkin():
    """
    签到接口（根据 user_id + session_id）。

    URL:
      POST /api/checkin/

    请求 JSON 示例：
      {
        "user_id": 1,
        "session_id": 3
      }

    返回示例（首次签到成功）：
      {
        "user_id": 1,
        "session_id": 3,
        "status": "registered",
        "checkin_time": "2025-12-09T19:30:00",
        "message_zh": "签到成功",
        "message_en": "Check-in successful"
      }

    返回示例（已签到过）：
      {
        "user_id": 1,
        "session_id": 3,
        "status": "registered",
        "checkin_time": "2025-12-09T19:30:00",
        "message_zh": "已签到，无需重复签到",
        "message_en": "Already checked in, no need to check in again"
      }
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    session_id = data.get("session_id")

    # 基础校验：简单检查 user_id / session_id 是否为整数
    if not isinstance(user_id, int) or not isinstance(session_id, int):
        return (
            jsonify(
                {
                    "error": "invalid_request",
                    "message_zh": "user_id 和 session_id 必须为整数",
                    "message_en": "user_id and session_id must be integers",
                }
            ),
            400,
        )

    with get_cursor() as cursor:
        # 1) 查询报名记录，确认用户是否有该场次的报名
        cursor.execute(
            """
            SELECT
                status,
                checkin_time
            FROM REGISTRATION
            WHERE user_id = %s AND session_id = %s
            """,
            (user_id, session_id),
        )
        row = cursor.fetchone()

        if not row:
            # 没有报名记录，不允许签到
            return (
                jsonify(
                    {
                        "error": "registration_not_found",
                        "message_zh": "该用户在此场次没有报名记录",
                        "message_en": "No registration found for this user and session",
                    }
                ),
                404,
            )

        status = row["status"]
        checkin_time = row["checkin_time"]

        # 只允许已报名成功（registered）的记录签到
        if status != "registered":
            return (
                jsonify(
                    {
                        "error": "invalid_status",
                        "message_zh": f"当前状态为 {status}，不能签到",
                        "message_en": f"Current status is {status}, check-in is not allowed",
                    }
                ),
                400,
            )

        # 已经有签到时间，视为重复签到，直接返回原签到时间
        if checkin_time is not None:
            return (
                jsonify(
                    {
                        "user_id": user_id,
                        "session_id": session_id,
                        "status": status,
                        "checkin_time": checkin_time,
                        "message_zh": "已签到，无需重复签到",
                        "message_en": "Already checked in, no need to check in again",
                    }
                ),
                200,
            )

        # 2) 执行签到：更新 REGISTRATION.checkin_time
        now = datetime.now()
        cursor.execute(
            """
            UPDATE REGISTRATION
            SET checkin_time = %s
            WHERE user_id = %s AND session_id = %s
            """,
            (now, user_id, session_id),
        )

    # 提示：如果 get_cursor 内部没有自动提交，可以在 db 层统一处理事务。
    # 这里假设 get_cursor 使用的连接为 autocommit。

    return (
        jsonify(
            {
                "user_id": user_id,
                "session_id": session_id,
                "status": "registered",
                "checkin_time": now.isoformat(),
                "message_zh": "签到成功",
                "message_en": "Check-in successful",
            }
        ),
        200,
    )


@checkin_bp.get("/history")
@login_required
@roles_required("staff", "admin")
def checkin_history():
    """Return recent persisted check-ins ordered by time desc."""
    limit_param = request.args.get("limit", 50)
    try:
        limit = max(1, min(int(limit_param), 200))
    except (TypeError, ValueError):
        limit = 50

    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                r.user_id,
                u.name AS user_name,
                r.session_id,
                r.checkin_time,
                s.start_time,
                s.end_time,
                e.title AS event_title
            FROM REGISTRATION r
            JOIN `USER` u ON u.user_id = r.user_id
            JOIN EVENT_SESSION s ON s.session_id = r.session_id
            JOIN EVENT e ON e.eid = s.eid
            WHERE r.checkin_time IS NOT NULL
            ORDER BY r.checkin_time DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append(
            {
                "user_id": row["user_id"],
                "user_name": row.get("user_name"),
                "session_id": row["session_id"],
                "event_title": row.get("event_title"),
                "checkin_time": row["checkin_time"].isoformat() if row.get("checkin_time") else None,
                "start_time": row.get("start_time").isoformat() if row.get("start_time") else None,
                "end_time": row.get("end_time").isoformat() if row.get("end_time") else None,
            }
        )

    return jsonify(result)
