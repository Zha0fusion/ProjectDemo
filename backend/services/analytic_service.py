# backend/services/analytic_service.py
from datetime import datetime
from typing import Dict, Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.db_orm import SessionLocal
from backend.models.models import (
    Event,
    EventSession,
    Registration,
    User,
)


class AnalyticError(Exception):
    pass


def _get_db() -> Session:
    return SessionLocal()


def get_event_overview(eid: int) -> Dict[str, Any]:
    db = _get_db()
    try:
        event = db.query(Event).filter(Event.eid == eid).first()
        if not event:
            raise AnalyticError("活动不存在")

        # 场次数
        session_count = (
            db.query(func.count(EventSession.session_id))
            .filter(EventSession.eid == eid)
            .scalar()
        )

        # 总报名数：从 Registration 出发，显式 select_from
        total_reg = (
            db.query(func.count(Registration.user_id))
            .select_from(Registration)
            .join(
                EventSession,
                Registration.session_id == EventSession.session_id,
            )
            .filter(EventSession.eid == eid)
            .scalar()
        )

        # 各状态人数
        status_counts = (
            db.query(
                Registration.status,
                func.count("*").label("cnt"),
            )
            .select_from(Registration)
            .join(
                EventSession,
                Registration.session_id == EventSession.session_id,
            )
            .filter(EventSession.eid == eid)
            .group_by(Registration.status)
            .all()
        )

        registered_count = 0
        waiting_count = 0
        cancelled_count = 0
        for status, cnt in status_counts:
            if status == "registered":
                registered_count = cnt
            elif status == "waiting":
                waiting_count = cnt
            elif status == "cancelled":
                cancelled_count = cnt

        # 已签到人数
        checked_in_count = (
            db.query(func.count("*"))
            .select_from(Registration)
            .join(
                EventSession,
                Registration.session_id == EventSession.session_id,
            )
            .filter(
                EventSession.eid == eid,
                Registration.checkin_time.isnot(None),
            )
            .scalar()
        )

        return {
            "eid": event.eid,
            "title": event.title,
            "location": event.location,
            "status": event.status,
            "created_at": event.created_at.isoformat()
            if event.created_at
            else None,
            "updated_at": event.updated_at.isoformat()
            if event.updated_at
            else None,
            "session_count": session_count,
            "total_registrations": total_reg,
            "registered_count": registered_count,
            "waiting_count": waiting_count,
            "cancelled_count": cancelled_count,
            "checked_in_count": checked_in_count,
        }
    finally:
        db.close()


def get_session_stats(session_id: int) -> Dict[str, Any]:
    db = _get_db()
    try:
        # 这里从 EventSession 出发，再 join Event
        session = (
            db.query(EventSession)
            .join(Event, EventSession.eid == Event.eid)
            .filter(EventSession.session_id == session_id)
            .first()
        )
        if not session:
            raise AnalyticError("场次不存在")

        # 总报名数
        total_reg = (
            db.query(func.count("*"))
            .select_from(Registration)
            .filter(Registration.session_id == session_id)
            .scalar()
        )

        # 各状态人数
        status_counts = (
            db.query(
                Registration.status,
                func.count("*").label("cnt"),
            )
            .select_from(Registration)
            .filter(Registration.session_id == session_id)
            .group_by(Registration.status)
            .all()
        )

        registered_count = 0
        waiting_count = 0
        cancelled_count = 0
        for status, cnt in status_counts:
            if status == "registered":
                registered_count = cnt
            elif status == "waiting":
                waiting_count = cnt
            elif status == "cancelled":
                cancelled_count = cnt

        # 已签到人数
        checked_in_count = (
            db.query(func.count("*"))
            .select_from(Registration)
            .filter(
                Registration.session_id == session_id,
                Registration.checkin_time.isnot(None),
            )
            .scalar()
        )

        return {
            "session_id": session.session_id,
            "eid": session.eid,
            "event_title": session.event.title if session.event else None,
            "start_time": session.start_time.isoformat()
            if session.start_time
            else None,
            "end_time": session.end_time.isoformat()
            if session.end_time
            else None,
            "capacity": session.capacity,
            "current_registered": session.current_registered,
            "status": session.status,
            "waiting_list_limit": session.waiting_list_limit,
            "total_registrations": total_reg,
            "registered_count": registered_count,
            "waiting_count": waiting_count,
            "cancelled_count": cancelled_count,
            "checked_in_count": checked_in_count,
        }
    finally:
        db.close()


def get_user_stats(user_id: int) -> Dict[str, Any]:
    db = _get_db()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise AnalyticError("用户不存在")

        # 总报名数
        total_reg = (
            db.query(func.count("*"))
            .select_from(Registration)
            .filter(Registration.user_id == user_id)
            .scalar()
        )

        # 各状态人数
        status_counts = (
            db.query(
                Registration.status,
                func.count("*").label("cnt"),
            )
            .select_from(Registration)
            .filter(Registration.user_id == user_id)
            .group_by(Registration.status)
            .all()
        )

        registered_count = 0
        waiting_count = 0
        cancelled_count = 0
        for status, cnt in status_counts:
            if status == "registered":
                registered_count = cnt
            elif status == "waiting":
                waiting_count = cnt
            elif status == "cancelled":
                cancelled_count = cnt

        # 已签到次数
        checked_in_count = (
            db.query(func.count("*"))
            .select_from(Registration)
            .filter(
                Registration.user_id == user_id,
                Registration.checkin_time.isnot(None),
            )
            .scalar()
        )

        # no-show 次数：报了名 + 未签到 + 场次已结束
        now = datetime.now()
        no_show_count = (
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
            )
            .scalar()
        )

        return {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "total_registrations": total_reg,
            "registered_count": registered_count,
            "waiting_count": waiting_count,
            "cancelled_count": cancelled_count,
            "checked_in_count": checked_in_count,
            "no_show_count": no_show_count,
        }
    finally:
        db.close()


def get_event_registration_trend(
    eid: int, start: datetime, end: datetime
) -> list[dict[str, Any]]:
    """
    示例：按日统计某活动的报名数量变化趋势
    """
    db = _get_db()
    try:
        # 基于 Registration + EventSession，并显式 select_from
        rows = (
            db.query(
                func.date(Registration.register_time).label("day"),
                func.count("*").label("cnt"),
            )
            .select_from(Registration)
            .join(
                EventSession,
                Registration.session_id == EventSession.session_id,
            )
            .filter(
                EventSession.eid == eid,
                Registration.register_time >= start,
                Registration.register_time < end,
            )
            .group_by(func.date(Registration.register_time))
            .order_by("day")
            .all()
        )

        return [
            {"date": r.day.isoformat(), "count": r.cnt}
            for r in rows
        ]
    finally:
        db.close()