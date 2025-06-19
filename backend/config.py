# config.py
import os
from pydantic import BaseModel
from typing import Optional

class Settings(BaseModel):
    """
    Application settings - loads from environment variables with defaults
    """
    # Database
    database_url: str
    
    # Azure Storage
    azure_storage_connection_string: str
    azure_storage_container_videos: str
    azure_storage_container_results: str
    
    # Environment
    environment: str
    
    # JWT
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    
    def __init__(self, **data):
        # Load values from environment variables with defaults
        env_values = {
            "database_url": os.getenv("DATABASE_URL", "postgresql://dbadmin:NYPBedok1234!@baduanjin-db-testing.postgres.database.azure.com:5432/postgres"),
            "azure_storage_connection_string": os.getenv("AZURE_STORAGE_CONNECTION_STRING", ""),
            "azure_storage_container_videos": os.getenv("AZURE_STORAGE_CONTAINER_VIDEOS", "videos"),
            "azure_storage_container_results": os.getenv("AZURE_STORAGE_CONTAINER_RESULTS", "results"),
            "environment": os.getenv("ENVIRONMENT", "testing"),
            "secret_key": os.getenv("SECRET_KEY", "your-secret-key-for-jwt-tokens-make-it-long-and-random"),
            "algorithm": os.getenv("ALGORITHM", "HS256"),
            "access_token_expire_minutes": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
        }
        
        # Merge with any provided data (provided data takes precedence)
        merged_data = {**env_values, **data}
        super().__init__(**merged_data)
    
    class Config:
        # Allow extra fields and validate assignment
        extra = "allow"
        validate_assignment = True

# Create settings instance
settings = Settings()