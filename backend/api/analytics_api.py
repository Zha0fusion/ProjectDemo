# backend/api/analytics_api.py
from datetime import datetime
from flask import Blueprint, jsonify, request, g

from sqlalchemy import func

from backend.services.analytic_service import (
    get_event_overview,
    get_session_stats,
    get_user_stats,
    get_event_registration_trend,
    AnalyticError,
)
from backend.auth_decorators import login_required, roles_required
from backend.db_orm import SessionLocal
from backend.models.models import Registration, EventSession, Event, EventTag, Tag, EventUserGroup, AudienceGroup
from backend.auth_decorators import login_required

analytics_bp = Blueprint("analytics_api", __name__)


@analytics_bp.get("/events/<int:eid>/overview")
@login_required
def event_overview_api(eid: int):
    try:
        data = get_event_overview(eid)
        return jsonify(data), 200
    except AnalyticError as e:
        return (
            jsonify(
                {
                    "error": "analytic_error",
                    "message_zh": str(e),
                    "message_en": str(e),
                }
            ),
            400,
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "error": "server_error",
                    "message_zh": "服务器内部错误",
                    "message_en": "Internal server error: " + str(e),
                }
            ),
            500,
        )


@analytics_bp.get("/sessions/<int:session_id>")
@login_required
def session_stats_api(session_id: int):
    try:
        data = get_session_stats(session_id)
        return jsonify(data), 200
    except AnalyticError as e:
        return (
            jsonify(
                {
                    "error": "analytic_error",
                    "message_zh": str(e),
                    "message_en": str(e),
                }
            ),
            400,
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "error": "server_error",
                    "message_zh": "服务器内部错误",
                    "message_en": "Internal server error: " + str(e),
                }
            ),
            500,
        )


@analytics_bp.get("/users/me")
@login_required
def my_stats_api():
    current_user = g.current_user
    user_id = current_user["user_id"]

    try:
        data = get_user_stats(user_id)
        return jsonify(data), 200
    except AnalyticError as e:
        return (
            jsonify(
                {
                    "error": "analytic_error",
                    "message_zh": str(e),
                    "message_en": str(e),
                }
            ),
            400,
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "error": "server_error",
                    "message_zh": "服务器内部错误",
                    "message_en": "Internal server error: " + str(e),
                }
            ),
            500,
        )


@analytics_bp.get("/events/<int:eid>/trend")
@login_required
def event_trend_api(eid: int):
    """
    活动报名趋势（按日期聚合）。
    可选 query 参数:
      - start: 2025-12-01
      - end:   2025-12-31
    """
    start_str = request.args.get("start")
    end_str = request.args.get("end")

    start = datetime.fromisoformat(start_str) if start_str else None
    end = datetime.fromisoformat(end_str) if end_str else None

    try:
        data = get_event_registration_trend(eid, start=start, end=end)
        return jsonify(data), 200
    except AnalyticError as e:
        return (
            jsonify(
                {
                    "error": "analytic_error",
                    "message_zh": str(e),
                    "message_en": str(e),
                }
            ),
            400,
        )


@analytics_bp.get("/events/<int:eid>/group-stats")
@login_required
@roles_required("staff", "admin")
def event_group_stats(eid: int):
    """按观众群体统计某活动的报名/签到人数。"""
    db = SessionLocal()
    try:
        rows = (
            db.query(
                AudienceGroup.group_name,
                func.count(Registration.user_id).label("registrations"),
                func.count(Registration.checkin_time).filter(Registration.checkin_time.isnot(None)).label("checkins"),
            )
            .select_from(Registration)
            .join(EventSession, Registration.session_id == EventSession.session_id)
            .join(Event, EventSession.eid == Event.eid)
            .join(EventUserGroup, (EventUserGroup.user_id == Registration.user_id) & (EventUserGroup.eid == Event.eid))
            .join(AudienceGroup, AudienceGroup.group_id == EventUserGroup.group_id)
            .filter(Event.eid == eid)
            .group_by(AudienceGroup.group_name)
            .all()
        )
        return jsonify(
            [
                {
                    "group_name": r.group_name,
                    "registrations": r.registrations,
                    "checkins": r.checkins,
                }
                for r in rows
            ]
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "error": "server_error",
                    "message_zh": "服务器内部错误",
                    "message_en": "Internal server error: " + str(e),
                }
            ),
            500,
        )
    finally:
        db.close()


@analytics_bp.get("/tags/<tag_name>/overview")
@login_required
@roles_required("staff", "admin")
def tag_overview(tag_name: str):
    """按标签汇总：活动数、场次数、报名数、签到数。"""
    db = SessionLocal()
    try:
        rows = (
            db.query(
                Event.eid,
                Event.title,
                func.count(EventSession.session_id).label("session_count"),
                func.count(Registration.user_id).label("registrations"),
                func.count(Registration.checkin_time).filter(Registration.checkin_time.isnot(None)).label("checkins"),
            )
            .select_from(Event)
            .join(EventTag, EventTag.eid == Event.eid)
            .join(Tag, Tag.tag_id == EventTag.tag_id)
            .outerjoin(EventSession, EventSession.eid == Event.eid)
            .outerjoin(Registration, Registration.session_id == EventSession.session_id)
            .filter(Tag.tag_name == tag_name)
            .group_by(Event.eid, Event.title)
            .all()
        )
        return jsonify(
            [
                {
                    "eid": r.eid,
                    "title": r.title,
                    "session_count": r.session_count,
                    "registrations": r.registrations,
                    "checkins": r.checkins,
                }
                for r in rows
            ]
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "error": "server_error",
                    "message_zh": "服务器内部错误",
                    "message_en": "Internal server error: " + str(e),
                }
            ),
            500,
        )
    finally:
        db.close()