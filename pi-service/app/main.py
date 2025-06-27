# pi-service/app/main.py
# Azure Pi Service - FastAPI Main Application
# CLEANED VERSION - Focuses only on Pi communication, video transfer moved to main backend

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import sys
from datetime import datetime

print("Initializing Baduanjin Pi Service for Pi Communication...")

# Create FastAPI app
app = FastAPI(
    title="Baduanjin Pi Service",
    description="Pi communication and coordination service",
    version="1.3.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Your frontend
        "https://nice-wave-0a2eb2e0f.4.azurestaticapps.net",
        "http://localhost:3000",  # Local development
        
        # Your main backend 
        "https://baduanjin-backend-docker.azurewebsites.net",
        
        # Physical Pi
        "http://172.20.10.5:5001",
        "http://172.20.10.6:5001",
        
        # Local development
        "http://localhost:5001",
        "http://127.0.0.1:5001",
        "*"  # Allow all for testing
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Import and include routers with error handling
try:
    from auth.router import router as auth_router
    app.include_router(auth_router)
    print("✅ Auth router included")
except Exception as e:
    print(f"⚠️ Could not include auth router: {e}")

try:
    from routers.pi_live import router as pi_live_router
    app.include_router(pi_live_router)
    print("✅ Pi Live router included")
except Exception as e:
    print(f"⚠️ Could not include pi_live router: {e}")

# Root endpoint
@app.get("/")
async def root():
    """Pi Service root endpoint"""
    return {
        "service": "Baduanjin Pi Service", 
        "status": "running",
        "version": "1.3.0",
        "description": "Pi communication and coordination service",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "timestamp": datetime.now().isoformat(),
        "integration": {
            "main_backend": os.getenv("MAIN_BACKEND_URL", "https://baduanjin-backend-docker.azurewebsites.net"),
            "pi_device": os.getenv("PI_BASE_URL", "http://172.20.10.5:5001"),
            "video_transfer": "Handled by main backend"
        },
        "features": [
            "Pi device communication",
            "Live session management", 
            "Real-time pose data streaming",
            "Pi status monitoring",
            "Video recording coordination"
        ],
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "pi_live": "/api/pi-live",
            "pi_status": "/api/pi-live/status",
            "recordings": "/api/pi-live/recordings"
        },
        "note": "Video transfer functionality moved to main backend"
    }

# Enhanced health check
@app.get("/health")
async def health_check():
    """Health check with Pi connectivity"""
    try:
        # Test database connection if available
        db_connected = False
        try:
            from database import engine
            from sqlalchemy import text
            
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1;"))
                db_connected = result.fetchone()[0] == 1
        except Exception as db_error:
            print(f"Database test: {db_error}")
        
        # Test Pi connectivity
        pi_status = "unknown"
        pi_url = os.getenv("PI_BASE_URL", "http://172.20.10.5:5001")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{pi_url}/api/health")
                pi_status = "connected" if response.status_code == 200 else "unreachable"
        except Exception:
            pi_status = "unreachable"
        
        overall_status = "healthy" if pi_status == "connected" else "degraded"
        
        return {
            "status": overall_status,
            "service": "baduanjin-pi-service",
            "environment": os.getenv("ENVIRONMENT", "production"),
            "database_connected": db_connected,
            "pi_connectivity": pi_status,
            "pi_communication_ready": pi_status == "connected",
            "timestamp": datetime.now().isoformat(),
            "urls": {
                "pi": pi_url
            },
            "capabilities": {
                "pi_communication": True,
                "live_sessions": True,
                "pose_streaming": True,
                "status_monitoring": True
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "service": "baduanjin-pi-service",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Service info endpoint
@app.get("/api/pi-service/info")
async def service_info():
    """Get Pi service information"""
    return {
        "service_name": "Baduanjin Pi Service",
        "service_type": "Pi Communication & Coordination Service",
        "version": "1.3.0",
        "capabilities": [
            "Pi device communication",
            "Live session management", 
            "Real-time pose data streaming",
            "Pi status monitoring",
            "Video recording coordination"
        ],
        "integration": {
            "main_backend_url": os.getenv("MAIN_BACKEND_URL", "https://baduanjin-backend-docker.azurewebsites.net"),
            "pi_device_url": os.getenv("PI_BASE_URL", "http://172.20.10.5:5001"),
            "video_transfer": "Handled by main backend /api/videos/pi-transfer endpoint"
        },
        "workflow": [
            "1. Pi records videos during live sessions",
            "2. Frontend gets recording list via pi-service",
            "3. Frontend requests transfer via main backend", 
            "4. Main backend downloads from Pi and stores videos",
            "5. Videos appear in user's normal video list"
        ],
        "status": "operational"
    }

# Quick Pi connectivity test
@app.get("/api/pi-test")
async def test_pi_connection():
    """Quick test of Pi connectivity"""
    pi_url = os.getenv("PI_BASE_URL", "http://172.20.10.5:5001")
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test basic connectivity
            health_response = await client.get(f"{pi_url}/api/health")
            
            # Test recordings endpoint
            recordings_response = await client.get(f"{pi_url}/api/recordings")
            
            return {
                "pi_url": pi_url,
                "connectivity": "connected",
                "health_status": health_response.status_code,
                "recordings_endpoint": recordings_response.status_code,
                "available_recordings": recordings_response.json().get("count", 0) if recordings_response.status_code == 200 else 0,
                "message": "Pi is reachable and responsive"
            }
    except Exception as e:
        return {
            "pi_url": pi_url,
            "connectivity": "failed",
            "error": str(e),
            "message": "Cannot reach Pi device"
        }

# Configuration endpoint
@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    return {
        "pi_base_url": os.getenv("PI_BASE_URL", "http://172.20.10.5:5001"),
        "main_backend_url": os.getenv("MAIN_BACKEND_URL", "https://baduanjin-backend-docker.azurewebsites.net"),
        "environment": os.getenv("ENVIRONMENT", "production"),
        "pi_communication_timeout": "10 seconds",
        "live_session_support": True,
        "pose_streaming_support": True,
        "video_transfer_location": "main_backend"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    try:
        print("🚀 Starting Baduanjin Pi Service...")
        
        # Initialize database if available
        try:
            from database import engine, Base
            Base.metadata.create_all(bind=engine)
            print("✅ Database connection verified")
        except Exception as db_error:
            print(f"⚠️ Database not available: {db_error}")
        
        # Test Pi connectivity
        pi_url = os.getenv("PI_BASE_URL", "http://172.20.10.5:5001")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{pi_url}/api/health")
                if response.status_code == 200:
                    print(f"✅ Pi device connected: {pi_url}")
                else:
                    print(f"⚠️ Pi device issues: HTTP {response.status_code}")
        except Exception as pi_error:
            print(f"⚠️ Pi device not reachable: {pi_error}")
        
        print("✅ Pi Service running on Azure")
        print("📡 Pi communication service ready")
        print("🎥 Live session management enabled")
        print("📊 Pose streaming support active")
        print("🔗 Video transfer handled by main backend")
        print("✨ Pi Service startup complete!")
        
    except Exception as e:
        print(f"⚠️ Startup warning: {e}")
        print("🔄 Service will continue with limited functionality")

# Error handlers
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
                "/api/pi-service/info",
                "/api/pi-live/status",
                "/api/pi-live/recordings",
                "/api/pi-live/start-session",
                "/api/pi-test",
                "/api/config"
            ],
            "note": "Video transfer endpoints moved to main backend",
            "suggestion": "Check /docs for full API documentation"
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "service": "baduanjin-pi-service",
            "message": "An unexpected error occurred",
            "timestamp": datetime.now().isoformat()
        }
    )

print("✅ Baduanjin Pi Service (Communication Only) initialized successfully")

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