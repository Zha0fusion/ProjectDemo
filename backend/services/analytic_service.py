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
    EventUserGroup,
    AudienceGroup,
    EventTag,
    Tag,
    EventType,
    Organization,
)


class AnalyticError(Exception):
    pass


def _get_db() -> Session:
    return SessionLocal()


def get_event_overview(eid: int, start: datetime | None = None, end: datetime | None = None) -> Dict[str, Any]:
    db = _get_db()
    try:
        event = db.query(Event).filter(Event.eid == eid).first()
        if not event:
            raise AnalyticError("活动不存在")

        session_filter = [EventSession.eid == eid]
        if start:
            session_filter.append(EventSession.start_time >= start)
        if end:
            session_filter.append(EventSession.start_time < end)

        # 场次数
        session_count = (
            db.query(func.count(EventSession.session_id))
            .filter(*session_filter)
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
            .filter(*session_filter)
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
            .filter(*session_filter)
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
                *session_filter,
                Registration.checkin_time.isnot(None),
            )
            .scalar()
        )

        tags = (
            db.query(Tag.tag_name)
            .select_from(EventTag)
            .join(Tag, Tag.tag_id == EventTag.tag_id)
            .filter(EventTag.eid == eid)
            .all()
        )

        sessions = (
            db.query(EventSession)
            .filter(*session_filter)
            .order_by(EventSession.start_time.asc())
            .all()
        )

        registrations = (
            db.query(
                Registration.user_id,
                User.name.label("user_name"),
                User.role.label("user_role"),
                Registration.status,
                Registration.register_time,
                Registration.checkin_time,
                Registration.session_id,
                EventSession.start_time.label("session_start"),
                EventSession.end_time.label("session_end"),
                EventUserGroup.group_id,
                AudienceGroup.group_name,
            )
            .join(EventSession, Registration.session_id == EventSession.session_id)
            .join(User, User.user_id == Registration.user_id)
            .outerjoin(
                EventUserGroup,
                (EventUserGroup.user_id == Registration.user_id)
                & (EventUserGroup.eid == EventSession.eid),
            )
            .outerjoin(AudienceGroup, AudienceGroup.group_id == EventUserGroup.group_id)
            .filter(*session_filter)
            .all()
        )

        return {
            "eid": event.eid,
            "title": event.title,
            "location": event.location,
            "status": event.status,
            "type_id": event.type_id,
            "type_name": event.event_type.type_name if event.event_type else None,
            "org_id": event.org_id,
            "org_name": event.organization.org_name if event.organization else None,
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
            "tags": [t.tag_name for t in tags],
            "sessions": [
                {
                    "session_id": s.session_id,
                    "start_time": s.start_time.isoformat() if s.start_time else None,
                    "end_time": s.end_time.isoformat() if s.end_time else None,
                    "capacity": s.capacity,
                    "current_registered": s.current_registered,
                    "waiting_list_limit": s.waiting_list_limit,
                    "status": s.status,
                }
                for s in sessions
            ],
            "registrations": [
                {
                    "user_id": r.user_id,
                    "user_name": r.user_name,
                    "user_role": r.user_role,
                    "status": r.status,
                    "register_time": r.register_time.isoformat() if r.register_time else None,
                    "checkin_time": r.checkin_time.isoformat() if r.checkin_time else None,
                    "session_id": r.session_id,
                    "session_start": r.session_start.isoformat() if r.session_start else None,
                    "session_end": r.session_end.isoformat() if r.session_end else None,
                    "group_id": r.group_id,
                    "group_name": r.group_name,
                }
                for r in registrations
            ],
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