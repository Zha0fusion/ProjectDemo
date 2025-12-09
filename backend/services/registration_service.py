from datetime import datetime
from typing import Literal, Dict, Any

from backend.db import get_connection

RegistrationStatus = Literal["registered", "waiting", "cancelled"]


class RegistrationError(Exception):
    """业务错误（例如活动已满、场次关闭等），用于返回友好提示。"""
    pass


def _build_bilingual_message_for_register(
    status: RegistrationStatus,
    base_message_zh: str,
    queue_position: int | None = None,
) -> Dict[str, str]:
    """
    根据报名结果状态，构造中英文提示。
    """
    if status == "registered":
        message_en = "Registration successful"
    elif status == "waiting":
        if queue_position is not None:
            message_en = f"Session is full. You have been added to the waiting list (position {queue_position})."
        else:
            message_en = "Session is full. You have been added to the waiting list."
    else:
        message_en = "Registration processed"

    return {
        "message": base_message_zh,       # 保留原本的中文 message 字段
        "message_zh": base_message_zh,
        "message_en": message_en,
    }


def register_for_session(user_id: int, session_id: int) -> Dict[str, Any]:
    """
    报名一个场次的核心逻辑：

      - 如果已有 status in ('registered', 'waiting')：不重复报名，直接返回
      - 如果已有 status = 'cancelled'：允许重新报名（复用这条记录）
      - 否则视为首次报名

      - 根据 capacity / current_registered 决定：
          * 还有名额 -> registered
          * 没有名额 -> waiting（并根据现有 waiting 人数给 queue_position）

    返回示例：
      {
        "session_id": 3,
        "user_id": 1,
        "status": "registered" / "waiting",
        "queue_position": null 或 int,
        "message": "报名成功",
        "message_zh": "报名成功",
        "message_en": "Registration successful"
      }
    """
    now = datetime.now()
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1) 锁定场次记录，防止并发问题
            cursor.execute(
                """
                SELECT
                    session_id,
                    eid,
                    start_time,
                    end_time,
                    capacity,
                    current_registered,
                    waiting_list_limit,
                    status
                FROM EVENT_SESSION
                WHERE session_id = %s
                FOR UPDATE
                """,
                (session_id,),
            )
            session_row = cursor.fetchone()
            if not session_row:
                raise RegistrationError("该场次不存在")

            if session_row["status"] != "open":
                raise RegistrationError("该场次已关闭报名")

            capacity = session_row["capacity"]
            current_registered = session_row["current_registered"]
            waiting_list_limit = session_row["waiting_list_limit"]

            # 2) 查询是否已经有报名记录（包括 cancelled）
            cursor.execute(
                """
                SELECT status, queue_position
                FROM REGISTRATION
                WHERE user_id = %s AND session_id = %s
                FOR UPDATE
                """,
                (user_id, session_id),
            )
            existing = cursor.fetchone()

            # 2.1 已经是 registered / waiting：不重复报名
            if existing and existing["status"] in ("registered", "waiting"):
                base_message_zh = "你已报名该场次（当前状态：%s）" % existing["status"]
                bilingual = _build_bilingual_message_for_register(
                    status=existing["status"],
                    base_message_zh=base_message_zh,
                    queue_position=existing.get("queue_position"),
                )
                return {
                    "session_id": session_id,
                    "user_id": user_id,
                    "status": existing["status"],
                    "queue_position": existing.get("queue_position"),
                    **bilingual,
                }

            # 2.2 cancelled -> 允许重新报名，后面统一当“复用旧记录”处理
            has_old_cancelled = bool(existing and existing["status"] == "cancelled")

            # 3) 判断这次是 registered 还是 waiting
            if current_registered < capacity:
                # 还有名额 -> registered
                new_status: RegistrationStatus = "registered"
                queue_position = None
                base_message_zh = "报名成功"

                # EVENT_SESSION.current_registered + 1
                cursor.execute(
                    """
                    UPDATE EVENT_SESSION
                    SET current_registered = current_registered + 1
                    WHERE session_id = %s
                    """,
                    (session_id,),
                )
            else:
                # 已满 -> 进入 waiting
                # 检查当前已在 waiting 的人数
                cursor.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM REGISTRATION
                    WHERE session_id = %s AND status = 'waiting'
                    """,
                    (session_id,),
                )
                wait_row = cursor.fetchone()
                current_waiting = wait_row["cnt"] or 0

                # 如果有 waiting_list_limit，就判断一下
                if waiting_list_limit is not None and waiting_list_limit > 0:
                    if current_waiting >= waiting_list_limit:
                        raise RegistrationError("场次已满且候补队列也已满")

                # 新的候补位次
                queue_position = current_waiting + 1
                new_status = "waiting"
                base_message_zh = "场次已满，已进入候补队列（排在第 %d 位）" % queue_position

            # 4) 写 REGISTRATION：复用旧 cancelled 记录，或者插入新记录
            if has_old_cancelled:
                cursor.execute(
                    """
                    UPDATE REGISTRATION
                    SET status = %s,
                        register_time = %s,
                        checkin_time = NULL,
                        queue_position = %s
                    WHERE user_id = %s AND session_id = %s
                    """,
                    (new_status, now, queue_position, user_id, session_id),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO REGISTRATION (
                        user_id, session_id, register_time, status, checkin_time, queue_position
                    ) VALUES (%s, %s, %s, %s, NULL, %s)
                    """,
                    (user_id, session_id, now, new_status, queue_position),
                )

        conn.commit()

        bilingual = _build_bilingual_message_for_register(
            status=new_status,
            base_message_zh=base_message_zh,
            queue_position=queue_position,
        )

        return {
            "session_id": session_id,
            "user_id": user_id,
            "status": new_status,
            "queue_position": queue_position,
            **bilingual,
        }

    except RegistrationError:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        # 这里仍抛中文，API 层会统一包装成 message_zh / message_en
        raise RegistrationError("报名过程中发生错误：%s" % str(e))
    finally:
        conn.close()


def _build_bilingual_message_for_cancel(
    current_status: RegistrationStatus,
) -> Dict[str, str]:
    """
    取消报名成功后的中英文提示。
    """
    if current_status == "registered":
        message_zh = "取消报名成功"
        message_en = "Cancellation successful"
    elif current_status == "waiting":
        message_zh = "已从候补队列中取消"
        message_en = "Removed from waiting list successfully"
    else:
        message_zh = "操作成功"
        message_en = "Operation successful"

    return {
        "message_zh": message_zh,
        "message_en": message_en,
    }


def cancel_registration(user_id: int, session_id: int) -> Dict[str, Any]:
    """
    取消报名逻辑：

      情况 1：当前是 registered
        - 当前记录 -> 'cancelled'
        - EVENT_SESSION.current_registered - 1
        - 若有 waiting：
            - 选 queue_position 最小的一条，转为 'registered'
            - EVENT_SESSION.current_registered + 1
            - 其他 waiting queue_position 依次 -1

      情况 2：当前是 waiting
        - 当前记录 -> 'cancelled'
        - 之后的 waiting 记录 queue_position 依次 -1

      情况 3：当前是 cancelled 或不存在
        - 抛业务错误
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1) 锁定报名记录
            cursor.execute(
                """
                SELECT *
                FROM REGISTRATION
                WHERE user_id = %s AND session_id = %s
                FOR UPDATE
                """,
                (user_id, session_id),
            )
            reg = cursor.fetchone()
            if not reg:
                raise RegistrationError("未找到报名记录")

            current_status: RegistrationStatus = reg["status"]
            if current_status == "cancelled":
                raise RegistrationError("该报名已取消")
            if current_status not in ("registered", "waiting"):
                raise RegistrationError(f"当前状态不支持取消：{current_status}")

            # 2) 锁定场次记录
            cursor.execute(
                """
                SELECT session_id, current_registered
                FROM EVENT_SESSION
                WHERE session_id = %s
                FOR UPDATE
                """,
                (session_id,),
            )
            session_row = cursor.fetchone()
            if not session_row:
                raise RegistrationError("场次不存在")

            promoted_user = None

            if current_status == "registered":
                # 情况 1：registered -> cancelled
                cursor.execute(
                    """
                    UPDATE REGISTRATION
                    SET status = 'cancelled', queue_position = NULL
                    WHERE user_id = %s AND session_id = %s
                    """,
                    (user_id, session_id),
                )

                # current_registered - 1
                cursor.execute(
                    """
                    UPDATE EVENT_SESSION
                    SET current_registered = current_registered - 1
                    WHERE session_id = %s AND current_registered > 0
                    """,
                    (session_id,),
                )

                # 找 waiting 队列里 queue_position 最小的一条
                cursor.execute(
                    """
                    SELECT *
                    FROM REGISTRATION
                    WHERE session_id = %s AND status = 'waiting'
                    ORDER BY queue_position ASC, register_time ASC
                    LIMIT 1
                    """,
                    (session_id,),
                )
                wait_top = cursor.fetchone()
                if wait_top:
                    # 提升为 registered
                    cursor.execute(
                        """
                        UPDATE REGISTRATION
                        SET status = 'registered', queue_position = NULL
                        WHERE user_id = %s AND session_id = %s
                        """,
                        (wait_top["user_id"], wait_top["session_id"]),
                    )

                    # current_registered +1
                    cursor.execute(
                        """
                        UPDATE EVENT_SESSION
                        SET current_registered = current_registered + 1
                        WHERE session_id = %s
                        """,
                        (session_id,),
                    )

                    promoted_user = {
                        "user_id": wait_top["user_id"],
                        "session_id": wait_top["session_id"],
                    }

                    # 其余 waiting 的 queue_position 前移
                    cursor.execute(
                        """
                        UPDATE REGISTRATION
                        SET queue_position = queue_position - 1
                        WHERE session_id = %s
                          AND status = 'waiting'
                          AND queue_position > %s
                        """,
                        (session_id, wait_top["queue_position"]),
                    )

            elif current_status == "waiting":
                # 情况 2：waiting -> cancelled
                old_pos = reg["queue_position"]

                cursor.execute(
                    """
                    UPDATE REGISTRATION
                    SET status = 'cancelled', queue_position = NULL
                    WHERE user_id = %s AND session_id = %s
                    """,
                    (user_id, session_id),
                )

                # 后面的人 queue_position -1
                cursor.execute(
                    """
                    UPDATE REGISTRATION
                    SET queue_position = queue_position - 1
                    WHERE session_id = %s
                      AND status = 'waiting'
                      AND queue_position > %s
                    """,
                    (session_id, old_pos),
                )

        conn.commit()

        bilingual = _build_bilingual_message_for_cancel(current_status=current_status)

        return {
            "session_id": session_id,
            "user_id": user_id,
            "old_status": current_status,
            "new_status": "cancelled",
            "promoted_user": promoted_user,
            **bilingual,
        }

    except RegistrationError:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise RegistrationError("取消报名过程中发生错误：%s" % str(e))
    finally:
        conn.close()