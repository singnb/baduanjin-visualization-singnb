# services/video_processor.py

import os
import subprocess
import json
import logging
from sqlalchemy.orm import Session
import models

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
UPLOAD_DIR = "uploads"
PROCESSED_DIR = "processed"
ANALYSIS_DIR = "analysis"

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(ANALYSIS_DIR, exist_ok=True)

def process_video(video_id: int, db: Session):
    """Process a video using mmpose and update the database with results"""
    try:
        # Get video record from database
        video = db.query(models.VideoUpload).filter(models.VideoUpload.id == video_id).first()
        if not video:
            logger.error(f"Video with id {video_id} not found")
            return
        
        # Update status to processing
        video.processing_status = "processing"
        db.commit()
        
        # Get file paths
        video_path = video.video_path
        output_dir = os.path.join(PROCESSED_DIR, f"video_{video_id}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Build command for mmpose
        command = [
            "python", "demo/topdown_demo_mmdet_no_heatmap.py",
            "demo/faster_rcnn_r50_fpn_coco.py",
            "https://download.openmmlab.com/mmdetection/v2.0/faster_rcnn/faster_rcnn_r50_fpn_1x_coco/faster_rcnn_r50_fpn_1x_coco_20200130-047c8118.pth",
            "configs/td-hm_hrnet-w32_8xb64-210e_coco-256x192.py",
            "https://download.openmmlab.com/mmpose/top_down/hrnet/hrnet_w32_coco_256x192-c78dce93_20200708.pth",
            "--input", video_path,
            "--output-root", output_dir,
            "--device", "cuda:0",
            "--bbox-thr", "0.5",
            "--kpt-thr", "0.2",
            "--nms-thr", "0.3",
            "--radius", "5",
            "--thickness", "2",
            "--draw-bbox",
            "--show-kpt-idx",
            "--save-predictions"
        ]
        
        # Execute command
        logger.info(f"Processing video {video_id} with mmpose")
        process = subprocess.run(command, capture_output=True, text=True)
        
        if process.returncode != 0:
            logger.error(f"Error processing video: {process.stderr}")
            video.processing_status = "failed"
            db.commit()
            return
        
        # Find generated JSON file
        json_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
        if not json_files:
            logger.error("No JSON files were generated")
            video.processing_status = "failed"
            db.commit()
            return
        
        json_path = os.path.join(output_dir, json_files[0])
        
        # Update video record with JSON path
        video.json_path = json_path
        video.processing_status = "completed"
        db.commit()
        
        # Analyze the video data
        analyze_video_data(video_id, db)
        
        logger.info(f"Successfully processed video {video_id}")
        
    except Exception as e:
        logger.error(f"Error in video processing: {str(e)}")
        # Update status to failed
        try:
            video = db.query(models.VideoUpload).filter(models.VideoUpload.id == video_id).first()
            if video:
                video.processing_status = "failed"
                db.commit()
        except Exception as inner_e:
            logger.error(f"Error updating video status: {str(inner_e)}")

def analyze_video_data(video_id: int, db: Session):
    """Analyze the processed video data and create analysis results"""
    try:
        # Get video record
        video = db.query(models.VideoUpload).filter(models.VideoUpload.id == video_id).first()
        if not video or not video.json_path or not os.path.exists(video.json_path):
            logger.error(f"Video data not found for video {video_id}")
            return
        
        # Load JSON data
        with open(video.json_path, 'r') as f:
            pose_data = json.load(f)
        
        # Process data for different analysis types
        joint_angle_data = process_joint_angles(pose_data, video.brocade_type)
        balance_data = process_balance_metrics(pose_data, video.brocade_type)
        smoothness_data = process_smoothness(pose_data, video.brocade_type)
        symmetry_data = process_symmetry(pose_data, video.brocade_type)
        
        # Generate recommendations
        recommendations = generate_recommendations(
            joint_angle_data, 
            balance_data, 
            smoothness_data, 
            symmetry_data,
            video.brocade_type
        )
        
        # Check if analysis already exists
        analysis = db.query(models.AnalysisResult).filter(
            models.AnalysisResult.video_id == video_id
        ).first()
        
        if analysis:
            # Update existing analysis
            analysis.joint_angle_data = json.dumps(joint_angle_data)
            analysis.balance_data = json.dumps(balance_data)
            analysis.smoothness_data = json.dumps(smoothness_data)
            analysis.symmetry_data = json.dumps(symmetry_data)
            analysis.recommendations = json.dumps(recommendations)
        else:
            # Create new analysis
            analysis = models.AnalysisResult(
                video_id=video_id,
                joint_angle_data=json.dumps(joint_angle_data),
                balance_data=json.dumps(balance_data),
                smoothness_data=json.dumps(smoothness_data),
                symmetry_data=json.dumps(symmetry_data),
                recommendations=json.dumps(recommendations)
            )
            db.add(analysis)
        
        db.commit()
        logger.info(f"Analysis completed for video {video_id}")
        
    except Exception as e:
        logger.error(f"Error in video analysis: {str(e)}")

# Placeholder functions for the actual analysis
# These would be implemented with proper biomechanical analysis algorithms
def process_joint_angles(pose_data, brocade_type):
    # Implement joint angle analysis based on the brocade type
    # For now, return placeholder data
    return {"angles": [{"frame": i, "knee": 150 - i % 30, "elbow": 90 + i % 45} for i in range(100)]}

def process_balance_metrics(pose_data, brocade_type):
    # Implement balance analysis
    return {"stability": [{"frame": i, "value": 0.7 + 0.3 * (i % 20) / 20} for i in range(100)]}

def process_smoothness(pose_data, brocade_type):
    # Implement smoothness analysis
    return {"jerk": [{"frame": i, "value": 0.2 + 0.4 * abs((i % 40) - 20) / 20} for i in range(100)]}

def process_symmetry(pose_data, brocade_type):
    # Implement symmetry analysis
    return {"leftRight": [{"frame": i, "value": 0.6 + 0.4 * (i % 30) / 30} for i in range(100)]}

def generate_recommendations(joint_angle_data, balance_data, smoothness_data, symmetry_data, brocade_type):
    # Generate personalized recommendations based on the analysis
    recommendations = []
    
    # Joint angle recommendations
    avg_knee = sum(item["knee"] for item in joint_angle_data["angles"]) / len(joint_angle_data["angles"])
    if avg_knee < 130:
        recommendations.append({
            "category": "joint_angle",
            "issue": "knee_flexion",
            "message": "Try to maintain a greater knee angle during the exercise."
        })
    
    # Balance recommendations
    avg_stability = sum(item["value"] for item in balance_data["stability"]) / len(balance_data["stability"])
    if avg_stability < 0.8:
        recommendations.append({
            "category": "balance",
            "issue": "stability",
            "message": "Work on improving your balance by focusing on a fixed point."
        })
    
    # Smoothness recommendations
    avg_jerk = sum(item["value"] for item in smoothness_data["jerk"]) / len(smoothness_data["jerk"])
    if avg_jerk > 0.4:
        recommendations.append({
            "category": "smoothness",
            "issue": "jerkiness",
            "message": "Try to make your movements more fluid and continuous."
        })
    
    # Symmetry recommendations
    avg_symmetry = sum(item["value"] for item in symmetry_data["leftRight"]) / len(symmetry_data["leftRight"])
    if avg_symmetry < 0.7:
        recommendations.append({
            "category": "symmetry",
            "issue": "imbalance",
            "message": "Focus on equal engagement of both sides of your body."
        })
    
    return recommendations