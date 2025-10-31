"""API Key management endpoints"""
from flask import Blueprint, request, jsonify, g
from app.api_keys.service import ApiKeyService
from app.api_keys.auth import basic_auth_required


api_keys_bp = Blueprint('api_keys', __name__)


@api_keys_bp.route('/generation', methods=['POST'])
@basic_auth_required
def generate_api_key():
    """
    Generate a new API key
    
    Requires: Basic Authentication
    
    Returns:
        201: JSON with new API key details
        500: Error during generation
    """
    try:
        service = ApiKeyService(g.db)
        api_key, error = service.generate_api_key()
        
        if error:
            return jsonify(error), 500
        
        response = {
            "api_key": api_key.api_key,
            "active": api_key.active,
            "created_at": api_key.created_at.isoformat()
        }
        
        return jsonify(response), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_keys_bp.route('/activation', methods=['POST'])
@basic_auth_required
def activate_api_key():
    """
    Activate or deactivate an API key
    
    Requires: Basic Authentication
    
    Body:
        {
            "api_key": "string",
            "active": boolean
        }
    
    Returns:
        200: JSON with updated API key details
        400: Invalid request body
        404: API key not found
    """
    try:
        data = request.get_json()
        
        # Validate request body
        if not data or 'api_key' not in data or 'active' not in data:
            return jsonify({"error": "Missing required fields: api_key, active"}), 400
        
        api_key = data['api_key']
        active = data['active']
        
        # Validate active is boolean
        if not isinstance(active, bool):
            return jsonify({"error": "Field 'active' must be a boolean"}), 400
        
        service = ApiKeyService(g.db)
        updated_key, error = service.activate_api_key(api_key, active)
        
        if error:
            return jsonify(error), 404
        
        response = {
            "api_key": updated_key.api_key,
            "active": updated_key.active,
            "created_at": updated_key.created_at.isoformat(),
            "last_used": updated_key.last_used.isoformat() if updated_key.last_used else None
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400
