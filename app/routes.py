from app.predictions import prediction_bp
from app.users import user_bp
from app.auth import auth_bp

def register_routes(app):
    # Register blueprints
    app.register_blueprint(prediction_bp, url_prefix='/predictions')
    app.register_blueprint(user_bp, url_prefix='/users')
    app.register_blueprint(auth_bp, url_prefix='/auth')