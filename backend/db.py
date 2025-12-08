# backend/db.py
import os
import pymysql
from contextlib import contextmanager
from dotenv import load_dotenv

# 在导入时就加载 .env（假设从项目根目录运行 python backend/app.py）
load_dotenv()


def get_connection():
    """
    获取一个新的数据库连接。
    - 使用环境变量配置（.env 由 python-dotenv 加载）
    - 关闭 autocommit，交由应用控制事务
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

    在 app.py 中可以这样用：
        with get_cursor() as cursor:
            cursor.execute("SELECT ...")
            ...
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
        # 继续向外抛出异常，让上层（比如 Flask/FastAPI）决定返回什么 HTTP 状态码
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def init_db_from_schema(schema_path: str = None):
    """
    可选工具函数：一键执行 schema.sql，用于本地快速初始化数据库。
    - schema_path 默认指向项目根目录的 db/schema.sql
    - 这个函数可以在单独的 init_db.py 或命令行脚本中调用，而不一定在 app.py 中调用。
    """
    if schema_path is None:
        # 默认：backend/../db/schema.sql
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        schema_path = os.path.join(base_dir, "db", "schema.sql")

    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"schema.sql not found: {schema_path}")

    # 这里要先连到 MySQL，而不一定已有 event_system 数据库
    # 所以先用不指定 database 的连接，再执行 schema.sql 里包含的 CREATE DATABASE/USE
    conn = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        charset=os.getenv("DB_CHARSET", "utf8mb4"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,  # 执行 schema.sql 时通常直接自动提交即可
    )

    try:
        with conn.cursor() as cursor, open(schema_path, "r", encoding="utf-8") as f:
            sql_commands = f.read()

            # 注意：pymysql 默认不支持一次 execute 多条语句
            # 简单做法：按分号切分；更复杂情况可用其它工具或在 schema.sql 里只放单条语句
            for statement in sql_commands.split(";"):
                stmt = statement.strip()
                if not stmt:
                    continue
                cursor.execute(stmt)
    finally:
        conn.close()
