# backend/config.py
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# ---------------------------------------------------------
# 明确从项目根目录加载 .env
# 假设当前文件路径: project_root/backend/config.py
# 项目根目录:       project_root
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")

# 如果 .env 存在，就加载
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
else:
    # 不存在时也不会报错，环境变量可能来自系统
    load_dotenv()


@dataclass
class BaseConfig:
    """
    基础配置：
    - 统一从环境变量读取数据库连接信息
    - 提供 DATABASE_URL（给 ORM 使用）
    - 保留 DB_HOST/DB_PORT/...（给 pymysql 使用）
    """

    # Flask
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")

    # DB 基本信息（给 pymysql 使用）
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", 3306))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "event_system")
    DB_CHARSET: str = os.getenv("DB_CHARSET", "utf8mb4")

    # 组合成 DATABASE_URL（给 SQLAlchemy 之类的 ORM 用）
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}?charset={charset}".format(
            user=os.getenv("DB_USER", "root"),
            pwd=os.getenv("DB_PASSWORD", ""),
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", 3306),
            db=os.getenv("DB_NAME", "event_system"),
            charset=os.getenv("DB_CHARSET", "utf8mb4"),
        ),
    )


class DevelopmentConfig(BaseConfig):
    DEBUG: bool = True


class ProductionConfig(BaseConfig):
    DEBUG: bool = False


def load_config(env_name: str | None = None) -> BaseConfig:
    """
    根据环境名返回配置对象。
    env_name 一般取自 FLASK_ENV：development / production
    """
    env_name = env_name or os.getenv("FLASK_ENV", "development")
    if env_name == "production":
        return ProductionConfig()
    return DevelopmentConfig()