import os
import re
import pymysql
from contextlib import contextmanager
from dotenv import load_dotenv

# 在导入时加载 .env
load_dotenv()


def get_connection():
    """
    获取一个数据库连接。
    使用 .env 中的配置：
      - DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_CHARSET
    默认 DB_NAME = event_system, DB_CHARSET = utf8mb4
    """
    conn = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "event_system"),
        charset=os.getenv("DB_CHARSET", "utf8mb4"),
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


def init_db_from_schema(schema_path: str = None):
    """
    从 db/schema.sql 初始化数据库结构。

    特性：
    - 使用 .env 中的 DB_NAME（默认为 event_system）作为目标数据库；
    - 自动 CREATE DATABASE IF NOT EXISTS 并 USE；
    - schema.sql 中可以包含：
        * DROP TABLE IF EXISTS
        * CREATE TABLE ...
        * INSERT ...
      但不应包含存储过程 / 触发器 / 复杂 DELIMITER 语句；
    - 可多次执行（开发环境方便重建）。

    用法：
        python -c "from backend.db import init_db_from_schema; init_db_from_schema()"
    """
    # 默认 schema.sql 路径：项目根目录 / db / schema.sql
    if schema_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        schema_path = os.path.join(base_dir, "db", "schema.sql")

    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"schema.sql not found: {schema_path}")

    db_name = os.getenv("DB_NAME", "event_system")

    # 先连接到 MySQL 服务器，不指定 database
    conn = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        charset=os.getenv("DB_CHARSET", "utf8mb4"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )

    try:
        with conn.cursor() as cursor:
            # 创建数据库并选择
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARACTER SET utf8mb4"
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
                # 再次保护：跳过 CREATE DATABASE / USE（已经在 Python 里执行过）
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
    # 允许直接运行 backend/db.py 来初始化数据库
    init_db_from_schema()