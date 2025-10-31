from flask import Blueprint, request, jsonify, g
from app.users.service import UserService
from app.users.schema import UserCreateSchema, UserOutSchema, UserUpdateSchema, UserHealthUpdateSchema, ChangePasswordSchema
from app.auth.controller import jwt_required

user_bp = Blueprint("users", __name__)

@user_bp.route("/", methods=["POST"])
@jwt_required
def create_user():
    """Create a new user - Admin only"""
    # Check if current user is admin
    if g.current_user.get('role') != 'admin':
        return jsonify({"error": "Admin access required"}), 403
        
    try:
        data = UserCreateSchema.parse_obj(request.json)
        service = UserService(g.db)
        user, error = service.create_user(data)
        
        if error:
            return jsonify(error), 400
            
        return jsonify(UserOutSchema.from_orm(user).dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@user_bp.route("/", methods=["GET"])
@jwt_required
def list_users():
    """List all users - Admin only"""
    # Check if current user is admin
    if g.current_user.get('role') != 'admin':
        return jsonify({"error": "Admin access required"}), 403
        
    service = UserService(g.db)
    users = service.list_users()
    return jsonify([UserOutSchema.from_orm(u).dict() for u in users]), 200

@user_bp.route("/<int:user_id>", methods=["GET"])
@jwt_required
def get_user(user_id):
    """Get user by ID - Users can only view their own profile, admins can view any"""
    current_user_id = g.current_user.get('user_id')
    current_user_role = g.current_user.get('role')
    
    # Users can only view their own profile, admins can view any
    if current_user_role != 'admin' and current_user_id != user_id:
        return jsonify({"error": "Access denied. You can only view your own profile."}), 403
    
    service = UserService(g.db)
    user = service.get_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(UserOutSchema.from_orm(user).dict()), 200

@user_bp.route("/profile", methods=["GET"])
@jwt_required
def get_current_user_profile():
    """Get current user's profile"""
    current_user_id = g.current_user.get('user_id')
    service = UserService(g.db)
    user = service.get_user(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(UserOutSchema.from_orm(user).dict()), 200

@user_bp.route("/<int:user_id>", methods=["PATCH"])
@jwt_required
def update_user(user_id):
    """Update user - Users can only update their own profile, admins can update any"""
    current_user_id = g.current_user.get('user_id')
    current_user_role = g.current_user.get('role')
    
    # Users can only update their own profile, admins can update any
    if current_user_role != 'admin' and current_user_id != user_id:
        return jsonify({"error": "Access denied. You can only update your own profile."}), 403
    
    try:
        data = UserUpdateSchema.parse_obj(request.json)
        service = UserService(g.db)
        user, error = service.update_user(user_id, data, current_user_role)
        
        if error:
            return jsonify(error), 400
            
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        return jsonify(UserOutSchema.from_orm(user).dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@user_bp.route("/profile", methods=["PATCH"])
@jwt_required
def update_current_user_profile():
    """Update current user's profile"""
    current_user_id = g.current_user.get('user_id')
    current_user_role = g.current_user.get('role')
    
    try:
        data = UserUpdateSchema.parse_obj(request.json)
        service = UserService(g.db)
        user, error = service.update_user(current_user_id, data, current_user_role)
        
        if error:
            return jsonify(error), 400
            
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        return jsonify(UserOutSchema.from_orm(user).dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@user_bp.route("/profile/health", methods=["PATCH"])
@jwt_required
def update_current_user_health():
    """Update current user's health-related fields only"""
    current_user_id = g.current_user.get('user_id')
    
    try:
        data = UserHealthUpdateSchema.parse_obj(request.json)
        service = UserService(g.db)
        user, error = service.update_user_health(current_user_id, data)
        
        if error:
            return jsonify(error), 400
            
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        return jsonify(UserOutSchema.from_orm(user).dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@user_bp.route("/change-password", methods=["PUT"])
@jwt_required
def change_password():
    """Change current user's password"""
    current_user_id = g.current_user.get('user_id')
    
    try:
        data = ChangePasswordSchema.parse_obj(request.json)
        service = UserService(g.db)
        success, error = service.change_user_password(
            current_user_id, 
            data.current_password, 
            data.new_password
        )
        
        if error:
            return jsonify(error), 400
            
        if not success:
            return jsonify({"error": "Failed to change password"}), 400
            
        return jsonify({"message": "Password changed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@user_bp.route("/<int:user_id>", methods=["DELETE"])
@jwt_required
def delete_user(user_id):
    """Delete user - Admin only"""
    current_user_role = g.current_user.get('role')
    current_user_id = g.current_user.get('user_id')
    
    # Only admins can delete users
    if current_user_role != 'admin':
        return jsonify({"error": "Admin access required"}), 403
    
    # Prevent admin from deleting themselves
    if current_user_id == user_id:
        return jsonify({"error": "You cannot delete your own account"}), 400
    
    service = UserService(g.db)
    if not service.delete_user(user_id):
        return jsonify({"error": "User not found"}), 404
    return jsonify({"message": "User deleted successfully"}), 200