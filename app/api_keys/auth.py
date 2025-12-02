from functools import wraps
from flask import request, jsonify, g
from app.api_keys.service import ApiKeyService


def api_key_required(f):
    """Decorator to require valid API key in x-api-key header."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get API key from header
        api_key = request.headers.get('x-api-key')
        
        if not api_key:
            return jsonify({"error": "Missing x-api-key header"}), 401
        
        # Validate API key using service
        service = ApiKeyService(g.db)
        if not service.validate_api_key(api_key):
            return jsonify({"error": "Invalid or inactive API key"}), 401
        
        # Store validated API key in request context
        g.api_key = api_key
        
        return f(*args, **kwargs)
    
    return decorated_function
