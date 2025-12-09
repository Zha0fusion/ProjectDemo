# backend/db_orm.py
"""
SQLAlchemy ORM 的数据库连接与 Session 工厂。

使用方式：
    from backend.db_orm import SessionLocal

    db = SessionLocal()
    try:
        ...  # ORM 查询
    finally:
        db.close()
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from backend.config import load_config

_config = load_config()

# 例如: mysql+pymysql://user:password@localhost:3306/event_system
engine = create_engine(
    _config.DATABASE_URL,
    echo=False,          # 如果想看 SQL，在开发阶段可以改成 True
    pool_pre_ping=True,
)

# 全局 Session 工厂（线程安全）
SessionLocal = scoped_session(
    sessionmaker(bind=engine, autocommit=False, autoflush=False)
)