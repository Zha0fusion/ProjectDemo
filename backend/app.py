# backend/app.py
import os

from flask import Flask, jsonify
from flask_cors import CORS

from dotenv import load_dotenv

# 确保在应用启动时加载 .env（db.py 里也会 load，但这里再做一次无害）
load_dotenv()

# ====== Blueprint 导入（按你的目录结构创建对应文件） ======
# 这里先假设你会有这些模块，后面可以一点点往里填实现
from backend.api.auth_api import auth_bp
from backend.api.events_api import events_bp
from backend.api.registration_api import registration_bp
from backend.api.analytics_api import analytics_bp
from backend.api.checkin_api import checkin_bp
from backend.api.groups_api import groups_bp
from backend.api.admin_api import admin_bp


def create_app(config_name: str | None = None) -> Flask:
    """
    Flask 应用工厂：
    - 加载配置（主要是 SECRET_KEY 之类）
    - 启用 CORS
    - 注册 Blueprint
    - 注册错误处理器
    """
    app = Flask(__name__)

    # 1. 基础配置（大部分数据库相关由 db.py 通过 .env 读取）
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    # 如果你之后需要区分 dev / prod，可以在这里根据 config_name 做更多设置
    app.config["ENV"] = config_name or os.getenv("FLASK_ENV", "development")
    app.config["JSON_AS_ASCII"] = False  # JSON 返回中文不转义

    # 2. CORS：允许前端 Vue 调用 /api/*
    # 部署时可以把 origins 改为你的前端域名
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # 3. 注册 Blueprint
    register_blueprints(app)

    # 4. 注册全局错误处理
    register_error_handlers(app)

    # 5. 简单健康检查 / 根路由（可选）
    @app.get("/")
    def index():
        return jsonify({"message": "Event Registration System backend is running."})

    return app


def register_blueprints(app: Flask) -> None:
    """
    把各个功能模块的 Blueprint 挂在 /api 下。
    """
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(events_bp, url_prefix="/api/events")
    app.register_blueprint(registration_bp, url_prefix="/api/registrations")
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")
    app.register_blueprint(checkin_bp, url_prefix="/api/checkin")
    app.register_blueprint(groups_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api")


def register_error_handlers(app: Flask) -> None:
    """
    统一错误返回格式，便于前端处理。
    """

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "error": "bad_request",
            "message": str(error)
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            "error": "unauthorized",
            "message": "Authentication required"
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            "error": "forbidden",
            "message": "Permission denied"
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "error": "not_found",
            "message": "Resource not found"
        }), 404

    @app.errorhandler(409)
    def conflict(error):
        return jsonify({
            "error": "conflict",
            "message": str(error)
        }), 409

    @app.errorhandler(500)
    def internal_error(error):
        # 生产环境一般不返回 error 的具体内容，只记录日志
        return jsonify({
            "error": "internal_server_error"
        }), 500


if __name__ == "__main__":
    """
    本地启动：
        # 确保 .env 中数据库配置正确，且已用 db.py 初始化 schema
        $ export FLASK_ENV=development      # 或在 .env 里设置
        $ python app.py
    """
    env = os.getenv("FLASK_ENV", "development")
    app = create_app(env)
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        debug=(env == "development"),
    )