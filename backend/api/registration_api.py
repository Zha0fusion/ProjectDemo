# backend/api/registration_api.py
from flask import Blueprint, jsonify, request, g
from datetime import datetime, timezone
from backend.db import get_cursor, get_connection
from backend.auth_decorators import login_required
from backend.services.registration_service import (
    register_for_session,
    cancel_registration,
    RegistrationError,
)
from backend.utils.qrcode_utils import (
    build_checkin_payload,
    generate_qr_png_bytes,
    send_qr_response,
)


registration_bp = Blueprint("registration_api", __name__)


@registration_bp.post("/")
@login_required
def create_registration():
    """
    报名接口（必须登录）

    URL:
      POST /api/registrations/

    请求 JSON 示例：
      {
        "session_id": 3
      }

    说明：
      - user_id 不再从请求体传，统一从当前登录用户(g.current_user)获取
    """
    data = request.get_json(silent=True) or {}

    current_user = g.current_user

     # ---- 新增：封禁检查 ----
    blocked_until = current_user.get("blocked_until")
    if blocked_until:
        # 如果从 token 里是字符串，转成 datetime 再比较
        if isinstance(blocked_until, str):
            from datetime import datetime
            blocked_until_dt = datetime.fromisoformat(blocked_until)
        else:
            blocked_until_dt = blocked_until

        from datetime import datetime as dt
        if blocked_until_dt > dt.now(timezone.utc):
            return (
                jsonify(
                    {
                        "error": "user_blocked",
                        "message_zh": f"账号已被封禁，解封时间：{blocked_until_dt}",
                        "message_en": f"User is blocked until {blocked_until_dt}",
                    }
                ),
                403,
            )
    # ---- 封禁检查结束 ----

    user_id = current_user["user_id"]
    session_id = data.get("session_id")

    # 基础校验：只需要校验 session_id
    if not isinstance(session_id, int):
        return (
            jsonify(
                {
                    "error": "invalid_request",
                    "message_zh": "session_id 必须为整数",
                    "message_en": "session_id must be an integer",
                }
            ),
            400,
        )

    try:
        result = register_for_session(user_id=user_id, session_id=session_id)
        return jsonify(result), 200
    except RegistrationError as e:
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
@login_required
def cancel_registration_api():
    """
    取消报名接口（必须登录）

    URL:
      POST /api/registrations/cancel

    请求 JSON 示例：
      {
        "session_id": 1
      }

    说明：
      - user_id 不再从请求体传，统一从当前登录用户获取
    """
    data = request.get_json(silent=True) or {}

    current_user = g.current_user
    user_id = current_user["user_id"]
    session_id = data.get("session_id")

    if not isinstance(session_id, int):
        return (
            jsonify(
                {
                    "error": "invalid_request",
                    "message_zh": "session_id 必须为整数",
                    "message_en": "session_id must be an integer",
                }
            ),
            400,
        )

    try:
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
    （目前保留）按 user_id 查看报名列表
    URL:
      GET /api/registrations/user/<user_id>

    未来如果只允许用户自己看自己的，可以下掉这个接口，
    或仅对管理员开放（配合 admin_required）。
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


@registration_bp.get("/me")
@login_required
def list_my_registrations():
    """
    当前登录用户的报名列表（推荐前端使用这个接口）

    URL:
      GET /api/registrations/me
    """
    current_user = g.current_user
    user_id = current_user["user_id"]

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

@registration_bp.get("/qrcode/<int:session_id>")
@login_required
def get_registration_qrcode(session_id: int):
    """
    获取“当前登录用户在某场次”的签到二维码（PNG 图片）。

    URL:
      GET /api/registrations/qrcode/<session_id>

    行为：
      - 如果当前用户没有报名该场次（REGISTRATION 中找不到记录），返回 404。
      - 否则生成包含 {user_id, session_id} 的 JSON，编码为二维码返回 PNG。
    """
    current_user = g.current_user
    user_id = current_user["user_id"]

    # 确认当前用户确实报了这个场次（不论 registered / waiting / cancelled）
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT status
                FROM REGISTRATION
                WHERE user_id = %s AND session_id = %s
                """,
                (user_id, session_id),
            )
            row = cursor.fetchone()

        if not row:
            return (
                jsonify(
                    {
                        "error": "registration_not_found",
                        "message_zh": "你没有该场次的报名记录，无法生成二维码",
                        "message_en": "No registration found for this session",
                    }
                ),
                404,
            )

        # 构造二维码内容（JSON 字符串）
        data_str = build_checkin_payload(user_id=user_id, session_id=session_id)
        # 生成 PNG 二进制
        qr_buf = generate_qr_png_bytes(data_str)

        # 返回图片响应
        # 文件名可以按需自定义，例如 event_<session_id>_ticket.png
        return send_qr_response(qr_buf, filename=f"ticket_session_{session_id}.png")

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
    finally:
        conn.close()