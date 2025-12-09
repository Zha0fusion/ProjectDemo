from flask import Blueprint, jsonify, request

from backend.auth_decorators import login_required, roles_required
from backend.db_orm import SessionLocal
from backend.models.models import AudienceGroup, EventUserGroup, Event, User

groups_bp = Blueprint("groups_api", __name__)


def _as_group_dict(group: AudienceGroup) -> dict:
    return {
        "group_id": group.group_id,
        "group_name": group.group_name,
        "description": group.description,
        "is_default": bool(group.is_default),
    }


@groups_bp.get("/groups")
def list_groups():
    db = SessionLocal()
    try:
        groups = db.query(AudienceGroup).order_by(AudienceGroup.group_name.asc()).all()
        return jsonify([_as_group_dict(g) for g in groups])
    finally:
        db.close()


@groups_bp.post("/groups")
@login_required
@roles_required("staff", "admin")
def create_group():
    data = request.get_json(silent=True) or {}
    name = (data.get("group_name") or "").strip()
    description = data.get("description")
    is_default = bool(data.get("is_default", False))

    if not name:
        return (
            jsonify(
                {
                    "error": "invalid_request",
                    "message_zh": "group_name 不能为空",
                    "message_en": "group_name is required",
                }
            ),
            400,
        )

    db = SessionLocal()
    try:
        exists = db.query(AudienceGroup).filter(AudienceGroup.group_name == name).first()
        if exists:
            return (
                jsonify(
                    {
                        "error": "conflict",
                        "message_zh": "group_name 已存在",
                        "message_en": "group_name already exists",
                    }
                ),
                409,
            )

        if is_default:
            # 确保只有一个默认分组
            db.query(AudienceGroup).update({AudienceGroup.is_default: False})

        group = AudienceGroup(
            group_name=name,
            description=description,
            is_default=is_default,
        )
        db.add(group)
        db.commit()
        return (
            jsonify(
                {
                    **_as_group_dict(group),
                    "message_zh": "分组创建成功",
                    "message_en": "Group created",
                }
            ),
            201,
        )
    except Exception as e:
        db.rollback()
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


@groups_bp.post("/events/<int:eid>/users/<int:user_id>/group")
@login_required
@roles_required("staff", "admin")
def assign_user_group(eid: int, user_id: int):
    """为某活动分配用户的观众群组。"""
    data = request.get_json(silent=True) or {}
    group_id = data.get("group_id")

    if not isinstance(group_id, int):
        return (
            jsonify(
                {
                    "error": "invalid_request",
                    "message_zh": "group_id 必须为整数",
                    "message_en": "group_id must be an integer",
                }
            ),
            400,
        )

    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.eid == eid).first()
        if not event:
            return (
                jsonify(
                    {
                        "error": "not_found",
                        "message_zh": "活动不存在",
                        "message_en": "Event not found",
                    }
                ),
                404,
            )

        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return (
                jsonify(
                    {
                        "error": "not_found",
                        "message_zh": "用户不存在",
                        "message_en": "User not found",
                    }
                ),
                404,
            )

        group = db.query(AudienceGroup).filter(AudienceGroup.group_id == group_id).first()
        if not group:
            return (
                jsonify(
                    {
                        "error": "not_found",
                        "message_zh": "观众群体不存在",
                        "message_en": "Audience group not found",
                    }
                ),
                404,
            )

        # upsert
        existing = (
            db.query(EventUserGroup)
            .filter(EventUserGroup.user_id == user_id, EventUserGroup.eid == eid)
            .first()
        )
        if existing:
            existing.group_id = group_id
        else:
            db.add(EventUserGroup(user_id=user_id, eid=eid, group_id=group_id))

        db.commit()
        return (
            jsonify(
                {
                    "eid": eid,
                    "user_id": user_id,
                    "group": _as_group_dict(group),
                    "message_zh": "分组已更新",
                    "message_en": "Group updated",
                }
            ),
            200,
        )
    except Exception as e:
        db.rollback()
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


@groups_bp.get("/events/<int:eid>/users/<int:user_id>/group")
@login_required
def get_user_group(eid: int, user_id: int):
    db = SessionLocal()
    try:
        record = (
            db.query(EventUserGroup)
            .filter(EventUserGroup.user_id == user_id, EventUserGroup.eid == eid)
            .first()
        )
        if not record:
            return (
                jsonify(
                    {
                        "error": "not_found",
                        "message_zh": "未找到对应的分组记录",
                        "message_en": "No group assignment found",
                    }
                ),
                404,
            )

        group = db.query(AudienceGroup).filter(AudienceGroup.group_id == record.group_id).first()
        return jsonify(
            {
                "eid": eid,
                "user_id": user_id,
                "group": _as_group_dict(group) if group else None,
            }
        )
    finally:
        db.close()
