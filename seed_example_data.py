# seed_example_data.py
"""
向数据库中插入示例数据（example data）。

用法（在项目根目录）：
    # 1. 初始化数据库结构（只需第一次）
    python init_db.py

    # 2. 插入示例数据（可多次执行）
    python seed_example_data.py
"""

from datetime import datetime, timedelta
import random
import string

from backend.db import get_cursor


def seed_users():
    """
    插入示例用户到 USER 表。
    字段: user_id(AI), name, email, password, role, blocked_until
    """
    users = [
        {
            "name": "Test Visitor 1",
            "email": "visitor1@example.com",
            "password": "password_visitor1",  # 实际项目应使用加密后的密码
            "role": "visitor",
        },
        {
            "name": "Test Admin",
            "email": "admin@example.com",
            "password": "password_admin",
            "role": "admin",
        },
    ]

    sql = """
    INSERT INTO `USER` (name, email, password, role)
    VALUES (%(name)s, %(email)s, %(password)s, %(role)s)
    ON DUPLICATE KEY UPDATE
        name = VALUES(name),
        password = VALUES(password),
        role = VALUES(role)
    """
    with get_cursor() as cursor:
        for u in users:
            cursor.execute(sql, u)

    print("✓ USER 示例数据插入完成")


def seed_organizations():
    """
    插入示例机构到 ORGANIZATION 表。
    字段: org_id(AI), org_name, contact_email
    """
    orgs = [
        {
            "org_name": "Sample School A",
            "contact_email": "contact_a@example.com",
        }
    ]

    sql = """
    INSERT INTO ORGANIZATION (org_name, contact_email)
    VALUES (%(org_name)s, %(contact_email)s)
    ON DUPLICATE KEY UPDATE
        contact_email = VALUES(contact_email)
    """
    with get_cursor() as cursor:
        for o in orgs:
            cursor.execute(sql, o)

    print("✓ ORGANIZATION 示例数据插入完成")


def seed_event_types():
    """
    插入示例 EVENTTYPE。
    字段: type_id(AI), type_name
    """
    types = [
        {"type_name": "Lecture"},
        {"type_name": "Workshop"},
    ]

    sql = """
    INSERT INTO EVENTTYPE (type_name)
    VALUES (%(type_name)s)
    ON DUPLICATE KEY UPDATE
        type_name = VALUES(type_name)
    """
    with get_cursor() as cursor:
        for t in types:
            cursor.execute(sql, t)

    print("✓ EVENTTYPE 示例数据插入完成")


def seed_events_and_sessions():
    """
    插入 EVENT 和 EVENT_SESSION 示例数据。

    EVENT:
      - eid(AI), org_id, type_id, title, description,
        location, status, created_at, updated_at

    EVENT_SESSION:
      - session_id(AI), eid, start_time, end_time,
        capacity, current_registered, waiting_list_limit, status
    """
    now = datetime.now()

    # 先查出一个 org_id 和几个 type_id 用来引用
    with get_cursor() as cursor:
        cursor.execute("SELECT org_id FROM ORGANIZATION ORDER BY org_id LIMIT 1")
        org_row = cursor.fetchone()
        org_id = org_row["org_id"] if org_row else None

        cursor.execute("SELECT type_id, type_name FROM EVENTTYPE ORDER BY type_id")
        type_rows = cursor.fetchall()

    # 做一下简单防御
    if not type_rows:
        raise RuntimeError("请先插入 EVENTTYPE 示例数据再运行本脚本")

    type_id_lecture = type_rows[0]["type_id"]
    type_id_workshop = type_rows[1]["type_id"] if len(type_rows) > 1 else type_rows[0]["type_id"]

    events = [
        {
            "eid": 1,  # 指定 eid，方便前端调试时使用固定 ID
            "org_id": org_id,
            "type_id": type_id_lecture,
            "title": "Sample Event A - Lecture",
            "description": "This is a sample lecture event A for development testing.",
            "location": "Teaching Building A101",
            "status": "published",
            "created_at": now,
            "updated_at": now,
        },
        {
            "eid": 2,
            "org_id": org_id,
            "type_id": type_id_workshop,
            "title": "Sample Event B - Workshop",
            "description": "This is a sample workshop event B for development testing.",
            "location": "Lab B202",
            "status": "published",
            "created_at": now,
            "updated_at": now,
        },
    ]

    event_sql = """
    INSERT INTO EVENT (
        eid, org_id, type_id, title, description,
        location, status, created_at, updated_at
    )
    VALUES (
        %(eid)s, %(org_id)s, %(type_id)s, %(title)s, %(description)s,
        %(location)s, %(status)s, %(created_at)s, %(updated_at)s
    )
    ON DUPLICATE KEY UPDATE
        org_id = VALUES(org_id),
        type_id = VALUES(type_id),
        title = VALUES(title),
        description = VALUES(description),
        location = VALUES(location),
        status = VALUES(status),
        updated_at = VALUES(updated_at)
    """

    session_sql = """
    INSERT INTO EVENT_SESSION (
        eid, start_time, end_time,
        capacity, current_registered, waiting_list_limit, status
    )
    VALUES (
        %(eid)s, %(start_time)s, %(end_time)s,
        %(capacity)s, %(current_registered)s, %(waiting_list_limit)s, %(status)s
    )
    """

    with get_cursor() as cursor:
        # 插入 EVENT
        for e in events:
            cursor.execute(event_sql, e)

        # 插入 EVENT_SESSION（给每个活动安排几个场次）
        sessions = [
            # 活动 1 的两场
            {
                "eid": 1,
                "start_time": now + timedelta(days=1, hours=9),
                "end_time": now + timedelta(days=1, hours=11),
                "capacity": 50,
                "current_registered": 0,
                "waiting_list_limit": 10,
                "status": "open",
            },
            {
                "eid": 1,
                "start_time": now + timedelta(days=2, hours=14),
                "end_time": now + timedelta(days=2, hours=16),
                "capacity": 30,
                "current_registered": 0,
                "waiting_list_limit": 5,
                "status": "open",
            },
            # 活动 2 的一场
            {
                "eid": 2,
                "start_time": now + timedelta(days=3, hours=10),
                "end_time": now + timedelta(days=3, hours=13),
                "capacity": 100,
                "current_registered": 0,
                "waiting_list_limit": 20,
                "status": "open",
            },
        ]

        for s in sessions:
            cursor.execute(session_sql, s)

    print("✓ EVENT & EVENT_SESSION 示例数据插入完成")


def seed_tags_and_event_tags():
    """
    插入 TAG 和 EVENT_TAG 示例数据。
    TAG: tag_id(AI), tag_name
    EVENT_TAG: eid, tag_id
    """
    tags = [
        {"tag_name": "Academic"},
        {"tag_name": "Career Development"},
        {"tag_name": "Hobby"},
    ]

    tag_sql = """
    INSERT INTO TAG (tag_name)
    VALUES (%(tag_name)s)
    ON DUPLICATE KEY UPDATE
        tag_name = VALUES(tag_name)
    """

    with get_cursor() as cursor:
        for t in tags:
            cursor.execute(tag_sql, t)

        # 查出 tag_id
        cursor.execute("SELECT tag_id, tag_name FROM TAG")
        tag_rows = cursor.fetchall()

        tag_map = {row["tag_name"]: row["tag_id"] for row in tag_rows}

        event_tags = [
            {"eid": 1, "tag_id": tag_map.get("Academic")},
            {"eid": 1, "tag_id": tag_map.get("Hobby")},
            {"eid": 2, "tag_id": tag_map.get("Career Development")},
        ]

        et_sql = """
        INSERT IGNORE INTO EVENT_TAG (eid, tag_id)
        VALUES (%(eid)s, %(tag_id)s)
        """

        for et in event_tags:
            # 防御：tag_id 有可能 None（意外情况）
            if et["tag_id"] is not None:
                cursor.execute(et_sql, et)

    print("✓ TAG & EVENT_TAG 示例数据插入完成")


def seed_event_user_group():
    """
    根据 schema，AUDIENCE_GROUP 默认已经插入了一个 Member 组：
      INSERT INTO AUDIENCE_GROUP (group_name, description, is_default)
      VALUES ('Member', 'Default audience group', TRUE);

    这里做两件事：
      1. 查询默认组 group_id
      2. 把示例用户绑定到示例活动的默认组上
    """
    with get_cursor() as cursor:
        # 1) 找默认组
        cursor.execute(
            "SELECT group_id FROM AUDIENCE_GROUP WHERE is_default = TRUE ORDER BY group_id LIMIT 1"
        )
        group_row = cursor.fetchone()
        if not group_row:
            print("⚠ 未找到默认 AUDIENCE_GROUP 记录，跳过 EVENT_USER_GROUP 示例数据插入")
            return

        default_group_id = group_row["group_id"]

        # 2) 找出几个示例用户和活动
        cursor.execute(
            "SELECT user_id, email FROM `USER` WHERE email IN ('visitor1@example.com', 'admin@example.com')"
        )
        user_rows = cursor.fetchall()
        cursor.execute("SELECT eid, title FROM EVENT WHERE eid IN (1, 2)")
        event_rows = cursor.fetchall()

        if not user_rows or not event_rows:
            print("⚠ 用户或活动示例数据不足，跳过 EVENT_USER_GROUP 插入")
            return

        eug_sql = """
        INSERT INTO EVENT_USER_GROUP (user_id, eid, group_id)
        VALUES (%(user_id)s, %(eid)s, %(group_id)s)
        ON DUPLICATE KEY UPDATE
            group_id = VALUES(group_id)
        """

        # 简单示例：把所有这些用户，都加入所有这些活动的默认组
        for u in user_rows:
            for e in event_rows:
                cursor.execute(
                    eug_sql,
                    {
                        "user_id": u["user_id"],
                        "eid": e["eid"],
                        "group_id": default_group_id,
                    },
                )

    print("✓ EVENT_USER_GROUP 示例数据插入完成")


# ===== 额外：可调规模的随机测试数据集 =====


def seed_test_data(
    *,
    user_count: int = 200,
    event_count: int = 20,
    sessions_per_event: int = 3,
    base_capacity: int = 50,
    capacity_jitter: int = 30,
    waiting_list_limit: int = 20,
):
    """生成可调规模的随机测试数据。"""

    now = datetime.now()

    # 1) 生成用户
    user_sql = """
    INSERT INTO `USER` (name, email, password, role)
    VALUES (%(name)s, %(email)s, %(password)s, %(role)s)
    ON DUPLICATE KEY UPDATE name=VALUES(name), password=VALUES(password), role=VALUES(role)
    """
    users = []
    for i in range(user_count):
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        users.append(
            {
                "name": f"TD_User_{suffix}",
                "email": f"td_user_{suffix}@example.com",
                "password": "password",
                "role": "visitor",
            }
        )

    # 2) 生成活动 + 场次
    event_sql = """
    INSERT INTO EVENT (org_id, type_id, title, description, location, status, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    session_sql = """
    INSERT INTO EVENT_SESSION (eid, start_time, end_time, capacity, current_registered, waiting_list_limit, status)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    with get_cursor() as cursor:
        # 插入用户
        for u in users:
            cursor.execute(user_sql, u)

        # 准备 type_id（如果没有则创建）
        cursor.execute("SELECT type_id FROM EVENTTYPE ORDER BY type_id LIMIT 1")
        type_row = cursor.fetchone()
        if not type_row:
            cursor.execute("INSERT INTO EVENTTYPE (type_name) VALUES ('AutoType')")
            type_id = cursor.lastrowid
        else:
            type_id = type_row["type_id"]

        # 插入活动和场次
        for eidx in range(event_count):
            title_suffix = "".join(random.choices(string.ascii_uppercase, k=4))
            event_title = f"TD Event {eidx}-{title_suffix}"
            cursor.execute(
                event_sql,
                (
                    None,
                    type_id,
                    event_title,
                    "Autogenerated for load tests",
                    f"Room-{eidx%5}",
                    "published",
                    now,
                    now,
                ),
            )
            eid = cursor.lastrowid

            for sidx in range(sessions_per_event):
                jitter = random.randint(-capacity_jitter, capacity_jitter)
                cap = max(5, base_capacity + jitter)
                start = now + timedelta(days=1 + eidx, hours=sidx * 3)
                end = start + timedelta(hours=2)
                cursor.execute(
                    session_sql,
                    (
                        eid,
                        start,
                        end,
                        cap,
                        0,
                        waiting_list_limit,
                        "open",
                    ),
                )

    print(
        f"✓ Test data generated: users={user_count}, events={event_count}, sessions_per_event={sessions_per_event}"
    )


def main():
    # 顺序很重要：先用户、机构、类型，再活动/场次，再标签，最后用户组
    seed_users()
    seed_organizations()
    seed_event_types()
    seed_events_and_sessions()
    seed_tags_and_event_tags()
    seed_event_user_group()
    print("✓ 所有示例数据插入完成")
    # 如需额外大规模测试数据，可手动调用 seed_test_data()
    # python -c "from seed_example_data import seed_test_data; seed_test_data(user_count=500, event_count=50, sessions_per_event=4, base_capacity=60, capacity_jitter=20, waiting_list_limit=30)"
if __name__ == "__main__":
    main()
