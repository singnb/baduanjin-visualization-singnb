# main.py
# main FastAPI application

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import os

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from mimetypes import add_type

# Import routers
from auth.router import router as auth_router
from routers.video import router as video_router
from routers.relationships import router as relationships_router
from routers.analysis import router as analysis_router  
from routers.analysis_with_master import router as analysis_with_master_router  
from routers.video_english import router as video_english_router
from baduanjin_analysis.router import router as baduanjin_router

# Import database
from database import engine, Base

# Azure imports for testing deployment 
from config import settings
from azure_services import azure_blob_service

# Create directory structure
for dir_name in ["uploads", "processed", "analysis"]:
    os.makedirs(dir_name, exist_ok=True)

# Create FastAPI app
app = FastAPI(title="Baduanjin Analysis API")

# Configure CORS - Updated for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # For local development
        "https://wonderful-island-01f223900.6.azurestaticapps.net"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Serve static files
# app.mount("/api/static", StaticFiles(directory="uploads"), name="static_files")
# app.mount("/api/static/outputs_json", StaticFiles(directory="outputs_json"), name="static_outputs_json")
# app.mount("/api/static", StaticFiles(directory="."), name="static_files")

# Add these mounts after creating your FastAPI app
app.mount("/api/static/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/api/static/outputs_json", StaticFiles(directory="outputs_json"), name="outputs_json")

# Include routers
app.include_router(auth_router)
app.include_router(video_router)
app.include_router(analysis_router)  
app.include_router(analysis_with_master_router)  
app.include_router(relationships_router)
app.include_router(baduanjin_router)
app.include_router(video_english_router)

# Add Azure health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint for Azure deployment"""
    try:
        # Test database connection
        from sqlalchemy import text, inspect
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            db_version = result.fetchone()[0][:50]
        
        # Check if tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        return {
            "status": "healthy",
            "environment": settings.environment,
            "azure_storage_configured": bool(settings.azure_storage_connection_string),
            "database_configured": bool(settings.database_url),
            "database_connected": True,
            "database_version": db_version,
            "tables_found": tables,
            "table_count": len(tables),
            "timestamp": "2024-06-08"
        }
    except Exception as e:
        return {
            "status": "healthy_but_db_issue",
            "environment": settings.environment,
            "azure_storage_configured": bool(settings.azure_storage_connection_string),
            "database_configured": bool(settings.database_url),
            "database_connected": False,
            "database_error": str(e),
            "tables_found": [],
            "table_count": 0,
            "timestamp": "2024-06-08"
        }

# Add a debug endpoint to help diagnose path issues
@app.get("/api/debug/paths")
def debug_paths():
    """Debug endpoint to check paths and file existence"""
    root_dir = os.getcwd()
    results = {
        "current_working_directory": root_dir,
        "directories": {},
        "sample_files": {}
    }
    
    # Check uploads directory
    uploads_dir = os.path.join(root_dir, "uploads")
    results["directories"]["uploads_exists"] = os.path.exists(uploads_dir)
    if results["directories"]["uploads_exists"]:
        results["directories"]["uploads_files"] = os.listdir(uploads_dir)
        
        # Check videos subdirectory
        videos_dir = os.path.join(uploads_dir, "videos")
        results["directories"]["videos_exists"] = os.path.exists(videos_dir)
        if results["directories"]["videos_exists"]:
            results["directories"]["videos_files"] = os.listdir(videos_dir)
            
            # Check user subdirectory
            user_dir = os.path.join(videos_dir, "2")
            results["directories"]["user_dir_exists"] = os.path.exists(user_dir)
            if results["directories"]["user_dir_exists"]:
                results["directories"]["user_files"] = os.listdir(user_dir)
                
                # Check for specific video files
                for file in results["directories"]["user_files"]:
                    if file.endswith(".mp4"):
                        file_path = os.path.join(user_dir, file)
                        results["sample_files"][file] = {
                            "exists": os.path.exists(file_path),
                            "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                            "absolute_path": os.path.abspath(file_path),
                            "relative_path": os.path.relpath(file_path, root_dir)
                        }
    
    # Check outputs_json directory
    outputs_dir = os.path.join(root_dir, "outputs_json")
    results["directories"]["outputs_json_exists"] = os.path.exists(outputs_dir)
    if results["directories"]["outputs_json_exists"]:
        results["directories"]["outputs_json_files"] = os.listdir(outputs_dir)
    
    return results

# Add custom MIME types
add_type("video/mp4", ".MP4")  # Add .MP4 (uppercase) mapping

# Add a custom route for video files
@app.get("/api/videos/{path:path}")
async def serve_video(path: str):
    """Serve video files with correct MIME type and headers"""
    import os
    
    # Clean the path
    clean_path = path.replace('\\', '/')
    
    # Construct file path
    filepath = os.path.join(".", clean_path)
    
    # Security check - ensure path doesn't escape current directory
    abs_path = os.path.abspath(filepath)
    abs_cwd = os.path.abspath(".")
    if not abs_path.startswith(abs_cwd):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Check if it's actually a video file
    if not filepath.lower().endswith(('.mp4', '.webm', '.ogg')):
        raise HTTPException(status_code=400, detail="Not a video file")
    
    # Serve with proper headers for video streaming
    return FileResponse(
        filepath, 
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": "inline",
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*",  # Updated for Azure
            "Access-Control-Allow-Credentials": "true"
        }
    )

@app.get("/")
def read_root():
    return {"message": "Welcome to the Baduanjin Analysis API"}

# Create database tables on startup
@app.get("/api/force-create-tables")
async def force_create_tables():
    """Manually force table creation"""
    try:
        # Create tables
        Base.metadata.create_all(bind=engine)
        
        # Verify
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        return {
            "status": "success",
            "message": "Tables created successfully",
            "tables": tables,
            "count": len(tables)
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": str(e)
        }

# 3. MODIFY your existing startup event (around line 110):
@app.on_event("startup")
async def startup_event():
    try:
        print("Starting application...")
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully!")
        
        # Quick verification
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"Tables found: {tables}")
        
    except Exception as e:
        print(f"Startup error: {e}")
        # Don't fail startup, just log the error

# Run with: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
