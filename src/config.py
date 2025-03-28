import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory of application
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Define configuration classes for different environments
class Config:
    """Base configuration class with common settings."""

    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'teamhack-dev-key'

    # Database settings
    DATABASE_PATH = os.environ.get('TEAMHACK_DB_PATH') or os.path.join(BASE_DIR, 'teamhack.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'

    # Gemini API settings
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

    # Form settings
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max upload size

    # User settings
    MAX_FAILED_LOGIN_ATTEMPTS = 5
    LOGIN_COOLDOWN_MINUTES = 15

    # App-specific settings
    DASHBOARD_ITEMS_PER_PAGE = 10
    FORM_TEMPLATE_PATH = os.path.join(BASE_DIR, 'webpages', 'form.html')


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing environment configuration."""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    TESTING = False
    # In production, SECRET_KEY should always come from environment variables
    SECRET_KEY = os.environ.get('SECRET_KEY')


# Dictionary mapping environment names to configuration classes
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


# Select active configuration based on environment variable
def get_config():
    env = os.environ.get('FLASK_ENV', 'default')
    return config.get(env, config['default'])