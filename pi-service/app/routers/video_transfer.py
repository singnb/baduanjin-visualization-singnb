# routers/video_transfer.py
# Video Transfer Router - Integrated with existing video upload system

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import os
import aiofiles
import httpx
from pathlib import Path
import uuid
from typing import Optional
import tempfile

from database import get_db
from models import VideoUpload, User
from schemas import VideoUploadResponse
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/video-transfer", tags=["Video Transfer"])

# Configuration - Match your existing upload structure
MAIN_BACKEND_URL = os.getenv("MAIN_BACKEND_URL", "https://baduanjin-backend-docker.azurewebsites.net")
PI_BASE_URL = os.getenv("PI_BASE_URL", "http://172.20.10.5:5001")

@router.get("/list-pi-recordings")
async def list_pi_recordings():
    """Get list of available recordings from Pi for transfer"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{PI_BASE_URL}/api/recordings")
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "pi_recordings": data.get("recordings", []),
                    "count": data.get("count", 0),
                    "pi_status": "connected",
                    "message": f"Found {data.get('count', 0)} recordings on Pi"
                }
            else:
                return {
                    "success": False,
                    "message": f"Pi responded with status {response.status_code}",
                    "pi_status": "error",
                    "pi_recordings": [],
                    "count": 0
                }
    except httpx.TimeoutException:
        return {
            "success": False,
            "message": "Pi connection timed out",
            "pi_status": "timeout", 
            "pi_recordings": [],
            "count": 0
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Cannot connect to Pi: {str(e)}",
            "pi_status": "disconnected",
            "pi_recordings": [],
            "count": 0
        }

@router.post("/transfer-from-pi")
async def transfer_from_pi(
    background_tasks: BackgroundTasks,
    timestamp: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(""),
    brocade_type: str = Form("LIVE_SESSION"),
    current_user: User = Depends(get_current_user)
):
    """
    Transfer dual videos from Pi and upload them using existing upload API
    This ensures both manual uploads and Pi transfers use the same storage/database
    """
    try:
        # Validate timestamp format
        if not timestamp or len(timestamp) != 15:  # YYYYMMDD_HHMMSS
            raise HTTPException(400, "Invalid timestamp format. Expected: YYYYMMDD_HHMMSS")
        
        # Define Pi filenames
        original_filename = f"baduanjin_original_{timestamp}.mp4"
        annotated_filename = f"baduanjin_annotated_{timestamp}.mp4"
        
        print(f"🔄 Starting transfer for timestamp: {timestamp}")
        print(f"📹 Original: {original_filename}")
        print(f"🤖 Annotated: {annotated_filename}")
        
        # Create temporary directory for downloads
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            local_original = temp_dir_path / original_filename
            local_annotated = temp_dir_path / annotated_filename
            
            # Download original video from Pi
            print(f"⬇️ Downloading original video...")
            async with httpx.AsyncClient(timeout=300.0) as client:
                original_response = await client.get(
                    f"{PI_BASE_URL}/api/download/{original_filename}"
                )
                if original_response.status_code != 200:
                    raise HTTPException(404, f"Original video not found on Pi: {original_filename}")
                
                async with aiofiles.open(local_original, 'wb') as f:
                    await f.write(original_response.content)
                
                print(f"✅ Original downloaded: {len(original_response.content)} bytes")
            
            # Download annotated video from Pi
            print(f"⬇️ Downloading annotated video...")
            async with httpx.AsyncClient(timeout=300.0) as client:
                annotated_response = await client.get(
                    f"{PI_BASE_URL}/api/download/{annotated_filename}"
                )
                if annotated_response.status_code != 200:
                    raise HTTPException(404, f"Annotated video not found on Pi: {annotated_filename}")
                
                async with aiofiles.open(local_annotated, 'wb') as f:
                    await f.write(annotated_response.content)
                
                print(f"✅ Annotated downloaded: {len(annotated_response.content)} bytes")
            
            # Get auth token for main backend
            from auth.utils import create_access_token
            token_data = {
                "id": current_user.id,
                "email": current_user.email,
                "username": current_user.username,
                "role": current_user.role
            }
            auth_token = create_access_token(data=token_data)
            
            # Upload original video to main backend using existing API
            print(f"📤 Uploading original to main backend...")
            async with httpx.AsyncClient(timeout=600.0) as client:
                with open(local_original, 'rb') as f:
                    files = {'file': (original_filename, f, 'video/mp4')}
                    data = {
                        'title': f"{title} (Original)",
                        'description': f"{description}\n\nOriginal video from Pi session {timestamp}",
                        'brocade_type': brocade_type
                    }
                    headers = {'Authorization': f'Bearer {auth_token}'}
                    
                    original_upload_response = await client.post(
                        f"{MAIN_BACKEND_URL}/api/videos/upload",
                        files=files,
                        data=data,
                        headers=headers
                    )
                    
                    if original_upload_response.status_code != 200:
                        raise HTTPException(500, f"Failed to upload original video: {original_upload_response.text}")
                    
                    original_result = original_upload_response.json()
                    print(f"✅ Original uploaded, ID: {original_result.get('id')}")
            
            # Upload annotated video to main backend
            print(f"📤 Uploading annotated to main backend...")
            async with httpx.AsyncClient(timeout=600.0) as client:
                with open(local_annotated, 'rb') as f:
                    files = {'file': (annotated_filename, f, 'video/mp4')}
                    data = {
                        'title': f"{title} (Annotated)",
                        'description': f"{description}\n\nAnnotated video with pose analysis from Pi session {timestamp}",
                        'brocade_type': brocade_type
                    }
                    headers = {'Authorization': f'Bearer {auth_token}'}
                    
                    annotated_upload_response = await client.post(
                        f"{MAIN_BACKEND_URL}/api/videos/upload",
                        files=files,
                        data=data,
                        headers=headers
                    )
                    
                    if annotated_upload_response.status_code != 200:
                        raise HTTPException(500, f"Failed to upload annotated video: {annotated_upload_response.text}")
                    
                    annotated_result = annotated_upload_response.json()
                    print(f"✅ Annotated uploaded, ID: {annotated_result.get('id')}")
        
        # Schedule Pi cleanup in background
        background_tasks.add_task(
            cleanup_pi_files,
            [original_filename, annotated_filename]
        )
        
        return {
            "success": True,
            "message": "Dual videos transferred successfully",
            "transfer_info": {
                "timestamp": timestamp,
                "original_size": len(original_response.content),
                "annotated_size": len(annotated_response.content),
                "total_size": len(original_response.content) + len(annotated_response.content),
                "pi_files_scheduled_for_cleanup": True
            },
            "uploaded_videos": {
                "original": {
                    "id": original_result.get("id"),
                    "title": original_result.get("title"),
                    "status": "uploaded"
                },
                "annotated": {
                    "id": annotated_result.get("id"), 
                    "title": annotated_result.get("title"),
                    "status": "uploaded"
                }
            },
            "backend_used": MAIN_BACKEND_URL
        }
        
    except httpx.TimeoutException:
        raise HTTPException(408, "Transfer timed out - files may be too large")
    except Exception as e:
        print(f"❌ Transfer error: {e}")
        raise HTTPException(500, f"Transfer failed: {str(e)}")

@router.get("/pi-status")
async def get_pi_status():
    """Get comprehensive Pi status including available recordings"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get Pi health
            health_response = await client.get(f"{PI_BASE_URL}/api/health")
            health_data = health_response.json() if health_response.status_code == 200 else {}
            
            # Get Pi recordings
            recordings_response = await client.get(f"{PI_BASE_URL}/api/recordings")
            recordings_data = recordings_response.json() if recordings_response.status_code == 200 else {}
            
            # Get current streaming status
            status_response = await client.get(f"{PI_BASE_URL}/api/status")
            status_data = status_response.json() if status_response.status_code == 200 else {}
            
            return {
                "pi_connected": health_response.status_code == 200,
                "pi_health": health_data,
                "recordings_available": recordings_data.get("count", 0),
                "latest_recording": recordings_data.get("recordings", [{}])[0] if recordings_data.get("recordings") else None,
                "is_streaming": status_data.get("is_running", False),
                "is_recording": status_data.get("is_recording", False),
                "current_fps": status_data.get("current_fps", 0),
                "status": "healthy" if health_response.status_code == 200 else "unreachable",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "pi_connected": False,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/cleanup-pi/{timestamp}")
async def manual_cleanup_pi(
    timestamp: str,
    current_user: User = Depends(get_current_user)
):
    """Manually trigger cleanup of specific Pi files"""
    try:
        original_filename = f"baduanjin_original_{timestamp}.mp4"
        annotated_filename = f"baduanjin_annotated_{timestamp}.mp4"
        
        cleanup_results = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for filename in [original_filename, annotated_filename]:
                try:
                    response = await client.delete(f"{PI_BASE_URL}/api/recordings/{filename}")
                    cleanup_results.append({
                        "filename": filename,
                        "success": response.status_code in [200, 404],  # 404 is OK (already deleted)
                        "status_code": response.status_code
                    })
                except Exception as e:
                    cleanup_results.append({
                        "filename": filename,
                        "success": False,
                        "error": str(e)
                    })
        
        return {
            "success": True,
            "message": f"Cleanup attempted for timestamp {timestamp}",
            "cleanup_results": cleanup_results
        }
    except Exception as e:
        raise HTTPException(500, f"Cleanup failed: {str(e)}")

# Background task for Pi cleanup
async def cleanup_pi_files(filenames: list):
    """Clean up files on Pi after successful transfer"""
    print(f"🧹 Starting Pi cleanup for {len(filenames)} files...")
    
    for filename in filenames:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(f"{PI_BASE_URL}/api/recordings/{filename}")
                if response.status_code in [200, 404]:  # 404 = already deleted
                    print(f"✅ Pi file cleaned: {filename}")
                else:
                    print(f"⚠️ Pi cleanup warning for {filename}: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Pi cleanup failed for {filename}: {e}")
    
    print("🧹 Pi cleanup task completed")

# Health check specifically for video transfer system
@router.get("/health")
async def video_transfer_health():
    """Health check for video transfer system"""
    try:
        # Test Pi connectivity
        pi_status = "unknown"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{PI_BASE_URL}/api/health")
                pi_status = "connected" if response.status_code == 200 else "unreachable"
        except:
            pi_status = "unreachable"
        
        # Test main backend connectivity  
        backend_status = "unknown"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{MAIN_BACKEND_URL}/health")
                backend_status = "connected" if response.status_code == 200 else "unreachable"
        except:
            backend_status = "unreachable"
        
        return {
            "service": "video_transfer",
            "status": "healthy",
            "pi_connectivity": pi_status,
            "main_backend_connectivity": backend_status,
            "pi_url": PI_BASE_URL,
            "main_backend_url": MAIN_BACKEND_URL,
            "transfer_ready": pi_status == "connected" and backend_status == "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "service": "video_transfer",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }