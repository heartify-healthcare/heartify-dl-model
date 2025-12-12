from flask import Blueprint, request, jsonify, current_app
from app.api_keys.auth import api_key_required
from app.predictions.ecg_model import ECGModel, CLASSES, DIAGNOSIS_MAP
import numpy as np
from datetime import datetime


predictions_bp = Blueprint('predictions', __name__)


@predictions_bp.route('', methods=['POST'])
@api_key_required
def predict_ecg():
    """Perform ECG prediction using the fine-tuned ECG-FM Multi-label model."""
    try:
        data = request.get_json()
        
        # Validate request body
        if not data or 'ecg_signal' not in data:
            return jsonify({
                "error": "Missing required field: ecg_signal",
                "expected_format": {
                    "ecg_signal": "array of 1300 float values (10 seconds @ 130Hz)"
                }
            }), 400
        
        ecg_signal = data['ecg_signal']
        
        # Validate ECG signal format
        if not isinstance(ecg_signal, list):
            return jsonify({"error": "ecg_signal must be an array"}), 400
        
        if len(ecg_signal) != 1300:
            return jsonify({
                "error": f"ecg_signal must have exactly 1300 values (got {len(ecg_signal)})",
                "note": "This model expects 130Hz sampling rate with 10-second duration (1300 samples)"
            }), 400
        
        # Convert to numpy array
        try:
            ecg_array = np.array(ecg_signal, dtype=np.float32)
        except Exception as e:
            return jsonify({"error": f"Invalid ecg_signal format: {str(e)}"}), 400
        
        # Get model instance and perform prediction
        model = ECGModel()
        probs, physio_features = model.predict(ecg_array)
        
        # Generate ECG visualization as Base64 image for multimodal AI
        ecg_image_base64 = model.generate_ecg_image_base64(ecg_array)
        
        # Get model version from config
        model_version = current_app.config.get('MODEL_VERSION', 1)
        
        # Find the class with the highest probability among 12 classes
        top_idx = int(np.argmax(probs))
        top_class_code = CLASSES[top_idx]
        top_probability = round(float(probs[top_idx]), 4)
        
        # Map to full diagnosis string using DIAGNOSIS_MAP
        diagnosis = DIAGNOSIS_MAP.get(top_class_code, top_class_code)
        
        # Format features - remove None values and add only valid features
        features = {}
        if physio_features.get("heart_rate") is not None:
            features["heart_rate"] = physio_features["heart_rate"]
        if physio_features.get("hrv_rmssd") is not None:
            features["hrv_rmssd"] = physio_features["hrv_rmssd"]
        if physio_features.get("qrs_duration") is not None:
            features["qrs_duration"] = physio_features["qrs_duration"]
        if physio_features.get("r_amplitude") is not None:
            features["r_amplitude"] = physio_features["r_amplitude"]
        if physio_features.get("signal_energy") is not None:
            features["signal_energy"] = physio_features["signal_energy"]
        if physio_features.get("r_peaks_count") is not None:
            features["r_peaks_count"] = physio_features["r_peaks_count"]
        
        # Build response matching the required format
        response = {
            "modelVersion": model_version,
            "diagnosis": diagnosis,
            "probability": top_probability,
            "features": features,
            "ecgImageBase64": ecg_image_base64
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
