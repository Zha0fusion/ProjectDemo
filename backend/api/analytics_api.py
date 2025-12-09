# backend/api/analytics_api.py
from flask import Blueprint, jsonify

analytics_bp = Blueprint("analytics_api", __name__)

@analytics_bp.get("/")
def list_analytics():
    # 先返回一个占位数据，后面再接 service + db
    return jsonify({"analytics": []})