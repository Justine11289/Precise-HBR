# routes/auth_routes.py
from flask import Blueprint, request, redirect, session, url_for, current_app
from fhirclient import client
import requests
import uuid


auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/launch')
def launch():
    patient_id = request.args.get('patient') # 獲取手動傳入的 ID
    launch_token = request.args.get('launch')
    iss = request.args.get('iss')
    if not iss:
        return "Missing 'iss' parameter", 400
    iss = iss.rstrip('/')

    # 🚀 開發者後門：如果網址帶有 patient，直接設定 Session 並跳轉
    if patient_id and not launch_token:
        print(f">>> [DEV MODE] 手動啟動 Patient: {patient_id}")
        # 清理並初始化 Session
        session.clear()
        session.permanent = True
        
        # 模擬換票成功後的 Session 結構，讓 api_routes 能夠讀取
        session['patient_id'] = patient_id
        session['fhir_data'] = {
            'server': iss,
            'token': None,  # 本地 HAPI 沒保護時可為 None
            'client_id': 'precise-hbr-app'
        }
        # 為了滿足 fhirclient 的 state 檢查
        session['fhir_state'] = {
            'api_base': iss,
            'patient': patient_id
        }
        return redirect(url_for('web.main_page'))
    # 清理舊狀態
    for key in ['auth_settings', 'fhir_data', 'fhir_state', 'patient_id', 'access_token']: 
        session.pop(key, None)
    
    # iss = request.args.get('iss')
    # if not iss:
    #     return "Missing 'iss' parameter", 400
    # iss = iss.rstrip('/')
    
    settings = {
        'app_id': 'precise-hbr-app',
        'api_base': iss,
        'redirect_uri': 'http://localhost:8080/callback',
        'scope': 'launch openid fhirUser profile',
        'launch_token': launch_token
    }
    
    smart = client.FHIRClient(settings=settings)
    try:
        smart.prepare() 
        session['auth_settings'] = settings
        session.modified = True
        return redirect(smart.authorize_url)
    except Exception as e:
        return f"Metadata failed: {str(e)}", 400

@auth_bp.route('/callback')
def callback():
    code = request.args.get('code')
    settings = session.get('auth_settings')
    
    if not settings or not code:
        return "Session lost or no code received", 401

    smart = client.FHIRClient(settings=settings)
    
    try:
        # 1. 取得 Token 端點
        well_known_url = f"{settings['api_base']}/.well-known/smart-configuration"
        try:
            config = requests.get(well_known_url, timeout=5).json()
            token_url = config.get('token_endpoint')
        except:
            token_url = f"{settings['api_base']}/token"

        # 2. 手動換票
        payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': settings['redirect_uri'],
            'client_id': settings['app_id']
        }
        response = requests.post(token_url, data=payload)
        token_res = response.json()
        
        if 'access_token' not in token_res:
            return f"換票失敗: {token_res}", 400

        # 3. 【核心修正】手動將資訊填入 smart.state，不使用不存在的 handle_token_post
        # 直接更新 smart 內部的 state 字典
        smart.state.update({
            'patient': token_res.get('patient'),
            'access_token': token_res.get('access_token'),
            'token_type': token_res.get('token_type', 'Bearer'),
            'expires_in': token_res.get('expires_in'),
            'scope': token_res.get('scope')
        })

        # 4. 同步 Session 資訊以滿足後端 API 檢查
        session['fhir_state'] = smart.state  # 解決 "No SMART state found" 的關鍵
        session['patient_id'] = token_res.get('patient')
        session['access_token'] = token_res['access_token']
        session['fhir_data'] = {
            'server': settings['api_base'].rstrip('/'),
            'token': token_res['access_token'],
            'client_id': settings['app_id']
        }
        
        session.modified = True
        print(f">>> [SUCCESS] OAuth2 complete. Patient ID: {session['patient_id']}")
        return redirect(url_for('web.main_page'))
        
    except Exception as e:
        return f"最終換票失敗: {str(e)}", 400

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('web.index'))