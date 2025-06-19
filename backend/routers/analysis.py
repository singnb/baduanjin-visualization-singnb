# routers/analysis.py

import os
import json
import subprocess
import sys
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
import models
import database
from auth.router import get_current_user
import time

from azure.storage.blob import BlobServiceClient
import io

def correct_azure_blob_path(stored_url: str, user_id: int, video_id: int) -> str:
    """
    Correct the blob path from the database to match actual Azure storage structure
    
    Database stores: baduanjin_analysis/2/18/analysis_report.txt
    Actual path should be: outputs_json/2/18/baduanjin_analysis/analysis_report.txt
    """
    if not stored_url:
        return None
        
    try:
        # Extract the filename from the URL
        url_parts = stored_url.split("blob.core.windows.net/results/")
        if len(url_parts) >= 2:
            stored_path = url_parts[-1]
            
            # Check if it's the incorrect format: baduanjin_analysis/{user_id}/{video_id}/filename
            if stored_path.startswith(f"baduanjin_analysis/{user_id}/{video_id}/"):
                # Extract just the filename
                filename = stored_path.split('/')[-1]  # gets "analysis_report.txt"
                
                # Construct the correct path
                correct_path = f"outputs_json/{user_id}/{video_id}/baduanjin_analysis/{filename}"
                
                print(f"Corrected path: {stored_path} -> {correct_path}")
                return correct_path
            
            # If it's already in correct format or other format, return as is
            return stored_path
    except Exception as e:
        print(f"Error correcting blob path: {e}")
        
    # Fallback: construct the expected path
    return f"outputs_json/{user_id}/{video_id}/baduanjin_analysis/analysis_report.txt"

router = APIRouter(
    prefix="/api/analysis",
    tags=["analysis"]
)

async def run_analysis_script(video_id: int, user_id: int, video: models.VideoUpload) -> bool:
    """
    Run the working_analysis.py script for a specific video
    """
    try:
        # Get the root directory
        root_dir = os.getcwd()
        print(f"Working directory: {root_dir}")
        
        # Construct paths using os.path.join which handles path separators correctly
        analysis_script_path = os.path.join(root_dir, "ml_pipeline", "working_analysis.py")
        print(f"Analysis script path: {analysis_script_path}")
        
        # Check if analysis script exists
        if not os.path.exists(analysis_script_path):
            raise FileNotFoundError(f"Analysis script not found at {analysis_script_path}")
        
        # Parse the keypoints_path to get the JSON file location
        if not video.keypoints_path:
            raise ValueError("No keypoints path found for this video")
            
        # Convert forward slashes to backslashes for Windows
        keypoints_path = video.keypoints_path.replace('/', os.path.sep)
        json_path = os.path.join(root_dir, keypoints_path)
        print(f"JSON path: {json_path}")
        
        # Check if JSON file exists
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"JSON file not found at {json_path}")
        
        # Get video path - prefer original analyzed video (without _web suffix)
        video_path = None
        outputs_dir = os.path.join(root_dir, "outputs_json", str(user_id), str(video_id))
        
        # First, try to find the original analyzed video (without _web suffix)
        if video.analyzed_video_path:
            # Convert forward slashes to backslashes
            analyzed_path = video.analyzed_video_path.replace('/', os.path.sep)
            
            # Check if it's a web version and try to find the original
            if "_web.mp4" in analyzed_path:
                # Replace _web.mp4 with .mp4 to get the original
                original_analyzed_path = analyzed_path.replace("_web.mp4", ".mp4")
                if original_analyzed_path.startswith("outputs_json"):
                    potential_path = os.path.join(root_dir, original_analyzed_path)
                else:
                    potential_path = original_analyzed_path
                    
                if os.path.exists(potential_path):
                    video_path = potential_path
                    print(f"Found original video at: {video_path}")
            else:
                # Use the analyzed_video_path as is
                if analyzed_path.startswith("outputs_json"):
                    video_path = os.path.join(root_dir, analyzed_path)
                else:
                    video_path = analyzed_path
        
        # If still no video_path, look for any non-web MP4 in the outputs directory
        if not video_path or not os.path.exists(video_path):
            if os.path.exists(outputs_dir):
                for file in os.listdir(outputs_dir):
                    if file.endswith(".mp4") and not file.endswith("_web.mp4"):
                        video_path = os.path.join(outputs_dir, file)
                        print(f"Found video file: {video_path}")
                        break
        
        # Final fallback to original uploaded video
        if not video_path or not os.path.exists(video_path):
            if video.video_path:
                video_path = video.video_path.replace('/', os.path.sep)
                if not os.path.isabs(video_path):
                    video_path = os.path.join(root_dir, video_path)
            else:
                print("WARNING: No video path available")
                video_path = ""
            
        print(f"Final video path: {video_path}")
        
        # Check if video exists (if provided)
        if video_path and not os.path.exists(video_path):
            print(f"WARNING: Video file not found at {video_path}")
            # Continue anyway - the analysis might work without video
            
        # Output directory for analysis results
        output_dir = os.path.join(root_dir, "outputs_json", str(user_id), str(video_id), "baduanjin_analysis")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Construct the command - all paths should now use proper OS separators
        cmd = [
            sys.executable,
            analysis_script_path,
            "--pose_results", json_path,
            "--output_dir", output_dir
        ]
        
        # Only add video argument if we have a valid path
        if video_path and os.path.exists(video_path):
            cmd.extend(["--video", video_path])
        
        print(f"Running analysis command: {' '.join(cmd)}")
        
        # Use subprocess.run for Windows compatibility
        # Run in a separate thread to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        
        def run_subprocess():
            try:
                # For Windows, we need to use shell=True for complex commands
                # But it's safer to use the list form
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minutes timeout
                    cwd=root_dir,
                    shell=False  # Don't use shell for security
                )
                
                return result.returncode, result.stdout, result.stderr
            except subprocess.TimeoutExpired:
                return -1, "", "Analysis script timed out after 5 minutes"
            except Exception as e:
                return -1, "", str(e)
        
        # Run the subprocess in a thread executor
        returncode, stdout, stderr = await loop.run_in_executor(None, run_subprocess)
        
        print(f"Analysis stdout: {stdout}")
        print(f"Analysis stderr: {stderr}")
        
        if returncode != 0:
            error_msg = f"Analysis process exited with code {returncode}\nSTDERR: {stderr}\nSTDOUT: {stdout}"
            print(f"Analysis error: {error_msg}")
            raise RuntimeError(error_msg)
            
        print("Analysis completed successfully")
        return True
        
    except Exception as e:
        print(f"Error running analysis: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

@router.get("/{video_id}")
async def get_analysis_results(
    video_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Get analysis results for a specific video - Azure storage compatible
    """
    print(f"Getting analysis results for video {video_id}, user {current_user.id}")
    
    # Verify video ownership
    video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == video_id,
        models.VideoUpload.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    print(f"Video found: {video.title}, status: {video.processing_status}")
    
    # Direct database query to get analysis_report_path (bypasses model issues)
    analysis_report_url = None
    try:
        from sqlalchemy import text
        result = db.execute(
            text("SELECT analysis_report_path FROM video_uploads WHERE id = :video_id"),
            {"video_id": video_id}
        ).fetchone()
        
        analysis_report_url = result[0] if result and result[0] else None
        print(f"Direct DB query - analysis_report_path: {analysis_report_url}")
        
    except Exception as e:
        print(f"Error querying analysis_report_path: {e}")
        # Check if column exists
        try:
            column_check = db.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name = 'video_uploads' AND column_name = 'analysis_report_path'")
            ).fetchone()
            
            if not column_check:
                print("WARNING: analysis_report_path column does not exist in database")
            else:
                print("Column exists but query failed for other reason")
        except:
            pass
    
    # Check Azure first if we have an Azure URL
    report_exists_azure = False
    azure_report_content = None
    
    if analysis_report_url and analysis_report_url.startswith('https://'):
        try:
            connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            if connection_string:
                print(f"Original DB URL: {analysis_report_url}")
                
                # Correct the blob path using our helper function
                corrected_blob_path = correct_azure_blob_path(analysis_report_url, current_user.id, video_id)
                
                if corrected_blob_path:
                    print(f"Checking Azure for analysis report with corrected path: {corrected_blob_path}")
                    
                    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
                    blob_client = blob_service_client.get_blob_client(
                        container="results",
                        blob=corrected_blob_path
                    )
                    
                    print(f"Checking blob: container='results', blob='{corrected_blob_path}'")
                    
                    # Check if blob exists with detailed error info
                    try:
                        blob_properties = blob_client.get_blob_properties()
                        print(f"Blob exists! Size: {blob_properties.size} bytes")
                        
                        # Download content
                        azure_report_content = blob_client.download_blob().readall().decode('utf-8')
                        report_exists_azure = True
                        print(f"Successfully downloaded report: {len(azure_report_content)} characters")
                        
                    except Exception as blob_error:
                        print(f"Blob check failed: {str(blob_error)}")
                        print(f"Error type: {type(blob_error).__name__}")
                        
                        # Try to list blobs with similar names for debugging
                        try:
                            container_client = blob_service_client.get_container_client("results")
                            
                            # Look for any blobs that start with outputs_json
                            similar_blobs = []
                            for blob in container_client.list_blobs(name_starts_with="outputs_json"):
                                similar_blobs.append(blob.name)
                            
                            print(f"Found similar blobs: {similar_blobs}")
                            
                            # Look for any blobs for this user/video
                            user_video_blobs = []
                            for blob in container_client.list_blobs(name_starts_with=f"outputs_json/{current_user.id}/{video_id}/baduanjin_analysis"):
                                user_video_blobs.append(blob.name)
                            
                            print(f"Found user/video blobs: {user_video_blobs}")
                            
                        except Exception as list_error:
                            print(f"Could not list similar blobs: {list_error}")
                else:
                    print(f"Could not correct blob path for URL: {analysis_report_url}")
            else:
                print("Azure connection string not available")
                
        except Exception as e:
            print(f"Error checking Azure for analysis report: {e}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
    else:
        print(f"No valid Azure URL found. analysis_report_url: {analysis_report_url}")
        print(f"URL type: {type(analysis_report_url)}, starts with https: {str(analysis_report_url).startswith('https://') if analysis_report_url else 'N/A'}")
    
    # Fallback: Check local files (for backward compatibility)
    analysis_dir = os.path.join("outputs_json", str(current_user.id), str(video_id), "baduanjin_analysis")
    report_path = os.path.join(analysis_dir, "analysis_report.txt")
    report_exists_local = os.path.exists(report_path)
    
    print(f"Checking local analysis report at: {report_path}")
    print(f"Local report exists: {report_exists_local}")
    
    if not report_exists_azure and not report_exists_local:
        # Analysis hasn't been run yet
        return {
            "status": "not_analyzed",
            "message": "Analysis has not been performed yet",
            "video_id": video_id,
            "video_title": video.title,
            "video_status": video.processing_status,
            "debug_info": {
                "azure_url_from_db": analysis_report_url,
                "local_path_checked": report_path,
                "azure_exists": report_exists_azure,
                "local_exists": report_exists_local
            }
        }
    
    # If we reach here, analysis exists - parse the report
    analysis_data = {
        "status": "analyzed",
        "video_id": video_id,
        "video_title": video.title,
        "key_poses": [],
        "joint_angles": {},
        "movement_smoothness": {},
        "movement_symmetry": {},
        "balance_metrics": {},
        "recommendations": [],
        "images": {},
        "report_source": "azure" if report_exists_azure else "local"
    }
    
    # Read and parse the report content
    try:
        if report_exists_azure:
            content = azure_report_content
            print("Using Azure report content for parsing")
        else:
            with open(report_path, 'r') as f:
                content = f.read()
            print("Using local report content for parsing")
        
        # Parse the content (keep your existing parsing logic)
        if content:
            sections = content.split("\n\n")
            
            for section in sections:
                lines = section.strip().split("\n")
                if not lines:
                    continue
                    
                header = lines[0].strip()
                
                if "Key Poses" in header:
                    for line in lines[1:]:
                        if line.startswith("Pose"):
                            parts = line.split(":")
                            if len(parts) >= 2:
                                pose_info = {
                                    "pose": parts[0].strip(),
                                    "frame": int(parts[1].replace("Frame", "").strip())
                                }
                                analysis_data["key_poses"].append(pose_info)
                
                elif "Movement Smoothness" in header:
                    for line in lines[1:]:
                        if ":" in line and not line.startswith("-"):
                            joint, value = line.split(":")
                            try:
                                analysis_data["movement_smoothness"][joint.strip()] = float(value.strip())
                            except ValueError:
                                pass
                
                elif "Movement Symmetry" in header:
                    for line in lines[1:]:
                        if ":" in line and not line.startswith("-"):
                            pair, value = line.split(":")
                            try:
                                analysis_data["movement_symmetry"][pair.strip()] = float(value.strip())
                            except ValueError:
                                pass
                
                elif "Balance Metrics" in header:
                    for line in lines[1:]:
                        if ":" in line and not line.startswith("-"):
                            metric, value = line.split(":")
                            try:
                                analysis_data["balance_metrics"][metric.strip()] = float(value.strip())
                            except ValueError:
                                pass
                
                elif "Teaching Recommendations" in header:
                    for line in lines[1:]:
                        if line.strip() and not line.startswith("-"):
                            analysis_data["recommendations"].append(line.strip())
        
    except Exception as e:
        print(f"Error parsing report: {str(e)}")
    
    # Add available image paths with corrected URLs
    image_files = [
        "key_poses.png",
        "joint_angles.png",
        "movement_smoothness.png",
        "movement_symmetry.png",
        "com_trajectory.png",
        "balance_metrics.png"
    ]
    
    for img_file in image_files:
        img_name = img_file.replace(".png", "")
        
        # Always use the backend endpoint - it will handle Azure/local automatically
        backend_img_url = f"/api/analysis/{video_id}/image/{img_name}"
        analysis_data["images"][img_name] = backend_img_url
        print(f"Added backend image URL: {img_name} -> {backend_img_url}")
        
        if report_exists_azure:
            # Use corrected Azure URLs for images
            corrected_img_blob_path = f"outputs_json/{current_user.id}/{video_id}/baduanjin_analysis/{img_file}"
            azure_img_url = f"https://baduanjintesting.blob.core.windows.net/results/{corrected_img_blob_path}"
            analysis_data["images"][img_name] = azure_img_url
            print(f"Added corrected Azure image URL: {img_name} -> {azure_img_url}")
        else:
            # Check local files
            img_path = os.path.join(analysis_dir, img_file)
            if os.path.exists(img_path):
                relative_path = f"outputs_json/{current_user.id}/{video_id}/baduanjin_analysis/{img_file}"
                analysis_data["images"][img_name] = relative_path
                print(f"Added local image path: {img_name} -> {relative_path}")
    
    print(f"Returning analysis data with {len(analysis_data['images'])} images")
    return analysis_data

# Alternative implementation using synchronous subprocess in background task
def run_analysis_sync(video_id: int, user_id: int, video: models.VideoUpload) -> bool:
    """
    Synchronous version of analysis script runner for use in background tasks
    """
    try:
        # Get the root directory
        root_dir = os.getcwd()
        print(f"Working directory: {root_dir}")
        
        # Construct paths using os.path.join which handles path separators correctly
        analysis_script_path = os.path.join(root_dir, "ml_pipeline", "working_analysis.py")
        print(f"Analysis script path: {analysis_script_path}")
        
        # Check if analysis script exists
        if not os.path.exists(analysis_script_path):
            raise FileNotFoundError(f"Analysis script not found at {analysis_script_path}")
        
        # Parse the keypoints_path to get the JSON file location
        if not video.keypoints_path:
            raise ValueError("No keypoints path found for this video")
            
        # Convert forward slashes to backslashes for Windows
        keypoints_path = video.keypoints_path.replace('/', os.path.sep)
        json_path = os.path.join(root_dir, keypoints_path)
        print(f"JSON path: {json_path}")
        
        # Check if JSON file exists
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"JSON file not found at {json_path}")
        
        # Get video path - prefer original analyzed video (without _web suffix)
        video_path = None
        outputs_dir = os.path.join(root_dir, "outputs_json", str(user_id), str(video_id))
        
        # First, try to find the original analyzed video (without _web suffix)
        if video.analyzed_video_path:
            # Convert forward slashes to backslashes
            analyzed_path = video.analyzed_video_path.replace('/', os.path.sep)
            
            # Check if it's a web version and try to find the original
            if "_web.mp4" in analyzed_path:
                # Replace _web.mp4 with .mp4 to get the original
                original_analyzed_path = analyzed_path.replace("_web.mp4", ".mp4")
                if original_analyzed_path.startswith("outputs_json"):
                    potential_path = os.path.join(root_dir, original_analyzed_path)
                else:
                    potential_path = original_analyzed_path
                    
                if os.path.exists(potential_path):
                    video_path = potential_path
                    print(f"Found original video at: {video_path}")
            else:
                # Use the analyzed_video_path as is
                if analyzed_path.startswith("outputs_json"):
                    video_path = os.path.join(root_dir, analyzed_path)
                else:
                    video_path = analyzed_path
        
        # If still no video_path, look for any non-web MP4 in the outputs directory
        if not video_path or not os.path.exists(video_path):
            if os.path.exists(outputs_dir):
                for file in os.listdir(outputs_dir):
                    if file.endswith(".mp4") and not file.endswith("_web.mp4"):
                        video_path = os.path.join(outputs_dir, file)
                        print(f"Found video file: {video_path}")
                        break
        
        # Final fallback to original uploaded video
        if not video_path or not os.path.exists(video_path):
            if video.video_path:
                video_path = video.video_path.replace('/', os.path.sep)
                if not os.path.isabs(video_path):
                    video_path = os.path.join(root_dir, video_path)
            else:
                print("WARNING: No video path available")
                video_path = ""
            
        print(f"Final video path: {video_path}")
        
        # Check if video exists (if provided)
        if video_path and not os.path.exists(video_path):
            print(f"WARNING: Video file not found at {video_path}")
            # Continue anyway - the analysis might work without video
            
        # Output directory for analysis results
        output_dir = os.path.join(root_dir, "outputs_json", str(user_id), str(video_id), "baduanjin_analysis")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Construct the command - all paths should now use proper OS separators
        cmd = [
            sys.executable,
            analysis_script_path,
            "--pose_results", json_path,
            "--output_dir", output_dir
        ]
        
        # Only add video argument if we have a valid path
        if video_path and os.path.exists(video_path):
            cmd.extend(["--video", video_path])
        
        print(f"Running analysis command: {' '.join(cmd)}")
        
        # Run the command using subprocess
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout
            cwd=root_dir
        )
        
        print(f"Analysis stdout: {result.stdout}")
        print(f"Analysis stderr: {result.stderr}")
        
        if result.returncode != 0:
            error_msg = f"Analysis process exited with code {result.returncode}\nSTDERR: {result.stderr}\nSTDOUT: {result.stdout}"
            print(f"Analysis error: {error_msg}")
            return False
            
        print("Analysis completed successfully")
        return True
        
    except subprocess.TimeoutExpired:
        print("Analysis script timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"Error running analysis: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

@router.post("/{video_id}/run")
async def run_analysis(
    video_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Run analysis for a specific video
    """
    # Verify video ownership and status
    video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == video_id,
        models.VideoUpload.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.processing_status != "completed":
        raise HTTPException(
            status_code=400, 
            detail="Video processing must be completed before running analysis"
        )
    
    # Check if analysis already exists
    analysis_dir = os.path.join("outputs_json", str(current_user.id), str(video_id), "baduanjin_analysis")
    report_path = os.path.join(analysis_dir, "analysis_report.txt")
    
    if os.path.exists(report_path):
        return {
            "status": "already_analyzed",
            "message": "Analysis already exists for this video"
        }
    
    # Run analysis in background using the synchronous version
    def analyze_in_background():
        try:
            success = run_analysis_sync(video_id, current_user.id, video)
            if not success:
                print(f"Analysis failed for video {video_id}")
                # You might want to update the database to mark this video as analysis failed
        except Exception as e:
            print(f"Background analysis error for video {video_id}: {e}")
            import traceback
            traceback.print_exc()
    
    background_tasks.add_task(analyze_in_background)
    
    return {
        "status": "analysis_started",
        "message": "Analysis started successfully"
    }

@router.get("/{video_id}/image/{image_name}")
async def get_analysis_image(
    video_id: int,
    image_name: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Serve analysis image files - supports both Azure and local storage
    """
    # Verify video ownership
    video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == video_id,
        models.VideoUpload.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Try Azure first
    try:
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if connection_string:
            blob_path = f"outputs_json/{current_user.id}/{video_id}/baduanjin_analysis/{image_name}.png"
            
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            blob_client = blob_service_client.get_blob_client(
                container="results",
                blob=blob_path
            )
            
            # Check if blob exists and download
            try:
                blob_data = blob_client.download_blob().readall()
                print(f"Successfully retrieved {image_name} from Azure: {len(blob_data)} bytes")
                
                return StreamingResponse(
                    io.BytesIO(blob_data),
                    media_type="image/png",
                    headers={
                        "Cache-Control": "public, max-age=3600",
                        "Access-Control-Allow-Origin": "*"
                    }
                )
            except Exception as azure_error:
                print(f"Azure blob not found: {azure_error}")
                # Fall through to local file check
                
    except Exception as e:
        print(f"Error accessing Azure storage: {e}")
    
    # Fallback to local file
    local_image_path = os.path.join(
        "outputs_json", 
        str(current_user.id), 
        str(video_id), 
        "baduanjin_analysis",
        f"{image_name}.png"
    )
    
    if os.path.exists(local_image_path):
        print(f"Serving local image: {local_image_path}")
        return FileResponse(
            local_image_path, 
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*"
            }
        )
    
    # Image not found anywhere
    raise HTTPException(status_code=404, detail=f"Image not found: {image_name}")

@router.get("/{video_id}/files/{file_type}/{filename}")
async def get_analysis_file(
    video_id: int,
    file_type: str,  # "images", "json", "report"
    filename: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Stream analysis files from Azure storage
    file_type: images, json, report
    filename: specific filename without extension
    """
    # Verify video ownership
    video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == video_id,
        models.VideoUpload.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.processing_status != "completed":
        raise HTTPException(status_code=400, detail="Video analysis not completed")
    
    try:
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not connection_string:
            raise HTTPException(status_code=500, detail="Azure storage not configured")
        
        # Determine file extension and blob path based on file type
        if file_type == "images":
            file_extension = ".png"
            blob_path = f"outputs_json/{current_user.id}/{video_id}/baduanjin_analysis/{filename}{file_extension}"
            content_type = "image/png"
        elif file_type == "json":
            file_extension = ".json" 
            blob_path = f"outputs_json/{current_user.id}/{video_id}/baduanjin_analysis/{filename}{file_extension}"
            content_type = "application/json"
        elif file_type == "report":
            file_extension = ".txt"
            blob_path = f"outputs_json/{current_user.id}/{video_id}/analysis_report{file_extension}"
            content_type = "text/plain"
        else:
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        # Download from Azure
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = blob_service_client.get_blob_client(
            container="results",
            blob=blob_path
        )
        
        content = blob_client.download_blob().readall()
        
        # Return appropriate response
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Content-Disposition": "inline"
        }
        
        if file_type == "images":
            headers["Cache-Control"] = "public, max-age=3600"
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers=headers
        )
        
    except Exception as e:
        print(f"Error accessing analysis file: {e}")
        raise HTTPException(status_code=404, detail=f"Analysis file not found: {filename}")

@router.get("/{video_id}/analysis-summary")
async def get_analysis_summary(
    video_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Get a summary of all available analysis files for a video
    """
    # Verify video ownership
    video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == video_id,
        models.VideoUpload.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.processing_status != "completed":
        return {
            "status": "not_completed",
            "video_id": video_id,
            "available_files": []
        }
    
    try:
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not connection_string:
            raise HTTPException(status_code=500, detail="Azure storage not configured")
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client("results")
        
        # List all files for this user/video in baduanjin_analysis
        prefix = f"outputs_json/{current_user.id}/{video_id}/baduanjin_analysis/"
        available_files = {
            "images": [],
            "json": [], 
            "reports": [],
            "urls": {}
        }
        
        for blob in container_client.list_blobs(name_starts_with=prefix):
            filename = blob.name.split("/")[-1]  # Get just the filename
            
            if filename.endswith('.png'):
                file_base = filename.replace('.png', '')
                available_files["images"].append(file_base)
                available_files["urls"][file_base] = f"/api/analysis/{video_id}/files/images/{file_base}"
            elif filename.endswith('.json'):
                file_base = filename.replace('.json', '')
                available_files["json"].append(file_base)
                available_files["urls"][file_base] = f"/api/analysis/{video_id}/files/json/{file_base}"
            elif filename.endswith('.txt'):
                file_base = filename.replace('.txt', '')
                available_files["reports"].append(file_base)
                available_files["urls"][file_base] = f"/api/analysis/{video_id}/files/report/{file_base}"
        
        return {
            "status": "completed",
            "video_id": video_id,
            "video_title": video.title,
            "available_files": available_files,
            "analysis_paths": {
                "analyzed_video": video.analyzed_video_path,
                "keypoints_data": video.keypoints_path
            }
        }
        
    except Exception as e:
        print(f"Error getting analysis summary: {e}")
        return {
            "status": "error",
            "video_id": video_id,
            "error": str(e),
            "available_files": []
        }
    
@router.get("/debug/azure-results-contents")
async def debug_azure_results_contents(
    current_user: models.User = Depends(get_current_user)
):
    """Debug endpoint to check what's actually in the Azure results container"""
    try:
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not connection_string:
            return {"error": "No Azure connection string"}
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client("results")
        
        # List all blobs in results container
        all_blobs = []
        user_blobs = []
        
        for blob in container_client.list_blobs():
            blob_info = {
                "name": blob.name,
                "size": blob.size,
                "url": f"https://baduanjintesting.blob.core.windows.net/results/{blob.name}",
                "last_modified": blob.last_modified.isoformat() if blob.last_modified else None
            }
            all_blobs.append(blob_info)
            
            # Check if this blob belongs to current user
            if f"/{current_user.id}/" in blob.name or blob.name.startswith(f"{current_user.id}/"):
                user_blobs.append(blob_info)
        
        return {
            "container": "results",
            "total_blobs": len(all_blobs),
            "user_blobs": len(user_blobs),
            "current_user_id": current_user.id,
            "all_blobs": all_blobs[:20],  # First 20 blobs
            "user_specific_blobs": user_blobs,
            "looking_for": f"outputs_json/{current_user.id}/{video_id}/baduanjin_analysis/analysis_report.txt"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "container": "results",
            "details": "Failed to list blobs"
        }
    
