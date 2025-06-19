# test_config.py - Test configuration
import os

# Set some test environment variables
os.environ["DATABASE_URL"] = "postgresql://dbadmin:NYPBedok1234!@baduanjin-db-testing.postgres.database.azure.com:5432/postgres"
os.environ["ENVIRONMENT"] = "testing"
os.environ["SECRET_KEY"] = "your-secret-key-for-jwt-tokens-make-it-long-and-random"

# Import your config
from Backend.test_config import settings

def test_config():
    """Test that configuration loads correctly"""
    print("🧪 Testing configuration...")
    
    # Test database URL
    assert settings.database_url == "postgresql://dbadmin:NYPBedok1234!@baduanjin-db-testing.postgres.database.azure.com:5432/postgres"
    print("✅ Database URL loaded correctly")
    
    # Test environment
    assert settings.environment == "testing"
    print("✅ Environment loaded correctly")
    
    # Test secret key
    assert settings.secret_key == "your-secret-key-for-jwt-tokens-make-it-long-and-random"
    print("✅ Secret key loaded correctly")
    
    # Test defaults
    assert settings.algorithm == "HS256"  # Should use default
    assert settings.access_token_expire_minutes == 30  # Should use default
    print("✅ Defaults working correctly")
    
    # Test Azure settings (should use defaults since not set)
    assert settings.azure_storage_container_videos == "videos"
    assert settings.azure_storage_container_results == "results"
    print("✅ Azure defaults working correctly")
    
    print("🎉 All configuration tests passed!")

if __name__ == "__main__":
    test_config()