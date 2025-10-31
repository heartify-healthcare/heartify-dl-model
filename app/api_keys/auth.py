"""Authentication and authorization decorators"""
import os
from functools import wraps
from flask import request, jsonify, g
from app.api_keys.service import ApiKeyService


def basic_auth_required(f):
    """
    Decorator to require HTTP Basic Authentication
    Validates against BASIC_AUTH_USERNAME and BASIC_AUTH_PASSWORD environment variables
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.authorization
        
        # Check if authorization header is present
        if not auth:
            return jsonify({"error": "Missing authorization header"}), 401
        
        # Get credentials from environment
        username = os.environ.get('BASIC_AUTH_USERNAME')
        password = os.environ.get('BASIC_AUTH_PASSWORD')
        
        # Validate credentials
        if not username or not password:
            return jsonify({"error": "Server configuration error"}), 500
        
        if auth.username != username or auth.password != password:
            return jsonify({"error": "Invalid credentials"}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


def api_key_required(f):
    """
    Decorator to require valid API key in x-api-key header
    Validates the key against the database
    """
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
