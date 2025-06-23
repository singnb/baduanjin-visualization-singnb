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
PI_BASE_URL = "https://25de-122-11-245-27.ngrok-free.app/api"
PI_WEBSOCKET_URL = "wss://25de-122-11-245-27.ngrok-free.app"

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
        """Check if Pi is available and get status - FAST RESPONSE"""
        try:
            # Reduce timeout to 3 seconds for faster response
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{PI_BASE_URL}/status")
                return {"connected": True, "data": response.json()}
        except httpx.TimeoutException:
            return {
                "connected": False, 
                "error": "Pi connection timeout - Pi may be offline",
                "pi_ip": "172.20.10.5:5001"
            }
        except httpx.ConnectError:
            return {
                "connected": False, 
                "error": "Cannot reach Pi - check network connection",
                "pi_ip": "172.20.10.5:5001"
            }
        except Exception as e:
            return {
                "connected": False, 
                "error": f"Pi connection error: {str(e)}",
                "pi_ip": "172.20.10.5:5001"
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
        """Download recording from Pi to local storage - ROBUST VERSION"""
        try:
            pi_download_url = f"http://172.20.10.5:5001/api/download/{filename}"
            print(f"🔄 Starting download: {filename} from {pi_download_url}")
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Method 1: Try streaming with modern httpx
                try:
                    async with client.stream('GET', pi_download_url) as response:
                        response.raise_for_status()
                        
                        print(f"📡 Stream opened, status: {response.status_code}")
                        total_size = 0
                        
                        # Write file in chunks - Compatible with different httpx versions
                        async with aiofiles.open(local_path, 'wb') as f:
                            try:
                                # Try with chunk size parameter (newer httpx)
                                async for chunk in response.aiter_bytes(8192):
                                    await f.write(chunk)
                                    total_size += len(chunk)
                            except TypeError:
                                # Fallback for older httpx - no chunk size parameter
                                print("📡 Using fallback streaming method...")
                                async for chunk in response.aiter_bytes():
                                    await f.write(chunk)
                                    total_size += len(chunk)
                        
                        print(f"✅ Downloaded {total_size} bytes")
                        
                except Exception as stream_error:
                    print(f"⚠️ Streaming failed: {stream_error}, trying direct download...")
                    
                    # Method 2: Fallback to direct download
                    response = await client.get(pi_download_url)
                    response.raise_for_status()
                    
                    async with aiofiles.open(local_path, 'wb') as f:
                        await f.write(response.content)
                    
                    print(f"✅ Direct download completed: {len(response.content)} bytes")
            
            # Verify file was downloaded
            if local_path.exists() and local_path.stat().st_size > 0:
                file_size = local_path.stat().st_size
                print(f"✅ File verification passed: {file_size} bytes")
                
                return {
                    "success": True, 
                    "filename": filename,
                    "local_path": str(local_path),
                    "size": file_size
                }
            else:
                error_msg = "Downloaded file is empty or missing"
                print(f"❌ File verification failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except httpx.HTTPStatusError as http_error:
            error_msg = f"HTTP error {http_error.response.status_code}: {http_error.response.text}"
            print(f"❌ HTTP error: {error_msg}")
            return {"success": False, "error": error_msg}
            
        except httpx.TimeoutException:
            error_msg = "Download timeout - file might be too large or network is slow"
            print(f"❌ Timeout error: {error_msg}")
            return {"success": False, "error": error_msg}
            
        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            print(f"❌ General error: {error_msg}")
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
    
    result = await pi_service.get_pi_recordings()
    
    if result.get("success"):
        return {
            "success": True,
            "recordings": result.get("recordings", []),
            "count": len(result.get("recordings", []))
        }
    else:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get recordings: {result.get('error', 'Unknown error')}"
        )

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
async def get_transfer_status(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """Get transfer status for a file"""
    
    if filename not in pi_service.transfer_queue:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    transfer_info = pi_service.transfer_queue[filename]
    
    if transfer_info["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return {
        "filename": filename,
        "status": transfer_info["status"],
        "start_time": transfer_info["start_time"].isoformat(),
        "size": transfer_info.get("size"),
        "error": transfer_info.get("error"),
        "completion_time": transfer_info.get("completion_time").isoformat() if transfer_info.get("completion_time") else None
    }

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