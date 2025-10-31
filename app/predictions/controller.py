"""Predictions endpoint controller"""
from flask import Blueprint, request, jsonify
from app.api_keys.auth import api_key_required
from app.predictions.ecg_model import ECGModel
import numpy as np
from datetime import datetime


predictions_bp = Blueprint('predictions', __name__)


@predictions_bp.route('/', methods=['POST'])
@api_key_required
def predict_ecg():
    """
    Perform ECG prediction using the fine-tuned ECG-FM model
    
    Requires: x-api-key header with valid API key
    
    Body:
        {
            "ecg_signal": [array of 130 float values for 130Hz 1-lead ECG]
        }
    
    Returns:
        200: JSON with prediction results
        400: Invalid request
        401: Invalid or missing API key
        500: Model inference error
    """
    try:
        data = request.get_json()
        
        # Validate request body
        if not data or 'ecg_signal' not in data:
            return jsonify({
                "error": "Missing required field: ecg_signal",
                "expected_format": {
                    "ecg_signal": "array of 130 float values"
                }
            }), 400
        
        ecg_signal = data['ecg_signal']
        
        # Validate ECG signal format
        if not isinstance(ecg_signal, list):
            return jsonify({"error": "ecg_signal must be an array"}), 400
        
        if len(ecg_signal) != 130:
            return jsonify({
                "error": f"ecg_signal must have exactly 130 values (got {len(ecg_signal)})",
                "note": "This model expects 130Hz sampling rate with 1-second duration"
            }), 400
        
        # Convert to numpy array
        try:
            ecg_array = np.array(ecg_signal, dtype=np.float32)
        except Exception as e:
            return jsonify({"error": f"Invalid ecg_signal format: {str(e)}"}), 400
        
        # Get model instance and perform prediction
        model = ECGModel()
        label, probabilities, embedding = model.predict(ecg_array)
        
        # Build response
        response = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "prediction": label,
            "confidence": probabilities[label],
            "probabilities": probabilities,
            "metadata": {
                "model": "ECG-FM fine-tuned 130Hz",
                "signal_length": len(ecg_signal),
                "sampling_rate": "130Hz"
            }
        }
        
        return jsonify(response), 200
        
    except RuntimeError as e:
        # Model not loaded error
        return jsonify({
            "error": "Model initialization error",
            "details": str(e)
        }), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
