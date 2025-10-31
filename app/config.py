import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask core settings
    SECRET_KEY = os.environ['SECRET_KEY']
    DEBUG = os.environ['DEBUG'].lower() == 'true'

    # Model paths
    MODEL_PATH = os.environ['MODEL_PATH'] #
    SCALER_PATH = os.environ['SCALER_PATH'] #

    # JWT secret
    JWT_SECRET = os.environ['JWT_SECRET'] #

    # SMTP config
    SMTP_SERVER = os.environ['SMTP_SERVER'] #
    SMTP_PORT = int(os.environ['SMTP_PORT']) #
    SMTP_USERNAME = os.environ['SMTP_USERNAME'] #
    SMTP_PASSWORD = os.environ['SMTP_PASSWORD'] #

    # PostgreSQL database URI
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL'] #
