import os
from flask import Blueprint, request, jsonify, g, render_template_string
from app.api_keys.service import ApiKeyService
from app.api_keys.email_service import EmailService
from app.config import Config


api_keys_bp = Blueprint('api_keys', __name__)


def get_email_service():
    """Get configured email service instance."""
    return EmailService(
        smtp_host=Config.SMTP_HOST,
        smtp_port=Config.SMTP_PORT,
        smtp_user=Config.SMTP_USER,
        smtp_password=Config.SMTP_PASSWORD,
        sender_email=Config.SENDER_EMAIL
    )


def get_base_url():
    """Get base URL from request or config."""
    return Config.BASE_URL or request.url_root.rstrip('/')


@api_keys_bp.route('/generation', methods=['POST'])
def request_api_key():
    """Request API key generation by providing email."""
    try:
        data = request.get_json()
        
        # Validate request body
        if not data or 'email' not in data:
            return jsonify({"error": "Missing required field: email"}), 400
        
        email = data['email'].strip().lower()
        
        # Basic email validation
        if '@' not in email or '.' not in email:
            return jsonify({"error": "Invalid email format"}), 400
        
        # Check if email already has an active API key
        service = ApiKeyService(g.db)
        repo = service.repo
        existing_active_key = repo.get_active_by_email(email)
        
        if existing_active_key:
            return jsonify({"error": "Email already has an active API key. Please deactivate it first."}), 409
        
        # Create verification token
        token = service.create_verification_token(email, action="generate")
        
        # Send verification email
        email_service = get_email_service()
        base_url = get_base_url()
        
        if not email_service.send_verification_email(email, token, base_url, action="generate"):
            return jsonify({"error": "Failed to send verification email"}), 500
        
        return jsonify({
            "message": "Verification email sent. Please check your inbox.",
            "email": email
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_keys_bp.route('/deactivation', methods=['POST'])
def request_api_key_deactivation():
    """Request API key deactivation by providing email."""
    try:
        data = request.get_json()
        
        # Validate request body
        if not data or 'email' not in data:
            return jsonify({"error": "Missing required field: email"}), 400
        
        email = data['email'].strip().lower()
        
        # Basic email validation
        if '@' not in email or '.' not in email:
            return jsonify({"error": "Invalid email format"}), 400
        
        # Check if email has an active API key
        service = ApiKeyService(g.db)
        repo = service.repo
        active_key = repo.get_active_by_email(email)
        
        if not active_key:
            return jsonify({"error": "No active API key found for this email"}), 404
        
        # Create verification token
        token = service.create_verification_token(email, action="deactivate")
        
        # Send verification email
        email_service = get_email_service()
        base_url = get_base_url()
        
        if not email_service.send_verification_email(email, token, base_url, action="deactivate"):
            return jsonify({"error": "Failed to send verification email"}), 500
        
        return jsonify({
            "message": "Verification email sent. Please check your inbox.",
            "email": email
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_keys_bp.route('/verify', methods=['GET'])
def verify_email():
    """Verify email and complete API key generation or deactivation."""
    try:
        token = request.args.get('token')
        
        if not token:
            return "Invalid verification link", 400
        
        # Verify token
        service = ApiKeyService(g.db)
        email, action, error = service.verify_token(token)
        
        if error:
            return jsonify(error), 400
        
        email_service = get_email_service()
        
        if action == "generate":
            # Generate API key
            api_key, error = service.generate_api_key_for_email(email)
            
            if error:
                return jsonify(error), 400
            
            # Send API key via email
            if not email_service.send_api_key_email(email, api_key.api_key):
                return jsonify({"error": "API key generated but failed to send email"}), 500
            
        elif action == "deactivate":
            # Deactivate API key
            success, error = service.deactivate_api_key_for_email(email)
            
            if error:
                return jsonify(error), 400
            
            # Send deactivation confirmation email
            if not email_service.send_deactivation_confirmation_email(email):
                return jsonify({"error": "API key deactivated but failed to send confirmation email"}), 500
        
        # Load success template
        template_path = os.path.join(os.path.dirname(__file__), 'templates', 'verification_success.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        return render_template_string(template_content)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
