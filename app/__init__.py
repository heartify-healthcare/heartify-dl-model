from flask import Flask, g
from app.config import Config
from app.database import Base, engine, get_db_connection
from app.api_keys.entity import ApiKey
from app.predictions.ecg_model import ECGModel


def create_app(config_class=Config):
    """
    Create and configure the Flask application
    
    This is the main application factory that:
    - Loads configuration
    - Sets up database connection
    - Registers blueprints (API routes)
    - Initializes ML models
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Database connection setup - inject db session into request context
    @app.before_request
    def before_request():
        g.db = get_db_connection()
    
    @app.teardown_request
    def teardown_request(exception=None):
        db = g.pop('db', None)
        if db is not None:
            db.close()
    
    # Create database tables
    with app.app_context():
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created")
    
    # Load ECG model
    try:
        ecg_model = ECGModel()
        ecg_model.load(app.config['ECG_MODEL_PATH'])
    except Exception as e:
        print(f"⚠️  Warning: Could not load ECG model - {str(e)}")
        print("   Predictions endpoint will not work until model is loaded")
    
    # Register blueprints
    from app.api_keys import api_keys_bp
    from app.predictions import predictions_bp
    
    app.register_blueprint(api_keys_bp, url_prefix='/api/v1/api-keys')
    app.register_blueprint(predictions_bp, url_prefix='/api/v1/predictions')
    
    return app