# backend/db/db.py
import os
import re
from contextlib import contextmanager

import pymysql

from backend.config import load_config

# 加载配置（内部会从项目根目录的 .env 读取）
config = load_config()


def get_connection():
    """
    获取一个数据库连接。

    使用 backend/config.py 中的配置：
      - config.DB_HOST, config.DB_PORT, config.DB_USER,
        config.DB_PASSWORD, config.DB_NAME, config.DB_CHARSET
    """
    conn = pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        charset=config.DB_CHARSET,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
    return conn


@contextmanager
def get_cursor():
    """
    通用的上下文管理器：
    - 建立连接，生成 cursor
    - 正常结束时 commit
    - 出现异常时 rollback 并再次抛出
    - 最后关闭 cursor 和连接

    用法示例：
        from backend.db import get_cursor

        with get_cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception:
        if conn is not None:
            conn.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def init_db_from_schema(schema_path: str | None = None):
    """
    从 db/schema.sql 初始化数据库结构。

    特性：
    - 使用 config.DB_NAME 作为目标数据库；
    - 自动 CREATE DATABASE IF NOT EXISTS 并 USE；
    - schema.sql 中可以包含：
        * DROP TABLE IF EXISTS
        * CREATE TABLE ...
        * INSERT ...
      但不应包含存储过程 / 触发器 / 复杂 DELIMITER 语句；
    - 可多次执行（开发环境方便重建）。

    用法（在项目根目录运行）：
        python -c "from backend.db import init_db_from_schema; init_db_from_schema()"
    """
    # 默认 schema.sql 路径：与当前 db.py 同目录（backend/db/schema.sql）
    if schema_path is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(current_dir, "schema.sql")

    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"schema.sql not found: {schema_path}")

    db_name = config.DB_NAME

    # 先连接到 MySQL 服务器，不指定 database
    conn = pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        charset=config.DB_CHARSET,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )

    try:
        with conn.cursor() as cursor:
            # 创建数据库并选择
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                f"DEFAULT CHARACTER SET {config.DB_CHARSET}"
            )
            cursor.execute(f"USE `{db_name}`")

            # 读取 schema 文件
            with open(schema_path, "r", encoding="utf-8") as f:
                sql_content = f.read()

            # 去掉整行以 -- 开头的注释
            lines = []
            for line in sql_content.splitlines():
                if line.strip().startswith("--"):
                    continue
                lines.append(line)
            sql_content = "\n".join(lines)

            # 按分号分割语句（适用于当前纯 DDL + 简单 INSERT 的场景）
            statements = [s.strip() for s in sql_content.split(";") if s.strip()]

            for stmt in statements:
                # 再保护一下：跳过 CREATE DATABASE / USE（已经在 Python 里执行过）
                if re.match(r"^\s*(CREATE\s+DATABASE|USE\s+)", stmt, re.IGNORECASE):
                    continue
                cursor.execute(stmt)

        conn.commit()
        print(f"✓ Database '{db_name}' initialized successfully from schema.sql")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    # 允许直接运行:
    #   python -m backend.db.db
    # 或在项目根目录:
    #   python -c "from backend.db import init_db_from_schema; init_db_from_schema()"
    init_db_from_schema()