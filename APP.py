from flask import Flask, Response, jsonify, session, request
import logging
import os
import datetime

# 內部模組導入
from services.app_config import Config, get_secret
from extensions import limiter
from utils.logging_filter import setup_ephi_logging_filter

# 導入路由藍圖
from routes.auth_routes import auth_bp
from routes.web_routes import web_bp
from routes.api_routes import api_bp
from routes.tradeoff_routes import tradeoff_bp
from routes.hooks import hooks_bp



def create_app():
    app = Flask(__name__)
    # 確保 secret_key 存在以啟用 Session
    app.secret_key = get_secret('FLASK_SECRET_KEY') or "precise_hbr_dev_key"

    # 強制統一為 localhost 的 Session 設定
    app.config.update(
        SESSION_COOKIE_NAME='fhir_app_session',
        SESSION_COOKIE_SAMESITE='Lax', 
        SESSION_COOKIE_SECURE=False,   # HTTP 環境必須為 False
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_DOMAIN=None,    # 讓瀏覽器自動決定
        SESSION_REFRESH_EACH_REQUEST=True, # 強制每次請求都更新 Cookie 狀態
        PERMANENT_SESSION_LIFETIME=datetime.timedelta(minutes=30)
    )

    @app.before_request
    def make_session_permanent():
        # 只要進入 launch，就確保 Session 是持久的，直到瀏覽器關閉或超時
        if request.path == '/launch':
            session.permanent = True
        # 移除原本的 else: session.permanent = False，避免在 callback 階段失效

    @app.after_request
    def add_security_headers(response):
        response.headers.pop('X-Frame-Options', None)
        origin = request.headers.get('Origin')
        if origin in ['http://localhost:4013', 'http://localhost:8180']:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRFToken'
        
        # 3. 解決 Cross-Origin 跳轉問題
        response.headers['Cross-Origin-Opener-Policy'] = 'unsafe-none' # 改為 unsafe-none 更有利於 OAuth2 跳轉
        response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
        
        return response
    

    # 初始化套件
    limiter.init_app(app)
    # 註解掉 Flask-Session 以使用原生的穩定 Cookie Session
    # Session(app) 
    
    # 註冊所有藍圖
    app.register_blueprint(web_bp)
    app.register_blueprint(auth_bp) # 沒加 prefix，網址即為 /launch
    app.register_blueprint(api_bp)
    app.register_blueprint(tradeoff_bp)
    app.register_blueprint(hooks_bp)
    
    return app

app = create_app()

if __name__ == '__main__':
    # 全部統一使用 localhost
    host = "localhost" 
    port = int(os.environ.get("PORT", 8080))
    # 開發模式下開啟 Debug
    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    
    print(f">>> 伺服器已啟動: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug_mode)