from datetime import datetime, timedelta
from typing import List, Dict, Any

from backend.db import get_connection


class EventError(Exception):
    """Event business error"""
    pass


ALLOWED_STATUS = ("draft", "published", "closed", "archived")


def create_event_with_sessions(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    创建一个 EVENT 以及若干 EVENT_SESSION（放在同一事务里）。

    预期 payload 结构：
      {
        "title": str,
        "description": str | None,
        "location": str | None,
        "status": "draft" | "published",
        "type_id": int (可选，缺省为 1),
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

    title = (payload.get("title") or "").strip()
    description = payload.get("description")
    location = payload.get("location")
    status = (payload.get("status") or "draft").strip()
    image_url = payload.get("image_url")
    allow_multi_session = bool(payload.get("allow_multi_session", False))

    if not title:
        raise EventError("title 不能为空")

    if status not in ALLOWED_STATUS:
        raise EventError("status must be one of: draft, published, closed, archived")

    # 新增：活动类型，前端可以传 type_id，不传就默认为 1
    type_id = payload.get("type_id", 1)

    sessions: List[Dict[str, Any]] = payload.get("sessions") or []
    if not isinstance(sessions, list) or len(sessions) == 0:
        raise EventError("At least one session is required")

    now = datetime.now()

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. 插入 EVENT，这里已经包含 type_id 字段
            cursor.execute(
                """
                INSERT INTO EVENT (
                    title, description, location, status,
                    type_id, image_url, allow_multi_session,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (title, description, location, status, type_id, image_url, allow_multi_session, now, now),
            )
            eid = cursor.lastrowid

            created_sessions: List[Dict[str, Any]] = []

            # 2. 插入每一个 EVENT_SESSION
            for s in sessions:
                start_time = s.get("start_time")
                end_time = s.get("end_time")
                capacity = s.get("capacity")
                waiting_list_limit = s.get("waiting_list_limit", 0)

                # 简单校验
                if not start_time or not end_time:
                    raise EventError("Each session must include start_time and end_time")
                if not isinstance(capacity, int) or capacity <= 0:
                    raise EventError("session.capacity must be a positive integer")

                if not isinstance(waiting_list_limit, int) or waiting_list_limit < 0:
                    waiting_list_limit = 0

                cursor.execute(
                    """
                    INSERT INTO EVENT_SESSION (
                        eid, start_time, end_time, capacity,
                        current_registered, waiting_list_limit, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        eid,
                        start_time,
                        end_time,
                        capacity,
                        0,  # current_registered 初始为 0
                        waiting_list_limit,
                        "open",  # 新建场次默认为 open
                    ),
                )

                session_id = cursor.lastrowid
                created_sessions.append(
                    {
                        "session_id": session_id,
                        "start_time": start_time,
                        "end_time": end_time,
                        "capacity": capacity,
                        "waiting_list_limit": waiting_list_limit,
                    }
                )

        conn.commit()

        return {
            "eid": eid,
            "title": title,
            "status": status,
            "allow_multi_session": allow_multi_session,
            "sessions": created_sessions,
        }

    except EventError:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise EventError("Error occurred while creating event: %s" % str(e))
    finally:
        conn.close()


def update_event_basic(eid: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update basic EVENT fields (no session edits here)."""

    title = (payload.get("title") or "").strip()
    description = payload.get("description")
    location = payload.get("location")
    status = (payload.get("status") or "draft").strip()
    image_url = payload.get("image_url")
    allow_multi_session = bool(payload.get("allow_multi_session", False))
    type_id = payload.get("type_id", 1)

    if not title:
        raise EventError("title cannot be empty")
    if status not in ALLOWED_STATUS:
        raise EventError("status must be one of: draft, published, closed, archived")

    now = datetime.now()
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE EVENT
                SET title = %s,
                    description = %s,
                    location = %s,
                    status = %s,
                    type_id = %s,
                    image_url = %s,
                    allow_multi_session = %s,
                    updated_at = %s
                WHERE eid = %s
                """,
                (title, description, location, status, type_id, image_url, allow_multi_session, now, eid),
            )
            if cursor.rowcount == 0:
                raise EventError("event not found")
        conn.commit()
        return {
            "eid": eid,
            "title": title,
            "status": status,
            "image_url": image_url,
            "allow_multi_session": allow_multi_session,
            "updated_at": now.isoformat(),
        }
    except EventError:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise EventError("Error occurred while updating event: %s" % str(e))
    finally:
        conn.close()


def delete_event(eid: int) -> Dict[str, Any]:
    """Delete an event and cascaded sessions."""

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM EVENT WHERE eid = %s", (eid,))
            if cursor.rowcount == 0:
                raise EventError("event not found")
        conn.commit()
        return {"eid": eid, "deleted": True}
    except EventError:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise EventError("Error occurred while deleting event: %s" % str(e))
    finally:
        conn.close()


def list_today_sessions() -> List[Dict[str, Any]]:
    """Return sessions happening today with event info."""
    today = datetime.now()
    start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    sql = """
    SELECT
        s.session_id,
        s.eid,
        s.start_time,
        s.end_time,
        s.capacity,
        s.current_registered,
        s.waiting_list_limit,
        s.status,
        e.title AS event_title
    FROM EVENT_SESSION s
    JOIN EVENT e ON e.eid = s.eid
    WHERE s.start_time < %s
      AND s.end_time >= %s
      AND e.status IN ('published', 'draft', 'closed')
    ORDER BY s.start_time ASC
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (end_of_day, start_of_day))
            return cursor.fetchall()
    finally:
        conn.close()