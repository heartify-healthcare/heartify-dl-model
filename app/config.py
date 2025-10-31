import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration from environment variables"""
    
    # Flask core settings
    SECRET_KEY = os.environ['SECRET_KEY']
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    # PostgreSQL database URI
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
    
    # Basic Authentication credentials for API key management endpoints
    BASIC_AUTH_USERNAME = os.environ['BASIC_AUTH_USERNAME']
    BASIC_AUTH_PASSWORD = os.environ['BASIC_AUTH_PASSWORD']
    
    # ECG Model path (PyTorch .pt file)
    ECG_MODEL_PATH = os.environ['ECG_MODEL_PATH']
    
    # ECG Model version (integer)
    MODEL_VERSION = int(os.environ.get('MODEL_VERSION', '1'))
