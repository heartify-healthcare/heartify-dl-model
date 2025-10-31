from flask import Blueprint, request, jsonify, g
from functools import wraps
from app.auth.service import AuthService
from app.auth.schema import RegisterSchema, RequestVerifySchema, VerifySchema, LoginSchema, RecoverPasswordSchema

auth_bp = Blueprint("auth", __name__)

def jwt_required(f):
    """Decorator to require JWT authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({"error": "Invalid token format"}), 401
        
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        
        service = AuthService(g.db)
        payload, error = service.verify_jwt_token(token)
        
        if error:
            return jsonify({"error": error}), 401
        
        g.current_user = payload
        return f(*args, **kwargs)
    
    return decorated_function

@auth_bp.route("/register", methods=["POST"])
def register():
    try:
        data = RegisterSchema.parse_obj(request.json)
        service = AuthService(g.db)
        result, error = service.register(data)
        
        if error:
            return jsonify(error), 400
            
        return jsonify(result), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@auth_bp.route("/request-verify", methods=["POST"])
def request_verify():
    try:
        data = RequestVerifySchema.parse_obj(request.json)
        service = AuthService(g.db)
        result, error = service.request_verify(data)
        
        if error:
            return jsonify(error), 400
            
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@auth_bp.route("/verify", methods=["POST"])
def verify():
    try:
        data = VerifySchema.parse_obj(request.json)
        service = AuthService(g.db)
        result, error = service.verify(data)
        
        if error:
            return jsonify(error), 400
            
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@auth_bp.route("/login", methods=["POST"])
def login():
    # try:
        data = LoginSchema.parse_obj(request.json)
        service = AuthService(g.db)
        result, error = service.login(data)
        
        if error:
            return jsonify(error), 400
            
        return jsonify(result), 200
    # except Exception as e:
        # return jsonify({"error": str(e)}), 400

@auth_bp.route("/recover-password", methods=["POST"])
def recover_password():
    try:
        data = RecoverPasswordSchema.parse_obj(request.json)
        service = AuthService(g.db)
        result, error = service.recover_password(data)
        
        if error:
            return jsonify(error), 400
            
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Test endpoint to verify JWT token
@auth_bp.route("/me", methods=["GET"])
@jwt_required
def get_current_user():
    return jsonify(g.current_user), 200