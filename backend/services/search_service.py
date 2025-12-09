"""Event search service using SQLAlchemy multi-table joins.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import joinedload

from backend.db_orm import SessionLocal
from backend.models.models import Event, EventSession, EventTag, Tag


class SearchError(Exception):
    pass


def _parse_dt(value: str | datetime | None) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def search_events(
    *,
    tag_names: Optional[List[str]] = None,
    type_ids: Optional[List[int]] = None,
    status: Optional[List[str]] = None,
    start_time: str | datetime | None = None,
    end_time: str | datetime | None = None,
    keyword: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Multi-table search across Event / EventSession / EventTag / Tag using ORM.
    Filters:
      - tag_names: list of tag_name strings
      - type_ids: list of EVENTTYPE ids
      - status: list of event status
      - start_time / end_time: filter sessions overlapping the window
      - keyword: fuzzy match on title or location
    Pagination via limit/offset.
    Returns list of dicts with sessions and tags embedded.
    """
    db = SessionLocal()
    try:
        q = (
            db.query(Event)
            .join(Event.sessions)
            .options(
                joinedload(Event.sessions),
                joinedload(Event.tags).joinedload(EventTag.tag),
            )
        )

        if status:
            q = q.filter(Event.status.in_(status))

        if type_ids:
            q = q.filter(Event.type_id.in_(type_ids))

        # Session time window filter
        start_dt = _parse_dt(start_time)
        end_dt = _parse_dt(end_time)
        if start_dt:
            q = q.filter(EventSession.start_time >= start_dt)
        if end_dt:
            q = q.filter(EventSession.end_time <= end_dt)

        if keyword:
            like_expr = f"%{keyword}%"
            q = q.filter((Event.title.ilike(like_expr)) | (Event.location.ilike(like_expr)))

        if tag_names:
            q = q.join(EventTag, EventTag.eid == Event.eid).join(Tag, Tag.tag_id == EventTag.tag_id)
            q = q.filter(Tag.tag_name.in_(tag_names))

        # Deduplicate events because of joins
        q = q.distinct(Event.eid).order_by(Event.created_at.desc())

        events = q.offset(offset).limit(limit).all()

        def _event_to_dict(ev: Event) -> Dict[str, Any]:
            tags = [et.tag.tag_name for et in ev.tags if et.tag]
            sessions = [
                {
                    "session_id": s.session_id,
                    "start_time": s.start_time.isoformat() if s.start_time else None,
                    "end_time": s.end_time.isoformat() if s.end_time else None,
                    "capacity": s.capacity,
                    "current_registered": s.current_registered,
                    "waiting_list_limit": s.waiting_list_limit,
                    "status": s.status,
                }
                for s in ev.sessions
            ]
            return {
                "eid": ev.eid,
                "title": ev.title,
                "description": ev.description,
                "location": ev.location,
                "status": ev.status,
                "type_id": ev.type_id,
                "created_at": ev.created_at.isoformat() if ev.created_at else None, # type: ignore
                "updated_at": ev.updated_at.isoformat() if ev.updated_at else None, # type: ignore
                "tags": tags,
                "sessions": sessions,
            }

        return [_event_to_dict(ev) for ev in events]

    except Exception as e:
        raise SearchError(str(e))
    finally:
        db.close()
