# backend/api/auth_api.py
from flask import Blueprint, jsonify, request

from backend.services.auth_service import (
    login,
    logout,
    get_user_by_token,
    AuthError,
)

auth_bp = Blueprint("auth_api", __name__)


def _extract_token_from_header() -> str | None:
    """
    从 Authorization 头中取出 Bearer token（JWT）。
    例如：Authorization: Bearer xxxxx.yyyyy.zzzzz
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return None

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


@auth_bp.post("/login")
def login_api():
    """
    登录接口（返回 JWT）

    URL:
      POST /api/auth/login
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    # 基础校验
    if not isinstance(email, str) or not isinstance(password, str):
        return (
            jsonify(
                {
                    "error": "invalid_request",
                    "message_zh": "email 和 password 必须为字符串",
                    "message_en": "email and password must be strings",
                }
            ),
            400,
        )

    try:
        result = login(email=email, password=password)
        return jsonify(result), 200
    except AuthError as e:
        err_msg = str(e)
        return (
            jsonify(
                {
                    "error": "auth_failed",
                    "message_zh": err_msg,
                    "message_en": "Authentication failed: " + err_msg,
                }
            ),
            401,
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


@auth_bp.post("/logout")
def logout_api():
    """
    登出接口（JWT 无状态，后端只是幂等调用 logout）

    URL:
      POST /api/auth/logout
    """
    token = _extract_token_from_header()
    if not token:
        return (
            jsonify(
                {
                    "error": "invalid_token",
                    "message_zh": "缺少或格式错误的 Authorization 头",
                    "message_en": "Missing or invalid Authorization header",
                }
            ),
            401,
        )

    logout(token)

    return (
        jsonify(
            {
                "message_zh": "已退出登录",
                "message_en": "Logged out successfully",
            }
        ),
        200,
    )


@auth_bp.get("/me")
def get_me():
    """
    获取当前登录用户信息

    URL:
      GET /api/auth/me
    """
    token = _extract_token_from_header()
    if not token:
        return (
            jsonify(
                {
                    "error": "invalid_token",
                    "message_zh": "缺少或格式错误的 Authorization 头",
                    "message_en": "Missing or invalid Authorization header",
                }
            ),
            401,
        )

    user = get_user_by_token(token)
    if not user:
        return (
            jsonify(
                {
                    "error": "invalid_token",
                    "message_zh": "token 无效或已过期",
                    "message_en": "Token is invalid or has expired",
                }
            ),
            401,
        )

    return jsonify(user), 200