# backend/models.py
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum,
    ForeignKey,
    Text,
    Boolean,
    CheckConstraint,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "USER"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255))
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    role = Column(Enum("visitor", "staff", "admin", name="user_role"), nullable=False)
    blocked_until = Column(DateTime, nullable=True)

    registrations = relationship("Registration", back_populates="user")
    event_user_groups = relationship("EventUserGroup", back_populates="user")


class Organization(Base):
    __tablename__ = "ORGANIZATION"

    org_id = Column(Integer, primary_key=True, autoincrement=True)
    org_name = Column(String(255), nullable=False, unique=True)
    contact_email = Column(String(255))

    events = relationship("Event", back_populates="organization")


class EventType(Base):
    __tablename__ = "EVENTTYPE"

    type_id = Column(Integer, primary_key=True, autoincrement=True)
    type_name = Column(String(255), nullable=False, unique=True)

    events = relationship("Event", back_populates="event_type")


class Event(Base):
    __tablename__ = "EVENT"

    eid = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, ForeignKey("ORGANIZATION.org_id"), nullable=True)
    type_id = Column(Integer, ForeignKey("EVENTTYPE.type_id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    location = Column(String(255), nullable=False)
    status = Column(
        Enum("draft", "published", "closed", "archived", name="event_status"),
        nullable=False,
    )
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    organization = relationship("Organization", back_populates="events")
    event_type = relationship("EventType", back_populates="events")
    sessions = relationship("EventSession", back_populates="event")
    tags = relationship("EventTag", back_populates="event")
    event_user_groups = relationship("EventUserGroup", back_populates="event")


class EventSession(Base):
    __tablename__ = "EVENT_SESSION"

    session_id = Column(Integer, primary_key=True, autoincrement=True)
    eid = Column(Integer, ForeignKey("EVENT.eid"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    capacity = Column(Integer, nullable=False)
    current_registered = Column(Integer, nullable=False, default=0)
    waiting_list_limit = Column(Integer, nullable=False, default=0)
    status = Column(Enum("open", "closed", name="session_status"), nullable=False)

    __table_args__ = (
        CheckConstraint("capacity > 0", name="chk_session_capacity"),
        CheckConstraint("current_registered >= 0", name="chk_session_current_registered"),
        CheckConstraint("waiting_list_limit >= 0", name="chk_session_waiting_list"),
    )

    event = relationship("Event", back_populates="sessions")
    registrations = relationship("Registration", back_populates="session")


class Tag(Base):
    __tablename__ = "TAG"

    tag_id = Column(Integer, primary_key=True, autoincrement=True)
    tag_name = Column(String(255), nullable=False, unique=True)

    event_tags = relationship("EventTag", back_populates="tag")


class EventTag(Base):
    __tablename__ = "EVENT_TAG"

    eid = Column(Integer, ForeignKey("EVENT.eid"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("TAG.tag_id"), primary_key=True)

    event = relationship("Event", back_populates="tags")
    tag = relationship("Tag", back_populates="event_tags")


class Registration(Base):
    __tablename__ = "REGISTRATION"

    user_id = Column(Integer, ForeignKey("USER.user_id"), nullable=False)
    session_id = Column(Integer, ForeignKey("EVENT_SESSION.session_id"), nullable=False)
    register_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(
        Enum("registered", "waiting", "cancelled", name="registration_status"),
        nullable=False,
    )
    checkin_time = Column(DateTime, nullable=True)
    queue_position = Column(Integer, nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "session_id", name="pk_registration"),
    )

    user = relationship("User", back_populates="registrations")
    session = relationship("EventSession", back_populates="registrations")


class AudienceGroup(Base):
    __tablename__ = "AUDIENCE_GROUP"

    group_id = Column(Integer, primary_key=True, autoincrement=True)
    group_name = Column(String(255), nullable=False, unique=True)
    description = Column(String(255))
    is_default = Column(Boolean, nullable=False, default=False)

    event_user_groups = relationship("EventUserGroup", back_populates="group")


class EventUserGroup(Base):
    __tablename__ = "EVENT_USER_GROUP"

    user_id = Column(Integer, ForeignKey("USER.user_id"), nullable=False)
    eid = Column(Integer, ForeignKey("EVENT.eid"), nullable=False)
    group_id = Column(Integer, ForeignKey("AUDIENCE_GROUP.group_id"), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "eid", name="pk_event_user_group"),
    )

    user = relationship("User", back_populates="event_user_groups")
    event = relationship("Event", back_populates="event_user_groups")
    group = relationship("AudienceGroup", back_populates="event_user_groups")