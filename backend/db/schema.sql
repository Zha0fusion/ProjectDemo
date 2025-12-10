-- =========================================================
-- Database & Schema for Event Management System
-- =========================================================
-- NOTE:
--   - Database name is controlled by .env: DB_NAME (default: event_system)
--   - CREATE DATABASE / USE are handled in backend/db.py:init_db_from_schema
--   - If you run this file manually in a SQL client, you can:
--       CREATE DATABASE IF NOT EXISTS event_system DEFAULT CHARACTER SET utf8mb4;
--       USE event_system;
-- =========================================================

-- =========================================================
-- Drop existing tables (for idempotent initialization in dev)
-- Order: child tables first, then parent tables
-- =========================================================
DROP TABLE IF EXISTS EVENT_USER_GROUP;
DROP TABLE IF EXISTS REGISTRATION;
DROP TABLE IF EXISTS EVENT_TAG;
DROP TABLE IF EXISTS TAG;
DROP TABLE IF EXISTS EVENT_SESSION;
DROP TABLE IF EXISTS EVENT;
DROP TABLE IF EXISTS EVENTTYPE;
DROP TABLE IF EXISTS ORGANIZATION;
DROP TABLE IF EXISTS AUDIENCE_GROUP;
DROP TABLE IF EXISTS `USER`;

-- =========================================================
-- 1. USER
-- =========================================================
CREATE TABLE `USER` (
    user_id        INT AUTO_INCREMENT PRIMARY KEY,
    name           VARCHAR(255),
    email          VARCHAR(255) NOT NULL UNIQUE,
    password       VARCHAR(255) NOT NULL,
    role           ENUM('visitor', 'staff', 'admin') NOT NULL,
    blocked_until  DATETIME NULL,

    INDEX idx_user_role (role),
    INDEX idx_user_blocked_until (blocked_until)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================
-- 2. ORGANIZATION (optional)
-- =========================================================
CREATE TABLE ORGANIZATION (
    org_id         INT AUTO_INCREMENT PRIMARY KEY,
    org_name       VARCHAR(255) NOT NULL UNIQUE,
    contact_email  VARCHAR(255) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================
-- 3. EVENTTYPE
-- =========================================================
CREATE TABLE EVENTTYPE (
    type_id    INT AUTO_INCREMENT PRIMARY KEY,
    type_name  VARCHAR(255) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================
-- 4. EVENT
-- =========================================================
CREATE TABLE EVENT (
    eid          INT AUTO_INCREMENT PRIMARY KEY,
    org_id       INT NULL,
    type_id      INT NOT NULL,
    title        VARCHAR(255) NOT NULL,
    description  TEXT NULL,
    location     VARCHAR(255) NOT NULL,
    image_url    VARCHAR(255) NULL,
    allow_multi_session BOOLEAN NOT NULL DEFAULT FALSE,
    status       ENUM('draft', 'published', 'closed', 'archived') NOT NULL,
    created_at   DATETIME NOT NULL,
    updated_at   DATETIME NOT NULL,

    CONSTRAINT fk_event_org
        FOREIGN KEY (org_id) REFERENCES ORGANIZATION(org_id)
        ON UPDATE CASCADE ON DELETE SET NULL,

    CONSTRAINT fk_event_type
        FOREIGN KEY (type_id) REFERENCES EVENTTYPE(type_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    INDEX idx_event_type_status (type_id, status),
    INDEX idx_event_created_at (created_at),
    INDEX idx_event_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================
-- 5. EVENT_SESSION
-- =========================================================
CREATE TABLE EVENT_SESSION (
    session_id          INT AUTO_INCREMENT PRIMARY KEY,
    eid                 INT NOT NULL,
    start_time          DATETIME NOT NULL,
    end_time            DATETIME NOT NULL,
    capacity            INT NOT NULL,
    current_registered  INT NOT NULL DEFAULT 0,
    waiting_list_limit  INT NOT NULL DEFAULT 0,
    status              ENUM('open', 'closed') NOT NULL,

    CONSTRAINT fk_session_event
        FOREIGN KEY (eid) REFERENCES EVENT(eid)
        ON UPDATE CASCADE ON DELETE CASCADE,

    CONSTRAINT chk_session_capacity
        CHECK (capacity > 0),
    CONSTRAINT chk_session_current_registered
        CHECK (current_registered >= 0),
    CONSTRAINT chk_session_waiting_list
        CHECK (waiting_list_limit >= 0),

    INDEX idx_session_eid (eid),
    INDEX idx_session_start_time (start_time),
    INDEX idx_session_end_time (end_time),
    INDEX idx_session_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- NOTE (enforced in application layer):
--   - start_time < end_time
--   - current_registered <= capacity

-- =========================================================
-- 6. TAG
-- =========================================================
CREATE TABLE TAG (
    tag_id    INT AUTO_INCREMENT PRIMARY KEY,
    tag_name  VARCHAR(255) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================
-- 7. EVENT_TAG (many-to-many: EVENT <-> TAG)
-- =========================================================
CREATE TABLE EVENT_TAG (
    eid     INT NOT NULL,
    tag_id  INT NOT NULL,

    PRIMARY KEY (eid, tag_id),

    CONSTRAINT fk_event_tag_event
        FOREIGN KEY (eid) REFERENCES EVENT(eid)
        ON UPDATE CASCADE ON DELETE CASCADE,

    CONSTRAINT fk_event_tag_tag
        FOREIGN KEY (tag_id) REFERENCES TAG(tag_id)
        ON UPDATE CASCADE ON DELETE CASCADE,

    INDEX idx_event_tag_tag_id (tag_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================
-- 8. REGISTRATION
-- =========================================================
CREATE TABLE REGISTRATION (
    user_id        INT NOT NULL,
    session_id     INT NOT NULL,
    register_time  DATETIME NOT NULL,
    status         ENUM('registered', 'waiting', 'cancelled') NOT NULL,
    checkin_time   DATETIME NULL,
    queue_position INT NULL,

    PRIMARY KEY (user_id, session_id),

    CONSTRAINT fk_registration_user
        FOREIGN KEY (user_id) REFERENCES `USER`(user_id)
        ON UPDATE CASCADE ON DELETE CASCADE,

    CONSTRAINT fk_registration_session
        FOREIGN KEY (session_id) REFERENCES EVENT_SESSION(session_id)
        ON UPDATE CASCADE ON DELETE CASCADE,

    INDEX idx_registration_user (user_id),
    INDEX idx_registration_session (session_id),
    INDEX idx_registration_session_status (session_id, status),
    INDEX idx_registration_user_status (user_id, status),
    INDEX idx_registration_checkin_time (checkin_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Business semantics (handled in application layer):
--   - status = 'registered'  -> counts into EVENT_SESSION.current_registered
--   - status = 'waiting'     -> waiting list (ordered by queue_position)
--   - status = 'cancelled'   -> not counted
--   - checkin_time IS NOT NULL: checked-in
--   - no-show: session finished AND status='registered' AND checkin_time IS NULL

-- =========================================================
-- 9. AUDIENCE_GROUP (configurable audience segments)
-- =========================================================
CREATE TABLE AUDIENCE_GROUP (
    group_id     INT AUTO_INCREMENT PRIMARY KEY,
    group_name   VARCHAR(255) NOT NULL UNIQUE,
    description  VARCHAR(255) NULL,
    is_default   BOOLEAN NOT NULL DEFAULT FALSE,

    INDEX idx_audience_group_is_default (is_default)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert one default group "Member"
INSERT INTO AUDIENCE_GROUP (group_name, description, is_default)
VALUES ('Member', 'Default audience group', TRUE);

-- Admins can add more groups via application UI.

-- =========================================================
-- 10. EVENT_USER_GROUP (user group per event)
-- =========================================================
CREATE TABLE EVENT_USER_GROUP (
    user_id   INT NOT NULL,
    eid       INT NOT NULL,
    group_id  INT NOT NULL,

    PRIMARY KEY (user_id, eid),

    CONSTRAINT fk_event_user_group_user
        FOREIGN KEY (user_id) REFERENCES `USER`(user_id)
        ON UPDATE CASCADE ON DELETE CASCADE,

    CONSTRAINT fk_event_user_group_event
        FOREIGN KEY (eid) REFERENCES EVENT(eid)
        ON UPDATE CASCADE ON DELETE CASCADE,

    CONSTRAINT fk_event_user_group_group
        FOREIGN KEY (group_id) REFERENCES AUDIENCE_GROUP(group_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    INDEX idx_event_user_group_eid_group (eid, group_id),
    INDEX idx_event_user_group_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Business semantics (handled in application layer):
--   - One group per (user, event): PK(user_id, eid)
--   - On first registration to an event, if no group specified,
--     assign the default group from AUDIENCE_GROUP (is_default = TRUE).

-- =========================================================
-- End of schema.sql
-- =========================================================