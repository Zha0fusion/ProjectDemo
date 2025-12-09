# backend/services/auth_service.py
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import jwt

from backend.db import get_connection
from backend.config import load_config

config = load_config()


class AuthError(Exception):
    """认证/授权相关业务错误（登录失败、token 无效等）"""
    pass


def verify_password(plain_password: str, stored_password: str) -> bool:
    """
    开发阶段版本：明文比对。
    之后切换到 bcrypt 时再改这里。
    """
    return plain_password == stored_password


def _create_access_token(user_id: int, role: str) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    expire = now + config.JWT_ACCESS_TOKEN_EXPIRES

    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    token = jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)

    return {
        "token": token,
        "expires_at": expire.isoformat(),
    }


def login(email: str, password: str) -> Dict[str, Any]:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    user_id,
                    name,
                    email,
                    password,
                    role,
                    blocked_until
                FROM `USER`
                WHERE email = %s
                """,
                (email,),
            )
            user = cursor.fetchone()

        print("DEBUG login: email=", email, "password_input=", password)

        if not user:
            print("DEBUG login: user not found")
            raise AuthError("wrong email or password")

        print("DEBUG login: db_password=", user["password"])

        if not verify_password(password, user["password"]):
            print("DEBUG login: password verify failed")
            raise AuthError("wrong email or password")

        # 注意：不在这里拦 blocked_until，blocked_until 只限制报名等业务

        token_data = _create_access_token(user["user_id"], user["role"])

        return {
            "user": {
                "user_id": user["user_id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
            },
            "token": token_data["token"],
            "expires_at": token_data["expires_at"],
            "message_zh": "登录成功",
            "message_en": "Login successful",
        }
    finally:
        conn.close()


def get_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(
            token,
            config.JWT_SECRET_KEY,
            algorithms=[config.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    user_id,
                    name,
                    email,
                    role,
                    blocked_until
                FROM `USER`
                WHERE user_id = %s
                """,
                (int(user_id),),
            )
            user = cursor.fetchone()
    finally:
        conn.close()

    if not user:
        return None

    return {
        "user_id": user["user_id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "blocked_until": user.get("blocked_until"),
    }


def logout(token: str) -> None:
    """
    JWT 无状态，这里是幂等空操作。
    """
    return