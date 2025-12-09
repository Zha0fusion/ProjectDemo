# backend/auth_decorators.py
from functools import wraps
from typing import Callable, Any

from flask import request, jsonify, g

from backend.services.auth_service import get_user_by_token


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


def login_required(view_func: Callable) -> Callable:
    """
    要求用户必须登录的装饰器：
      - 成功时：在 g.current_user 中放入用户信息
      - 失败时：返回 401（中英双语）
    """
    @wraps(view_func)
    def wrapper(*args: Any, **kwargs: Any):
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

        # 在全局对象 g 上挂当前用户信息，后续视图可以直接使用
        g.current_user = user

        return view_func(*args, **kwargs)

    return wrapper


def roles_required(*roles: str) -> Callable:
    """
    角色校验装饰器：要求当前用户的 role 在给定 roles 中。
    需要先经过 login_required，或在本装饰器里检查 g.current_user。
    """

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(*args: Any, **kwargs: Any):
            current_user = getattr(g, "current_user", None)
            if not current_user:
                return (
                    jsonify(
                        {
                            "error": "unauthorized",
                            "message_zh": "未登录或 token 无效",
                            "message_en": "Not authenticated or token invalid",
                        }
                    ),
                    401,
                )

            role = current_user.get("role")
            if role not in roles:
                return (
                    jsonify(
                        {
                            "error": "forbidden",
                            "message_zh": "当前角色无权限执行此操作",
                            "message_en": "Current role is not allowed to perform this action",
                        }
                    ),
                    403,
                )

            return view_func(*args, **kwargs)

        return wrapper

    return decorator