# backend/api/auth_api.py
from flask import Blueprint, jsonify, request

from backend.services.auth_service import (
    login,
    logout,
    get_user_by_token,
    register,
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
                    "message_zh": "Email and password must be strings",
                    "message_en": "Email and password must be strings",
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
                    "message_zh": "Internal server error: " + str(e),
                    "message_en": "Internal server error: " + str(e),
                }
            ),
            500,
        )


@auth_bp.post("/register")
def register_api():
    """注册接口

    URL:
      POST /api/auth/register

    请求 JSON 示例：
      {
        "name": "Alice",
        "email": "alice@example.com",
        "password": "password123"
      }
    """
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not isinstance(name, str) or not isinstance(email, str) or not isinstance(password, str):
        return (
            jsonify(
                {
                    "error": "invalid_request",
                    "message_zh": "Name, email and password must be strings",
                    "message_en": "Name, email and password must be strings",
                }
            ),
            400,
        )

    try:
        result = register(name=name, email=email, password=password)
        # 注册成功返回 201
        return jsonify(result), 201
    except AuthError as e:
        err_msg = str(e)
        # email 重复可以视为冲突
        status = 409 if "already registered" in err_msg else 400
        return (
            jsonify(
                {
                    "error": "register_failed",
                    "message_zh": err_msg,
                    "message_en": "Registration failed: " + err_msg,
                }
            ),
            status,
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "error": "server_error",
                    "message_zh": "Internal server error: " + str(e),
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
                    "message_zh": "Missing or invalid Authorization header",
                    "message_en": "Missing or invalid Authorization header",
                }
            ),
            401,
        )

    logout(token)

    return (
        jsonify(
            {
                "message_zh": "Logged out successfully",
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
                    "message_zh": "Missing or invalid Authorization header",
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
                    "message_zh": "Token is invalid or has expired",
                    "message_en": "Token is invalid or has expired",
                }
            ),
            401,
        )

    return jsonify(user), 200