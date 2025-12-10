from datetime import datetime
from typing import Any

from flask import Blueprint, jsonify, request, Response

from backend.auth_decorators import login_required, roles_required
from backend.services import admin_service

admin_bp = Blueprint("admin_api", __name__)


def _error_response(message_en: str, message_zh: str, status: int = 400):
    return (
        jsonify(
            {
                "error": "invalid_request" if status == 400 else "server_error",
                "message_en": message_en,
                "message_zh": message_zh,
            }
        ),
        status,
    )


def _parse_datetime(value: Any):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        raise admin_service.AdminError("invalid datetime format")


@admin_bp.get("/admin/users")
@login_required
@roles_required("admin")
def list_users():
    keyword = request.args.get("q") or None
    role = request.args.get("role") or None
    try:
        users = admin_service.list_users(keyword=keyword, role=role)
        return jsonify(users)
    except admin_service.AdminError as e:
        return _error_response(str(e), str(e), 400)


@admin_bp.post("/admin/users")
@login_required
@roles_required("admin")
def create_user():
    data = request.get_json(silent=True) or {}
    try:
        user = admin_service.create_user(
            name=data.get("name"),
            email=data.get("email"),
            password=data.get("password"),
            role=data.get("role", "visitor"),
        )
        return (
            jsonify(
                {
                    **user,
                    "message_zh": "用户创建成功",
                    "message_en": "User created",
                }
            ),
            201,
        )
    except admin_service.AdminError as e:
        return _error_response(str(e), str(e), 400)
    except Exception as e:
        return _error_response(str(e), "服务器内部错误", 500)


@admin_bp.put("/admin/users/<int:user_id>")
@login_required
@roles_required("admin")
def update_user(user_id: int):
    data = request.get_json(silent=True) or {}
    try:
        user = admin_service.update_user(
            user_id=user_id,
            name=data.get("name"),
            email=data.get("email"),
            password=data.get("password"),
            role=data.get("role"),
            blocked_until=_parse_datetime(data.get("blocked_until")),
        )
        return jsonify(
            {
                **user,
                "message_zh": "用户已更新",
                "message_en": "User updated",
            }
        )
    except admin_service.AdminError as e:
        status = 404 if "not found" in str(e) else 400
        return _error_response(str(e), str(e), status)
    except Exception as e:
        return _error_response(str(e), "服务器内部错误", 500)


@admin_bp.delete("/admin/users/<int:user_id>")
@login_required
@roles_required("admin")
def delete_user(user_id: int):
    try:
        admin_service.delete_user(user_id)
        return jsonify(
            {
                "message_zh": "用户已删除",
                "message_en": "User deleted",
            }
        )
    except Exception as e:
        return _error_response(str(e), "服务器内部错误", 500)


@admin_bp.get("/admin/tags")
@login_required
@roles_required("admin")
def list_tags():
    try:
        tags = admin_service.list_tags()
        return jsonify(tags)
    except Exception as e:
        return _error_response(str(e), "服务器内部错误", 500)


@admin_bp.post("/admin/tags")
@login_required
@roles_required("admin")
def create_tag():
    data = request.get_json(silent=True) or {}
    try:
        tag = admin_service.create_tag(data.get("tag_name"))
        return (
            jsonify(
                {
                    **tag,
                    "message_zh": "标签创建成功",
                    "message_en": "Tag created",
                }
            ),
            201,
        )
    except admin_service.AdminError as e:
        return _error_response(str(e), str(e), 400)
    except Exception as e:
        return _error_response(str(e), "服务器内部错误", 500)


@admin_bp.put("/admin/tags/<int:tag_id>")
@login_required
@roles_required("admin")
def update_tag(tag_id: int):
    data = request.get_json(silent=True) or {}
    try:
        tag = admin_service.update_tag(tag_id, data.get("tag_name"))
        return jsonify(
            {
                **tag,
                "message_zh": "标签已更新",
                "message_en": "Tag updated",
            }
        )
    except admin_service.AdminError as e:
        status = 404 if "not found" in str(e) else 400
        return _error_response(str(e), str(e), status)
    except Exception as e:
        return _error_response(str(e), "服务器内部错误", 500)


@admin_bp.delete("/admin/tags/<int:tag_id>")
@login_required
@roles_required("admin")
def delete_tag(tag_id: int):
    try:
        admin_service.delete_tag(tag_id)
        return jsonify(
            {
                "message_zh": "标签已删除",
                "message_en": "Tag deleted",
            }
        )
    except Exception as e:
        return _error_response(str(e), "服务器内部错误", 500)


@admin_bp.post("/admin/registrations/force")
@login_required
@roles_required("admin")
def force_registration():
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get("user_id"))
        session_id = int(data.get("session_id"))
    except (TypeError, ValueError):
        return _error_response("user_id and session_id are required", "user_id 和 session_id 必须为整数", 400)

    status = data.get("status", "registered")
    try:
        result = admin_service.force_set_registration(user_id=user_id, session_id=session_id, status=status)
        return jsonify({**result, "message_en": "Registration updated", "message_zh": "报名记录已更新"})
    except admin_service.AdminError as e:
        status_code = 404 if "not found" in str(e) else 400
        return _error_response(str(e), str(e), status_code)
    except Exception as e:
        return _error_response(str(e), "服务器内部错误", 500)


@admin_bp.get("/admin/events/<int:eid>/groups/summary")
@login_required
@roles_required("admin")
def event_group_summary(eid: int):
    try:
        rows = admin_service.list_event_group_summary(eid)
        return jsonify(rows)
    except Exception as e:
        return _error_response(str(e), "服务器内部错误", 500)


@admin_bp.get("/admin/events/<int:eid>/members")
@login_required
@roles_required("admin")
def event_members(eid: int):
    try:
        rows = admin_service.list_event_members(eid)
        return jsonify(rows)
    except Exception as e:
        return _error_response(str(e), "服务器内部错误", 500)


@admin_bp.get("/admin/events/<int:eid>/groups/<int:group_id>/members")
@login_required
@roles_required("admin")
def event_group_members(eid: int, group_id: int):
    try:
        rows = admin_service.list_group_members_for_event(eid, group_id)
        return jsonify(rows)
    except Exception as e:
        return _error_response(str(e), "服务器内部错误", 500)


@admin_bp.post("/admin/events/<int:eid>/groups/assign")
@login_required
@roles_required("admin")
def assign_group(eid: int):
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get("user_id"))
        group_id = int(data.get("group_id"))
    except (TypeError, ValueError):
        return _error_response("user_id/group_id required", "user_id 与 group_id 必须为整数", 400)

    try:
        result = admin_service.assign_event_user_group(eid, user_id, group_id)
        return jsonify({**result, "message_zh": "分组已更新", "message_en": "Group updated"})
    except admin_service.AdminError as e:
        status_code = 404 if "not found" in str(e) else 400
        return _error_response(str(e), str(e), status_code)
    except Exception as e:
        return _error_response(str(e), "服务器内部错误", 500)


@admin_bp.get("/admin/events/<int:eid>/registrations/export")
@login_required
@roles_required("admin")
def export_event_registrations(eid: int):
    try:
        filename, content = admin_service.export_event_registrations_csv(eid)
        return Response(
            content,
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            },
        )
    except admin_service.AdminError as e:
        status_code = 404 if "not found" in str(e) else 400
        return _error_response(str(e), str(e), status_code)
    except Exception as e:
        return _error_response(str(e), "服务器内部错误", 500)
