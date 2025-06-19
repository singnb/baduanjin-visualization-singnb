# routers/analysis_with_master.py

import os
import json
import subprocess
import sys
import asyncio
from typing import List, Dict, Any
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import models
import database
from auth.router import get_current_user
import io

# Add Azure imports
from azure.storage.blob import BlobServiceClient

router = APIRouter(
    prefix="/api/analysis-master",
    tags=["analysis-master"]
)

# Helper function to read JSON from Azure or local storage
async def read_json_file_azure_local(user_id: int, video_id: int, file_name: str) -> Dict:
    """
    Read JSON file from Azure storage first, then fallback to local storage
    """
    # Try Azure first
    try:
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if connection_string:
            # Construct Azure blob path - matching your existing structure
            blob_path = f"outputs_json/{user_id}/{video_id}/baduanjin_analysis/{file_name}"
            
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            blob_client = blob_service_client.get_blob_client(
                container="results",
                blob=blob_path
            )
            
            try:
                blob_data = blob_client.download_blob().readall()
                json_data = json.loads(blob_data.decode('utf-8'))
                print(f"Successfully loaded {file_name} from Azure: {blob_path}")
                return json_data
            except Exception as azure_error:
                print(f"Azure blob not found for {file_name}: {azure_error}")
                
    except Exception as e:
        print(f"Error accessing Azure storage for {file_name}: {e}")
    
    # Fallback to local file - using your existing path structure
    local_path = os.path.join(
        "outputs_json",
        str(user_id),
        str(video_id),
        "baduanjin_analysis",
        file_name
    )
    
    if os.path.exists(local_path):
        try:
            with open(local_path, 'r') as f:
                json_data = json.load(f)
            print(f"Successfully loaded {file_name} from local storage: {local_path}")
            return json_data
        except Exception as e:
            print(f"Error reading local file {local_path}: {e}")
    
    # File not found anywhere
    raise FileNotFoundError(f"JSON file {file_name} not found in Azure or local storage")

# Helper function to check if JSON file exists in Azure or local
async def json_file_exists(user_id: int, video_id: int, file_name: str) -> bool:
    """
    Check if JSON file exists in Azure or local storage
    """
    # Check Azure first
    try:
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if connection_string:
            blob_path = f"outputs_json/{user_id}/{video_id}/baduanjin_analysis/{file_name}"
            
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            blob_client = blob_service_client.get_blob_client(
                container="results",
                blob=blob_path
            )
            
            try:
                blob_client.get_blob_properties()
                return True
            except:
                pass
    except:
        pass
    
    # Check local file
    local_path = os.path.join(
        "outputs_json",
        str(user_id),
        str(video_id),
        "baduanjin_analysis",
        file_name
    )
    
    return os.path.exists(local_path)

# Helper function to upload JSON to Azure storage
async def upload_json_to_azure(json_data: Dict, user_id: int, video_id: int, file_name: str) -> str:
    """
    Upload JSON data to Azure storage using your existing path structure
    """
    try:
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not connection_string:
            print("No Azure connection string available")
            return None
            
        # Construct Azure blob path - matching your existing structure
        blob_path = f"outputs_json/{user_id}/{video_id}/baduanjin_analysis/{file_name}"
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = blob_service_client.get_blob_client(
            container="results",
            blob=blob_path
        )
        
        # Convert JSON to bytes
        json_bytes = json.dumps(json_data, indent=2).encode('utf-8')
        
        # Upload to Azure
        blob_client.upload_blob(json_bytes, overwrite=True)
        
        azure_url = f"https://baduanjintesting.blob.core.windows.net/results/{blob_path}"
        print(f"Successfully uploaded {file_name} to Azure: {azure_url}")
        return azure_url
        
    except Exception as e:
        print(f"Error uploading {file_name} to Azure: {e}")
        return None

async def run_extract_json_files(input_dir: str, output_dir: str, user_id: int, video_id: int, user_type: str = "master") -> bool:
    """
    Run the extract_json_files.py script to extract analysis JSON files
    """
    try:
        # Get the root directory
        root_dir = os.getcwd()
        
        # Construct the script path
        script_path = os.path.join(root_dir, "ml_pipeline", "extract_json_files.py")
        
        # Convert paths to use proper separators
        input_dir_full = os.path.join(root_dir, input_dir.replace('/', os.path.sep))
        output_dir_full = os.path.join(root_dir, output_dir.replace('/', os.path.sep))
        
        # Construct the command
        cmd = [
            sys.executable,
            script_path,
            "--input_dir", input_dir_full,
            "--output_dir", output_dir_full,
            "--user_type", user_type
        ]
        
        print(f"Running extract command: {' '.join(cmd)}")
        
        # Run the command synchronously
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Print output for debugging
        print(f"Extract stdout: {process.stdout}")
        print(f"Extract stderr: {process.stderr}")
        
        if process.returncode != 0:
            print(f"Extract failed with return code: {process.returncode}")
            print(f"Extract error: {process.stderr}")
            return False
            
        print("Extract completed successfully")
        
        # After successful extraction, upload JSON files to Azure
        await upload_extracted_json_files(output_dir_full, user_id, video_id, user_type)
        
        return True
        
    except Exception as e:
        print(f"Error running extract: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

async def upload_extracted_json_files(output_dir: str, user_id: int, video_id: int, user_type: str):
    """
    Upload the extracted JSON files to Azure storage
    """
    try:
        # List of JSON files to upload - matching your existing naming convention
        json_files = [
            f"{user_type}_joint_angles.json",
            f"{user_type}_smoothness.json",
            f"{user_type}_symmetry.json",
            f"{user_type}_balance.json",
            f"{user_type}_recommendations.json"
        ]
        
        for file_name in json_files:
            local_path = os.path.join(output_dir, file_name)
            if os.path.exists(local_path):
                try:
                    # Read the local JSON file
                    with open(local_path, 'r') as f:
                        json_data = json.load(f)
                    
                    # Upload to Azure
                    azure_url = await upload_json_to_azure(json_data, user_id, video_id, file_name)
                    if azure_url:
                        print(f"Uploaded {file_name} to Azure")
                    else:
                        print(f"Failed to upload {file_name} to Azure")
                        
                except Exception as e:
                    print(f"Error processing {file_name}: {e}")
            else:
                print(f"Local file not found: {local_path}")
                
    except Exception as e:
        print(f"Error uploading JSON files to Azure: {e}")

async def run_results_analysis(video_id: int, user_id: int) -> bool:
    """
    Run the results_analysis.py script for a video
    """
    try:
        # Get the root directory
        root_dir = os.getcwd()
        
        # Construct the script path
        script_path = os.path.join(root_dir, "ml_pipeline", "results_analysis.py")
        
        # Find the pose results and video files
        video_dir = os.path.join(root_dir, "outputs_json", str(user_id), str(video_id))
        
        # Find results JSON file
        results_files = [f for f in os.listdir(video_dir) if f.startswith("results_") and f.endswith(".json")]
        if not results_files:
            print(f"No results JSON found in {video_dir}")
            return False
            
        pose_results_path = os.path.join(video_dir, results_files[0])
        
        # Find video file (prefer non-web version)
        video_files = [f for f in os.listdir(video_dir) if f.endswith(".mp4") and not f.endswith("_web.mp4")]
        if not video_files:
            # Fallback to any MP4 file
            video_files = [f for f in os.listdir(video_dir) if f.endswith(".mp4")]
        
        if not video_files:
            print(f"No video files found in {video_dir}")
            return False
            
        video_path = os.path.join(video_dir, video_files[0])
        
        # Output directory
        output_dir = os.path.join(video_dir, "baduanjin_analysis")
        
        # Construct the command
        cmd = [
            sys.executable,
            script_path,
            "--pose_results", pose_results_path,
            "--video", video_path,
            "--output_dir", output_dir
        ]
        
        print(f"Running results analysis command: {' '.join(cmd)}")
        
        # Run the command synchronously
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if process.returncode != 0:
            print(f"Results analysis error: {process.stderr}")
            return False
            
        return True
        
    except Exception as e:
        print(f"Error running results analysis: {str(e)}")
        return False

@router.get("/master-videos/{master_id}")
async def get_master_videos(
    master_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Get analyzed videos from a specific master
    """
    # Verify the master exists
    master = db.query(models.User).filter(
        models.User.id == master_id,
        models.User.role == "master"
    ).first()
    
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    
    # Get master's analyzed videos
    videos = db.query(models.VideoUpload).filter(
        models.VideoUpload.user_id == master_id,
        models.VideoUpload.processing_status == "completed",
        models.VideoUpload.analyzed_video_path.isnot(None)
    ).all()
    
    return videos

@router.get("/user-extracted-videos")
async def get_user_extracted_videos(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Get user's videos that have extracted JSON files (checks both Azure and local)
    """
    # Get all completed videos
    videos = db.query(models.VideoUpload).filter(
        models.VideoUpload.user_id == current_user.id,
        models.VideoUpload.processing_status == "completed"
    ).all()
    
    # Filter only those with extracted JSON files
    extracted_videos = []
    user_type = "learner" if current_user.role == "learner" else "master"
    
    for video in videos:
        # Check if JSON files exist using the helper function
        json_file_name = f"{user_type}_joint_angles.json"
        
        if await json_file_exists(current_user.id, video.id, json_file_name):
            extracted_videos.append(video)
    
    return extracted_videos

@router.get("/master-extracted-videos/{master_id}")
async def get_master_extracted_videos(
    master_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Get master's videos that have extracted JSON files (checks both Azure and local)
    """
    # Verify master exists
    master = db.query(models.User).filter(
        models.User.id == master_id,
        models.User.role == "master"
    ).first()
    
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    
    # Get all completed videos
    videos = db.query(models.VideoUpload).filter(
        models.VideoUpload.user_id == master_id,
        models.VideoUpload.processing_status == "completed"
    ).all()
    
    # Filter only those with extracted JSON files
    extracted_videos = []
    
    for video in videos:
        # Check if master JSON files exist
        json_file_name = "master_joint_angles.json"
        
        if await json_file_exists(master_id, video.id, json_file_name):
            extracted_videos.append(video)
    
    return extracted_videos

@router.post("/extract/{video_id}")
async def extract_json_files(
    video_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Extract JSON files from analysis results for a specific video
    """
    # Get the video
    video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == video_id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail=f"Video with ID {video_id} not found")
    
    # Check if analysis has been completed
    if video.processing_status != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Video analysis must be completed first. Current status: {video.processing_status}"
        )
    
    # Determine user type
    video_owner = db.query(models.User).filter(
        models.User.id == video.user_id
    ).first()
    
    user_type = video_owner.role if video_owner else "learner"
    
    # Construct the paths - using your existing structure
    input_dir = f"outputs_json/{video.user_id}/{video_id}/baduanjin_analysis"
    output_dir = f"outputs_json/{video.user_id}/{video_id}/baduanjin_analysis"
    
    # Check if analysis directory exists
    analysis_dir = os.path.join(os.getcwd(), input_dir.replace('/', os.path.sep))
    
    # Check if the analysis report exists
    report_path = os.path.join(analysis_dir, "analysis_report.txt")
    
    if not os.path.exists(analysis_dir):
        # First, check if the basic video analysis was done
        json_dir = os.path.join(os.getcwd(), f"outputs_json/{video.user_id}/{video_id}")
        
        if not os.path.exists(json_dir):
            raise HTTPException(
                status_code=400,
                detail=f"No video analysis found. The video needs to be processed first."
            )
        
        # Check if we have the pose results JSON
        pose_results_files = [f for f in os.listdir(json_dir) if f.startswith("results_") and f.endswith(".json")]
        
        if not pose_results_files:
            raise HTTPException(
                status_code=400,
                detail=f"No pose estimation results found. Please process the video first."
            )
        
        # If we have pose results but no analysis report, we need to run results_analysis.py
        raise HTTPException(
            status_code=400,
            detail=f"The video has been processed but not analyzed. Run results_analysis.py for video ID {video_id} first."
        )
    
    if not os.path.exists(report_path):
        raise HTTPException(
            status_code=400,
            detail="Analysis report not found. Please run the full video analysis first."
        )
    
    # Check if JSON files already exist (check both Azure and local)
    expected_files = [
        f"{user_type}_joint_angles.json",
        f"{user_type}_smoothness.json",
        f"{user_type}_symmetry.json",
        f"{user_type}_balance.json",
        f"{user_type}_recommendations.json"
    ]
    
    existing_files = []
    azure_files = []
    local_files = []
    
    # Check which files exist where
    for file_name in expected_files:
        # Check Azure
        try:
            connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            if connection_string:
                blob_path = f"outputs_json/{video.user_id}/{video_id}/baduanjin_analysis/{file_name}"
                blob_service_client = BlobServiceClient.from_connection_string(connection_string)
                blob_client = blob_service_client.get_blob_client(container="results", blob=blob_path)
                
                try:
                    blob_client.get_blob_properties()
                    azure_files.append(file_name)
                    existing_files.append(file_name)
                except:
                    pass
        except:
            pass
        
        # Check local
        local_path = os.path.join(analysis_dir, file_name)
        if os.path.exists(local_path):
            local_files.append(file_name)
            if file_name not in existing_files:
                existing_files.append(file_name)
    
    if len(existing_files) == len(expected_files):
        # Files already exist, no need to extract again
        return {
            "status": "success",
            "message": "JSON files already exist",
            "output_dir": output_dir,
            "existing_files": existing_files,
            "azure_files": azure_files,
            "local_files": local_files,
            "user_type": user_type
        }
    
    # Run the extraction with user type
    success = await run_extract_json_files(input_dir, output_dir, video.user_id, video_id, user_type)
    
    if success:
        # Check if files were actually created
        created_files = []
        for f in expected_files:
            if os.path.exists(os.path.join(analysis_dir, f)):
                created_files.append(f)
        
        return {
            "status": "success",
            "message": "JSON files extracted and uploaded to Azure successfully",
            "output_dir": output_dir,
            "created_files": created_files,
            "user_type": user_type
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to extract JSON files. Check the server logs for details."
        )

@router.post("/analyze/{video_id}")
async def analyze_video_with_results_analysis(
    video_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Run results_analysis.py for a video if not already done
    """
    # Get the video
    video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == video_id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail=f"Video with ID {video_id} not found")
    
    # Check if analysis already exists
    analysis_dir = os.path.join("outputs_json", str(video.user_id), str(video_id), "baduanjin_analysis")
    report_path = os.path.join(analysis_dir, "analysis_report.txt")
    
    if os.path.exists(report_path):
        return {
            "status": "already_analyzed",
            "message": "Video already analyzed",
            "analysis_dir": analysis_dir
        }
    
    # Run the analysis
    success = await run_results_analysis(video_id, video.user_id)
    
    if success:
        return {
            "status": "success",
            "message": "Analysis completed successfully",
            "analysis_dir": analysis_dir
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to run analysis. Check the logs for details."
        )

@router.get("/master-data/{video_id}")
async def get_master_data(
    video_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Get master data and extracted JSON files for a specific video (supports Azure storage)
    """
    # Get the video
    video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == video_id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Get the master user
    master = db.query(models.User).filter(
        models.User.id == video.user_id,
        models.User.role == "master"
    ).first()
    
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    
    master_data = {
        "id": master.id,
        "name": master.name,
        "email": master.email
    }
    
    video_data = {
        "id": video.id,
        "title": video.title,
        "brocade_type": video.brocade_type
    }
    
    # Load JSON files from Azure or local storage
    json_files = {}
    json_file_names = [
        "master_joint_angles.json",
        "master_smoothness.json", 
        "master_symmetry.json",
        "master_balance.json",
        "master_recommendations.json"
    ]
    
    for file_name in json_file_names:
        try:
            # Use the helper function to read from Azure or local
            json_data = await read_json_file_azure_local(video.user_id, video_id, file_name)
            json_files[file_name.replace(".json", "")] = json_data
            
        except FileNotFoundError:
            print(f"JSON file not found: {file_name}")
        except Exception as e:
            print(f"Error loading {file_name}: {str(e)}")
    
    return {
        "masterData": master_data,
        "videoData": video_data,
        "analysisData": json_files
    }

@router.get("/data/{video_id}/{file_name}")
async def get_analysis_data_file(
    video_id: int,
    file_name: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Get specific JSON data file for a video (supports Azure storage)
    """
    # Get the video to determine user
    video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == video_id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    try:
        # Use the helper function to read from Azure or local
        json_data = await read_json_file_azure_local(video.user_id, video_id, file_name)
        return json_data
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Data file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading data file: {str(e)}")

@router.get("/compare/{user_video_id}/{master_video_id}")
async def compare_analysis(
    user_video_id: int,
    master_video_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Compare user's video analysis with master's video analysis (supports Azure storage)
    """
    # Verify user owns the video
    user_video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == user_video_id,
        models.VideoUpload.user_id == current_user.id
    ).first()
    
    if not user_video:
        raise HTTPException(status_code=404, detail="User video not found")
    
    # Get master video
    master_video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == master_video_id
    ).first()
    
    if not master_video:
        raise HTTPException(status_code=404, detail="Master video not found")
    
    # Load user's analysis data
    user_data = {}
    learner_json_files = [
        "learner_joint_angles.json",
        "learner_smoothness.json",
        "learner_symmetry.json",
        "learner_balance.json"
    ]
    
    for file_name in learner_json_files:
        try:
            # Use helper function to read from Azure or local
            json_data = await read_json_file_azure_local(current_user.id, user_video_id, file_name)
            key = file_name.replace("learner_", "").replace(".json", "")
            user_data[key] = json_data
            
        except FileNotFoundError:
            print(f"User JSON file not found: {file_name}")
        except Exception as e:
            print(f"Error loading user {file_name}: {str(e)}")
    
    # Load master's analysis data  
    master_data = {}
    master_json_files = [
        "master_joint_angles.json",
        "master_smoothness.json",
        "master_symmetry.json",
        "master_balance.json"
    ]
    
    for file_name in master_json_files:
        try:
            # Use helper function to read from Azure or local
            json_data = await read_json_file_azure_local(master_video.user_id, master_video_id, file_name)
            key = file_name.replace("master_", "").replace(".json", "")
            master_data[key] = json_data
            
        except FileNotFoundError:
            print(f"Master JSON file not found: {file_name}")
        except Exception as e:
            print(f"Error loading master {file_name}: {str(e)}")
    
    # Generate comparison and recommendations
    comparison_result = {
        "userJointAngles": user_data.get('joint_angles', {}),
        "masterJointAngles": master_data.get('joint_angles', {}),
        "userSmoothness": user_data.get('smoothness', {}),
        "masterSmoothness": master_data.get('smoothness', {}),
        "userSymmetry": user_data.get('symmetry', {}),
        "masterSymmetry": master_data.get('symmetry', {}),
        "userBalance": user_data.get('balance', {}),
        "masterBalance": master_data.get('balance', {}),
        "recommendations": generate_comparison_recommendations(user_data, master_data)
    }
    
    return comparison_result

def generate_comparison_recommendations(user_data: Dict, master_data: Dict) -> List[str]:
    """
    Generate recommendations based on comparison between learner and master data
    """
    recommendations = []
    
    # Compare overall smoothness
    user_smoothness = user_data.get('smoothness', {}).get('overallSmoothness', 1.0)
    master_smoothness = master_data.get('smoothness', {}).get('overallSmoothness', 0.9)
    
    if user_smoothness > master_smoothness * 1.1:
        recommendations.append(f"Your movement smoothness ({user_smoothness:.2f}) needs improvement. "
                             f"Master's smoothness is {master_smoothness:.2f}. "
                             "Focus on smoother transitions between movements.")
    
    # Compare overall symmetry
    user_symmetry = user_data.get('symmetry', {}).get('overallSymmetry', 0.9)
    master_symmetry = master_data.get('symmetry', {}).get('overallSymmetry', 0.95)
    
    if user_symmetry < master_symmetry * 0.95:
        recommendations.append(f"Your movement symmetry ({user_symmetry:.2f}) is below the master's level ({master_symmetry:.2f}). "
                             "Work on balancing left and right side movements.")
    
    # Compare overall balance/stability
    user_balance = user_data.get('balance', {}).get('overallStability', 0.85)
    master_balance = master_data.get('balance', {}).get('overallStability', 0.9)
    
    if user_balance < master_balance * 0.95:
        recommendations.append(f"Your balance stability ({user_balance:.2f}) needs improvement compared to the master ({master_balance:.2f}). "
                             "Practice balance exercises and focus on center of mass control.")
    
    # Compare joint angle ranges
    if 'joint_angles' in user_data and 'joint_angles' in master_data:
        user_rom = user_data['joint_angles'].get('rangeOfMotion', {})
        master_rom = master_data['joint_angles'].get('rangeOfMotion', {})
        
        for joint in user_rom:
            if joint in master_rom:
                user_range = user_rom[joint]['max'] - user_rom[joint]['min']
                master_range = master_rom[joint]['max'] - master_rom[joint]['min']
                
                if abs(user_range - master_range) > 10:  # More than 10 degrees difference
                    recommendations.append(f"Your {joint} range of motion ({user_range:.0f}°) differs from "
                                         f"the master's ({master_range:.0f}°). Practice flexibility exercises.")
    
    # Add general recommendations
    recommendations.extend([
        "Study the master's key pose positions and practice matching them",
        "Pay attention to the timing and rhythm of the master's movements",
        "Focus on maintaining proper alignment throughout the sequence",
        "Practice with slower movements first to improve control before matching the master's speed"
    ])
    
    return recommendations