# backend/util/qrcode_utils.py
import io
import json

import qrcode
from flask import send_file


def build_checkin_payload(user_id: int, session_id: int) -> str:
    """
    构造二维码中要编码的 JSON 字符串内容。
    这里只放最基础信息：user_id + session_id，type 用来区分用途。
    """
    payload = {
        "type": "event_checkin",
        "user_id": user_id,
        "session_id": session_id,
    }
    # ensure_ascii=False 以便未来如果有中文也能正常编码
    return json.dumps(payload, ensure_ascii=False)


def generate_qr_png_bytes(data: str) -> io.BytesIO:
    """
    根据传入字符串生成 QRCode 图片，返回内存中的 BytesIO。

    使用 qrcode.make(data) 得到一个 PIL.Image 对象，
    再直接保存到 BytesIO 中，不显式传 format 参数，
    以提高在不同 Pillow 版本中的兼容性。
    """
    img = qrcode.make(data)

    buf = io.BytesIO()
    # 不传 format，使用默认格式（通常是 PNG，对我们的场景足够）
    img.save(buf)
    buf.seek(0)
    return buf


def send_qr_response(qr_buf: io.BytesIO, filename: str | None = None):
    """
    封装一个 Flask send_file 响应，方便 API 直接返回二维码图片。
    """
    return send_file(
        qr_buf,
        mimetype="image/png",
        as_attachment=False,
        download_name=filename or "qrcode.png",
    )