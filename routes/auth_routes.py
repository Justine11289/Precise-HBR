# routes/auth_routes.py
from flask import Blueprint, request, redirect, session, url_for, current_app
from fhirclient import client
import requests
import uuid

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/launch')
def launch():
    # 清理舊狀態
    for key in ['auth_settings', 'fhir_data']: session.pop(key, None)
    
    iss = request.args.get('iss').rstrip('/')
    settings = {
        'app_id': 'precise-hbr-app',
        'api_base': iss,
        'redirect_uri': 'http://localhost:8080/callback',
        'scope': 'launch openid fhirUser profile',
        'launch_token': request.args.get('launch')
    }
    
    smart = client.FHIRClient(settings=settings)
    try:
        smart.prepare() 
        session['auth_settings'] = settings
        return redirect(smart.authorize_url)
    except:
        return "Metadata failed", 400

@auth_bp.route('/callback')
def callback():
    code = request.args.get('code')
    settings = session.get('auth_settings')
    
    try:
        # 【最穩定的作法】手動找出 Token 端點，不理會套件物件
        # 1. 嘗試從標準路徑抓取 OpenID 組態 (Keycloak 跟沙盒都支援)
        well_known_url = f"{settings['api_base']}/.well-known/smart-configuration"
        try:
            config = requests.get(well_known_url).json()
            token_url = config.get('token_endpoint')
        except:
            # 如果不支援 .well-known，使用沙盒預設路徑
            token_url = f"{settings['api_base']}/token"

        # 2. 直接用標準 requests 發送 POST (不使用 fhirclient 換票)
        payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': settings['redirect_uri'],
            'client_id': settings['app_id']
        }
        token_res = requests.post(token_url, data=payload).json()
        
        if 'access_token' not in token_res:
            return f"換票失敗: {token_res}", 400

        # 3. 成功後存入 Session，供後續 API 使用
        session['patient_id'] = token_res.get('patient')
        session['access_token'] = token_res['access_token']
        session['fhir_data'] = {
            'server': settings['api_base'],
            'token': token_res['access_token'],
            'client_id': settings['app_id']
        }
        return redirect(url_for('web.main_page'))
        
    except Exception as e:
        return f"最終換票失敗: {str(e)}", 400

@auth_bp.route('/logout')
def logout():
    # 清空所有相關的 Session 資訊
    session.clear()
    # 重新導向回首頁或是登入頁面
    return "已成功登出，請關閉視窗或重新從沙盒啟動。"