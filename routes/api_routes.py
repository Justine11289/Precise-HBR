from flask import Blueprint, jsonify, request, session, current_app
from fhirclient import client
from fhirclient.models.patient import Patient
from fhirclient.models.observation import Observation
from functools import wraps
import logging

# 導入你原本的計算邏輯與設定
from services import precise_hbr_calculator, risk_classifier
import services.fhir_data_service as fhir_data_service
from services.app_config import Config

api_bp = Blueprint('api', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. 支援 Keycloak 傳送的 Header 驗證
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            # 這裡之後會串接 Keycloak 的 token 驗證邏輯
            return f(*args, **kwargs)
            
        # 2. 保留原有的 Session 檢查供沙盒環境使用
        if 'fhir_state' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@api_bp.route('/api/calculate_risk', methods=['POST'])
@login_required
def calculate_risk_api():
    # 1. 🚀 初始化變數，防止 UnboundLocalError
    patient_data = {} 
    patient_info = {'patient_id': session.get('patient_id'), 'name': 'N/A', 'age': 'N/A', 'gender': 'N/A'}
    
    try:
        fhir_session_data = session.get('fhir_data')
        patient_id = session.get('patient_id')
        
        # 🛡️ 檢查 Session 是否遺失
        if not fhir_session_data or not patient_id:
            return jsonify({
                'status': 'error', 
                'error': 'Missing Session (iss/patient_id). Please launch with ?iss= URL',
                'patient_info': patient_info
            }), 400
        
        # 2. 執行資料抓取
        try:
            data_tuple = fhir_data_service.get_fhir_data(
                fhir_server_url=fhir_session_data.get('server'),
                access_token=fhir_session_data.get('token'),
                patient_id=patient_id,
                client_id=fhir_session_data.get('client_id')
            )
            patient_data = data_tuple[0] if isinstance(data_tuple, tuple) else data_tuple
        except Exception as fetch_err:
            current_app.logger.error(f"Fetch Error: {str(fetch_err)}")
            return jsonify({'status': 'error', 'error': f"FHIR Server connection failed: {str(fetch_err)}"}), 500

        # 3. 解析基本資料
        demographics = fhir_data_service.get_patient_demographics(patient_data.get('patient'))
        patient_info.update({
            'name': demographics.get('name', 'N/A'),
            'age': demographics.get('age', 'N/A'),
            'gender': demographics.get('gender', 'N/A')
        })
        
        # 4. 執行風險計算
        components, total_score = precise_hbr_calculator.calculate_score(patient_data, demographics)

        return jsonify({
            'status': 'success',
            'patient_info': patient_info,
            'score': total_score,
            'risk_level': risk_classifier.get_risk_category_info(total_score)['category'],
            'score_components': components
        })

    except Exception as e:
        current_app.logger.error(f"Critical API Error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'patient_info': patient_info,
            'score_components': []
        }), 500


@api_bp.route('/api/patient_info', methods=['GET'])
@login_required
def get_current_patient():
    """
    簡單的 API：回傳目前沙盒選擇的病人基本資料
    """
    try:
        smart = client.FHIRClient(state=session.get('fhir_state'))
        # 抓取 Patient Resource
        patient = Patient.read(smart.patient_id, smart.server)
        
        return jsonify({
            'name': smart.human_name(patient.name[0]),
            'id': patient.id,
            'gender': patient.gender,
            'birthDate': patient.birthDate.isostring
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500