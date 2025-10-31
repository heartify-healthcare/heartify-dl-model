from flask import Flask, g
from app.config import Config
from app.routes import register_routes
from app.database import Base, engine, get_db_connection
from app.users.entity import User
from app.predictions.entity import Prediction

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    @app.before_request
    def before_request():
        g.db = get_db_connection()

    # Create tables
    with app.app_context():
        Base.metadata.create_all(bind=engine)
    
    # Register all routes and blueprints
    register_routes(app)
    
    @app.route('/health')
    def health_check():
        return {'status': 'ok'}
    
    return app