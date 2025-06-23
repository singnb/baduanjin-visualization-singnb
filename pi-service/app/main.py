# pi-service/app/main.py
# Azure Pi Service - FastAPI Main Application

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import sys
from datetime import datetime

print("Initializing Baduanjin Pi Service...")

# Create FastAPI app
app = FastAPI(
    title="Baduanjin Pi Service",
    description="Raspberry Pi coordination and live streaming service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Frontend
        "https://nice-wave-0a2eb2e0f.4.azurestaticapps.net",
        "http://localhost:3000",  # Local development
        
        # Main Backend 
        "https://baduanjin-backend-docker.azurewebsites.net",
        
        # Physical Pi (update with your Pi's IP)
        "http://172.20.10.5:5001",
        "http://172.20.10.6:5001",
        
        # Local development
        "http://localhost:5001",
        "http://127.0.0.1:5001",
        "*"  # Allow all for initial testing
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Import and include routers (with error handling)
try:
    from auth.router import router as auth_router
    app.include_router(auth_router)
    print("Auth router included")
except Exception as e:
    print(f"Could not include auth router: {e}")

try:
    # Fix import path - assuming pi_live.py is in routers folder
    from routers.pi_live import router as pi_live_router
    app.include_router(pi_live_router)
    print("Pi Live router included")
except Exception as e:
    print(f"Could not include pi_live router: {e}")
    # Try alternative import path
    try:
        from pi_live import router as pi_live_router
        app.include_router(pi_live_router)
        print("Pi Live router included (alternative path)")
    except Exception as e2:
        print(f"Could not include pi_live router (alternative): {e2}")

# Root endpoint
@app.get("/")
async def root():
    """Pi Service root endpoint"""
    return {
        "service": "Baduanjin Pi Service",
        "status": "running", 
        "version": "1.0.0",
        "description": "Raspberry Pi coordination and live streaming service",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "redoc": "/redoc",
            "pi_status": "/api/pi-live/status",
            "auth": "/api/auth/me"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Azure App Service"""
    try:
        # Try to test database connection if available
        try:
            from database import engine
            from sqlalchemy import text
            
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1;"))
                db_connected = result.fetchone()[0] == 1
        except Exception as db_error:
            print(f"Database test failed: {db_error}")
            db_connected = False
        
        return {
            "status": "healthy",
            "service": "baduanjin-pi-service",
            "environment": os.getenv("ENVIRONMENT", "production"),
            "database_connected": db_connected,
            "timestamp": datetime.now().isoformat(),
            "azure_deployment": True,
            "python_version": f"{sys.version}"
        }
    except Exception as e:
        return {
            "status": "partially_healthy",
            "service": "baduanjin-pi-service", 
            "database_connected": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "note": "Service running but some components may not be available"
        }

# Service info endpoint
@app.get("/api/pi-service/info")
async def service_info():
    """Get Pi service information"""
    return {
        "service_name": "Baduanjin Pi Service",
        "service_type": "Pi Coordination Service",
        "capabilities": [
            "Pi device management",
            "Live streaming coordination", 
            "Video recording management",
            "Real-time pose data relay",
            "Session management"
        ],
        "communication": {
            "pi_api_base": "http://172.20.10.5:5001/api",
            "websocket_url": "ws://172.20.10.5:5001",
            "protocol": "HTTP/WebSocket"
        },
        "status": "operational"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    try:
        print("Starting Baduanjin Pi Service...")
        
        # Try to initialize database if available
        try:
            from database import engine, Base
            Base.metadata.create_all(bind=engine)
            print("Database tables verified/created")
        except Exception as db_error:
            print(f"Database initialization warning: {db_error}")
        
        print("Pi Service running on Azure")
        print("Ready to coordinate with Raspberry Pi")
        print("Pi Service startup complete!")
        
    except Exception as e:
        print(f"Startup warning: {e}")
        print("Service will continue running with limited functionality")

# FIXED: Error handler for 404 - Return JSONResponse instead of dict
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint not found",
            "service": "baduanjin-pi-service",
            "available_endpoints": [
                "/",
                "/health", 
                "/docs",
                "/api/pi-service/info"
            ],
            "suggestion": "Check /docs for full API documentation"
        }
    )

# ADDED: Generic exception handler for other errors
@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "service": "baduanjin-pi-service",
            "message": "An unexpected error occurred"
        }
    )

print("Baduanjin Pi Service initialized successfully")

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )