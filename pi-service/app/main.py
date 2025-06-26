# pi-service/app/main.py
# Azure Pi Service - FastAPI Main Application

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import sys
from datetime import datetime

print("Initializing Baduanjin Pi Service for Video Transfer...")

# Create FastAPI app
app = FastAPI(
    title="Baduanjin Pi Service",
    description="Pi coordination and video transfer service - integrates with main backend",
    version="1.2.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS (match your existing CORS setup)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Your frontend
        "https://nice-wave-0a2eb2e0f.4.azurestaticapps.net",
        "http://localhost:3000",  # Local development
        
        # Your main backend 
        "https://baduanjin-backend-docker.azurewebsites.net",
        
        # Physical Pi (update with your actual Pi IP)
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

# NEW: Include video transfer router
try:
    from routers.video_transfer import router as video_transfer_router
    app.include_router(video_transfer_router)
    print("✅ Video Transfer router included")
except Exception as e:
    print(f"⚠️ Could not include video_transfer router: {e}")
    print("🔧 To fix: Create routers/video_transfer.py with the transfer endpoints")

# Root endpoint
@app.get("/")
async def root():
    """Pi Service root endpoint"""
    return {
        "service": "Baduanjin Pi Service", 
        "status": "running",
        "version": "1.2.0",
        "description": "Pi coordination and video transfer service",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "timestamp": datetime.now().isoformat(),
        "integration": {
            "main_backend": os.getenv("MAIN_BACKEND_URL", "https://baduanjin-backend-docker.azurewebsites.net"),
            "pi_device": os.getenv("PI_BASE_URL", "http://172.20.10.5:5001"),
            "transfer_enabled": True
        },
        "features": [
            "Pi device coordination",
            "Video transfer from Pi to main backend",
            "Dual video support (original + annotated)",
            "Automatic Pi cleanup after transfer",
            "Integration with existing upload system"
        ],
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "video_transfer": "/api/video-transfer",
            "pi_recordings": "/api/video-transfer/list-pi-recordings",
            "transfer": "/api/video-transfer/transfer-from-pi"
        }
    }

# Enhanced health check
@app.get("/health")
async def health_check():
    """Health check with Pi and main backend connectivity"""
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
        
        # Test main backend connectivity
        backend_status = "unknown"
        backend_url = os.getenv("MAIN_BACKEND_URL", "https://baduanjin-backend-docker.azurewebsites.net")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{backend_url}/health")
                backend_status = "connected" if response.status_code == 200 else "unreachable"
        except Exception:
            backend_status = "unreachable"
        
        overall_status = "healthy"
        if pi_status == "unreachable" and backend_status == "unreachable":
            overall_status = "critical"
        elif pi_status == "unreachable" or backend_status == "unreachable":
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "service": "baduanjin-pi-service",
            "environment": os.getenv("ENVIRONMENT", "production"),
            "database_connected": db_connected,
            "pi_connectivity": pi_status,
            "main_backend_connectivity": backend_status,
            "video_transfer_ready": pi_status == "connected" and backend_status == "connected",
            "timestamp": datetime.now().isoformat(),
            "urls": {
                "pi": pi_url,
                "main_backend": backend_url
            },
            "capabilities": {
                "video_transfer": True,
                "dual_recording": True,
                "pi_cleanup": True,
                "backend_integration": True
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
        "service_type": "Pi Coordination & Video Transfer Service",
        "version": "1.2.0",
        "capabilities": [
            "Pi device management",
            "Video transfer coordination", 
            "Dual video handling (original + annotated)",
            "Integration with main backend upload API",
            "Automatic Pi storage cleanup",
            "Real-time Pi status monitoring"
        ],
        "integration": {
            "main_backend_url": os.getenv("MAIN_BACKEND_URL", "https://baduanjin-backend-docker.azurewebsites.net"),
            "pi_device_url": os.getenv("PI_BASE_URL", "http://172.20.10.5:5001"),
            "upload_endpoint": "/api/videos/upload",
            "uses_existing_auth": True,
            "uses_existing_storage": True
        },
        "workflow": [
            "1. Pi records dual videos (original + annotated)",
            "2. Frontend calls /api/video-transfer/list-pi-recordings",
            "3. User selects recording to transfer", 
            "4. Pi-service downloads videos from Pi",
            "5. Pi-service uploads to main backend via existing API",
            "6. Pi files automatically cleaned up",
            "7. Videos appear in user's normal video list"
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
        "transfer_timeout": "600 seconds",
        "supported_formats": ["mp4"],
        "dual_video_support": True,
        "auto_cleanup": True
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
        
        # Test main backend connectivity
        backend_url = os.getenv("MAIN_BACKEND_URL", "https://baduanjin-backend-docker.azurewebsites.net")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{backend_url}/health")
                if response.status_code == 200:
                    print(f"✅ Main backend connected: {backend_url}")
                else:
                    print(f"⚠️ Main backend issues: HTTP {response.status_code}")
        except Exception as backend_error:
            print(f"⚠️ Main backend not reachable: {backend_error}")
        
        print("✅ Pi Service running on Azure")
        print("🎥 Video transfer service ready")
        print("🔗 Integrated with existing backend upload system")
        print("🧹 Automatic Pi cleanup enabled")
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
                "/api/video-transfer/list-pi-recordings",
                "/api/video-transfer/transfer-from-pi",
                "/api/pi-test",
                "/api/config"
            ],
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

print("✅ Baduanjin Pi Service with Video Transfer initialized successfully")

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