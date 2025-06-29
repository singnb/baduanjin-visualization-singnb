# pi-service/pi_live.py

"""
Enhanced Raspberry Pi Integration Router
Includes video recording, file transfer, and advanced session management
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, Optional, List
import httpx
import json
import aiofiles
import shutil
import os
from datetime import datetime
from pathlib import Path

from database import get_db
from models import User, VideoUpload, KeypointData
from auth.router import get_current_user

import uuid
import asyncio

router = APIRouter(prefix="/api/pi-live", tags=["pi-live-sessions"])

# Pi Configuration - Updated to match your IP
PI_BASE_URL = "https://mongoose-hardy-caiman.ngrok-free.app/api"
PI_WEBSOCKET_URL = "wss://mongoose-hardy-caiman.ngrok-free.app"

# File storage configuration
VIDEOS_DIR = Path("uploaded_videos")
RECORDINGS_DIR = Path("pi_recordings")

# Create directories
VIDEOS_DIR.mkdir(exist_ok=True)
RECORDINGS_DIR.mkdir(exist_ok=True)

class EnhancedPiService:
    """Enhanced service for Pi communication with video recording"""
    
    def __init__(self):
        self.active_sessions = {}  # Track active sessions
        self.transfer_queue = {}   # Track file transfers
    
    async def check_pi_status(self) -> Dict[str, Any]:
        """Enhanced Pi status check for static ngrok URL"""
        try:
            # Use static ngrok URL with enhanced headers
            headers = {
                'ngrok-skip-browser-warning': 'true',
                'User-Agent': 'Azure-Pi-Service/1.0',
                'Accept': 'application/json'
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://mongoose-hardy-caiman.ngrok-free.app/api/status",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "connected": True, 
                        "data": data,
                        "ngrok_status": "active",
                        "connection_method": "static_ngrok"
                    }
                else:
                    return {
                        "connected": False,
                        "error": f"Pi returned HTTP {response.status_code}",
                        "ngrok_status": "error"
                    }
                    
        except httpx.TimeoutException:
            return {
                "connected": False, 
                "error": "Pi connection timeout (mobile network may be slow)",
                "ngrok_status": "timeout",
                "suggestion": "Check mobile network connection and ngrok tunnel"
            }
        except httpx.ConnectError:
            return {
                "connected": False, 
                "error": "Cannot reach Pi via ngrok - tunnel may be down",
                "ngrok_status": "unreachable",
                "suggestion": "Verify ngrok tunnel is running on Pi"
            }
        except Exception as e:
            return {
                "connected": False, 
                "error": f"Pi connection error: {str(e)}",
                "ngrok_status": "unknown_error"
            }
    
    async def start_pi_streaming(self) -> Dict[str, Any]:
        """Start streaming on Pi"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{PI_BASE_URL}/start")
                return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def stop_pi_streaming(self) -> Dict[str, Any]:
        """Stop streaming on Pi"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{PI_BASE_URL}/stop")
                return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def start_pi_recording(self) -> Dict[str, Any]:
        """Start video recording on Pi"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{PI_BASE_URL}/recording/start")
                return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def stop_pi_recording(self) -> Dict[str, Any]:
        """Stop video recording on Pi"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{PI_BASE_URL}/recording/stop")
                return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_pi_recordings(self) -> Dict[str, Any]:
        """Get list of recordings from Pi"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{PI_BASE_URL}/recordings")
                return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def download_pi_recording(self, filename: str, local_path: Path) -> Dict[str, Any]:
        """Enhanced download method with ngrok static URL and better error handling"""
        try:
            # Use static ngrok URL for download
            pi_download_url = f"https://mongoose-hardy-caiman.ngrok-free.app/api/download/{filename}"
            print(f"🔄 Starting download: {filename} from {pi_download_url}")
            
            # Check if file exists on Pi first
            try:
                status_url = f"https://mongoose-hardy-caiman.ngrok-free.app/api/download-status/{filename}"
                async with httpx.AsyncClient(timeout=30.0) as client:
                    status_response = await client.get(status_url, headers={
                        'ngrok-skip-browser-warning': 'true',
                        'User-Agent': 'Azure-Pi-Service/1.0'
                    })
                    
                    if status_response.status_code != 200:
                        return {
                            "success": False, 
                            "error": f"File not ready on Pi: HTTP {status_response.status_code}"
                        }
                    
                    status_data = status_response.json()
                    if not status_data.get("exists", False):
                        return {
                            "success": False,
                            "error": f"File does not exist on Pi: {filename}"
                        }
                    
                    expected_size = status_data.get("size", 0)
                    print(f"📁 File confirmed on Pi: {filename} ({expected_size} bytes)")
                    
            except Exception as status_error:
                print(f"⚠️ Could not verify file status: {status_error}")
                # Continue anyway, but with warning
            
            # Download with enhanced settings for ngrok
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0),
                limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
                follow_redirects=True
            ) as client:
                
                # Method 1: Try streaming download
                try:
                    headers = {
                        'ngrok-skip-browser-warning': 'true',
                        'User-Agent': 'Azure-Pi-Service/1.0',
                        'Accept': 'video/mp4,application/octet-stream,*/*',
                        'Cache-Control': 'no-cache'
                    }
                    
                    print(f"📡 Starting streaming download...")
                    async with client.stream('GET', pi_download_url, headers=headers) as response:
                        
                        if response.status_code != 200:
                            error_text = await response.atext()
                            return {
                                "success": False,
                                "error": f"HTTP {response.status_code}: {error_text[:200]}"
                            }
                        
                        content_length = response.headers.get('content-length')
                        if content_length:
                            expected_size = int(content_length)
                            print(f"📊 Expected download size: {expected_size} bytes")
                        
                        total_size = 0
                        chunk_count = 0
                        
                        # Stream download with progress tracking
                        async with aiofiles.open(local_path, 'wb') as f:
                            async for chunk in response.aiter_bytes(chunk_size=65536):  # 64KB chunks
                                if chunk:
                                    await f.write(chunk)
                                    total_size += len(chunk)
                                    chunk_count += 1
                                    
                                    # Progress log every 100 chunks (about 6.4MB)
                                    if chunk_count % 100 == 0:
                                        print(f"📥 Downloaded {total_size:,} bytes...")
                        
                        print(f"✅ Streaming download completed: {total_size:,} bytes")
                        
                except Exception as stream_error:
                    print(f"⚠️ Streaming failed: {stream_error}, trying direct download...")
                    
                    # Method 2: Direct download fallback
                    response = await client.get(pi_download_url, headers={
                        'ngrok-skip-browser-warning': 'true',
                        'User-Agent': 'Azure-Pi-Service/1.0'
                    })
                    
                    if response.status_code != 200:
                        return {
                            "success": False,
                            "error": f"Direct download failed: HTTP {response.status_code}"
                        }
                    
                    async with aiofiles.open(local_path, 'wb') as f:
                        await f.write(response.content)
                    
                    total_size = len(response.content)
                    print(f"✅ Direct download completed: {total_size:,} bytes")
            
            # Verify download
            if local_path.exists() and local_path.stat().st_size > 0:
                actual_size = local_path.stat().st_size
                
                # Size verification
                if 'expected_size' in locals() and expected_size > 0:
                    if actual_size != expected_size:
                        print(f"⚠️ Size mismatch: expected {expected_size}, got {actual_size}")
                    else:
                        print(f"✅ Size verification passed: {actual_size} bytes")
                
                return {
                    "success": True, 
                    "filename": filename,
                    "local_path": str(local_path),
                    "size": actual_size,
                    "download_method": "streaming" if 'stream_error' not in locals() else "direct"
                }
            else:
                return {
                    "success": False, 
                    "error": "Downloaded file is empty or missing"
                }
                
        except httpx.TimeoutException:
            return {
                "success": False, 
                "error": "Download timeout - ngrok connection may be slow on mobile network"
            }
        except httpx.ConnectError:
            return {
                "success": False, 
                "error": "Cannot connect to Pi - check ngrok tunnel status"
            }
        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
    
    async def delete_pi_recording(self, filename: str) -> Dict[str, Any]:
        """Delete recording from Pi"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.delete(f"{PI_BASE_URL}/recordings/{filename}")
                return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_pi_pose_data(self) -> Dict[str, Any]:
        """Get current pose data from Pi"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{PI_BASE_URL}/pose_data")
                return response.json()
        except Exception as e:
            return {"error": str(e), "pose_data": []}

# Initialize service
pi_service = EnhancedPiService()

@router.get("/status")
async def check_pi_connection():
    """Check Pi connection and enhanced status"""
    status = await pi_service.check_pi_status()
    
    if status["connected"]:
        pi_data = status["data"]
        
        # Get recordings count
        recordings_info = await pi_service.get_pi_recordings()
        recordings_count = 0
        if recordings_info.get("success"):
            recordings_count = len(recordings_info.get("recordings", []))
        
        return {
            "pi_connected": True,
            "pi_ip": "172.20.10.5:5001",
            "camera_available": pi_data.get("camera_available", False),
            "yolo_available": pi_data.get("yolo_available", False),
            "is_running": pi_data.get("is_running", False),
            "is_recording": pi_data.get("is_recording", False),
            "persons_detected": pi_data.get("persons_detected", 0),
            "recordings_available": recordings_count,
            "websocket_url": PI_WEBSOCKET_URL
        }
    else:
        return {
            "pi_connected": False,
            "error": status.get("error", "Unknown error"),
            "pi_ip": "172.20.10.5:5001"
        }

@router.post("/start-session")
async def start_live_session(
    session_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a live pose analysis session with optional recording"""
    
    try:
        session_name = session_data.get("session_name", "Live Baduanjin Session")
        
        # Check if Pi is available first
        pi_status = await pi_service.check_pi_status()
        if not pi_status["connected"]:
            raise HTTPException(
                status_code=503, 
                detail=f"Pi not available: {pi_status.get('error', 'Connection failed')}"
            )
        
        # Create session record
        session_record = None
        
        try:
            # Try using LIVE_SESSION enum
            insert_sql = text("""
                INSERT INTO video_uploads 
                (user_id, title, description, brocade_type, video_path, processing_status, upload_timestamp)
                VALUES 
                (:user_id, :title, :description, :brocade_type, :video_path, :processing_status, NOW())
                RETURNING id
            """)
            
            result = db.execute(insert_sql, {
                "user_id": current_user.id,
                "title": session_name,
                "description": "Live pose analysis session from Raspberry Pi",
                "brocade_type": "LIVE_SESSION",
                "video_path": "",
                "processing_status": "live_active"
            })
            
            session_id = result.fetchone()[0]
            db.commit()
            
            session_record = db.query(VideoUpload).filter(VideoUpload.id == session_id).first()
            print(f"✅ Created live session using LIVE_SESSION enum, ID: {session_id}")
            
        except Exception as enum_error:
            print(f"⚠️ LIVE_SESSION enum failed: {enum_error}")
            db.rollback()
            
            # Fallback
            try:
                session_record = VideoUpload(
                    user_id=current_user.id,
                    title=f"[LIVE] {session_name}",
                    description="Live pose analysis session from Raspberry Pi",
                    brocade_type="FIRST",
                    video_path="",
                    processing_status="live_active",
                    upload_timestamp=datetime.now()
                )
                
                db.add(session_record)
                db.commit()
                db.refresh(session_record)
                print(f"✅ Created live session using FIRST enum fallback, ID: {session_record.id}")
                
            except Exception as fallback_error:
                print(f"❌ Fallback also failed: {fallback_error}")
                db.rollback()
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create session record: {str(fallback_error)}"
                )
        
        if not session_record:
            raise HTTPException(status_code=500, detail="Failed to create session record")
        
        # Create session ID for Pi
        pi_session_id = f"live_{session_record.id}"
        
        # Start streaming on Pi
        try:
            pi_result = await pi_service.start_pi_streaming()
            if not pi_result.get("success", False):
                db.delete(session_record)
                db.commit()
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to start Pi streaming: {pi_result.get('error', 'Unknown error')}"
                )
        except Exception as pi_error:
            db.delete(session_record)
            db.commit()
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to communicate with Pi: {str(pi_error)}"
            )
        
        # Track session in memory
        pi_service.active_sessions[pi_session_id] = {
            "db_id": session_record.id,
            "user_id": current_user.id,
            "start_time": datetime.now(),
            "session_name": session_name,
            "status": "active",
            "recording_files": []  # Track recordings made during this session
        }
        
        print(f"🚀 Live session started successfully: {pi_session_id}")
        
        return {
            "success": True,
            "session_id": pi_session_id,
            "db_session_id": session_record.id,
            "message": "Live session started successfully",
            "pi_status": pi_result,
            "websocket_url": PI_WEBSOCKET_URL,
            "direct_pi_url": "http://172.20.10.5:5001",
            "session_name": session_name,
            "start_time": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in start_live_session: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/stop-session/{session_id}")
async def stop_live_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stop live session"""
    
    # Stop any active recording first
    try:
        await pi_service.stop_pi_recording()
    except Exception as e:
        print(f"⚠️ Error stopping recording: {e}")
    
    # Stop streaming on Pi
    pi_result = await pi_service.stop_pi_streaming()
    
    # Update session record
    if session_id in pi_service.active_sessions:
        session_data = pi_service.active_sessions[session_id]
        db_session_id = session_data["db_id"]
        
        # Update database record
        db_session = db.query(VideoUpload).filter(VideoUpload.id == db_session_id).first()
        if db_session:
            db_session.processing_status = "live_completed"
            db.commit()
        
        # Keep session data for potential save operation (don't delete yet)
        session_data["status"] = "stopped"
        session_data["stop_time"] = datetime.now()
        
        return {
            "success": True,
            "message": "Live session stopped successfully",
            "session_duration": str(datetime.now() - session_data["start_time"]),
            "pi_result": pi_result
        }
    else:
        return {
            "success": False,
            "message": "Session not found in active sessions",
            "pi_result": pi_result
        }

@router.post("/recording/start/{session_id}")
async def start_session_recording(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Start video recording for active session"""
    
    if session_id not in pi_service.active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = pi_service.active_sessions[session_id]
    if session_data["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this session")
    
    # Start recording on Pi
    result = await pi_service.start_pi_recording()
    
    if result.get("success"):
        return {
            "success": True,
            "message": "Recording started successfully",
            "session_id": session_id
        }
    else:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to start recording: {result.get('error', 'Unknown error')}"
        )

@router.post("/recording/stop/{session_id}")
async def stop_session_recording(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Stop video recording for active session"""
    
    if session_id not in pi_service.active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = pi_service.active_sessions[session_id]
    if session_data["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this session")
    
    # Stop recording on Pi
    result = await pi_service.stop_pi_recording()
    
    if result.get("success"):
        # Track the recording file if provided
        if "recording_info" in result and "filename" in result["recording_info"]:
            filename = result["recording_info"]["filename"]
            session_data["recording_files"].append(filename)
        
        return {
            "success": True,
            "message": "Recording stopped successfully",
            "session_id": session_id,
            "recording_info": result.get("recording_info")
        }
    else:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to stop recording: {result.get('error', 'Unknown error')}"
        )

@router.get("/recordings")
async def get_available_recordings(current_user: User = Depends(get_current_user)):
    """Get list of available recordings from Pi"""
    
    try:
        result = await pi_service.get_pi_recordings()
        
        if result.get("success"):
            return {
                "success": True,
                "recordings": result.get("recordings", []),
                "count": len(result.get("recordings", []))
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Failed to get recordings"),
                "recordings": [],
                "count": 0
            }
    except Exception as e:
        print(f"❌ Error getting recordings: {e}")
        return {
            "success": False,
            "error": f"Internal server error: {str(e)}",
            "recordings": [],
            "count": 0
        }

@router.post("/transfer-video/{filename}")
async def transfer_video_from_pi(
    filename: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Transfer video file from Pi to backend storage"""
    
    try:
        # Validate filename
        if not filename.endswith('.mp4'):
            raise HTTPException(status_code=400, detail="Only MP4 files are supported")
        
        # Check if file exists on Pi
        recordings = await pi_service.get_pi_recordings()
        if not recordings.get("success"):
            raise HTTPException(status_code=503, detail="Cannot access Pi recordings")
        
        available_files = [r["filename"] for r in recordings.get("recordings", [])]
        if filename not in available_files:
            raise HTTPException(status_code=404, detail="File not found on Pi")
        
        # Create local file path
        local_filename = f"{current_user.id}_{int(datetime.now().timestamp())}_{filename}"
        local_path = RECORDINGS_DIR / local_filename
        
        # Start background transfer
        pi_service.transfer_queue[filename] = {
            "status": "transferring",
            "user_id": current_user.id,
            "local_path": local_path,
            "start_time": datetime.now()
        }
        
        background_tasks.add_task(transfer_file_background, filename, local_path, current_user.id)
        
        return {
            "success": True,
            "message": f"Transfer started for {filename}",
            "filename": filename,
            "local_filename": local_filename,
            "estimated_time": "1-3 minutes"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transfer initiation failed: {str(e)}")

async def transfer_file_background(filename: str, local_path: Path, user_id: int):
    """Background task to transfer file from Pi - ENHANCED VERSION"""
    try:
        print(f"🚀 Starting background transfer: {filename}")
        
        # Update status
        pi_service.transfer_queue[filename]["status"] = "downloading"
        
        # Download file with enhanced error handling
        result = await pi_service.download_pi_recording(filename, local_path)
        
        if result["success"]:
            pi_service.transfer_queue[filename].update({
                "status": "completed",
                "size": result["size"],
                "completion_time": datetime.now()
            })
            print(f"✅ Transfer completed: {filename} -> {local_path} ({result['size']} bytes)")
        else:
            pi_service.transfer_queue[filename].update({
                "status": "failed",
                "error": result["error"],
                "completion_time": datetime.now()
            })
            print(f"❌ Transfer failed: {filename} - {result['error']}")
            
    except Exception as e:
        error_msg = str(e)
        pi_service.transfer_queue[filename].update({
            "status": "failed",
            "error": error_msg,
            "completion_time": datetime.now()
        })
        print(f"❌ Transfer exception: {filename} - {error_msg}")

# Alternative: Simple requests-based download if httpx continues to cause issues
def download_pi_recording_requests_fallback(self, filename: str, local_path: Path) -> Dict[str, Any]:
    """Fallback download method using requests (sync) - USE IF HTTPX FAILS"""
    import requests
    
    try:
        pi_download_url = f"http://172.20.10.5:5001/api/download/{filename}"
        print(f"🔄 Fallback download: {filename}")
        
        response = requests.get(pi_download_url, stream=True, timeout=120)
        response.raise_for_status()
        
        total_size = 0
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total_size += len(chunk)
        
        print(f"✅ Fallback download completed: {total_size} bytes")
        
        return {
            "success": True,
            "filename": filename,
            "local_path": str(local_path),
            "size": total_size
        }
        
    except Exception as e:
        error_msg = f"Fallback download failed: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}

@router.get("/transfer-status/{filename}")
async def get_transfer_status_enhanced(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """Enhanced transfer status with better debugging info"""
    
    if filename not in pi_service.transfer_queue:
        # Check if file exists on Pi for debugging
        try:
            recordings = await pi_service.get_pi_recordings()
            pi_files = [r["filename"] for r in recordings.get("recordings", [])]
            
            return {
                "transfer_found": False,
                "error": "Transfer not found in queue",
                "filename": filename,
                "available_on_pi": filename in pi_files,
                "pi_files_count": len(pi_files),
                "suggestion": "Check if transfer was initiated" if filename not in pi_files else "Initiate transfer first"
            }
        except:
            return {"transfer_found": False, "error": "Transfer not found and cannot check Pi"}
    
    transfer_info = pi_service.transfer_queue[filename]
    
    if transfer_info["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Enhanced status with debugging info
    status_data = {
        "filename": filename,
        "status": transfer_info["status"],
        "start_time": transfer_info["start_time"].isoformat(),
        "user_id": transfer_info["user_id"],
        "local_path": str(transfer_info.get("local_path", "")),
    }
    
    # Add completion info if available
    if transfer_info.get("completion_time"):
        status_data["completion_time"] = transfer_info["completion_time"].isoformat()
        duration = transfer_info["completion_time"] - transfer_info["start_time"]
        status_data["duration_seconds"] = duration.total_seconds()
    
    if transfer_info.get("size"):
        status_data["size"] = transfer_info["size"]
        status_data["size_mb"] = round(transfer_info["size"] / 1024 / 1024, 2)
    
    if transfer_info.get("error"):
        status_data["error"] = transfer_info["error"]
        status_data["error_details"] = "Check Pi connection and ngrok tunnel status"
    
    # File verification for completed transfers
    if transfer_info["status"] == "completed" and transfer_info.get("local_path"):
        local_path = Path(transfer_info["local_path"])
        status_data["file_exists_locally"] = local_path.exists()
        if local_path.exists():
            status_data["actual_file_size"] = local_path.stat().st_size
    
    return status_data

@router.post("/save-session")
async def save_live_session(
    save_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save live session with optional video file"""
    
    try:
        # Extract data
        title = save_data.get("title", "").strip()
        description = save_data.get("description", "").strip()
        brocade_type = save_data.get("brocade_type", "FIRST")
        session_id = save_data.get("session_id", "")
        video_filename = save_data.get("video_filename")
        has_video_file = save_data.get("has_video_file", False)
        
        if not title:
            raise HTTPException(status_code=400, detail="Title is required")
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID is required")
        
        # Map brocade type
        brocade_mapping = {
            "FIRST": "BROCADE_1", "SECOND": "BROCADE_2", "THIRD": "BROCADE_3",
            "FOURTH": "BROCADE_4", "FIFTH": "BROCADE_5", "SIXTH": "BROCADE_6",
            "SEVENTH": "BROCADE_7", "EIGHTH": "BROCADE_8"
        }
        mapped_brocade_type = brocade_mapping.get(brocade_type, "BROCADE_1")
        
        # Find session
        if session_id not in pi_service.active_sessions:
            raise HTTPException(status_code=404, detail="Live session not found")
        
        session_data = pi_service.active_sessions[session_id]
        db_session_id = session_data["db_id"]
        
        # Find database record
        db_session = db.query(VideoUpload).filter(
            VideoUpload.id == db_session_id,
            VideoUpload.user_id == current_user.id
        ).first()
        
        if not db_session:
            raise HTTPException(status_code=404, detail="Session record not found")
        
        # Update record
        db_session.title = title
        db_session.description = description
        db_session.brocade_type = mapped_brocade_type
        
        if has_video_file and video_filename:
            # Find transferred video file
            local_path = None
            for transfer_file, transfer_info in pi_service.transfer_queue.items():
                if (transfer_info.get("status") == "completed" and 
                    transfer_info.get("user_id") == current_user.id and
                    video_filename in str(transfer_info.get("local_path", ""))):
                    local_path = transfer_info["local_path"]
                    break
            
            if local_path and Path(local_path).exists():
                db_session.video_path = str(local_path)
                db_session.processing_status = "completed"
                print(f"✅ Session saved with video file: {local_path}")
            else:
                db_session.video_path = f"TRANSFER_FAILED_{video_filename}"
                db_session.processing_status = "live_completed"
                print(f"⚠️ Video transfer failed, saving metadata only")
        else:
            # Metadata only
            session_duration = datetime.now() - session_data.get("start_time", datetime.now())
            db_session.video_path = f"LIVE_SESSION_STREAM_ONLY_{db_session_id}_{session_duration.total_seconds():.0f}s"
            db_session.processing_status = "live_completed"
            print(f"✅ Session saved as streaming metadata only")
        
        db.commit()
        db.refresh(db_session)
        
        # Clean up
        if session_id in pi_service.active_sessions:
            del pi_service.active_sessions[session_id]
        
        return {
            "status": "success",
            "video_id": db_session_id,
            "message": "Live session saved successfully",
            "title": title,
            "brocade_type": brocade_type,
            "has_video_file": has_video_file,
            "video_filename": video_filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error saving live session: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save session: {str(e)}")

@router.get("/current-pose")
async def get_current_pose(current_user: User = Depends(get_current_user)):
    """Get current pose data from Pi"""
    pose_data = await pi_service.get_pi_pose_data()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "user_id": current_user.id,
        "pose_data": pose_data.get("pose_data", []),
        "success": "error" not in pose_data
    }

@router.get("/active-sessions")
async def get_active_sessions(current_user: User = Depends(get_current_user)):
    """Get active sessions for current user"""
    
    user_sessions = {
        session_id: data for session_id, data in pi_service.active_sessions.items()
        if data["user_id"] == current_user.id
    }
    
    return {
        "active_sessions": len(user_sessions),
        "sessions": [
            {
                "session_id": session_id,
                "db_id": data["db_id"],
                "start_time": data["start_time"].isoformat(),
                "duration": str(datetime.now() - data["start_time"]),
                "status": data["status"],
                "recording_files": data.get("recording_files", [])
            }
            for session_id, data in user_sessions.items()
        ]
    }

@router.get("/session-history")
async def get_session_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's live session history"""
    
    # Try both LIVE_SESSION and fallback with [LIVE] prefix
    live_sessions = db.query(VideoUpload).filter(
        VideoUpload.user_id == current_user.id,
        ((VideoUpload.brocade_type == "LIVE_SESSION") | 
         (VideoUpload.title.like("[LIVE]%")))
    ).order_by(VideoUpload.upload_timestamp.desc()).limit(20).all()
    
    return {
        "total_sessions": len(live_sessions),
        "sessions": [
            {
                "id": session.id,
                "title": session.title,
                "timestamp": session.upload_timestamp.isoformat(),
                "status": session.processing_status,
                "description": session.description,
                "has_video_file": session.video_path and not session.video_path.startswith("LIVE_SESSION")
            }
            for session in live_sessions
        ]
    }


@router.post("/start-session-debug")
async def start_live_session_debug(
    session_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Debug version of start session - bypasses Pi communication"""
    
    try:
        session_name = session_data.get("session_name", "Debug Live Session")
        
        # CREATE SESSION RECORD (without Pi communication)
        session_record = VideoUpload(
            user_id=current_user.id,
            title=f"[DEBUG] {session_name}",
            description="Debug live session - Pi communication bypassed",
            brocade_type="FIRST",
            video_path="",
            processing_status="live_active",
            upload_timestamp=datetime.now()
        )
        
        db.add(session_record)
        db.commit()
        db.refresh(session_record)
        
        # Create session ID
        pi_session_id = f"debug_{session_record.id}"
        
        # Track session in memory
        pi_service.active_sessions[pi_session_id] = {
            "db_id": session_record.id,
            "user_id": current_user.id,
            "start_time": datetime.now(),
            "session_name": session_name,
            "status": "active",
            "recording_files": []
        }
        
        print(f"🔍 Debug session created: {pi_session_id}")
        
        return {
            "success": True,
            "session_id": pi_session_id,
            "db_session_id": session_record.id,
            "message": "Debug session started (Pi bypassed)",
            "pi_status": {"success": True, "debug": True},
            "websocket_url": PI_WEBSOCKET_URL,
            "session_name": session_name,
            "start_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Debug session error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Debug session failed: {str(e)}")
    
@router.get("/test-pi-connection")
async def test_pi_connection_detailed():
    """Detailed Pi connection test for debugging ngrok issues"""
    
    test_results = {
        "timestamp": datetime.now().isoformat(),
        "tests": {}
    }
    
    # Test 1: Basic connectivity
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://mongoose-hardy-caiman.ngrok-free.app/api/health",
                headers={'ngrok-skip-browser-warning': 'true'}
            )
            test_results["tests"]["basic_connectivity"] = {
                "status": "pass" if response.status_code == 200 else "fail",
                "http_code": response.status_code,
                "response_time_ms": response.elapsed.total_seconds() * 1000
            }
    except Exception as e:
        test_results["tests"]["basic_connectivity"] = {
            "status": "fail",
            "error": str(e)
        }
    
    # Test 2: Status endpoint
    try:
        status_result = await pi_service.check_pi_status()
        test_results["tests"]["status_endpoint"] = {
            "status": "pass" if status_result["connected"] else "fail",
            "pi_running": status_result.get("data", {}).get("is_running", False),
            "camera_available": status_result.get("data", {}).get("camera_available", False)
        }
    except Exception as e:
        test_results["tests"]["status_endpoint"] = {
            "status": "fail",
            "error": str(e)
        }
    
    # Test 3: Recordings list
    try:
        recordings_result = await pi_service.get_pi_recordings()
        test_results["tests"]["recordings_endpoint"] = {
            "status": "pass" if recordings_result.get("success") else "fail",
            "recordings_count": len(recordings_result.get("recordings", []))
        }
    except Exception as e:
        test_results["tests"]["recordings_endpoint"] = {
            "status": "fail",
            "error": str(e)
        }
    
    return test_results

async def transfer_file_background_enhanced(filename: str, local_path: Path, user_id: int):
    """Enhanced background transfer with better error handling and logging"""
    try:
        print(f"🚀 Starting enhanced background transfer: {filename}")
        
        # Update status
        pi_service.transfer_queue[filename]["status"] = "downloading"
        pi_service.transfer_queue[filename]["progress"] = "Initializing download..."
        
        # Check Pi file status first
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                status_url = f"https://mongoose-hardy-caiman.ngrok-free.app/api/download-status/{filename}"
                status_response = await client.get(status_url, headers={
                    'ngrok-skip-browser-warning': 'true'
                })
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data.get("exists"):
                        expected_size = status_data.get("size", 0)
                        pi_service.transfer_queue[filename]["expected_size"] = expected_size
                        pi_service.transfer_queue[filename]["progress"] = f"File verified on Pi ({expected_size:,} bytes)"
                        print(f"✅ File verified on Pi: {filename} ({expected_size:,} bytes)")
                    else:
                        raise Exception("File does not exist on Pi")
                else:
                    raise Exception(f"Pi status check failed: HTTP {status_response.status_code}")
                    
        except Exception as status_error:
            error_msg = f"Pi file verification failed: {status_error}"
            pi_service.transfer_queue[filename].update({
                "status": "failed",
                "error": error_msg,
                "completion_time": datetime.now()
            })
            print(f"❌ {error_msg}")
            return
        
        # Perform download
        pi_service.transfer_queue[filename]["progress"] = "Downloading from Pi..."
        result = await pi_service.download_pi_recording(filename, local_path)
        
        if result["success"]:
            pi_service.transfer_queue[filename].update({
                "status": "completed",
                "size": result["size"],
                "completion_time": datetime.now(),
                "progress": f"Transfer completed ({result['size']:,} bytes)",
                "download_method": result.get("download_method", "unknown")
            })
            print(f"✅ Enhanced transfer completed: {filename} -> {local_path} ({result['size']:,} bytes)")
        else:
            pi_service.transfer_queue[filename].update({
                "status": "failed",
                "error": result["error"],
                "completion_time": datetime.now(),
                "progress": f"Transfer failed: {result['error']}"
            })
            print(f"❌ Enhanced transfer failed: {filename} - {result['error']}")
            
    except Exception as e:
        error_msg = f"Background transfer exception: {str(e)}"
        pi_service.transfer_queue[filename].update({
            "status": "failed",
            "error": error_msg,
            "completion_time": datetime.now(),
            "progress": f"Exception occurred: {error_msg}"
        })
        print(f"❌ {error_msg}")

@router.get("/current-frame")
async def get_current_frame(current_user: User = Depends(get_current_user)):
    """Get current video frame from Pi for live streaming"""
    
    try:
        # Check if Pi is connected
        pi_status = await pi_service.check_pi_status()
        if not pi_status["connected"]:
            return {
                "success": False,
                "error": "Pi not connected",
                "pi_status": pi_status.get("error", "Unknown connection error")
            }
        
        # Get current frame from Pi
        headers = {
            'ngrok-skip-browser-warning': 'true',
            'User-Agent': 'Azure-Pi-Service/1.0',
            'Accept': 'application/json'
        }
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{PI_BASE_URL}/current_frame",  # This should match your Pi's endpoint
                headers=headers
            )
            
            if response.status_code == 200:
                frame_data = response.json()
                
                # Add timestamp and additional info
                return {
                    "success": True,
                    "image": frame_data.get("image"),
                    "timestamp": frame_data.get("timestamp", datetime.now().timestamp() * 1000),
                    "stats": {
                        "current_fps": frame_data.get("fps", 0),
                        "persons_detected": frame_data.get("persons_detected", 0),
                        "processing_time": frame_data.get("processing_time", 0)
                    },
                    "pose_data": frame_data.get("pose_data", []),
                    "is_recording": frame_data.get("is_recording", False),
                    "pi_timestamp": frame_data.get("timestamp"),
                    "server_timestamp": datetime.now().timestamp() * 1000
                }
            else:
                error_text = await response.atext()
                return {
                    "success": False,
                    "error": f"Pi returned HTTP {response.status_code}: {error_text[:200]}"
                }
                
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Pi frame timeout - mobile network may be slow",
            "suggestion": "Check mobile network connection"
        }
    except httpx.ConnectError:
        return {
            "success": False,
            "error": "Cannot reach Pi - ngrok tunnel may be down",
            "suggestion": "Verify ngrok tunnel is running on Pi"
        }
    except Exception as e:
        print(f"❌ Frame fetch error: {str(e)}")
        return {
            "success": False,
            "error": f"Frame fetch failed: {str(e)}"
        }

# Also add this enhanced method to the EnhancedPiService class
async def get_pi_current_frame(self) -> Dict[str, Any]:
    """Get current video frame from Pi"""
    try:
        headers = {
            'ngrok-skip-browser-warning': 'true',
            'User-Agent': 'Azure-Pi-Service/1.0',
            'Accept': 'application/json'
        }
        
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(
                f"{PI_BASE_URL}/current_frame",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
    
# Real time feedback control API endpoints
@router.get("/baduanjin/exercises")
async def get_exercises_via_azure(current_user: User = Depends(get_current_user)):
    """Get Baduanjin exercises via Azure service"""
    try:
        headers = {
            'ngrok-skip-browser-warning': 'true',
            'User-Agent': 'Azure-Pi-Service/1.0'
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{PI_BASE_URL}/baduanjin/exercises", headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"Pi returned HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/baduanjin/start/{exercise_id}")
async def start_exercise_via_azure(
    exercise_id: int,
    current_user: User = Depends(get_current_user)
):
    """Start exercise tracking via Azure service"""
    try:
        headers = {
            'ngrok-skip-browser-warning': 'true',
            'User-Agent': 'Azure-Pi-Service/1.0'
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{PI_BASE_URL}/baduanjin/start/{exercise_id}", headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"Pi returned HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/baduanjin/feedback")
async def get_feedback_via_azure(current_user: User = Depends(get_current_user)):
    """Get real-time feedback via Azure service"""
    try:
        headers = {
            'ngrok-skip-browser-warning': 'true',
            'User-Agent': 'Azure-Pi-Service/1.0'
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{PI_BASE_URL}/baduanjin/feedback", headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"Pi returned HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/baduanjin/stop")
async def stop_exercise_via_azure(current_user: User = Depends(get_current_user)):
    """Stop exercise tracking via Azure service"""
    try:
        headers = {
            'ngrok-skip-browser-warning': 'true',
            'User-Agent': 'Azure-Pi-Service/1.0'
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{PI_BASE_URL}/baduanjin/stop", headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"Pi returned HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/baduanjin/status")
async def get_exercise_status_via_azure(current_user: User = Depends(get_current_user)):
    """Get exercise tracking status via Azure service"""
    try:
        headers = {
            'ngrok-skip-browser-warning': 'true',
            'User-Agent': 'Azure-Pi-Service/1.0'
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{PI_BASE_URL}/baduanjin/status", headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"Pi returned HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}