from flask import Blueprint, request, jsonify, g
from app.predictions.schema import HeartDiseaseInput, PredictionResponse
from app.predictions.service import PredictionService
from app.auth.controller import jwt_required

prediction_bp = Blueprint('predictions', __name__)

@prediction_bp.route('/heart-disease', methods=['POST'])
@jwt_required
def predict_heart_disease():
    try:
        data = HeartDiseaseInput.parse_obj(request.json)
        service = PredictionService(g.db)
        
        # Use authenticated user's ID from JWT token
        prediction, error = service.predict_heart_disease(data, g.current_user['user_id'])
        
        if error:
            return jsonify(error), 400
            
        # Create response from prediction entity
        response = PredictionResponse(
            id=prediction.id,
            user_id=prediction.user_id,
            age=prediction.age,
            sex=prediction.sex,
            cp=prediction.cp,
            trestbps=prediction.trestbps,
            restecg=prediction.restecg,
            thalach=prediction.thalach,
            exang=prediction.exang,
            probability=prediction.probability,
            prediction=prediction.prediction,
            created_at=prediction.created_at
        )
            
        return jsonify(response.dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@prediction_bp.route('/', methods=['GET'])
@jwt_required
def list_predictions():
    """Get all predictions for the authenticated user"""
    service = PredictionService(g.db)
    user_id = g.current_user['user_id']
    predictions = service.get_user_predictions(user_id)
    result = []
    for p in predictions:
        response = PredictionResponse(
            id=p.id,
            user_id=p.user_id,
            age=p.age,
            sex=p.sex,
            cp=p.cp,
            trestbps=p.trestbps,
            restecg=p.restecg,
            thalach=p.thalach,
            exang=p.exang,
            probability=p.probability,
            prediction=p.prediction,
            created_at=p.created_at
        )
        result.append(response.dict())
    return jsonify(result), 200

@prediction_bp.route('/<int:prediction_id>', methods=['GET'])
@jwt_required
def get_prediction(prediction_id):
    service = PredictionService(g.db)
    user_id = g.current_user['user_id']
    
    prediction = service.get_prediction(prediction_id)
    if not prediction:
        return jsonify({"error": "Prediction not found"}), 404
    
    # Check if prediction belongs to authenticated user
    if prediction.user_id != user_id:
        return jsonify({"error": "Access denied"}), 403
    
    response = PredictionResponse(
        id=prediction.id,
        user_id=prediction.user_id,
        age=prediction.age,
        sex=prediction.sex,
        cp=prediction.cp,
        trestbps=prediction.trestbps,
        restecg=prediction.restecg,
        thalach=prediction.thalach,
        exang=prediction.exang,
        probability=prediction.probability,
        prediction=prediction.prediction,
        created_at=prediction.created_at
    )
    return jsonify(response.dict()), 200

@prediction_bp.route('/user/<int:user_id>', methods=['GET'])
@jwt_required
def get_user_predictions(user_id):
    """Get predictions for a specific user (only accessible by the user themselves or admin)"""
    current_user_id = g.current_user['user_id']
    current_user_role = g.current_user.get('role', 'user')
    
    # Check if user is trying to access their own data or is an admin
    if current_user_id != user_id and current_user_role != 'admin':
        return jsonify({"error": "Access denied"}), 403
    
    service = PredictionService(g.db)
    predictions = service.get_user_predictions(user_id)
    result = []
    for p in predictions:
        response = PredictionResponse(
            id=p.id,
            user_id=p.user_id,
            age=p.age,
            sex=p.sex,
            cp=p.cp,
            trestbps=p.trestbps,
            restecg=p.restecg,
            thalach=p.thalach,
            exang=p.exang,
            probability=p.probability,
            prediction=p.prediction,
            created_at=p.created_at
        )
        result.append(response.dict())
    return jsonify(result), 200

@prediction_bp.route('/<int:prediction_id>', methods=['DELETE'])
@jwt_required
def delete_prediction(prediction_id):
    service = PredictionService(g.db)
    user_id = g.current_user['user_id']
    user_role = g.current_user.get('role', 'user')
    
    # Check if prediction exists
    prediction = service.get_prediction(prediction_id)
    if not prediction:
        return jsonify({"error": "Prediction not found"}), 404
    
    # Check if user owns the prediction or is admin
    if prediction.user_id != user_id and user_role != 'admin':
        return jsonify({"error": "Access denied"}), 403
    
    if not service.delete_prediction(prediction_id):
        return jsonify({"error": "Failed to delete prediction"}), 500
        
    return jsonify({"message": "Prediction deleted"}), 200

# Admin-only route to get all predictions
@prediction_bp.route('/admin/all', methods=['GET'])
@jwt_required
def get_all_predictions():
    """Admin only: Get all predictions from all users"""
    user_role = g.current_user.get('role', 'user')
    
    if user_role != 'admin':
        return jsonify({"error": "Admin access required"}), 403
    
    service = PredictionService(g.db)
    predictions = service.get_all_predictions()
    result = []
    for p in predictions:
        response = PredictionResponse(
            id=p.id,
            user_id=p.user_id,
            age=p.age,
            sex=p.sex,
            cp=p.cp,
            trestbps=p.trestbps,
            restecg=p.restecg,
            thalach=p.thalach,
            exang=p.exang,
            probability=p.probability,
            prediction=p.prediction,
            created_at=p.created_at
        )
        result.append(response.dict())
    return jsonify(result), 200