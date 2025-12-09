# backend/api/registration_api.py
from flask import Blueprint, jsonify, request
from backend.db import get_cursor
from backend.services.registration_service import (
    register_for_session,
    cancel_registration,
    RegistrationError,
)

registration_bp = Blueprint("registration_api", __name__)


@registration_bp.post("/")
def create_registration():
    """
    报名接口（最小版）

    URL:
      POST /api/registrations/

    请求 JSON 示例：
      {
        "user_id": 1,
        "session_id": 3
      }

    返回示例：
      {
        "session_id": 3,
        "user_id": 1,
        "status": "registered",
        "queue_position": null,
        "message": "报名成功",
        "message_zh": "报名成功",
        "message_en": "Registration successful"
      }
    """
    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")
    session_id = data.get("session_id")

    # 基础校验
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

    try:
        # service 层已经返回中英双语结构，直接透传
        result = register_for_session(user_id=user_id, session_id=session_id)
        return jsonify(result), 200
    except RegistrationError as e:
        # 业务错误 -> 4xx
        err_msg = str(e)
        return (
            jsonify(
                {
                    "error": "registration_failed",
                    "message_zh": err_msg,
                    "message_en": "Registration failed: " + err_msg,
                }
            ),
            400,
        )
    except Exception as e:
        # 未预料错误 -> 5xx
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


@registration_bp.post("/cancel")
def cancel_registration_api():
    """
    取消报名接口

    URL:
      POST /api/registrations/cancel

    请求 JSON 示例：
      {
        "user_id": 1,
        "session_id": 1
      }

    返回示例：
      {
        "session_id": 1,
        "user_id": 1,
        "old_status": "registered",
        "new_status": "cancelled",
        "promoted_user": {
          "user_id": 2,
          "session_id": 1
        },
        "message_zh": "取消报名成功",
        "message_en": "Cancellation successful"
      }
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    session_id = data.get("session_id")

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

    try:
        # service 层已经返回中英双语结构，直接透传
        result = cancel_registration(user_id=user_id, session_id=session_id)
        return jsonify(result), 200
    except RegistrationError as e:
        err_msg = str(e)
        return (
            jsonify(
                {
                    "error": "registration_cancel_failed",
                    "message_zh": err_msg,
                    "message_en": "Cancel registration failed: " + err_msg,
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


@registration_bp.get("/session/<int:session_id>")
def list_registrations_for_session(session_id: int):
    """
    （辅助查看）列出某个场次的所有报名记录。
    URL: GET /api/registrations/session/<session_id>
    """

    sql = """
    SELECT
        r.user_id,
        u.name AS user_name,
        r.session_id,
        r.register_time,
        r.status,
        r.checkin_time,
        r.queue_position
    FROM REGISTRATION r
    JOIN `USER` u ON r.user_id = u.user_id
    WHERE r.session_id = %s
    ORDER BY
        CASE r.status
            WHEN 'registered' THEN 1
            WHEN 'waiting' THEN 2
            WHEN 'cancelled' THEN 3
            ELSE 4
        END,
        r.queue_position ASC,
        r.register_time ASC
    """
    with get_cursor() as cursor:
        cursor.execute(sql, (session_id,))
        rows = cursor.fetchall()
    return jsonify(rows)


@registration_bp.get("/user/<int:user_id>")
def list_user_registrations(user_id: int):
    """
    我的报名列表

    URL:
      GET /api/registrations/user/<user_id>

    示例：
      GET /api/registrations/user/1
    """
    sql = """
    SELECT
        r.session_id,
        s.eid,
        e.title AS event_title,
        e.location AS event_location,
        s.start_time,
        s.end_time,
        r.status,
        r.queue_position,
        r.register_time,
        r.checkin_time
    FROM REGISTRATION r
    JOIN EVENT_SESSION s ON r.session_id = s.session_id
    JOIN EVENT e ON s.eid = e.eid
    WHERE r.user_id = %s
    ORDER BY s.start_time ASC, r.register_time ASC
    """
    with get_cursor() as cursor:
        cursor.execute(sql, (user_id,))
        rows = cursor.fetchall()
    return jsonify(rows)
