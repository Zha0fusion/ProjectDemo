from datetime import datetime, timedelta, timezone
from typing import Literal, Dict, Any

from backend.db import get_connection

RegistrationStatus = Literal["registered", "waiting", "cancelled"]

# ===== 新增：爽约惩罚相关配置 =====
NO_SHOW_WINDOW_DAYS = 30      # 统计最近 30 天
BLOCK_DAYS = 30               # 被封禁 30 天
NO_SHOW_THRESHOLD = 3         # 30 天内爽约达到 3 次，触发封禁


class RegistrationError(Exception):
    """业务错误（例如活动已满、场次关闭等），用于返回友好提示。"""
    pass


def _get_utc_now() -> datetime:
    """
    使用带时区的 UTC 时间，避免 datetime.utcnow 的弃用警告。
    """
    return datetime.now(timezone.utc)


def _maybe_block_user_for_no_show(cursor, user_id: int) -> datetime | None:
    """
    使用给定 cursor，在数据库中统计该用户“最近 30 天”的爽约次数：
      - REGISTRATION.status = 'registered'
      - REGISTRATION.checkin_time IS NULL
      - 对应 EVENT_SESSION.end_time < now
      - 且 end_time 在 [now - NO_SHOW_WINDOW_DAYS, now) 之间

    如果次数 >= NO_SHOW_THRESHOLD，则将 USER.blocked_until 设置为 now + BLOCK_DAYS，
    返回 blocked_until；否则返回 None。

    注意：这里只执行 UPDATE，不做 commit；由上层事务统一提交。
    """
    now = _get_utc_now()
    start_window = now - timedelta(days=NO_SHOW_WINDOW_DAYS)

    # 统计爽约次数
    cursor.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM REGISTRATION r
        JOIN EVENT_SESSION s ON r.session_id = s.session_id
        WHERE r.user_id = %s
          AND r.status = 'registered'
          AND r.checkin_time IS NULL
          AND s.end_time < %s
          AND s.end_time >= %s
        """,
        (user_id, now, start_window),
    )
    row = cursor.fetchone()
    no_show_count = row["cnt"] or 0

    if no_show_count < NO_SHOW_THRESHOLD:
        return None

    # 达到阈值 -> 计算封禁截止时间并写入 USER.blocked_until
    blocked_until = now + timedelta(days=BLOCK_DAYS)

    cursor.execute(
        """
        UPDATE `USER`
        SET blocked_until = %s
        WHERE user_id = %s
        """,
        (blocked_until, user_id),
    )

    return blocked_until


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
            message_en = (
                f"Session is full. You have been added to the waiting list "
                f"(position {queue_position})."
            )
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

    同时增加逻辑：
      - 每次报名前：
          * 若 USER.blocked_until > now，则拒绝报名；
          * 统计最近 30 天爽约次数（未签到 + 已结束场次）；
            若达到 NO_SHOW_THRESHOLD，则自动设置 blocked_until = now + BLOCK_DAYS，
            并拒绝本次报名。

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
    now = _get_utc_now()
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 0) 检查当前用户是否已存在，及是否已被封禁
            cursor.execute(
                """
                SELECT blocked_until
                FROM `USER`
                WHERE user_id = %s
                """,
                (user_id,),
            )
            user_row = cursor.fetchone()
            if not user_row:
                raise RegistrationError("用户不存在")

            blocked_until = user_row["blocked_until"]
            if blocked_until is not None:
                # 数据库存的是 DATETIME（通常无 tzinfo），与 now 的 naive 部分比较
                if isinstance(blocked_until, datetime):
                    # 将 now 转成 naive 再比较（或根据你的存储策略统一处理）
                    if blocked_until > now.replace(tzinfo=None):
                        raise RegistrationError(
                            f"账号已被封禁，解封时间：{blocked_until}"
                        )

            # 1) 统计最近 30 天爽约次数，如超标则立刻封禁并拒绝当前报名
            newly_blocked_until = _maybe_block_user_for_no_show(cursor, user_id)
            if newly_blocked_until is not None:
                raise RegistrationError(
                    f"最近 {NO_SHOW_WINDOW_DAYS} 天内爽约次数过多，"
                    f"账号已被封禁至 {newly_blocked_until}"
                )

            # 2) 锁定场次记录，防止并发问题
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

            # 2.1 如果活动不允许多场次报名，检查用户是否已在同一活动的其他场次中
            cursor.execute(
                "SELECT allow_multi_session FROM EVENT WHERE eid = %s",
                (session_row["eid"],),
            )
            event_row = cursor.fetchone()
            allow_multi_session = bool(event_row["allow_multi_session"]) if event_row else False

            if not allow_multi_session:
                cursor.execute(
                    """
                    SELECT r.session_id, r.status
                    FROM REGISTRATION r
                    JOIN EVENT_SESSION es ON r.session_id = es.session_id
                    WHERE r.user_id = %s
                      AND es.eid = %s
                      AND r.status IN ('registered', 'waiting')
                      AND r.session_id <> %s
                    FOR UPDATE
                    """,
                    (user_id, session_row["eid"], session_id),
                )
                existing_same_event = cursor.fetchone()
                if existing_same_event:
                    raise RegistrationError("You are already registered for another session of this event")

            capacity = session_row["capacity"]
            current_registered = session_row["current_registered"]
            waiting_list_limit = session_row["waiting_list_limit"]

            # 3) 查询是否已经有报名记录（包括 cancelled）
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

            # 3.1 已经是 registered / waiting：不重复报名
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

            # 3.2 cancelled -> 允许重新报名，后面统一当“复用旧记录”处理
            has_old_cancelled = bool(
                existing and existing["status"] == "cancelled"
            )

            # 4) 判断这次是 registered 还是 waiting
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
                base_message_zh = (
                    "场次已满，已进入候补队列（排在第 %d 位）" % queue_position
                )

            # 5) 写 REGISTRATION：复用旧 cancelled 记录，或者插入新记录
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

        bilingual = _build_bilingual_message_for_cancel(
            current_status=current_status
        )

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