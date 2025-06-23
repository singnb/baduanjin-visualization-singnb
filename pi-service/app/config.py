# pi-service/app/config.py
import os

class Settings:
    """Settings class to match backend-docker config structure"""
    
    # Database Configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "")
    
    # JWT Configuration
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-jwt-tokens-make-it-long-and-random")
    JWT_SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-jwt-tokens-make-it-long-and-random")
    ALGORITHM = "HS256"
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 30
    
    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    TESTING = os.getenv("TESTING", "False").lower() == "true"
    
    # CORS Origins
    CORS_ORIGINS = [
        "https://nice-wave-0a2eb2e0f.4.azurestaticapps.net",
        "http://localhost:3000",
        "https://baduanjin-backend-docker.azurewebsites.net",
        "http://172.20.10.5:5001",
        "http://172.20.10.6:5001",
        "http://localhost:5001",
        "http://127.0.0.1:5001"
    ]
    
    # Azure-specific settings
    AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "")
    
    # Pi-specific Configuration
    PI_BASE_URL = os.getenv("PI_BASE_URL", "http://172.20.10.5:5001/api")
    PI_WEBSOCKET_URL = os.getenv("PI_WEBSOCKET_URL", "ws://172.20.10.5:5001")

# Create settings instance - this is what auth/router.py imports
settings = Settings()

# Also provide individual variables for backward compatibility
DATABASE_URL = settings.DATABASE_URL
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
PI_BASE_URL = settings.PI_BASE_URL
PI_WEBSOCKET_URL = settings.PI_WEBSOCKET_URL
ENVIRONMENT = settings.ENVIRONMENT