# backend/services/user_penalty_service.py
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.db_orm import SessionLocal
from backend.models.models import User, Registration, EventSession


NO_SHOW_WINDOW_DAYS = 30          # 统计时间窗口：最近 30 天
BLOCK_DAYS = 30                   # 封禁时长：30 天
NO_SHOW_THRESHOLD = 3             # 触发封禁的爽约次数


def _utcnow() -> datetime:
    # 推荐使用有时区信息的 UTC 时间
    return datetime.now(timezone.utc)


def get_recent_no_show_count(db: Session, user_id: int) -> int:
    """
    统计用户最近 NO_SHOW_WINDOW_DAYS 天内的“爽约次数”：
    条件：
      - Registration.status = 'registered'
      - Registration.checkin_time IS NULL
      - 对应 EventSession.end_time 已经结束
      - 且 end_time 在最近 N 天窗口内
    """
    now = _utcnow()
    start_window = now - timedelta(days=NO_SHOW_WINDOW_DAYS)

    count = (
        db.query(func.count("*"))
        .select_from(Registration)
        .join(
            EventSession,
            Registration.session_id == EventSession.session_id,
        )
        .filter(
            Registration.user_id == user_id,
            Registration.status == "registered",
            Registration.checkin_time.is_(None),
            EventSession.end_time < now,
            EventSession.end_time >= start_window,
        )
        .scalar()
    )
    return int(count or 0)


def apply_no_show_penalty_if_needed(db: Session, user: User) -> Optional[datetime]:
    """
    检查给定 user 是否因为最近 30 天爽约次数过多需要被封禁：
      - 若在窗口内 no_show_count >= 阈值，则：
        - 设置 user.blocked_until 为 now + BLOCK_DAYS
        - 返回 blocked_until
      - 否则返回 None
    注意：此函数内部不提交事务，由调用者 commit。
    """
    no_show_count = get_recent_no_show_count(db, user.user_id)
    if no_show_count < NO_SHOW_THRESHOLD:
        return None

    now = _utcnow()
    blocked_until = now + timedelta(days=BLOCK_DAYS)

    user.blocked_until = blocked_until
    # 不 commit，由外部事务统一提交
    return blocked_until