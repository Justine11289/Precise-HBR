# routes/tradeoff_routes.py
from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for
from services import fhir_data_service
from fhirclient import client
import logging
from utils.web_utils import login_required

logger = logging.getLogger('werkzeug')
tradeoff_bp = Blueprint('tradeoff', __name__, template_folder='templates')

@tradeoff_bp.route('/tradeoff_analysis')
@login_required
def tradeoff_analysis_page():
    """Renders the Tradeoff Analysis UI."""
    patient_id = session.get('patient_id', 'N/A')
    return render_template('tradeoff_analysis.html', patient_id=patient_id)

@tradeoff_bp.route('/api/calculate_tradeoff', methods=['POST'])
@login_required
def calculate_tradeoff_api():
    """API for Bleeding vs. Thrombosis Tradeoff Analysis."""
    try:
        data = request.get_json()
        model = fhir_data_service.get_tradeoff_model_predictors()
        
        if model is None:
            logger.error("Failed to load tradeoff model. Configuration missing.")
            return jsonify({'error': 'Model configuration unavailable.'}), 500

        # Scenario A: Interactive recalculation based on user selection
        if 'active_factors' in data:
            active_factors = data.get('active_factors', {})
            recalculated_scores = fhir_data_service.calculate_tradeoff_scores_interactive(model, active_factors)
            return jsonify(recalculated_scores)

        # Scenario B: Initial load based on Patient ID
        patient_id = data.get('patientId')
        if not patient_id:
            return jsonify({'error': 'Patient ID or active factors required.'}), 400

        # SYNC: Read the session key created in auth_routes.py
        fhir_session_data = session.get('fhir_data')
        
        if not fhir_session_data:
            logger.error("Session data 'fhir_data' missing.")
            return jsonify({'error': 'Unauthorized: SMART session not found.'}), 401

        # Fetch clinical data from FHIR server
        raw_data, error = fhir_data_service.get_fhir_data(
            fhir_server_url=fhir_session_data.get('server'),
            access_token=fhir_session_data.get('token'),
            patient_id=patient_id,
            client_id=fhir_session_data.get('client_id')
        )
        
        if error:
            raise Exception(f"FHIR Service Error: {error}")
            
        demographics = fhir_data_service.get_patient_demographics(raw_data.get('patient'))
        
        tradeoff_data = fhir_data_service.get_tradeoff_model_data(
            fhir_server_url=fhir_session_data.get('server'),
            access_token=fhir_session_data.get('token'),
            client_id=fhir_session_data.get('client_id'),
            patient_id=patient_id
        )

        # Map clinical data to risk factors
        detected_factors_list = fhir_data_service.detect_tradeoff_factors(raw_data, demographics, tradeoff_data)
        
        # Create factor dictionary
        all_factors = {p['factor']: False for p in model['bleedingEvents']['predictors']}
        all_factors.update({p['factor']: False for p in model['thromboticEvents']['predictors']})
        for factor in detected_factors_list:
            if factor in all_factors:
                all_factors[factor] = True

        # Calculate initial risk scores
        initial_scores = fhir_data_service.calculate_tradeoff_scores_interactive(model, all_factors)

        return jsonify({
            'model': model, 
            'detected_factors': all_factors,
            'initial_scores': initial_scores
        })

    except Exception as e:
        logger.error(f"Tradeoff API Error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal error during calculation.'}), 500