from flask import Blueprint, jsonify, request, session, current_app
from fhirclient import client
from fhirclient.models.patient import Patient
from fhirclient.models.observation import Observation
from functools import wraps
import logging

# 導入你原本的計算邏輯與設定
import services.fhir_data_service as fhir_data_service
from services.app_config import Config

api_bp = Blueprint('api', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 檢查 session 中是否有 SMART 授權狀態
        if 'fhir_state' not in session:
            return jsonify({'error': 'Unauthorized: No SMART state found in session'}), 401
        return f(*args, **kwargs)
    return decorated_function

@api_bp.route('/api/calculate_risk', methods=['POST'])
@login_required
def calculate_risk_api():
    """
    從沙盒抓取真實資料並計算 PRECISE-HBR 風險評分
    """
    try:
        # 1. 從 Session 恢復 SMART Client
        smart = client.FHIRClient(state=session.get('fhir_state'))
        server = smart.server
        patient_id = smart.patient_id
        
        current_app.logger.info(f"Calculating risk for Patient: {patient_id}")

        # 2. 從沙盒伺服器抓取必要的數據 (例如 Hemoglobin, WBC, eGFR)
        # 這裡會使用你的 fhir_data_service 進行 API 調用
        # 確保你的 service 能接受 smart.server 作為參數
        try:
            patient_data, error = fhir_data_service.get_fhir_data(
                fhir_server_url=smart.server.base_uri,
                access_token=smart.access_token,
                patient_id=smart.patient_id,
                client_id=current_app.config.get('CLIENT_ID')
            )
        except Exception as e:
            current_app.logger.error(f"Failed to fetch data from Sandbox: {str(e)}")
            return jsonify({'error': '無法從沙盒取得病人資料'}), 500

        # 3. 執行 PRECISE-HBR 計算邏輯
        # 假設你的 service 中有計算方法
        risk_result = fhir_data_service.calculate_precise_hbr_score(patient_data)

        # 4. 回傳結果給前端
        return jsonify({
            'status': 'success',
            'patient_id': smart.patient_id,
            'score': risk_result.get('total_score'),
            'risk_level': risk_result.get('risk_level'),
            'recommendations': risk_result.get('recommendations'),
            'data_points': patient_data 
        })

    except Exception as e:
        current_app.logger.error(f"API Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

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