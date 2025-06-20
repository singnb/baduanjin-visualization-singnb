# routers/video.py

import os
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, BackgroundTasks, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import models
import database
from auth.router import get_current_user

# For Azure Testing Deployment 
from azure_services import azure_blob_service
from azure.storage.blob import BlobServiceClient
from config import settings
import io
import json
from datetime import datetime

router = APIRouter(
    prefix="/api/videos",
    tags=["videos"]
)

# Define the upload directory
UPLOAD_DIR = "uploads/videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def map_brocade_type(frontend_type):
    """
    Maps frontend brocade types to database values
    """
    mapping = {
        "FIRST": "BROCADE_1",
        "SECOND": "BROCADE_2",
        "THIRD": "BROCADE_3",
        "FOURTH": "BROCADE_4",
        "FIFTH": "BROCADE_5",
        "SIXTH": "BROCADE_6",
        "SEVENTH": "BROCADE_7",
        "EIGHTH": "BROCADE_8"
    }
    
    return mapping.get(frontend_type, "BROCADE_1")

@router.get("")
async def get_videos(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Get all videos for the current user (excluding deleted ones)
    """
    videos = db.query(models.VideoUpload).filter(
        models.VideoUpload.user_id == current_user.id,
        models.VideoUpload.processing_status != "deleted"
    ).order_by(models.VideoUpload.upload_timestamp.desc()).all()
    
    return videos

# get_video endpoint to allow learners to view master's videos
@router.get("/{video_id}")
async def get_video(
    video_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Get details for a specific video (Enhanced with English audio info)
    Allow masters to view their learners' videos
    """
    # Find the video
    video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == video_id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check access permissions (keep existing logic)
    has_access = False
    
    if video.user_id == current_user.id:
        has_access = True
    else:
        if current_user.role == models.UserRole.MASTER:
            relationship = db.query(models.MasterLearnerRelationship).filter(
                models.MasterLearnerRelationship.master_id == current_user.id,
                models.MasterLearnerRelationship.learner_id == video.user_id,
                models.MasterLearnerRelationship.status == "accepted"
            ).first()
            
            if relationship:
                has_access = True
                
        elif current_user.role == models.UserRole.LEARNER:
            video_owner = db.query(models.User).filter(
                models.User.id == video.user_id
            ).first()
            
            if video_owner and video_owner.role == models.UserRole.MASTER:
                has_access = True
    
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Convert video object to dict and add extra fields
    video_dict = {
        "id": video.id,
        "title": video.title,
        "description": video.description,
        "user_id": video.user_id,
        "video_path": video.video_path,
        "analyzed_video_path": getattr(video, 'analyzed_video_path', None),
        "video_uuid": getattr(video, 'video_uuid', None),
        "brocade_type": getattr(video, 'brocade_type', None),
        "processing_status": video.processing_status,
        "upload_timestamp": video.upload_timestamp,
        "keypoints_path": getattr(video, 'keypoints_path', None)
    }
    
    return video_dict

@router.get("/{video_id}/has-english-audio")
async def check_english_audio(
    video_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """Check if a video has an English audio version available"""
    
    # Get video details first
    video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == video_id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check access permissions (same logic as existing get_video endpoint)
    has_access = False
    
    if video.user_id == current_user.id:
        has_access = True
    else:
        if current_user.role == models.UserRole.MASTER:
            relationship = db.query(models.MasterLearnerRelationship).filter(
                models.MasterLearnerRelationship.master_id == current_user.id,
                models.MasterLearnerRelationship.learner_id == video.user_id,
                models.MasterLearnerRelationship.status == "accepted"
            ).first()
            if relationship:
                has_access = True
                
        elif current_user.role == models.UserRole.LEARNER:
            video_owner = db.query(models.User).filter(
                models.User.id == video.user_id
            ).first()
            if video_owner and video_owner.role == models.UserRole.MASTER:
                relationship = db.query(models.MasterLearnerRelationship).filter(
                    models.MasterLearnerRelationship.master_id == video.user_id,
                    models.MasterLearnerRelationship.learner_id == current_user.id,
                    models.MasterLearnerRelationship.status == "accepted"
                ).first()
                if relationship:
                    has_access = True
    
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check for English audio file
    has_english_audio = False
    english_audio_path = None
    
    try:
        # Method 1: Check if video has english_audio_path field (if it exists in your model)
        if hasattr(video, 'english_audio_path') and video.english_audio_path:
            has_english_audio = True
            english_audio_path = video.english_audio_path
            print(f"Found English audio path in database: {english_audio_path}")
        
        # Method 2: Check in outputs_json directory for English audio files
        if not has_english_audio:
            from pathlib import Path
            base_path = Path("outputs_json") / str(video.user_id) / str(video.id)
            
            # Try different possible English audio file patterns
            possible_patterns = [
                "*_english.mp4",
                "english.mp4",
                "*english*.mp4"
            ]
            
            for pattern in possible_patterns:
                english_files = list(base_path.glob(pattern))
                if english_files:
                    has_english_audio = True
                    english_audio_path = str(english_files[0])
                    print(f"Found English audio file: {english_audio_path}")
                    break
        
        # Method 3: Check Azure blob storage pattern
        if not has_english_audio and hasattr(video, 'video_uuid') and video.video_uuid:
            # Construct potential Azure URL for English audio
            azure_path = f"https://baduanjintesting.blob.core.windows.net/videos/outputs_json/{video.user_id}/{video.id}/{video.video_uuid}_english.mp4"
            
            # For now, assume it exists if we can construct the path
            # The frontend will verify if it actually loads
            has_english_audio = True
            english_audio_path = azure_path
            print(f"Constructed Azure English audio path: {azure_path}")
        
        # Method 4: Fallback - check if we have video_uuid and construct standard path
        if not has_english_audio:
            # Try to extract UUID from video_path or use a standard pattern
            video_path = video.video_path
            if video_path and "outputs_json" in video_path:
                # Try to find English version in the same directory
                import os
                video_dir = os.path.dirname(video_path)
                base_name = os.path.splitext(os.path.basename(video_path))[0]
                
                # Try common English audio naming patterns
                possible_english_paths = [
                    os.path.join(video_dir, f"{base_name}_english.mp4"),
                    os.path.join(video_dir, "english.mp4"),
                ]
                
                for eng_path in possible_english_paths:
                    if os.path.exists(eng_path):
                        has_english_audio = True
                        english_audio_path = eng_path
                        print(f"Found English audio at: {eng_path}")
                        break
    
    except Exception as e:
        print(f"Error checking English audio for video {video_id}: {str(e)}")
        # Return False if we can't determine
        has_english_audio = False
    
    return {
        "has_english_audio": has_english_audio,
        "english_audio_path": english_audio_path,
        "video_id": video_id,
        "video_uuid": getattr(video, 'video_uuid', None)
    }


@router.post("/upload")
async def upload_video(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    brocade_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """Upload a video file to Azure Blob Storage"""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="File must be a video")
        
        # Read file content
        file_content = await file.read()
        
        # Check file size (limit to 100MB for now)
        max_size = 100 * 1024 * 1024  # 100MB
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Maximum size is {max_size // (1024*1024)}MB"
            )
        
        print(f"Uploading video: {file.filename}, size: {len(file_content)} bytes")
        
        # Upload to Azure Blob Storage
        try:
            from azure.storage.blob import BlobServiceClient
            import os
            import uuid
            
            # Get connection string
            connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            if not connection_string:
                raise Exception("Azure storage not configured")
            
            # Create blob service client
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            
            # Generate unique filename
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            blob_path = f"uploads/videos/{current_user.id}/{unique_filename}"
            
            # Upload to Azure
            blob_client = blob_service_client.get_blob_client(
                container="videos",
                blob=blob_path
            )
            
            blob_client.upload_blob(
                file_content,
                overwrite=True,
                content_type="video/mp4",
                metadata={
                    "original_filename": file.filename,
                    "user_id": str(current_user.id),
                    "upload_type": "video"
                }
            )
            
            # Get the blob URL
            blob_url = blob_client.url
            file_path = blob_url  # Store Azure URL as path
            storage_type = "azure_blob"
            
            print(f"Successfully uploaded to Azure: {blob_url}")
            
        except Exception as azure_error:
            print(f"Azure upload failed: {azure_error}")
            # Fallback to local storage (your existing logic)
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            UPLOAD_DIR = "uploads/videos"
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            user_dir = os.path.join(UPLOAD_DIR, str(current_user.id))
            os.makedirs(user_dir, exist_ok=True)
            file_path = os.path.join(user_dir, unique_filename)
            
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
            storage_type = "local_fallback"
            print(f"Fallback: Uploaded to local storage: {file_path}")
        
        # Map the frontend brocade type to database enum value
        mapped_brocade_type = map_brocade_type(brocade_type)
        
        # Create database record
        new_video = models.VideoUpload(
            user_id=current_user.id,
            title=title,
            description=description,
            brocade_type=mapped_brocade_type,
            video_path=file_path,  # Either Azure URL or local path
            processing_status="uploaded"
        )
        
        db.add(new_video)
        db.commit()
        db.refresh(new_video)
        
        print(f"Video record created with ID: {new_video.id}")
        
        return {
            "id": new_video.id,
            "title": new_video.title,
            "brocade_type": brocade_type,
            "processing_status": new_video.processing_status,
            "upload_timestamp": new_video.upload_timestamp,
            "storage_type": storage_type,
            "video_path": file_path,  # Include for debugging
            "message": f"Video uploaded successfully to {storage_type}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/{video_id}/analyze")
async def analyze_video(
    video_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Analyze a video using MMPose
    """
    video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == video_id,
        models.VideoUpload.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Set the video to "processing" status
    video.processing_status = "processing"
    db.commit()
    db.refresh(video)
    
    # Store necessary values for background task
    user_id = current_user.id
    video_path = video.video_path
    
    # Define background task function
    def process_video_analysis():
        try:
            # Create a new DB session for this background task
            task_db = database.SessionLocal()
            
            try:
                # Import here to avoid circular imports
                from ml_pipeline.pose_analyzer import analyze_video as run_analysis
                
                # Run the analysis
                result = run_analysis(video_path, user_id, video_id)
                
                # Update the database with results
                db_video = task_db.query(models.VideoUpload).filter(
                    models.VideoUpload.id == video_id
                ).first()
                
                if not db_video:
                    return
                    
                if result:
                    db_video.analyzed_video_path = result.get("analyzed_video_path", result.get("original_video"))
                    db_video.keypoints_path = result.get("keypoints_path", result.get("results_json"))
                    db_video.processing_status = "completed"
                else:
                    db_video.processing_status = "failed"
                    
                task_db.commit()
            except Exception as e:
                try:
                    db_video = task_db.query(models.VideoUpload).filter(
                        models.VideoUpload.id == video_id
                    ).first()
                    if db_video:
                        db_video.processing_status = "failed"
                        task_db.commit()
                except:
                    pass
            finally:
                task_db.close()
        except Exception as e:
            print(f"Background task error: {str(e)}")
    
    # Add the task
    background_tasks.add_task(process_video_analysis)
    
    return {"message": "Analysis started successfully"}

# stream_converted_video endpoint to allow learners to view master's videos
@router.get("/{video_id}/stream-video")
async def stream_specific_video(
    video_id: int,
    type: str = Query("original"),
    token: str = Query(None),
    db: Session = Depends(database.get_db)
):
    """Stream video with support for both Azure Blob Storage and local files"""
    if not token:
        raise HTTPException(status_code=401, detail="Authentication token required")
    
    try:
        # JWT token decoding (keep your existing logic)
        import base64
        import json
        
        token_parts = token.split('.')
        if len(token_parts) != 3:
            raise HTTPException(status_code=401, detail="Invalid token format")
        
        payload_part = token_parts[1]
        padding = '=' * (4 - len(payload_part) % 4) if len(payload_part) % 4 else ''
        payload_part += padding
        
        decoded_bytes = base64.urlsafe_b64decode(payload_part)
        payload = json.loads(decoded_bytes)
        
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token missing user_id claim")
        
        current_user = db.query(models.User).filter(models.User.id == user_id).first()
        if current_user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Get video and check access (keep your existing access control logic)
        video = db.query(models.VideoUpload).filter(
            models.VideoUpload.id == video_id
        ).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Access control logic (keep your existing logic exactly)
        has_access = False
        if video.user_id == current_user.id:
            has_access = True
        elif current_user.role == models.UserRole.MASTER:
            relationship = db.query(models.MasterLearnerRelationship).filter(
                models.MasterLearnerRelationship.master_id == current_user.id,
                models.MasterLearnerRelationship.learner_id == video.user_id,
                models.MasterLearnerRelationship.status == "accepted"
            ).first()
            if relationship:
                has_access = True
        elif current_user.role == models.UserRole.LEARNER:
            video_owner = db.query(models.User).filter(
                models.User.id == video.user_id
            ).first()
            if video_owner and video_owner.role == models.UserRole.MASTER:
                relationship = db.query(models.MasterLearnerRelationship).filter(
                    models.MasterLearnerRelationship.master_id == video.user_id,
                    models.MasterLearnerRelationship.learner_id == current_user.id,
                    models.MasterLearnerRelationship.status == "accepted"
                ).first()
                if relationship:
                    has_access = True
        
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Determine which video to stream (keep your existing logic)
        video_path = None
        
        if type == "original":
            video_path = video.video_path
            print(f"Streaming original video: {video_path}")
            
        elif type == "english":
            # Enhanced English audio handling
            english_path = None
            
            # Method 1: Check if video has english_audio_path field
            if hasattr(video, 'english_audio_path') and video.english_audio_path:
                english_path = video.english_audio_path
                print(f"Using database English audio path: {english_path}")
            
            # Method 2: Look in outputs directory
            if not english_path:
                from pathlib import Path
                base_path = Path("outputs_json") / str(video.user_id) / str(video_id)
                
                if base_path.exists():
                    # Try different English audio patterns
                    english_patterns = ["*_english.mp4", "english.mp4", "*english*.mp4"]
                    for pattern in english_patterns:
                        english_files = list(base_path.glob(pattern))
                        if english_files:
                            english_path = str(english_files[0])
                            print(f"Found English audio in outputs: {english_path}")
                            break
            
            # Method 3: Construct Azure URL if we have video_uuid
            if not english_path and hasattr(video, 'video_uuid') and video.video_uuid:
                english_path = f"https://baduanjintesting.blob.core.windows.net/videos/outputs_json/{video.user_id}/{video_id}/{video.video_uuid}_english.mp4"
                print(f"Constructed Azure English audio URL: {english_path}")
            
            # Method 4: Try to construct based on original video path
            if not english_path and video.video_path:
                import os
                video_dir = os.path.dirname(video.video_path) if not video.video_path.startswith('http') else None
                
                if video_dir:
                    base_name = os.path.splitext(os.path.basename(video.video_path))[0]
                    potential_english = os.path.join(video_dir, f"{base_name}_english.mp4")
                    
                    if os.path.exists(potential_english):
                        english_path = potential_english
                        print(f"Found English audio based on original path: {english_path}")
            
            if english_path:
                video_path = english_path
                print(f"Streaming English audio version: {video_path}")
            else:
                print(f"English audio version not found for video {video_id}")
                raise HTTPException(status_code=404, detail="English audio version not found")
            
        elif type == "analyzed":
            if video.analyzed_video_path:
                video_path = video.analyzed_video_path
                print(f"Streaming analyzed version: {video_path}")
            else:
                # Fallback logic for outputs directory (keep your existing logic)
                outputs_dir = os.path.join("outputs_json", str(video.user_id), str(video_id))
                print(f"Looking for analyzed video in outputs directory: {outputs_dir}")
                
                if os.path.exists(outputs_dir):
                    mp4_files = [f for f in os.listdir(outputs_dir) if f.endswith('.mp4')]
                    for file in mp4_files:
                        if '_web.mp4' in file:
                            video_path = os.path.join(outputs_dir, file)
                            print(f"Found analyzed video in outputs: {video_path}")
                            break
                
                if not video_path:
                    video_path = video.video_path  # Fallback to original
                    print(f"Analyzed video not found, falling back to original: {video_path}")
        else:
            raise HTTPException(status_code=400, detail=f"Invalid video type: {type}")
        
        if not video_path:
            raise HTTPException(status_code=404, detail="Video path not found")
        
        # Helper function to check if path is Azure URL
        def is_azure_url(path: str) -> bool:
            return (
                isinstance(path, str) and 
                path.startswith('https://') and 
                '.blob.core.windows.net' in path
            )
        
        if is_azure_url(video_path):
            # Stream from Azure Blob Storage with your nested structure
            try:
                connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
                if not connection_string:
                    raise HTTPException(status_code=500, detail="Azure storage not configured")
                
                blob_service_client = BlobServiceClient.from_connection_string(connection_string)
                
                # Parse the Azure URL to determine container and blob path
                if "blob.core.windows.net/videos/" in video_path:
                    container_name = "videos"
                    blob_name = video_path.split("blob.core.windows.net/videos/")[-1]
                elif "blob.core.windows.net/results/" in video_path:
                    container_name = "results"
                    blob_name = video_path.split("blob.core.windows.net/results/")[-1]
                else:
                    raise HTTPException(status_code=400, detail="Invalid Azure URL format")
                
                print(f"Streaming from Azure: container='{container_name}', blob='{blob_name}'")
                
                # Download from appropriate container
                blob_client = blob_service_client.get_blob_client(
                    container=container_name,
                    blob=blob_name
                )
                
                # Get blob properties to determine content type
                blob_properties = blob_client.get_blob_properties()
                content_type = blob_properties.content_settings.content_type or "application/octet-stream"
                
                # Override content type based on file extension if not set properly
                if blob_name.endswith('.mp4'):
                    content_type = "video/mp4"
                elif blob_name.endswith('.json'):
                    content_type = "application/json"
                elif blob_name.endswith('.png'):
                    content_type = "image/png"
                elif blob_name.endswith('.txt'):
                    content_type = "text/plain"
                
                # Download content
                content = blob_client.download_blob().readall()
                print(f"Successfully downloaded from Azure: {len(content)} bytes, type: {content_type}")
                
                # Set appropriate headers based on content type
                headers = {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Range, Content-Range, Content-Length"
                }
                
                if content_type.startswith("video/"):
                    headers.update({
                        "Accept-Ranges": "bytes",
                        "Content-Disposition": "inline",
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Pragma": "no-cache",
                        "Expires": "0"
                    })
                elif content_type.startswith("image/"):
                    headers.update({
                        "Cache-Control": "public, max-age=3600",
                        "Content-Disposition": "inline"
                    })
                elif content_type == "application/json":
                    headers.update({
                        "Cache-Control": "public, max-age=300",
                        "Content-Disposition": "inline"
                    })
                
                # Stream the content
                return StreamingResponse(
                    io.BytesIO(content),
                    media_type=content_type,
                    headers=headers
                )
                
            except Exception as azure_error:
                print(f"Error streaming from Azure: {azure_error}")
                print(f"Failed URL: {video_path}")
                print(f"Attempted container: {container_name if 'container_name' in locals() else 'unknown'}")
                print(f"Attempted blob: {blob_name if 'blob_name' in locals() else 'unknown'}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Error accessing content from Azure storage: {str(azure_error)}"
                )
        else:
            # Handle local files (backward compatibility)
            if not os.path.exists(video_path):
                # Try alternative paths (keep your existing logic)
                print(f"Video file not found: {video_path}")
                alt_paths = [
                    os.path.join("/home/site/wwwroot", video_path),
                    video_path.replace("uploads/", "/home/site/wwwroot/uploads/")
                ]
                
                found_path = None
                for alt_path in alt_paths:
                    if os.path.exists(alt_path):
                        found_path = alt_path
                        print(f"Found video at alternative path: {alt_path}")
                        break
                
                if found_path:
                    video_path = found_path
                else:
                    raise HTTPException(status_code=404, detail=f"Video file not found: {video_path}")
            
            # Stream local file
            print(f"Successfully found local video file: {video_path}")
            return FileResponse(
                video_path,
                media_type="video/mp4",
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Disposition": "inline",
                    "Cache-Control": "no-cache",
                    "Access-Control-Allow-Origin": "*"
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in stream_specific_video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@router.delete("/{video_id}")
async def delete_video(
    video_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Delete a video and all associated files
    """
    video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == video_id,
        models.VideoUpload.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Store paths before deleting
    files_to_delete = []
    
    if video.video_path and os.path.exists(video.video_path):
        files_to_delete.append(video.video_path)
    
    if video.analyzed_video_path and video.analyzed_video_path != video.video_path:
        if os.path.exists(video.analyzed_video_path):
            files_to_delete.append(video.analyzed_video_path)
    
    # Get outputs directory
    outputs_dir = os.path.join("outputs_json", str(current_user.id), str(video_id))
    
    # Delete from database
    try:
        db.delete(video)
        db.commit()
    except Exception as e:
        db.rollback()
        try:
            # Use text() for raw SQL
            db.execute(
                text("DELETE FROM keypoint_data WHERE video_id = :video_id"),
                {"video_id": video_id}
            )
            db.execute(
                text("DELETE FROM video_uploads WHERE id = :video_id"),
                {"video_id": video_id}
            )
            db.commit()
        except:
            db.rollback()
            video.processing_status = "deleted"
            db.commit()
    
    # Delete files
    for file_path in files_to_delete:
        try:
            os.remove(file_path)
        except:
            pass
    
    # Delete outputs directory
    if os.path.exists(outputs_dir):
        try:
            import shutil
            shutil.rmtree(outputs_dir)
        except:
            pass
    
    # Clean up empty directories
    user_upload_dir = os.path.join("uploads", "videos", str(current_user.id))
    if os.path.exists(user_upload_dir):
        try:
            if not os.listdir(user_upload_dir):
                os.rmdir(user_upload_dir)
        except:
            pass
    
    return {
        "message": "Video deleted successfully",
        "video_id": video_id
    }

@router.post("/{video_id}/reset-status")
async def reset_video_processing_status(
    video_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """Reset a video's processing status to 'uploaded' when it gets stuck"""
    
    # Verify video ownership
    video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == video_id,
        models.VideoUpload.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Reset the status to 'uploaded' if it's 'processing'
    if video.processing_status == "processing":
        video.processing_status = "uploaded"
        db.commit()
        db.refresh(video)
        
        return {
            "message": "Processing status reset successfully",
            "status": "uploaded"
        }
    else:
        return {
            "message": f"Video is not in 'processing' state. Current status: {video.processing_status}",
            "status": video.processing_status
        }

@router.post("/{video_id}/analyze-enhanced") 
async def analyze_video_enhanced(
    video_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Enhanced video analysis endpoint that properly updates status
    This should REPLACE one of your existing analyze endpoints
    """
    try:
        # Get video from database
        video = db.query(models.VideoUpload).filter(
            models.VideoUpload.id == video_id,
            models.VideoUpload.user_id == current_user.id
        ).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        if video.processing_status == "processing":
            raise HTTPException(status_code=400, detail="Video is already being processed")
        
        # Print debug info
        print(f"Starting enhanced analysis for video ID: {video_id}, current status: {video.processing_status}")
        
        # Set status to processing
        video.processing_status = "processing"
        db.commit()
        
        # Store necessary values for background task
        user_id = current_user.id
        video_path = video.video_path
        
        # Check if video file exists
        if not os.path.exists(video_path):
            print(f"ERROR: Video file not found: {video_path}")
            video.processing_status = "failed"
            db.commit()
            raise HTTPException(status_code=400, detail="Video file not found on server")
        
        # Enhanced background task function
        def process_video_analysis_enhanced():
            try:
                # Create a new DB session for this background task
                task_db = database.SessionLocal()
                
                try:
                    print(f"Starting enhanced video analysis task for ID: {video_id}")
                    # Import here to avoid circular imports
                    from ml_pipeline.pose_analyzer import analyze_video as run_analysis
                    
                    # Print path confirmation
                    print(f"Video path being analyzed: {video_path}")
                    
                    # Run the analysis
                    result = run_analysis(video_path, user_id, video_id)
                    
                    print(f"Analysis result for video {video_id}: {result}")
                    
                    # Update the database with results
                    db_video = task_db.query(models.VideoUpload).filter(
                        models.VideoUpload.id == video_id
                    ).first()
                    
                    if not db_video:
                        print(f"WARNING: Could not find video with ID {video_id} in database after analysis")
                        return
                        
                    if result:
                        # Use the paths from the analysis result
                        db_video.analyzed_video_path = result.get("analyzed_video_path", result.get("original_video"))
                        db_video.keypoints_path = result.get("keypoints_path", result.get("results_json"))
                        db_video.processing_status = "completed"  # FIXED: Ensure this is set
                        
                        print(f"Video {video_id} analysis completed successfully")
                        print(f"  - Analyzed video path: {db_video.analyzed_video_path}")
                        print(f"  - Keypoints path: {db_video.keypoints_path}")
                    else:
                        db_video.processing_status = "failed"
                        print(f"Video {video_id} analysis failed - no results returned")
                        
                    task_db.commit()
                    print(f"Database updated for video {video_id} with status: {db_video.processing_status}")
                    
                except Exception as e:
                    print(f"Error in enhanced analysis process for video {video_id}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    
                    try:
                        db_video = task_db.query(models.VideoUpload).filter(
                            models.VideoUpload.id == video_id
                        ).first()
                        if db_video:
                            db_video.processing_status = "failed"
                            task_db.commit()
                            print(f"Set video {video_id} status to failed due to exception")
                    except Exception as db_error:
                        print(f"Error updating video status after analysis exception: {str(db_error)}")
                finally:
                    task_db.close()
            except Exception as e:
                print(f"Enhanced background task error: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Add the enhanced task
        background_tasks.add_task(process_video_analysis_enhanced)
        print(f"Added enhanced video analysis background task for video {video_id}")
        
        return {
            "message": "Enhanced analysis started successfully",
            "video_id": video_id,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in enhanced video analysis: {e}")
        # Ensure status is reset on error
        try:
            video.processing_status = "failed"
            db.commit()
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{video_id}/check-completion")
async def check_video_completion(
    video_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Check if video analysis is actually complete by looking for output files
    """
    try:
        # Get video from database
        video = db.query(models.VideoUpload).filter(
            models.VideoUpload.id == video_id,
            models.VideoUpload.user_id == current_user.id
        ).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Check if analysis output files exist
        outputs_dir = os.path.join("outputs_json", str(current_user.id), str(video_id))
        
        # Look for required analysis files
        analysis_complete = False
        found_files = {}
        
        if os.path.exists(outputs_dir):
            try:
                all_files = os.listdir(outputs_dir)
                
                # Check for JSON results file
                json_files = [f for f in all_files if f.startswith('results_') and f.endswith('.json')]
                
                # Check for MP4 files (analyzed video)
                mp4_files = [f for f in all_files if f.endswith('.mp4')]
                
                # Check for specific web version
                web_files = [f for f in all_files if f.endswith('_web.mp4')]
                
                found_files = {
                    "json_files": json_files,
                    "mp4_files": mp4_files,
                    "web_files": web_files,
                    "total_files": len(all_files),
                    "all_files": all_files  # For debugging
                }
                
                # Analysis is complete if we have both JSON and MP4 files
                analysis_complete = len(json_files) > 0 and len(mp4_files) > 0
                
                print(f"Completion check for video {video_id}: JSON={len(json_files)}, MP4={len(mp4_files)}, Complete={analysis_complete}")
                
            except Exception as list_error:
                print(f"Error listing files in {outputs_dir}: {list_error}")
                found_files["error"] = str(list_error)
        
        return {
            "video_id": video_id,
            "completed": analysis_complete,
            "current_status": video.processing_status,
            "files_found": found_files,
            "outputs_dir_exists": os.path.exists(outputs_dir),
            "outputs_dir": outputs_dir,
            "database_paths": {
                "analyzed_video_path": video.analyzed_video_path,
                "keypoints_path": video.keypoints_path
            }
        }
        
    except Exception as e:
        print(f"Error checking completion for video {video_id}: {e}")
        return {
            "video_id": video_id,
            "completed": False,
            "error": str(e),
            "current_status": getattr(video, 'processing_status', 'unknown') if 'video' in locals() else 'unknown'
        }


@router.post("/{video_id}/force-complete")
async def force_mark_video_complete(
    video_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Force mark a video as completed if analysis files exist but status is stuck
    """
    try:
        # Get video from database
        video = db.query(models.VideoUpload).filter(
            models.VideoUpload.id == video_id,
            models.VideoUpload.user_id == current_user.id
        ).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Check if analysis files actually exist
        outputs_dir = os.path.join("outputs_json", str(current_user.id), str(video_id))
        
        if not os.path.exists(outputs_dir):
            raise HTTPException(status_code=400, detail="No analysis output directory found")
        
        # Look for analysis files
        try:
            all_files = os.listdir(outputs_dir)
            json_files = [f for f in all_files if f.startswith('results_') and f.endswith('.json')]
            mp4_files = [f for f in all_files if f.endswith('.mp4')]
            
            print(f"Force completion check - JSON files: {json_files}, MP4 files: {mp4_files}")
            
        except Exception as list_error:
            raise HTTPException(status_code=500, detail=f"Error accessing output directory: {str(list_error)}")
        
        if not json_files or not mp4_files:
            raise HTTPException(
                status_code=400, 
                detail=f"Analysis files incomplete. JSON files: {len(json_files)}, MP4 files: {len(mp4_files)}"
            )
        
        # Update video paths if not already set
        results_json = json_files[0]  # Use first JSON file
        analyzed_mp4 = mp4_files[0]   # Use first MP4 file
        
        # Build relative paths (consistent with your existing pattern)
        new_keypoints_path = f"outputs_json/{current_user.id}/{video_id}/{results_json}"
        new_analyzed_path = f"outputs_json/{current_user.id}/{video_id}/{analyzed_mp4}"
        
        # Update video record
        video.keypoints_path = new_keypoints_path
        video.analyzed_video_path = new_analyzed_path
        video.processing_status = "completed"
        
        # Commit changes
        try:
            db.commit()
            db.refresh(video)
            
            print(f"Successfully force marked video {video_id} as completed")
            print(f"  - Keypoints path: {new_keypoints_path}")
            print(f"  - Analyzed video path: {new_analyzed_path}")
            
        except Exception as commit_error:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Database update failed: {str(commit_error)}")
        
        return {
            "status": "completed",
            "message": "Video status updated to completed",
            "video_id": video_id,
            "analyzed_video_path": video.analyzed_video_path,
            "keypoints_path": video.keypoints_path,
            "files_found": {
                "json_files": json_files,
                "mp4_files": mp4_files
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error force completing video {video_id}: {e}")
        if 'db' in locals():
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating video status: {str(e)}")

# For Azure Testing Deployment 
@router.post("/upload-azure")
async def upload_video_azure(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Upload video to Azure for testing deployment
    In testing mode: returns mock analysis
    In production mode: uses your existing MMPose processing
    """
    try:
        # Validate file type
        if not file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="File must be a video")
        
        # Read file content
        file_content = await file.read()
        
        # Check file size (5MB limit for testing)
        if len(file_content) > 5 * 1024 * 1024:  # 5MB
            raise HTTPException(status_code=400, detail="File too large. Maximum 5MB allowed.")
        
        # Upload to Azure Blob Storage
        uploaded_filename = await azure_blob_service.upload_video(file_content, file.filename)
        
        # Check environment mode
        if settings.environment == "testing":
            # TESTING MODE - Return mock analysis (similar to your existing analysis format)
            mock_result = {
                "status": "processed",
                "original_filename": file.filename,
                "stored_filename": uploaded_filename,
                "upload_time": datetime.now().isoformat(),
                "file_size_mb": len(file_content) / (1024 * 1024),
                "analysis": {
                    "total_frames": 150,
                    "detected_poses": 145,
                    "confidence_avg": 0.87,
                    "pose_quality": "Good",
                    "baduanjin_movements": [
                        {"movement": "lifting_sky", "frames": [1, 30], "quality": "excellent"},
                        {"movement": "drawing_bow", "frames": [31, 60], "quality": "good"},
                        {"movement": "supporting_heaven", "frames": [61, 90], "quality": "good"}
                    ]
                },
                "keypoints": [
                    {
                        "frame": 1,
                        "timestamp": 0.033,
                        "pose_keypoints": [
                            {"joint": "nose", "x": 320, "y": 240, "confidence": 0.9},
                            {"joint": "left_shoulder", "x": 300, "y": 280, "confidence": 0.85},
                            {"joint": "right_shoulder", "x": 340, "y": 280, "confidence": 0.87}
                        ]
                    }
                ],
                "mock_mode": True,
                "note": "This is mock data for Azure testing. GPU processing is disabled."
            }
            
            # Save mock result to blob storage
            result_filename = await azure_blob_service.upload_result(mock_result, uploaded_filename)
            mock_result["result_file"] = result_filename
            
            return {
                "success": True,
                "message": "Video uploaded and analyzed (Azure testing mode)",
                "data": mock_result
            }
        
        else:
            # PRODUCTION MODE - This is where you'd call your existing video processing
            # You can integrate with your existing video processing logic here
            return {
                "success": True,
                "message": "Video uploaded to Azure successfully",
                "filename": uploaded_filename,
                "status": "pending_analysis",
                "note": "Production mode - will call your existing MMPose processing"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Azure upload failed: {str(e)}")

# Add health check endpoint for Azure deployment
@router.get("/health")
async def health_check():
    """Health check endpoint for Azure deployment"""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "azure_storage_configured": bool(settings.azure_storage_connection_string),
        "database_configured": bool(settings.database_url),
        "timestamp": datetime.now().isoformat()
    }

@router.get("/test/storage-final")
async def test_storage_complete():
    """Complete test of your Azure Storage setup"""
    import os
    from datetime import datetime
    from azure.storage.blob import BlobServiceClient
    
    # Your existing connection string
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = "videos"
    
    result = {
        "storage_account": "baduanjintesting",
        "container_name": container_name,
        "connection_string_configured": bool(connection_string),
        "tests": {},
        "recommendations": []
    }
    
    if not connection_string:
        result["error"] = "Connection string not found"
        return result
    
    try:
        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        result["tests"]["1_connection"] = "Connection established"
        
        # Check if videos container exists
        container_client = blob_service_client.get_container_client(container_name)
        container_exists = container_client.exists()
        result["tests"]["2_container_exists"] = f"Container exists: {container_exists}"
        
        if not container_exists:
            # Try to create the container
            try:
                container_client.create_container(public_access='blob')
                result["tests"]["3_container_created"] = "Created 'videos' container"
            except Exception as create_error:
                result["tests"]["3_container_creation"] = f"Failed to create container: {str(create_error)}"
                result["recommendations"].append("Manually create 'videos' container in Azure Portal")
        
        # Test upload a small file
        try:
            test_blob_name = f"test/connection_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            test_content = f"Storage test from {os.getenv('WEBSITE_SITE_NAME', 'web-app')} at {datetime.now()}"
            
            blob_client = blob_service_client.get_blob_client(
                container=container_name,
                blob=test_blob_name
            )
            
            # Upload test
            blob_client.upload_blob(test_content.encode(), overwrite=True)
            result["tests"]["4_upload"] = "Upload successful"
            
            # Get URL and test public access
            blob_url = blob_client.url
            result["tests"]["5_public_url"] = f"Public URL: {blob_url}"
            
            # Download test
            downloaded = blob_client.download_blob().readall().decode()
            result["tests"]["6_download"] = "Download successful"
            
            # Clean up test file
            blob_client.delete_blob()
            result["tests"]["7_cleanup"] = "Cleanup successful"
            
            result["overall_status"] = "AZURE STORAGE IS FULLY WORKING!"
            result["ready_for_videos"] = True
            
        except Exception as blob_error:
            result["tests"]["4_blob_operations"] = f"Blob operations failed: {str(blob_error)}"
            
            if "PublicAccessNotPermitted" in str(blob_error):
                result["recommendations"].append("Enable 'Allow Blob public access' in Storage Account → Configuration")
            
            result["overall_status"] = "Storage connected but needs configuration"
            result["ready_for_videos"] = False
        
    except Exception as main_error:
        result["tests"]["connection_error"] = f"Connection failed: {str(main_error)}"
        result["overall_status"] = "Connection failed"
        result["ready_for_videos"] = False
    
    return result

@router.get("/debug/azure-contents")
async def debug_azure_contents():
    """Check what's actually stored in Azure"""
    try:
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not connection_string:
            return {"error": "No connection string"}
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client("videos")
        
        blobs = []
        for blob in container_client.list_blobs():
            blobs.append({
                "name": blob.name,
                "size": blob.size,
                "url": f"https://baduanjintesting.blob.core.windows.net/videos/{blob.name}",
                "last_modified": blob.last_modified.isoformat() if blob.last_modified else None
            })
        
        return {
            "container": "videos",
            "total_blobs": len(blobs),
            "blobs": blobs
        }
        
    except Exception as e:
        return {"error": str(e)}
    
