from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
import csv
import io

from backend.db import get_connection


ALLOWED_ROLES = {"visitor", "staff", "admin"}
ALLOWED_REG_STATUS: set[str] = {"registered", "waiting", "cancelled"}


class AdminError(Exception):
    """Raised when admin operations fail with a user-facing message."""


def list_users(keyword: str | None = None, role: str | None = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        clauses = []
        params: list[Any] = []

        if keyword:
            like = f"%{keyword.strip()}%"
            clauses.append("(name LIKE %s OR email LIKE %s)")
            params.extend([like, like])

        if role:
            if role not in ALLOWED_ROLES:
                raise AdminError("invalid role")
            clauses.append("role = %s")
            params.append(role)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = (
            "SELECT user_id, name, email, role, blocked_until "
            "FROM `USER` "
            f"{where_sql} "
            "ORDER BY user_id DESC"
        )

        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        return rows
    finally:
        conn.close()


def create_user(name: str, email: str, password: str, role: str) -> Dict[str, Any]:
    if role not in ALLOWED_ROLES:
        raise AdminError("invalid role")

    name = (name or "").strip()
    email = (email or "").strip()
    password = password or ""

    if not name:
        raise AdminError("name is required")
    if not email:
        raise AdminError("email is required")
    if not password:
        raise AdminError("password is required")

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id FROM `USER` WHERE email = %s", (email,))
            exists = cursor.fetchone()
            if exists:
                raise AdminError("email already exists")

            cursor.execute(
                """
                INSERT INTO `USER` (name, email, password, role)
                VALUES (%s, %s, %s, %s)
                """,
                (name, email, password, role),
            )
            user_id = cursor.lastrowid
        conn.commit()
        return {
            "user_id": user_id,
            "name": name,
            "email": email,
            "role": role,
            "blocked_until": None,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_user(
    user_id: int,
    name: Optional[str] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
    role: Optional[str] = None,
    blocked_until: Optional[datetime] = None,
) -> Dict[str, Any]:
    updates = []
    params: list[Any] = []

    if name is not None:
        updates.append("name = %s")
        params.append(name.strip())
    if email is not None:
        updates.append("email = %s")
        params.append(email.strip())
    if password is not None:
        updates.append("password = %s")
        params.append(password)
    if role is not None:
        if role not in ALLOWED_ROLES:
            raise AdminError("invalid role")
        updates.append("role = %s")
        params.append(role)
    if blocked_until is not None:
        updates.append("blocked_until = %s")
        params.append(blocked_until)

    if not updates:
        raise AdminError("no fields to update")

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id FROM `USER` WHERE user_id = %s", (user_id,))
            exists = cursor.fetchone()
            if not exists:
                raise AdminError("user not found")

            sql = f"UPDATE `USER` SET {', '.join(updates)} WHERE user_id = %s"
            cursor.execute(sql, params + [user_id])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    # return updated info
    users = list_users()
    for user in users:
        if user["user_id"] == user_id:
            return user
    raise AdminError("user not found")


def delete_user(user_id: int) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM `USER` WHERE user_id = %s", (user_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_tags() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT tag_id, tag_name FROM TAG ORDER BY tag_name ASC")
            return cursor.fetchall()
    finally:
        conn.close()


def create_tag(tag_name: str) -> Dict[str, Any]:
    tag_name = (tag_name or "").strip()
    if not tag_name:
        raise AdminError("tag_name is required")

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT tag_id FROM TAG WHERE tag_name = %s", (tag_name,))
            exists = cursor.fetchone()
            if exists:
                raise AdminError("tag already exists")

            cursor.execute(
                "INSERT INTO TAG (tag_name) VALUES (%s)",
                (tag_name,),
            )
            tag_id = cursor.lastrowid
        conn.commit()
        return {"tag_id": tag_id, "tag_name": tag_name}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_tag(tag_id: int, tag_name: str) -> Dict[str, Any]:
    tag_name = (tag_name or "").strip()
    if not tag_name:
        raise AdminError("tag_name is required")

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT tag_id FROM TAG WHERE tag_id = %s", (tag_id,))
            exists = cursor.fetchone()
            if not exists:
                raise AdminError("tag not found")

            cursor.execute(
                "UPDATE TAG SET tag_name = %s WHERE tag_id = %s",
                (tag_name, tag_id),
            )
        conn.commit()
        return {"tag_id": tag_id, "tag_name": tag_name}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_tag(tag_id: int) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM TAG WHERE tag_id = %s", (tag_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def force_set_registration(user_id: int, session_id: int, status: Literal["registered", "waiting", "cancelled"] = "registered") -> Dict[str, Any]:
    if status not in ALLOWED_REG_STATUS:
        raise AdminError("invalid registration status")

    now = datetime.now()
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT session_id, eid, current_registered
                FROM EVENT_SESSION
                WHERE session_id = %s
                FOR UPDATE
                """,
                (session_id,),
            )
            session_row = cursor.fetchone()
            if not session_row:
                raise AdminError("session not found")

            cursor.execute(
                """
                SELECT status
                FROM REGISTRATION
                WHERE user_id = %s AND session_id = %s
                FOR UPDATE
                """,
                (user_id, session_id),
            )
            existing = cursor.fetchone()

            delta_registered = 0
            queue_position = None

            if status == "registered":
                if existing:
                    prev_status = existing["status"]
                    if prev_status != "registered":
                        delta_registered = 1
                    cursor.execute(
                        """
                        UPDATE REGISTRATION
                        SET status = 'registered',
                            register_time = %s,
                            checkin_time = NULL,
                            queue_position = NULL
                        WHERE user_id = %s AND session_id = %s
                        """,
                        (now, user_id, session_id),
                    )
                else:
                    delta_registered = 1
                    cursor.execute(
                        """
                        INSERT INTO REGISTRATION (
                            user_id, session_id, register_time, status, checkin_time, queue_position
                        ) VALUES (%s, %s, %s, 'registered', NULL, NULL)
                        """,
                        (user_id, session_id, now),
                    )
            elif status == "waiting":
                cursor.execute(
                    "SELECT COUNT(*) AS cnt FROM REGISTRATION WHERE session_id = %s AND status = 'waiting'",
                    (session_id,),
                )
                queue_position = (cursor.fetchone()["cnt"] or 0) + 1
                if existing:
                    if existing["status"] == "registered":
                        delta_registered = -1
                    cursor.execute(
                        """
                        UPDATE REGISTRATION
                        SET status = 'waiting',
                            register_time = %s,
                            checkin_time = NULL,
                            queue_position = %s
                        WHERE user_id = %s AND session_id = %s
                        """,
                        (now, queue_position, user_id, session_id),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO REGISTRATION (
                            user_id, session_id, register_time, status, checkin_time, queue_position
                        ) VALUES (%s, %s, %s, 'waiting', NULL, %s)
                        """,
                        (user_id, session_id, now, queue_position),
                    )
            else:  # cancelled
                if existing:
                    if existing["status"] == "registered":
                        delta_registered = -1
                    cursor.execute(
                        """
                        UPDATE REGISTRATION
                        SET status = 'cancelled',
                            queue_position = NULL,
                            checkin_time = NULL
                        WHERE user_id = %s AND session_id = %s
                        """,
                        (user_id, session_id),
                    )

            if delta_registered != 0:
                cursor.execute(
                    """
                    UPDATE EVENT_SESSION
                    SET current_registered = GREATEST(0, current_registered + %s)
                    WHERE session_id = %s
                    """,
                    (delta_registered, session_id),
                )

        conn.commit()
        return {
            "user_id": user_id,
            "session_id": session_id,
            "status": status,
            "queue_position": queue_position,
            "updated_at": now.isoformat(),
        }
    except AdminError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_event_group_summary(eid: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    g.group_id,
                    g.group_name,
                    g.description,
                    g.is_default,
                    COUNT(eug.user_id) AS member_count
                FROM AUDIENCE_GROUP g
                LEFT JOIN EVENT_USER_GROUP eug
                    ON g.group_id = eug.group_id AND eug.eid = %s
                GROUP BY g.group_id, g.group_name, g.description, g.is_default
                ORDER BY g.group_name ASC
                """,
                (eid,),
            )
            return cursor.fetchall()
    finally:
        conn.close()


def list_group_members_for_event(eid: int, group_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT u.user_id, u.name, u.email, u.role
                FROM EVENT_USER_GROUP eug
                JOIN `USER` u ON u.user_id = eug.user_id
                WHERE eug.eid = %s AND eug.group_id = %s
                ORDER BY u.name ASC
                """,
                (eid, group_id),
            )
            return cursor.fetchall()
    finally:
        conn.close()


def assign_event_user_group(eid: int, user_id: int, group_id: int) -> Dict[str, Any]:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT group_id, group_name FROM AUDIENCE_GROUP WHERE group_id = %s", (group_id,))
            group_row = cursor.fetchone()
            if not group_row:
                raise AdminError("audience_group not found")

            cursor.execute("SELECT eid FROM EVENT WHERE eid = %s", (eid,))
            if not cursor.fetchone():
                raise AdminError("event not found")

            cursor.execute("SELECT user_id FROM `USER` WHERE user_id = %s", (user_id,))
            if not cursor.fetchone():
                raise AdminError("user not found")

            cursor.execute(
                """
                INSERT INTO EVENT_USER_GROUP (user_id, eid, group_id)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE group_id = VALUES(group_id)
                """,
                (user_id, eid, group_id),
            )
        conn.commit()
        return {
            "eid": eid,
            "user_id": user_id,
            "group": {
                "group_id": group_row["group_id"],
                "group_name": group_row["group_name"],
            },
        }
    except AdminError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def export_event_registrations_csv(eid: int) -> tuple[str, bytes]:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT title FROM EVENT WHERE eid = %s", (eid,))
            event_row = cursor.fetchone()
            if not event_row:
                raise AdminError("event not found")

            cursor.execute(
                """
                SELECT
                    s.session_id,
                    s.start_time,
                    s.end_time,
                    r.user_id,
                    u.name,
                    u.email,
                    u.role,
                    r.status,
                    r.queue_position,
                    r.checkin_time,
                    r.register_time,
                    g.group_name
                FROM EVENT_SESSION s
                LEFT JOIN REGISTRATION r ON r.session_id = s.session_id
                LEFT JOIN `USER` u ON u.user_id = r.user_id
                LEFT JOIN EVENT_USER_GROUP eug ON eug.user_id = r.user_id AND eug.eid = s.eid
                LEFT JOIN AUDIENCE_GROUP g ON g.group_id = eug.group_id
                WHERE s.eid = %s
                ORDER BY s.start_time ASC, r.register_time ASC
                """,
                (eid,),
            )
            rows = cursor.fetchall()

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "user_id",
                "name",
                "email",
                "role",
                "session_id",
                "session_start",
                "session_end",
                "status",
                "queue_position",
                "checkin_time",
                "register_time",
                "audience_group",
            ]
        )
        for r in rows:
            writer.writerow(
                [
                    r.get("user_id"),
                    r.get("name"),
                    r.get("email"),
                    r.get("role"),
                    r.get("session_id"),
                    r.get("start_time"),
                    r.get("end_time"),
                    r.get("status"),
                    r.get("queue_position"),
                    r.get("checkin_time"),
                    r.get("register_time"),
                    r.get("group_name"),
                ]
            )

        content = buffer.getvalue().encode("utf-8")
        safe_title = (event_row.get("title") or "event").replace(" ", "_")
        filename = f"event_{eid}_{safe_title}.csv"
        return filename, content
    finally:
        conn.close()
