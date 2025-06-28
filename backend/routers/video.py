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
import json
import httpx
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
    """Stream video with proper Azure path handling"""
    import os
    import io
    
    if not token:
        raise HTTPException(status_code=401, detail="Authentication token required")
    
    try:
        # JWT token decoding (your existing logic)
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
        
        # Get video and check access
        video = db.query(models.VideoUpload).filter(
            models.VideoUpload.id == video_id
        ).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Access control (your existing logic)
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
        
        # Get video UUID for path construction
        video_uuid = getattr(video, 'video_uuid', None)
        
        # Determine video path based on type
        video_path = None
        
        if type == "original":
            # Original videos are in uploads/videos/{user_id}/{uuid}.mp4
            if video.video_path:
                video_path = video.video_path
            elif video_uuid:
                video_path = f"https://baduanjintesting.blob.core.windows.net/videos/uploads/videos/{video.user_id}/{video_uuid}.mp4"
            else:
                raise HTTPException(status_code=404, detail="Original video path not found")
            
            print(f"Streaming original video: {video_path}")
            
        elif type == "analyzed":
            # Analyzed videos are in outputs_json/{user_id}/{video_id}/{uuid}_web.mp4
            if video.analyzed_video_path:
                video_path = video.analyzed_video_path
            elif video_uuid:
                video_path = f"https://baduanjintesting.blob.core.windows.net/videos/outputs_json/{video.user_id}/{video_id}/{video_uuid}_web.mp4"
            else:
                # Fallback: look for any MP4 in outputs directory
                outputs_dir = f"outputs_json/{video.user_id}/{video_id}"
                if os.path.exists(outputs_dir):
                    mp4_files = [f for f in os.listdir(outputs_dir) if f.endswith('.mp4')]
                    if mp4_files:
                        video_path = f"https://baduanjintesting.blob.core.windows.net/videos/{outputs_dir}/{mp4_files[0]}"
                
                if not video_path:
                    # Final fallback to original
                    video_path = video.video_path
                    print(f"Analyzed video not found, falling back to original")
            
            print(f"Streaming analyzed video: {video_path}")
            
        elif type == "english":
            # English videos are in outputs_json/{user_id}/{video_id}/{uuid}_english.mp4
            if hasattr(video, 'english_audio_path') and video.english_audio_path:
                video_path = video.english_audio_path
            elif video_uuid:
                video_path = f"https://baduanjintesting.blob.core.windows.net/videos/outputs_json/{video.user_id}/{video_id}/{video_uuid}_english.mp4"
            else:
                # Fallback: look for english files in outputs
                from pathlib import Path
                base_path = Path("outputs_json") / str(video.user_id) / str(video_id)
                if base_path.exists():
                    english_files = list(base_path.glob("*english*.mp4"))
                    if english_files:
                        video_path = f"https://baduanjintesting.blob.core.windows.net/videos/outputs_json/{video.user_id}/{video_id}/{english_files[0].name}"
                
                if not video_path:
                    raise HTTPException(status_code=404, detail="English audio version not found")
            
            print(f"Streaming English audio: {video_path}")
            
        else:
            raise HTTPException(status_code=400, detail=f"Invalid video type: {type}")
        
        if not video_path:
            raise HTTPException(status_code=404, detail="Video path not found")
        
        # Stream from Azure (all paths should be Azure URLs now)
        if video_path.startswith('https://') and '.blob.core.windows.net' in video_path:
            try:
                connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
                if not connection_string:
                    raise HTTPException(status_code=500, detail="Azure storage not configured")
                
                from azure.storage.blob import BlobServiceClient
                blob_service_client = BlobServiceClient.from_connection_string(connection_string)
                
                # Extract blob name from URL - everything after /videos/
                container_name = "videos"
                
                if "/videos/" in video_path:
                    blob_name = video_path.split("/videos/", 1)[1]  # Get everything after first /videos/
                else:
                    raise HTTPException(status_code=400, detail="Invalid Azure URL format")
                
                print(f"Azure streaming - Container: {container_name}, Blob: {blob_name}")
                
                # Get blob client
                blob_client = blob_service_client.get_blob_client(
                    container=container_name,
                    blob=blob_name
                )
                
                # Check if blob exists
                if not blob_client.exists():
                    print(f"Blob does not exist: {blob_name}")
                    raise HTTPException(status_code=404, detail="Video file not found in Azure storage")
                
                # Download and stream
                blob_properties = blob_client.get_blob_properties()
                content_type = blob_properties.content_settings.content_type or "video/mp4"
                
                # For video files, ensure proper content type
                if blob_name.endswith('.mp4'):
                    content_type = "video/mp4"
                
                content = blob_client.download_blob().readall()
                print(f"Successfully downloaded {len(content)} bytes from Azure")
                
                headers = {
                    "Accept-Ranges": "bytes",
                    "Content-Disposition": "inline",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Range, Content-Range, Content-Length"
                }
                
                return StreamingResponse(
                    io.BytesIO(content),
                    media_type=content_type,
                    headers=headers
                )
                
            except Exception as azure_error:
                print(f"Azure streaming error: {azure_error}")
                print(f"URL: {video_path}")
                print(f"Container: {container_name}")
                print(f"Blob: {blob_name if 'blob_name' in locals() else 'unknown'}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Error streaming from Azure: {str(azure_error)}"
                )
        else:
            # Handle local files (fallback)
            if not os.path.exists(video_path):
                print(f"Local file not found: {video_path}")
                raise HTTPException(status_code=404, detail="Video file not found")
            
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
        print(f"Stream video error: {str(e)}")
        import traceback
        traceback.print_exc()
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
    
@router.post("/pi-transfer")
async def transfer_video_from_pi_debug(
    transfer_data: dict,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """DEBUG VERSION - Transfer video from Pi with detailed error tracking"""
    
    try:
        print("🔍 DEBUG: Starting Pi transfer endpoint")
        
        # Step 1: Validate input
        print("🔍 DEBUG: Step 1 - Validating input")
        pi_filename = transfer_data.get("pi_filename")
        title = transfer_data.get("title", "")
        description = transfer_data.get("description", "")
        brocade_type = transfer_data.get("brocade_type", "FIRST")
        
        print(f"🔍 DEBUG: Input data - filename: {pi_filename}, title: {title}")
        
        if not pi_filename:
            raise HTTPException(status_code=400, detail="Pi filename is required")
        if not title:
            raise HTTPException(status_code=400, detail="Title is required")
        
        # Step 2: Test httpx import
        print("🔍 DEBUG: Step 2 - Testing httpx import")
        try:
            import httpx
            print("✅ DEBUG: httpx imported successfully")
        except ImportError as import_error:
            print(f"❌ DEBUG: httpx import failed: {import_error}")
            raise HTTPException(
                status_code=500, 
                detail=f"httpx not available: {str(import_error)}"
            )
        
        # Step 3: Test Azure connection string
        print("🔍 DEBUG: Step 3 - Checking Azure configuration")
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        print(f"🔍 DEBUG: Azure connection string exists: {bool(connection_string)}")
        
        # Step 4: Test Pi URL construction
        print("🔍 DEBUG: Step 4 - Constructing Pi URL")
        PI_DOWNLOAD_URL = f"https://mongoose-hardy-caiman.ngrok-free.app/api/download/{pi_filename}"
        print(f"🔍 DEBUG: Pi URL: {PI_DOWNLOAD_URL}")
        
        # Step 5: Test Pi connectivity
        print("🔍 DEBUG: Step 5 - Testing Pi connectivity")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    'ngrok-skip-browser-warning': 'true',
                    'User-Agent': 'Main-Backend-Pi-Transfer-Debug/1.0'
                }
                
                # First test: Pi health check
                health_url = "https://mongoose-hardy-caiman.ngrok-free.app/api/status"
                health_response = await client.get(health_url, headers=headers)
                print(f"🔍 DEBUG: Pi health check: HTTP {health_response.status_code}")
                
                if health_response.status_code != 200:
                    raise HTTPException(
                        status_code=503,
                        detail=f"Pi not responding. Health check failed: HTTP {health_response.status_code}"
                    )
                
        except httpx.TimeoutException:
            print("❌ DEBUG: Pi connection timeout")
            raise HTTPException(
                status_code=503,
                detail="Pi connection timeout - ngrok tunnel may be down"
            )
        except Exception as connectivity_error:
            print(f"❌ DEBUG: Pi connectivity error: {connectivity_error}")
            raise HTTPException(
                status_code=503,
                detail=f"Cannot reach Pi: {str(connectivity_error)}"
            )
        
        # Step 6: Test file download from Pi
        print("🔍 DEBUG: Step 6 - Testing file download")
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=30.0, read=60.0, write=30.0, pool=30.0)
            ) as client:
                headers = {
                    'ngrok-skip-browser-warning': 'true',
                    'User-Agent': 'Main-Backend-Pi-Transfer-Debug/1.0'
                }
                
                response = await client.get(PI_DOWNLOAD_URL, headers=headers)
                print(f"🔍 DEBUG: Download response: HTTP {response.status_code}")
                
                if response.status_code != 200:
                    error_text = response.text[:200] if hasattr(response, 'text') else 'Unknown error'
                    raise HTTPException(
                        status_code=503, 
                        detail=f"Pi download failed: HTTP {response.status_code} - {error_text}"
                    )
                
                file_content = response.content
                total_size = len(file_content)
                print(f"✅ DEBUG: Downloaded {total_size:,} bytes from Pi")
                
                if total_size == 0:
                    raise HTTPException(status_code=500, detail="Downloaded file is empty")
                
        except httpx.TimeoutException:
            print("❌ DEBUG: Download timeout")
            raise HTTPException(
                status_code=503,
                detail="Download timeout - file may be too large or connection slow"
            )
        
        # Step 7: Test UUID generation
        print("🔍 DEBUG: Step 7 - Testing UUID generation")
        try:
            import uuid
            file_extension = os.path.splitext(pi_filename)[1] or '.mp4'
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            print(f"✅ DEBUG: Generated UUID filename: {unique_filename}")
        except Exception as uuid_error:
            print(f"❌ DEBUG: UUID generation failed: {uuid_error}")
            raise HTTPException(status_code=500, detail=f"UUID generation failed: {str(uuid_error)}")
        
        # Step 8: Test Azure upload
        print("🔍 DEBUG: Step 8 - Testing Azure upload")
        try:
            from azure.storage.blob import BlobServiceClient
            
            if not connection_string:
                raise Exception("Azure storage not configured")
            
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            blob_path = f"uploads/videos/{current_user.id}/{unique_filename}"
            
            blob_client = blob_service_client.get_blob_client(
                container="videos",
                blob=blob_path
            )
            
            # Test upload
            blob_client.upload_blob(
                file_content,
                overwrite=True,
                content_type="video/mp4",
                metadata={
                    "original_filename": pi_filename,
                    "user_id": str(current_user.id),
                    "upload_type": "pi_transfer",
                    "source": "raspberry_pi"
                }
            )
            
            blob_url = blob_client.url
            file_path = blob_url
            storage_type = "azure_blob"
            
            print(f"✅ DEBUG: Azure upload successful: {blob_url}")
            
        except Exception as azure_error:
            print(f"⚠️ DEBUG: Azure upload failed, trying local fallback: {azure_error}")
            # Fallback to local storage
            try:
                UPLOAD_DIR = "uploads/videos"
                os.makedirs(UPLOAD_DIR, exist_ok=True)
                user_dir = os.path.join(UPLOAD_DIR, str(current_user.id))
                os.makedirs(user_dir, exist_ok=True)
                file_path = os.path.join(user_dir, unique_filename)
                
                with open(file_path, "wb") as buffer:
                    buffer.write(file_content)
                
                storage_type = "local_fallback"
                print(f"✅ DEBUG: Local storage fallback successful: {file_path}")
                
            except Exception as local_error:
                print(f"❌ DEBUG: Local storage also failed: {local_error}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Both Azure and local storage failed. Azure: {str(azure_error)}, Local: {str(local_error)}"
                )
        
        # Step 9: Test database record creation
        print("🔍 DEBUG: Step 9 - Creating database record")
        try:
            mapped_brocade_type = map_brocade_type(brocade_type)
            print(f"🔍 DEBUG: Mapped brocade type: {brocade_type} -> {mapped_brocade_type}")
            
            new_video = models.VideoUpload(
                user_id=current_user.id,
                title=title,
                description=description,
                brocade_type=mapped_brocade_type,
                video_path=file_path,
                processing_status="uploaded"
            )
            
            db.add(new_video)
            db.commit()
            db.refresh(new_video)
            
            print(f"✅ DEBUG: Database record created with ID: {new_video.id}")
            
        except Exception as db_error:
            print(f"❌ DEBUG: Database error: {db_error}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Database record creation failed: {str(db_error)}"
            )
        
        # Success!
        print("🎉 DEBUG: Pi transfer completed successfully!")
        
        return {
            "success": True,
            "status": "success",
            "message": "DEBUG: Video transferred successfully from Pi",
            "debug_info": {
                "steps_completed": 9,
                "video_id": new_video.id,
                "storage_type": storage_type,
                "file_size": total_size,
                "azure_filename": unique_filename,
                "original_pi_filename": pi_filename
            },
            # Standard response format
            "id": new_video.id,
            "title": new_video.title,
            "brocade_type": brocade_type,
            "processing_status": new_video.processing_status,
            "upload_timestamp": new_video.upload_timestamp,
            "video_path": file_path
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ DEBUG: Unexpected error in Pi transfer: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"DEBUG: Pi transfer failed at unknown step: {str(e)}"
        )


# Add this simple test endpoint to verify imports work
@router.get("/test-imports")
async def test_required_imports():
    """Test that all required imports are available"""
    
    test_results = {
        "timestamp": datetime.now().isoformat(),
        "imports": {}
    }
    
    # Test httpx
    try:
        import httpx
        test_results["imports"]["httpx"] = {
            "available": True,
            "version": getattr(httpx, '__version__', 'unknown')
        }
    except ImportError as e:
        test_results["imports"]["httpx"] = {
            "available": False,
            "error": str(e)
        }
    
    # Test Azure
    try:
        from azure.storage.blob import BlobServiceClient
        test_results["imports"]["azure_blob"] = {"available": True}
    except ImportError as e:
        test_results["imports"]["azure_blob"] = {
            "available": False,
            "error": str(e)
        }
    
    # Test environment
    test_results["environment"] = {
        "azure_connection_string_exists": bool(os.getenv("AZURE_STORAGE_CONNECTION_STRING"))
    }
    
    return test_results

@router.post("/pi-transfer-requests")
async def transfer_video_from_pi_requests(
    transfer_data: dict,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """Transfer video from Pi using requests instead of httpx"""
    
    try:
        # Extract and validate input
        pi_filename = transfer_data.get("pi_filename")
        title = transfer_data.get("title", "")
        description = transfer_data.get("description", "")
        brocade_type = transfer_data.get("brocade_type", "FIRST")
        
        if not pi_filename or not title:
            raise HTTPException(status_code=400, detail="Pi filename and title are required")
        
        print(f"Starting Pi transfer (requests): {pi_filename}")
        
        # Download from Pi using requests (synchronous)
        PI_DOWNLOAD_URL = f"https://mongoose-hardy-caiman.ngrok-free.app/api/download/{pi_filename}"
        
        import requests  # You already have this
        
        headers = {
            'ngrok-skip-browser-warning': 'true',
            'User-Agent': 'Main-Backend-Pi-Transfer-Requests/1.0'
        }
        
        print(f"Downloading from Pi: {PI_DOWNLOAD_URL}")
        
        # Download file
        response = requests.get(PI_DOWNLOAD_URL, headers=headers, timeout=120)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=503,
                detail=f"Pi download failed: HTTP {response.status_code}"
            )
        
        file_content = response.content
        total_size = len(file_content)
        
        if total_size == 0:
            raise HTTPException(status_code=500, detail="Downloaded file is empty")
        
        print(f"Downloaded {total_size:,} bytes from Pi")
        
        # Generate UUID filename (same as manual upload)
        import uuid
        file_extension = os.path.splitext(pi_filename)[1] or '.mp4'
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Upload to Azure (same as manual upload)
        try:
            from azure.storage.blob import BlobServiceClient
            
            connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            if not connection_string:
                raise Exception("Azure storage not configured")
            
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            blob_path = f"uploads/videos/{current_user.id}/{unique_filename}"
            
            blob_client = blob_service_client.get_blob_client(
                container="videos",
                blob=blob_path
            )
            
            blob_client.upload_blob(
                file_content,
                overwrite=True,
                content_type="video/mp4",
                metadata={
                    "original_filename": pi_filename,
                    "user_id": str(current_user.id),
                    "upload_type": "pi_transfer"
                }
            )
            
            file_path = blob_client.url
            storage_type = "azure_blob"
            
        except Exception as azure_error:
            # Fallback to local storage
            UPLOAD_DIR = "uploads/videos"
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            user_dir = os.path.join(UPLOAD_DIR, str(current_user.id))
            os.makedirs(user_dir, exist_ok=True)
            file_path = os.path.join(user_dir, unique_filename)
            
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
            
            storage_type = "local_fallback"
        
        # Create database record (same as manual upload)
        mapped_brocade_type = map_brocade_type(brocade_type)
        
        new_video = models.VideoUpload(
            user_id=current_user.id,
            title=title,
            description=description,
            brocade_type=mapped_brocade_type,
            video_path=file_path,
            processing_status="uploaded"
        )
        
        db.add(new_video)
        db.commit()
        db.refresh(new_video)
        
        print(f"Video record created with ID: {new_video.id}")
        
        return {
            "success": True,
            "id": new_video.id,
            "title": new_video.title,
            "brocade_type": brocade_type,
            "processing_status": new_video.processing_status,
            "upload_timestamp": new_video.upload_timestamp,
            "storage_type": storage_type,
            "message": f"Video uploaded successfully using requests",
            "original_pi_filename": pi_filename,
            "size": total_size
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Requests-based Pi transfer failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transfer failed: {str(e)}")
    