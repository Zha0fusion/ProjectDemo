# backend/api/auth_api.py
from flask import Blueprint, jsonify

auth_bp = Blueprint("auth_api", __name__)

@auth_bp.get("/")
def list_events():
    # 先返回一个占位数据，后面再接 service + db
    return jsonify({"auth": []})