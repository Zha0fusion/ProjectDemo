# backend/api/events_api.py
from flask import Blueprint, jsonify, request

from backend.auth_decorators import login_required, roles_required
from backend.db import get_cursor
from backend.db_orm import SessionLocal
from backend.models.models import Tag, Event, EventTag
from backend.services.event_service import create_event_with_sessions, EventError
from backend.services.search_service import search_events, SearchError

events_bp = Blueprint("events_api", __name__)


@events_bp.get("/health")
def events_health():
    # 健康检查接口：仅用于确认服务存活
    return jsonify(
        {
            "status": "ok",
            "message_zh": "events api 正常运行",
            "message_en": "events api alive",
        }
    )


@events_bp.post("/")
@login_required
@roles_required("staff", "admin")
def create_event():
    """
    创建活动 + 场次

    URL:
      POST /api/events/

    请求 JSON 示例：
      {
        "title": "Data Science Talk",
        "description": "Introductory sharing session for undergraduates",
        "location": "Teaching Building A101",
        "status": "published",
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
    data = request.get_json(silent=True) or {}

    try:
        result = create_event_with_sessions(data)
        # 创建成功返回 201
        # 这里也补充双语提示，便于前端展示
        result.setdefault("message_zh", "活动创建成功")
        result.setdefault("message_en", "Event created successfully")
        return jsonify(result), 201
    except EventError as e:
        return (
            jsonify(
                {
                    "error": "event_create_failed",
                    "message_zh": str(e),
                    "message_en": "Failed to create event: " + str(e),
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


@events_bp.get("/")
def list_events():
    """
    列出所有已发布的活动（不区分场次）。
    URL: GET /api/events/
    """
    sql = """
    SELECT
        e.eid,
        e.title,
        e.description,
        e.location,
        e.status,
        e.created_at,
        e.updated_at
    FROM EVENT e
    WHERE e.status = 'published'
    ORDER BY e.created_at DESC
    """
    with get_cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
    # 这里返回的是列表数据，本身不需要 message_zh / message_en，
    # 前端一般直接展示数据就行，如有需要可以在外层再包一层。
    return jsonify(rows)


@events_bp.get("/<int:eid>/sessions")
def list_event_sessions(eid: int):
    """
    列出某个活动的所有场次。
    URL: GET /api/events/<eid>/sessions
    """
    sql = """
    SELECT
        s.session_id,
        s.eid,
        s.start_time,
        s.end_time,
        s.capacity,
        s.current_registered,
        s.waiting_list_limit,
        s.status
    FROM EVENT_SESSION s
    WHERE s.eid = %s
    ORDER BY s.start_time ASC
    """
    with get_cursor() as cursor:
        cursor.execute(sql, (eid,))
        rows = cursor.fetchall()
    return jsonify(rows)


@events_bp.get("/<int:eid>/detail")
def get_event_detail(eid: int):
    """
    活动详情：返回活动基本信息 + 该活动下的所有场次。

    URL: GET /api/events/<eid>/detail
    """
    # 1. 查询活动基本信息
    sql_event = """
    SELECT
        e.eid,
        e.title,
        e.description,
        e.location,
        e.status,
        e.type_id,
        e.created_at,
        e.updated_at
    FROM EVENT e
    WHERE e.eid = %s
    """
    with get_cursor() as cursor:
        cursor.execute(sql_event, (eid,))
        event = cursor.fetchone()

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

        # 2. 查询该活动的所有场次
        sql_sessions = """
        SELECT
            s.session_id,
            s.eid,
            s.start_time,
            s.end_time,
            s.capacity,
            s.current_registered,
            s.waiting_list_limit,
            s.status
        FROM EVENT_SESSION s
        WHERE s.eid = %s
        ORDER BY s.start_time ASC
        """
        cursor.execute(sql_sessions, (eid,))
        sessions = cursor.fetchall()

    # 3. 拼出统一结构
    event["sessions"] = sessions
    return jsonify(event)


@events_bp.get("/tags")
def list_tags():
    """列出所有标签。"""
    db = SessionLocal()
    try:
        tags = db.query(Tag).order_by(Tag.tag_name.asc()).all()
        return jsonify(
            [
                {
                    "tag_id": t.tag_id,
                    "tag_name": t.tag_name,
                }
                for t in tags
            ]
        )
    finally:
        db.close()


@events_bp.post("/tags")
@login_required
@roles_required("staff", "admin")
def create_tag():
    """创建标签。"""
    data = request.get_json(silent=True) or {}
    tag_name = (data.get("tag_name") or "").strip()

    if not tag_name:
        return (
            jsonify(
                {
                    "error": "invalid_request",
                    "message_zh": "tag_name 不能为空",
                    "message_en": "tag_name is required",
                }
            ),
            400,
        )

    db = SessionLocal()
    try:
        exists = db.query(Tag).filter(Tag.tag_name == tag_name).first()
        if exists:
            return (
                jsonify(
                    {
                        "error": "conflict",
                        "message_zh": "标签已存在",
                        "message_en": "Tag already exists",
                    }
                ),
                409,
            )

        tag = Tag(tag_name=tag_name)
        db.add(tag)
        db.commit()
        return (
            jsonify(
                {
                    "tag_id": tag.tag_id,
                    "tag_name": tag.tag_name,
                    "message_zh": "标签创建成功",
                    "message_en": "Tag created",
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


@events_bp.post("/<int:eid>/tags")
@login_required
@roles_required("staff", "admin")
def set_event_tags(eid: int):
    """
    为活动设置标签（覆盖式）。
    请求体示例：{ "tag_names": ["Art", "Workshop"] }
    """
    data = request.get_json(silent=True) or {}
    names = data.get("tag_names") or []
    if not isinstance(names, list):
        return (
            jsonify(
                {
                    "error": "invalid_request",
                    "message_zh": "tag_names 必须为数组",
                    "message_en": "tag_names must be a list",
                }
            ),
            400,
        )

    clean_names = []
    for n in names:
        if isinstance(n, str) and n.strip():
            clean_names.append(n.strip())
    if not clean_names:
        return (
            jsonify(
                {
                    "error": "invalid_request",
                    "message_zh": "至少需要一个有效的标签名",
                    "message_en": "At least one valid tag_name is required",
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

        # 确保标签存在，不存在则创建
        existing_tags = db.query(Tag).filter(Tag.tag_name.in_(clean_names)).all()
        existing_map = {t.tag_name: t for t in existing_tags}

        for name in clean_names:
            if name not in existing_map:
                t = Tag(tag_name=name)
                db.add(t)
                db.flush()  # 获取 tag_id
                existing_map[name] = t

        # 清空旧关系，写入新关系
        db.query(EventTag).filter(EventTag.eid == eid).delete()
        for tag in existing_map.values():
            db.add(EventTag(eid=eid, tag_id=tag.tag_id))

        db.commit()
        return (
            jsonify(
                {
                    "eid": eid,
                    "tags": list(existing_map.keys()),
                    "message_zh": "标签已更新",
                    "message_en": "Tags updated",
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


@events_bp.get("/search")
def search_events_api():
    """基于 ORM 的多表联查搜索。"""
    tag_names = request.args.getlist("tag") or None
    type_ids_raw = request.args.getlist("type_id")
    status = request.args.getlist("status") or None
    start_time = request.args.get("start")
    end_time = request.args.get("end")
    keyword = request.args.get("q")

    def _parse_ints(vals):
        out = []
        for v in vals:
            try:
                out.append(int(v))
            except (TypeError, ValueError):
                pass
        return out or None

    type_ids = _parse_ints(type_ids_raw)

    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return (
            jsonify(
                {
                    "error": "invalid_request",
                    "message_zh": "limit/offset 必须为整数",
                    "message_en": "limit/offset must be integers",
                }
            ),
            400,
        )

    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    try:
        results = search_events(
            tag_names=tag_names,
            type_ids=type_ids,
            status=status,
            start_time=start_time,
            end_time=end_time,
            keyword=keyword,
            limit=limit,
            offset=offset,
        )
        return jsonify(results), 200
    except SearchError as e:
        return (
            jsonify(
                {
                    "error": "search_error",
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