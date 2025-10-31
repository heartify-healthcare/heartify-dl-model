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
    
    # Email configuration for API key verification
    SMTP_HOST = os.environ['SMTP_HOST']
    SMTP_PORT = int(os.environ['SMTP_PORT'])
    SMTP_USER = os.environ['SMTP_USER']
    SMTP_PASSWORD = os.environ['SMTP_PASSWORD']
    SENDER_EMAIL = os.environ['SENDER_EMAIL']
    
    # Base URL for email verification links
    BASE_URL = os.environ['BASE_URL']
    
    # ECG Model path (PyTorch .pt file)
    ECG_MODEL_PATH = os.environ['ECG_MODEL_PATH']
    
    # ECG Model version (integer)
    MODEL_VERSION = int(os.environ['MODEL_VERSION'])
