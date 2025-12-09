# init_db.py
"""
数据库初始化脚本。

用途：
  - 从 backend/db/schema.sql 读取 DDL/初始化数据
  - 使用 .env 中的 DB_* 配置连接 MySQL
  - 自动创建数据库（如果不存在）并执行 schema.sql 中的语句

用法（在项目根目录执行）：
    python init_db.py
"""

from backend.db import init_db_from_schema


def main():
    init_db_from_schema()


if __name__ == "__main__":
    main()