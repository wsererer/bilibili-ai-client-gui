import base64
import io
import json
import time
import threading
import qrcode
from PIL import Image
from flask import Flask, render_template_string, jsonify, request
import httpx
import sys
from pathlib import Path

_parent_dir = str(Path(__file__).parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from config import config
    from utils.logger import logger
except Exception as e:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.error(f"Import error in bilibili_login: {e}")

app = Flask(__name__)

LOGIN_DATA_LOCK = threading.Lock()
LOGIN_DATA = {
    "oauthKey": "",
    "cookie": None,
    "qrcode_data": None
}

BILIBILI_QR_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
BILIBILI_QR_POLL_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>B站登录 - Bilibili AI Client</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #00a1d6 0%, #fb7299 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-box {
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            text-align: center;
            max-width: 400px;
        }
        h1 { color: #00a1d6; margin-bottom: 10px; font-size: 24px; }
        p { color: #666; margin-bottom: 30px; font-size: 14px; }
        .qrcode { margin: 20px 0; text-align: center; }
        .qrcode img { border: 2px dashed #00a1d6; border-radius: 8px; width: 200px; height: 200px; }
        .status {
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            margin-top: 20px;
        }
        .status.pending { background: #f0f0f0; color: #666; }
        .status.scanned { background: #fff3e0; color: #e65100; }
        .status.confirmed { background: #e8f5e9; color: #2e7d32; }
        .status.error { background: #ffebee; color: #c62828; }
        .btn {
            background: #00a1d6;
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 20px;
        }
        .btn:hover { background: #008ba9; }
        .close-hint { font-size: 12px; color: #999; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>B站账号登录</h1>
        <p>请扫描下方二维码登录B站账号</p>
        <div class="qrcode">
            {% if qrcode %}
            <img src="{{ qrcode }}" alt="QR Code">
            {% else %}
            <p>加载中...</p>
            {% endif %}
        </div>
        <div id="status" class="status pending">请使用B站客户端扫描二维码</div>
        {% if error %}
        <div class="status error">{{ error }}</div>
        {% endif %}
        <button class="btn" onclick="refresh()">刷新二维码</button>
        <p class="close-hint">登录成功后可关闭此页面</p>
    </div>
    <script>
        let lastStatus = 'pending';
        function checkStatus() {
            fetch('/login_status')
                .then(r => r.json())
                .then(data => {
                    if (data.status !== lastStatus) {
                        lastStatus = data.status;
                        document.getElementById('status').className = 'status ' + data.status;
                        document.getElementById('status').textContent = data.message;
                        if (data.status === 'confirmed') {
                            setTimeout(() => {
                                fetch('/close');
                                setTimeout(() => window.close(), 500);
                            }, 1000);
                        }
                    }
                    if (data.status !== 'confirmed') {
                        setTimeout(checkStatus, 1500);
                    }
                });
        }
        function refresh() {
            window.location.reload();
        }
        checkStatus();
    </script>
</body>
</html>
'''

def generate_qrcode():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com/"
        }

        resp = httpx.get(BILIBILI_QR_URL, headers=headers, timeout=10)
        data = resp.json()

        if data.get("code") != 0:
            return None, data.get("message", "获取二维码失败")

        qr_data = data["data"]
        qrcode_key = qr_data["qrcode_key"]
        url = qr_data["url"]

        with LOGIN_DATA_LOCK:
            LOGIN_DATA["oauthKey"] = qrcode_key
            LOGIN_DATA["cookie"] = None

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_base64}", None

    except Exception as e:
        logger.error(f"生成二维码失败: {e}")
        return None, str(e)


def poll_login():
    with LOGIN_DATA_LOCK:
        qrcode_key = LOGIN_DATA.get("oauthKey")
    logger.info(f"poll_login called, oauthKey present: {bool(qrcode_key)}")
    if not qrcode_key:
        return {"status": "error", "message": "请先获取二维码"}

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com/"
        }

        resp = httpx.get(BILIBILI_QR_POLL_URL, params={"qrcode_key": qrcode_key, "source": "main-web", "gourl": "https://www.bilibili.com"}, headers=headers, timeout=10)
        logger.info(f"poll response status: {resp.status_code}, text: {resp.text[:500]}")

        if not resp.text:
            return {"status": "pending", "message": "等待扫码..."}

        try:
            result = resp.json()
        except Exception:
            return {"status": "pending", "message": "等待扫码..."}

        logger.info(f"poll result code: {result.get('code')}, data: {str(result.get('data'))[:200]}")

        if result.get("code") == 0:
            data = result.get("data", {})
            url_data = data.get("url", "")
            cookie_str = data.get("cookie", "")

            if cookie_str:
                with LOGIN_DATA_LOCK:
                    LOGIN_DATA["cookie"] = cookie_str
                return {"status": "confirmed", "message": "登录成功！正在保存..."}
            elif url_data and ("SESSDATA" in url_data or "access_key" in url_data):
                from urllib.parse import urlparse, parse_qs, unquote
                parsed = urlparse(url_data)
                raw_query = unquote(parsed.query)
                logger.info(f"Raw query (decoded): {raw_query[:100]}")
                params = parse_qs(raw_query, keep_blank_values=True)
                logger.info(f"params keys: {list(params.keys())}")
                sessdata = params.get("SESSDATA", [""])[0] if params.get("SESSDATA") else ""
                bili_jct = params.get("bili_jct", [""])[0] if params.get("bili_jct") else ""
                dedeuserid = params.get("DedeUserID", [""])[0] if params.get("DedeUserID") else ""
                logger.info(f"sessdata length: {len(sessdata)}, bili_jct: {bili_jct[:20] if bili_jct else 'empty'}, dedeuserid: {dedeuserid}")
                if sessdata:
                    cookie = f"SESSDATA={sessdata}; bili_jct={bili_jct}; DedeUserID={dedeuserid}"
                    with LOGIN_DATA_LOCK:
                        LOGIN_DATA["cookie"] = cookie
                    logger.info(f"Extracted cookie: {cookie[:50]}...")
                    return {"status": "confirmed", "message": "登录成功！正在保存..."}

        if result.get("code") == -1:
            return {"status": "pending", "message": "请扫描二维码"}
        elif result.get("code") == -2:
            return {"status": "error", "message": "二维码已过期，请刷新"}

        return {"status": "pending", "message": "等待扫码..."}

    except Exception as e:
        logger.error(f"轮询错误: {e}")
        return {"status": "pending", "message": "等待扫码..."}


def get_config_path():
    from utils.app_data import APP_DATA_DIR
    return APP_DATA_DIR / "login_cookie.txt"

def save_cookie():
    with LOGIN_DATA_LOCK:
        cookie = LOGIN_DATA.get("cookie")
    logger.info(f"save_cookie called, cookie present: {bool(cookie)}")
    if cookie:
        try:
            config.set("bili_auth", cookie)
            config.set("bili_login_time", str(int(time.time())))

            cookie_file = get_config_path()
            logger.info(f"Saving cookie to: {cookie_file}")
            cookie_file.write_text(cookie, encoding='utf-8')
            logger.info(f"Cookie saved successfully, file exists: {cookie_file.exists()}")

            return True
        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")
    return False


@app.route('/')
def index():
    try:
        qrcode_img, error = generate_qrcode()
        if error:
            print(f"QR生成错误: {error}")
        return render_template_string(HTML_TEMPLATE, qrcode=qrcode_img, error=error)
    except Exception as e:
        print(f"index路由错误: {e}")
        return f"错误: {e}", 500


@app.route('/login_status')
def login_status():
    with LOGIN_DATA_LOCK:
        has_cookie = bool(LOGIN_DATA.get('cookie'))
    logger.info(f"/login_status called, cookie in LOGIN_DATA: {has_cookie}")
    if has_cookie:
        logger.info("Cookie found in LOGIN_DATA, calling save_cookie")
        if save_cookie():
            logger.info("save_cookie returned True")
            return jsonify({"status": "confirmed", "message": "登录成功！"})
        logger.info("save_cookie returned False")
        return jsonify({"status": "error", "message": "保存失败"})

    result = poll_login()
    logger.info(f"poll_login returned: {result}")
    if result.get("status") == "confirmed":
        with LOGIN_DATA_LOCK:
            has_cookie = bool(LOGIN_DATA.get("cookie"))
        if has_cookie:
            logger.info("Confirmed via poll, calling save_cookie immediately")
            if save_cookie():
                logger.info("save_cookie returned True")
            else:
                logger.info("save_cookie returned False")
    return jsonify(result)


@app.route('/refresh')
def refresh():
    with LOGIN_DATA_LOCK:
        LOGIN_DATA["oauthKey"] = ""
        LOGIN_DATA["cookie"] = None
    return index()


@app.route('/close')
def close():
    return "<script>window.close();</script>"


def run_login_server(port=51888):
    logger.info(f"启动B站登录服务 http://localhost:{port}")
    app.run(host='127.0.0.1', port=port, debug=False, threaded=True)


if __name__ == "__main__":
    run_login_server()