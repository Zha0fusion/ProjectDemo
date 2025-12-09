# backend/api/analytics_api.py
from datetime import datetime
from flask import Blueprint, jsonify, request, g

from backend.services.analytic_service import (
    get_event_overview,
    get_session_stats,
    get_user_stats,
    get_event_registration_trend,
    AnalyticError,
)
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