"""
config.py - Configuration Settings - ENHANCED with Exercise Tracking
"""

import os
from pathlib import Path

class Config:
    """Application configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'baduanjin_secret_key'
    
    # Pi Configuration
    PI_IP = "172.20.10.6"
    PI_PORT = 5001
    
    # Ngrok Configuration
    NGROK_STATIC_URL = "https://mongoose-hardy-caiman.ngrok-free.app"
    
    # Camera Configuration
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT = 480
    CAMERA_FPS = 30
    
    # YOLO Configuration
    YOLO_MODEL_PATH = Path("models") / "yolov8n-pose.pt"
    YOLO_CONFIDENCE = 0.5
    
    # Recording Configuration
    RECORDINGS_DIR = Path.cwd() / "recordings"
    VIDEO_CODEC = 'mp4v'
    VIDEO_FPS = 15.0
    VIDEO_QUALITY = 80  # JPEG quality for streaming
    MOBILE_VIDEO_QUALITY = 50  # Reduced quality for mobile networks
    
    # 🚀 NEW: Exercise Tracking Configuration
    BADUANJIN_DATA_DIR = Path.cwd() / "baduanjin_data"
    EXERCISE_TRACKING_ENABLED = True
    POSE_CONFIDENCE_THRESHOLD = 0.5  # Minimum pose detection confidence
    POSE_HOLD_DURATION = 2.0  # Seconds to hold pose for completion
    TRANSITION_TOLERANCE = 0.3  # Movement smoothness tolerance
    FORM_SCORE_THRESHOLD = 70.0  # Minimum score for "good" form
    REAL_TIME_FEEDBACK_FILE = Path.cwd() / "real_time_feedback.json"
    
    # Exercise Analysis Parameters
    SHOULDER_ALIGNMENT_TOLERANCE = 20  # pixels
    HIP_ALIGNMENT_TOLERANCE = 20  # pixels
    ARM_EXTENSION_THRESHOLD = 80  # pixels
    SPINE_ALIGNMENT_TOLERANCE = 30  # pixels
    
    # Session Management
    MAX_POSE_HISTORY = 100  # Maximum poses to keep in memory
    MAX_FEEDBACK_HISTORY = 50  # Maximum feedback items to keep
    SESSION_EXPORT_FORMAT = "json"  # Export format for session data
    
    # Network Configuration
    STREAM_EMIT_INTERVAL = 0.1  # 10 FPS for WebSocket emission
    FRAME_BUFFER_SIZE = 3  # Max frames in buffer
    
    # Mobile Network Optimization
    MOBILE_PING_TIMEOUT = 300  # 5 minutes
    MOBILE_PING_INTERVAL = 120  # 2 minutes
    MOBILE_MAX_HTTP_BUFFER = 1000000  # 1MB
    
    # API Timeouts
    API_TIMEOUT = 10.0
    DOWNLOAD_TIMEOUT = 300.0  # 5 minutes for file downloads
    
    # 🚀 NEW: Exercise Feedback Configuration
    FEEDBACK_UPDATE_INTERVAL = 1.0  # Seconds between feedback updates
    OVERLAY_TRANSPARENCY = 0.7  # Transparency for exercise overlay (0.0-1.0)
    CORRECTION_MESSAGE_LIMIT = 2  # Max correction messages to show at once
    FEEDBACK_MESSAGE_LIMIT = 2  # Max feedback messages to show at once
    
    # Real-time Analysis Settings
    MOVEMENT_VARIANCE_THRESHOLD = 10  # For fluidity analysis
    BALANCE_THRESHOLD = 100  # Foot distance for balance analysis
    HEIGHT_DIFFERENCE_TOLERANCE = 50  # Arm height difference tolerance
    
    @classmethod
    def init_directories(cls):
        """Initialize required directories"""
        cls.RECORDINGS_DIR.mkdir(exist_ok=True)
        
        # Create models directory if it doesn't exist
        models_dir = Path("models")
        models_dir.mkdir(exist_ok=True)
        
        # 🚀 NEW: Create exercise tracking directory
        cls.BADUANJIN_DATA_DIR.mkdir(exist_ok=True)
        
        print(f"📁 Recordings directory: {cls.RECORDINGS_DIR}")
        print(f"📁 Models directory: {models_dir}")
        print(f"📁 Exercise data directory: {cls.BADUANJIN_DATA_DIR}")
        
        return True
    
    @classmethod
    def get_exercise_config(cls):
        """Get exercise-specific configuration"""
        return {
            "confidence_threshold": cls.POSE_CONFIDENCE_THRESHOLD,
            "hold_duration": cls.POSE_HOLD_DURATION,
            "transition_tolerance": cls.TRANSITION_TOLERANCE,
            "form_score_threshold": cls.FORM_SCORE_THRESHOLD,
            "analysis_params": {
                "shoulder_tolerance": cls.SHOULDER_ALIGNMENT_TOLERANCE,
                "hip_tolerance": cls.HIP_ALIGNMENT_TOLERANCE,
                "arm_threshold": cls.ARM_EXTENSION_THRESHOLD,
                "spine_tolerance": cls.SPINE_ALIGNMENT_TOLERANCE
            }
        }
    
    @classmethod
    def get_display_config(cls):
        """Get display and overlay configuration"""
        return {
            "overlay_transparency": cls.OVERLAY_TRANSPARENCY,
            "correction_limit": cls.CORRECTION_MESSAGE_LIMIT,
            "feedback_limit": cls.FEEDBACK_MESSAGE_LIMIT,
            "update_interval": cls.FEEDBACK_UPDATE_INTERVAL
        }