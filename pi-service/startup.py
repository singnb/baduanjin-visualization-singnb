# pi-service/startup.py
# Azure App Service Startup Script

import os
import sys
from pathlib import Path

print("Baduanjin Pi Service - Azure Startup")

# Add the app directory to Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

print(f"App directory: {app_dir}")
print(f"Python path: {sys.path}")

try:
    # Import the FastAPI app
    from main import app
    print("FastAPI app imported successfully")
except ImportError as e:
    print(f"Import error: {e}")
    # Try alternative import
    try:
        from app.main import app
        print("✅ FastAPI app imported with alternative path")
    except ImportError as e2:
        print(f"Alternative import also failed: {e2}")
        raise

# Main execution
if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment (Azure sets this automatically)
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    print(f"Starting server on {host}:{port}")
    print(f"Environment: {os.environ.get('ENVIRONMENT', 'production')}")
    print(f"Database URL configured: {'DATABASE_URL' in os.environ}")
    
    # Start the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )