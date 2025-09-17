# video_english.py 

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

import models
import database
from auth.router import get_current_user

router = APIRouter(
    prefix="/api/videos",
    tags=["video_english"]
)

# Global variable to track conversion status
conversion_status: Dict[int, str] = {}  # {video_id: status}

@router.post("/{video_id}/convert-audio")
async def convert_video_audio(
    video_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Convert a video's audio from Mandarin to English
    Only available for master users
    """
    # Check if user is a master
    if current_user.role != models.UserRole.MASTER:
        raise HTTPException(status_code=403, detail="Only masters can convert video audio")
    
    # Verify video ownership
    video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == video_id,
        models.VideoUpload.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Print debug information
    print(f"Video ID: {video_id}, Status: {video.processing_status}")
    
    # IMPORTANT: Allow video conversion for both uploaded AND completed videos
    # This ensures it works for both newly uploaded videos and analyzed ones
    if video.processing_status not in ["uploaded", "completed"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Video must be in 'uploaded' or 'completed' status to convert audio. Current status: {video.processing_status}"
        )
    
    # Check if the video file exists
    if not video.video_path or not os.path.exists(video.video_path):
        raise HTTPException(
            status_code=400,
            detail="Video file not found on server"
        )
    
    # Set conversion status
    conversion_status[video_id] = "processing"
    
    # Get the original video path
    original_video_path = video.video_path
    
    # Create output path for the converted video
    # First, get the directory and filename
    original_path = Path(original_video_path)
    filename = original_path.stem
    
    # Create output directory if it doesn't exist
    output_dir = Path("outputs_json") / str(current_user.id) / str(video_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Output path for the converted video
    output_video_path = str(output_dir / f"{filename}_english.mp4")
    
    # Define background task function
    def convert_audio_background():
        try:
            # Get script path
            script_path = os.path.join("ml_pipeline", "mandarin_to_english.py")
            
            # Check if script exists
            if not os.path.exists(script_path):
                print(f"ERROR: Script not found: {script_path}")
                conversion_status[video_id] = "failed"
                return
            
            # Create absolute paths
            abs_script_path = os.path.abspath(script_path)
            abs_input_path = os.path.abspath(original_video_path)
            abs_output_path = os.path.abspath(output_video_path)
            
            print(f"Starting audio conversion for video {video_id}")
            print(f"Script: {abs_script_path}")
            print(f"Input: {abs_input_path}")
            print(f"Output: {abs_output_path}")
            
            # Get Python executable path
            python_exe = sys.executable
            
            # Set PYTHONIOENCODING environment variable to handle Unicode
            my_env = os.environ.copy()
            my_env["PYTHONIOENCODING"] = "utf-8"
            
            # Run the conversion script
            cmd = [
                python_exe,
                abs_script_path,
                abs_input_path,
                abs_output_path
            ]
            
            # Execute the command with PIPE for stdout/stderr and encoding set to utf-8
            # This handles Chinese characters better
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',  # Explicitly set encoding
                errors='replace',   # Replace any characters that can't be decoded
                env=my_env          # Set environment variables
            )
            
            # Use communicate() to get the output with proper encoding handling
            stdout, stderr = process.communicate()
            
            # Safely print outputs - this avoids encoding errors
            try:
                print("STDOUT from conversion script:")
                for line in stdout.splitlines():
                    print(f"  {line}")
            except UnicodeEncodeError:
                print("STDOUT contains characters that can't be displayed in the console")
                
            try:
                print("STDERR from conversion script:")
                for line in stderr.splitlines():
                    print(f"  {line}")
            except UnicodeEncodeError:
                print("STDERR contains characters that can't be displayed in the console")
            
            # Check if conversion was successful
            if process.returncode == 0 and os.path.exists(abs_output_path):
                print(f"Audio conversion successful for video {video_id}")
                
                # Create a new DB session for this background task
                task_db = database.SessionLocal()
                
                try:
                    # Update the video record with English audio path
                    db_video = task_db.query(models.VideoUpload).filter(
                        models.VideoUpload.id == video_id
                    ).first()
                    
                    if db_video:
                        # Store the English audio version path
                        db_video.english_audio_path = output_video_path
                        task_db.commit()
                    
                    # Update the conversion status
                    conversion_status[video_id] = "completed"
                except Exception as e:
                    print(f"Database update error for video {video_id}: {str(e)}")
                    conversion_status[video_id] = "failed"
                finally:
                    task_db.close()
            else:
                print(f"Audio conversion failed for video {video_id}")
                conversion_status[video_id] = "failed"
                
        except Exception as e:
            print(f"Error in audio conversion for video {video_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            conversion_status[video_id] = "failed"
    
    # Add the background task
    background_tasks.add_task(convert_audio_background)
    
    # Return initial response
    return {
        "status": "started",
        "message": "Audio conversion started",
        "video_id": video_id
    }

@router.get("/{video_id}/conversion-status")
async def get_conversion_status(
    video_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """Get the status of an audio conversion process"""
    
    # Verify video ownership
    video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == video_id,
        models.VideoUpload.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Get status from the tracking dictionary
    status = conversion_status.get(video_id, "not_started")
    
    return {
        "status": status,
        "video_id": video_id
    }

@router.get("/{video_id}/has-english-audio")
async def check_english_audio_version(
    video_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """Check if a video has an English audio version"""
    
    # Verify video access permissions
    video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == video_id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check permissions
    has_access = False
    if video.user_id == current_user.id:
        has_access = True
    elif current_user.role == models.UserRole.MASTER:
        # Check if the video belongs to a learner that follows this master
        relationship = db.query(models.MasterLearnerRelationship).filter(
            models.MasterLearnerRelationship.master_id == current_user.id,
            models.MasterLearnerRelationship.learner_id == video.user_id,
            models.MasterLearnerRelationship.status == "accepted"
        ).first()
        
        if relationship:
            has_access = True
    elif current_user.role == models.UserRole.LEARNER:
        # Check if the video belongs to a master that this learner follows
        video_owner = db.query(models.User).filter(
            models.User.id == video.user_id
        ).first()
        
        if video_owner and video_owner.role == models.UserRole.MASTER:
            has_access = True
    
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if the video has an English audio version
    has_english_audio = video.english_audio_path is not None and os.path.exists(video.english_audio_path)
    
    return {
        "video_id": video_id,
        "has_english_audio": has_english_audio,
        "english_audio_path": video.english_audio_path if has_english_audio else None
    }