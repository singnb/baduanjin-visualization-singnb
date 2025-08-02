# /baduanjin_analysis/web_server.py 
# !/usr/bin/env python3

"""
Revised Baduanjin Web Server for Raspberry Pi 5
Compatible with Azure pi-service middleware
Maintains legacy API endpoints while implementing proper session/recording workflow
"""

from flask import Flask, Response, jsonify, render_template, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import cv2
import numpy as np
import time
import json
import threading
import base64
import io
from datetime import datetime
import sys
import site
from pathlib import Path
from flask import send_file
import uuid
import os

# Add user site-packages to path
sys.path.append(site.getusersitepackages())

# Import your existing analyzer
try:
    from picamera2 import Picamera2
    from ultralytics import YOLO
    CAMERA_AVAILABLE = True
    YOLO_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    CAMERA_AVAILABLE = False
    YOLO_AVAILABLE = False

app = Flask(__name__)
app.config['SECRET_KEY'] = 'baduanjin_secret_key'

# CORS configuration
CORS(app, cors_allowed_origins="*")

# SocketIO configuration  
socketio = SocketIO(app, 
    cors_allowed_origins="*",
    async_mode='threading',
    logger=False,  # Disable to reduce ngrok overhead
    engineio_logger=False,  # Disable to reduce ngrok overhead
    
    # Ngrok-optimized settings
    ping_timeout=300,  # Longer timeout for mobile network
    ping_interval=120,  # Less frequent pings for mobile
    
    # Important: These settings help with ngrok static URLs
    transports=['polling'],  # Force polling instead of WebSocket for better ngrok compatibility
    allow_upgrades=False,    # Prevent WebSocket upgrade attempts
    
    # Additional stability settings
    max_http_buffer_size=1e6  # 1MB buffer for larger frames
)

class BaduanjinWebAnalyzer:
    def __init__(self):
        self.analyzer = None
        
        # Session State (tracks what Azure pi-service thinks is happening)
        self.is_running = False  # Streaming state for Azure pi-service
        self.current_session = None
        self.session_start_time = None
        
        # Recording State (separate from session - this is the NEW functionality)
        self.is_recording = False
        self.current_recording = None
        self.video_writer = None
        self.recording_start_time = None
        self.recordings_dir = Path.cwd() / "recordings"
        self.recordings_dir.mkdir(exist_ok=True)
        
        # Frame and Data State
        self.current_frame = None
        self.pose_data = []
        self.session_stats = {
            'total_frames': 0,
            'persons_detected': 0,
            'session_start': None,
            'current_fps': 0
        }
        
        if CAMERA_AVAILABLE:
            self.setup_analyzer()
    
    def setup_analyzer(self):
        """Initialize the pose analyzer - FIXED MODEL PATH"""
        try:
            # Initialize camera
            self.picam2 = Picamera2()
            config = self.picam2.create_preview_configuration(
                main={"format": 'XRGB8888', "size": (640, 480)}
            )
            self.picam2.configure(config)
            
            # Initialize YOLO with models folder path
            if YOLO_AVAILABLE:
                model_path = Path("models") / "yolov8n-pose.pt"
                if not model_path.exists():
                    # Fallback to root directory
                    model_path = Path("yolov8n-pose.pt")
                    if not model_path.exists():
                        print(f"❌ YOLO model not found in models/ or root directory")
                        self.model = None
                        return
                
                print(f"📦 Loading YOLO model from: {model_path}")
                self.model = YOLO(str(model_path))
                print(f"✅ YOLO model loaded successfully")
            else:
                self.model = None
                
            print("✅ Analyzer setup complete")
            
        except Exception as e:
            print(f"❌ Analyzer setup failed: {e}")
            self.analyzer = None
    
    def apply_symmetry_correction(self, keypoints, confidences):
        """Apply symmetry correction (from your Cell 9)"""
        if len(keypoints) == 0:
            return keypoints, confidences
            
        left_shoulder_idx = 5
        right_shoulder_idx = 6
        
        if confidences[left_shoulder_idx] > 0.5 and confidences[right_shoulder_idx] > 0.5:
            x_sym = (keypoints[left_shoulder_idx, 0] + keypoints[right_shoulder_idx, 0]) / 2
            
            symmetric_pairs = [(9, 10), (7, 8), (13, 14), (15, 16)]
            corrected_kpts = keypoints.copy()
            
            for left_idx, right_idx in symmetric_pairs:
                c_l, c_r = confidences[left_idx], confidences[right_idx]
                p_l, p_r = keypoints[left_idx], keypoints[right_idx]
                
                if c_l > 0.5 and c_r < 0.5:
                    p_r_sym = np.array([2 * x_sym - p_l[0], p_l[1]])
                    alpha = c_r / (c_l + c_r) if c_l + c_r > 0 else 0
                    corrected_kpts[right_idx] = alpha * p_r + (1 - alpha) * p_r_sym
                elif c_r > 0.5 and c_l < 0.5:
                    p_l_sym = np.array([2 * x_sym - p_r[0], p_r[1]])
                    alpha = c_l / (c_r + c_l) if c_r + c_l > 0 else 0
                    corrected_kpts[left_idx] = alpha * p_l + (1 - alpha) * p_l_sym
            
            return corrected_kpts, confidences
        return keypoints, confidences
    
    def draw_pose(self, frame, keypoints, confidences):
        """Draw pose with skeleton (from your Cell 9)"""
        skeleton_connections = [
            (0, 1), (0, 2), (1, 3), (2, 4),  # Head
            (5, 6), (5, 11), (6, 12), (11, 12),  # Torso
            (5, 7), (7, 9), (6, 8), (8, 10),  # Arms
            (11, 13), (13, 15), (12, 14), (14, 16)  # Legs
        ]
        
        # Draw keypoints
        for i, (x, y) in enumerate(keypoints):
            if confidences[i] > 0.5:
                if i in [0, 1, 2, 3, 4]:  # Head
                    color = (255, 255, 0)
                elif i in [5, 6, 7, 8, 9, 10]:  # Upper body
                    color = (0, 255, 0)
                else:  # Lower body
                    color = (255, 0, 0)
                    
                cv2.circle(frame, (int(x), int(y)), 6, color, -1)
                cv2.putText(frame, str(i), (int(x)+8, int(y)), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
        
        # Draw skeleton
        for connection in skeleton_connections:
            pt1_idx, pt2_idx = connection
            if confidences[pt1_idx] > 0.5 and confidences[pt2_idx] > 0.5:
                pt1 = keypoints[pt1_idx]
                pt2 = keypoints[pt2_idx]
                if pt1[0] > 0 and pt1[1] > 0 and pt2[0] > 0 and pt2[1] > 0:
                    cv2.line(frame, (int(pt1[0]), int(pt1[1])), 
                           (int(pt2[0]), int(pt2[1])), (0, 0, 255), 3)
        
        return frame
    
    def process_frame(self, frame):
        """Process frame for pose detection"""
        if not self.model:
            return []
            
        try:
            results = self.model(frame, conf=0.5, verbose=False, device='cpu')
            processed_data = []
            
            for result in results:
                if result.keypoints is not None:
                    keypoints = result.keypoints.xy.cpu().numpy()
                    confidences = result.keypoints.conf.cpu().numpy()
                    
                    for person_idx in range(keypoints.shape[0]):
                        person_kpts = keypoints[person_idx]
                        person_confs = confidences[person_idx]
                        
                        corrected_kpts, corrected_confs = self.apply_symmetry_correction(
                            person_kpts, person_confs
                        )
                        processed_data.append({
                            'keypoints': corrected_kpts.tolist(),
                            'confidences': corrected_confs.tolist(),
                            'person_id': person_idx
                        })
            
            return processed_data
        except Exception as e:
            print(f"❌ Processing error: {e}")
            return []
    
    # === RECORDING MANAGEMENT (NEW - for actual video files) ===
    def start_recording(self):
        """Start video recording during active session"""
        try:
            if not self.is_running:
                return {
                    "success": False,
                    "message": "Cannot start recording - no active session"
                }
            
            if self.is_recording:
                return {
                    "success": True,
                    "message": "Recording already active",
                    "was_already_recording": True,
                    "recording_filename": getattr(self.current_recording, 'filename', 'unknown')
                }
            
            # Generate recording filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"baduanjin_recording_{timestamp}.mp4"
            filepath = self.recordings_dir / filename
            
            # Initialize video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(
                str(filepath), fourcc, 15.0, (640, 480)
            )
            
            if not self.video_writer.isOpened():
                return {
                    "success": False,
                    "message": "Failed to initialize video writer"
                }
            
            # Set recording state
            self.is_recording = True
            self.recording_start_time = datetime.now()
            self.current_recording = {
                "filename": filename,
                "filepath": str(filepath),
                "start_time": self.recording_start_time.isoformat()
            }
            
            print(f"🔴 Recording started: {filename}")
            
            return {
                "success": True,
                "message": "Recording started successfully",
                "recording_info": {
                    "filename": filename,
                    "start_time": self.recording_start_time.isoformat()
                }
            }
            
        except Exception as e:
            print(f"❌ Error starting recording: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to start recording"
            }
    
    def stop_recording(self):
        """Stop video recording"""
        try:
            if not self.is_recording:
                return {
                    "success": False,
                    "message": "No active recording to stop"
                }
            
            recording_info = self.current_recording.copy() if self.current_recording else {}
            recording_duration = 0
            
            # Calculate recording duration
            if self.recording_start_time:
                recording_duration = (datetime.now() - self.recording_start_time).total_seconds()
            
            # Close video writer
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            
            # Update recording info
            recording_info.update({
                "end_time": datetime.now().isoformat(),
                "duration_seconds": round(recording_duration, 2),
                "status": "completed"
            })
            
            # Clear recording state
            self.is_recording = False
            self.recording_start_time = None
            
            # Verify file was created
            if self.current_recording and Path(self.current_recording["filepath"]).exists():
                file_size = Path(self.current_recording["filepath"]).stat().st_size
                recording_info["file_size"] = file_size
                print(f"✅ Recording saved: {self.current_recording['filename']} ({file_size} bytes)")
            else:
                print(f"⚠️ Recording file not found: {self.current_recording.get('filepath', 'unknown')}")
            
            filename = self.current_recording.get("filename", "unknown") if self.current_recording else "unknown"
            self.current_recording = None
            
            return {
                "success": True,
                "message": "Recording stopped successfully",
                "recording_info": recording_info
            }
            
        except Exception as e:
            print(f"❌ Error stopping recording: {e}")
            self.is_recording = False
            self.recording_start_time = None
            self.current_recording = None
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to stop recording"
            }
    
    # === STREAMING MANAGEMENT (for Azure pi-service compatibility) ===
    def start_stream(self):
        """Start the video stream (called by Azure pi-service via /api/start)"""
        try:
            if not CAMERA_AVAILABLE:
                print("❌ Camera not available")
                return False
                
            if self.is_running:
                print("⚠️ Stream already running")
                return True
                
            # Initialize camera if not already done
            if not hasattr(self, 'picam2') or self.picam2 is None:
                self.setup_analyzer()
                
            if not hasattr(self, 'picam2') or self.picam2 is None:
                print("❌ Failed to initialize camera")
                return False
            
            # Set running flag (this is what Azure pi-service checks)
            self.is_running = True
            self.session_start_time = datetime.now()
            self.session_stats['session_start'] = self.session_start_time.isoformat()
            
            # Start camera
            try:
                self.picam2.start()
                print("✅ Camera started successfully")
            except Exception as cam_error:
                print(f"❌ Camera start error: {cam_error}")
                self.is_running = False
                return False
            
            # Start stream loop in separate thread
            def stream_loop():
                fps_counter = 0
                fps_start_time = time.time()
                last_emit_time = 0
                
                print("🎥 Starting stream loop...")
                
                while self.is_running:
                    try:
                        # Capture frame
                        frame = self.picam2.capture_array()
                        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                        
                        # Process pose
                        pose_data = self.process_frame(frame_bgr)
                        self.pose_data = pose_data
                        
                        # Draw pose overlay
                        display_frame = frame_bgr.copy()
                        for person_data in pose_data:
                            keypoints = np.array(person_data['keypoints'])
                            confidences = np.array(person_data['confidences'])
                            display_frame = self.draw_pose(display_frame, keypoints, confidences)
                        
                        # Add overlay info
                        cv2.putText(display_frame, 'Baduanjin Live Analysis', (10, 30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                        cv2.putText(display_frame, f'FPS: {self.session_stats.get("current_fps", 0)}', (10, 60), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        cv2.putText(display_frame, f'Persons: {len(pose_data)}', (10, 85), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        
                        # Add recording indicator and save frame if recording
                        if self.is_recording:
                            cv2.putText(display_frame, '🔴 REC', (10, 115), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                            # Save frame to video file (save original without overlay)
                            if self.video_writer and self.video_writer.isOpened():
                                self.video_writer.write(frame_bgr)
                        
                        # Calculate FPS
                        fps_counter += 1
                        if fps_counter % 30 == 0:
                            elapsed = time.time() - fps_start_time
                            current_fps = 30 / elapsed if elapsed > 0 else 0
                            fps_start_time = time.time()
                            self.session_stats['current_fps'] = round(current_fps, 1)
                        
                        # Update stats
                        self.session_stats['total_frames'] = self.session_stats.get('total_frames', 0) + 1
                        self.session_stats['persons_detected'] = len(pose_data)
                        
                        # Store current frame (with overlay for display)
                        self.current_frame = display_frame.copy()
                        
                        # Emit frame data (throttled)
                        current_time = time.time()
                        if current_time - last_emit_time > 0.1:  # 10 FPS emission
                            try:
                                _, buffer = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                                
                                frame_data = {
                                    'image': frame_base64,
                                    'pose_data': pose_data,
                                    'stats': self.session_stats,
                                    'is_recording': self.is_recording,
                                    'timestamp': int(current_time * 1000)
                                }
                                
                                emit_frame_safely(frame_data)
                                last_emit_time = current_time
                                    
                            except Exception as emit_error:
                                print(f"⚠️ Frame emission error: {emit_error}")
                        
                        time.sleep(0.033)  # ~30 FPS
                        
                    except Exception as e:
                        print(f"❌ Stream loop error: {e}")
                        time.sleep(0.1)
                        if not self.is_running:  # Exit if stop was called
                            break
                
                print("🏁 Stream loop ended")
            
            # Start stream thread
            self.stream_thread = threading.Thread(target=stream_loop, daemon=True)
            self.stream_thread.start()
            
            print("✅ Stream started successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error starting stream: {e}")
            self.is_running = False
            return False
    
    def stop_stream(self):
        """Stop the video stream (called by Azure pi-service via /api/stop)"""
        try:
            print("🛑 Stopping stream...")
            self.is_running = False
            
            # Stop any active recording
            if self.is_recording:
                print("⚠️ Auto-stopping recording when stream ends...")
                self.stop_recording()
            
            if hasattr(self, 'picam2') and self.picam2 is not None:
                try:
                    self.picam2.stop()
                    print("✅ Camera stopped")
                except Exception as cam_error:
                    print(f"⚠️ Camera stop warning: {cam_error}")
            
            # Wait for thread to finish
            if hasattr(self, 'stream_thread') and self.stream_thread.is_alive():
                self.stream_thread.join(timeout=2.0)
            
            # Clear session state
            self.current_frame = None
            self.pose_data = []
            self.session_start_time = None
            
            print("✅ Stream stopped successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error stopping stream: {e}")
            return False
    
    # === FILE MANAGEMENT ===
    def get_recordings_list(self):
        """Get list of available recordings"""
        try:
            recordings = []
            for file_path in self.recordings_dir.glob("*.mp4"):
                file_stats = file_path.stat()
                recordings.append({
                    "filename": file_path.name,
                    "size": file_stats.st_size,
                    "created": datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                })
            
            # Sort by creation time (newest first)
            recordings.sort(key=lambda x: x["created"], reverse=True)
            return recordings
            
        except Exception as e:
            print(f"❌ Error getting recordings list: {e}")
            return []

# Initialize analyzer
web_analyzer = BaduanjinWebAnalyzer()

# === LEGACY API ENDPOINTS (for Azure pi-service compatibility) ===

@app.route('/')
def index():
    """Main page"""
    return jsonify({
        "service": "Baduanjin Real-time Analysis",
        "status": "running",
        "version": "1.2",
        "compatibility": "Azure pi-service compatible",
        "workflow": [
            "Azure pi-service calls /api/start to begin streaming",
            "Azure pi-service calls /api/recording/start for video recording",
            "Azure pi-service calls /api/recording/stop to end recording", 
            "Azure pi-service calls /api/stop to end streaming session",
            "Azure pi-service calls /api/recordings to list files"
        ]
    })

@app.route('/api/start', methods=['POST'])
def legacy_start_stream():
    """Legacy start endpoint - called by Azure pi-service"""
    try:
        success = web_analyzer.start_stream()
        
        if success:
            return jsonify({
                "success": True,
                "message": "Live streaming started successfully",
                "camera_available": CAMERA_AVAILABLE,
                "yolo_available": YOLO_AVAILABLE,
                "is_running": True
            })
        else:
            return jsonify({
                "success": False,
                "message": "Failed to start streaming - camera not available",
                "camera_available": CAMERA_AVAILABLE,
                "yolo_available": YOLO_AVAILABLE
            }), 500
            
    except Exception as e:
        print(f"❌ Error in legacy start: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Internal error starting streaming"
        }), 500

@app.route('/api/stop', methods=['POST'])
def legacy_stop_stream():
    """Legacy stop endpoint - called by Azure pi-service"""
    try:
        web_analyzer.stop_stream()
        
        return jsonify({
            "success": True,
            "message": "Live streaming stopped successfully",
            "is_running": False
        })
        
    except Exception as e:
        print(f"❌ Error in legacy stop: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Internal error stopping streaming"
        }), 500

@app.route('/api/status')
def enhanced_legacy_get_status():
    """Enhanced status endpoint with more detailed info for Azure service"""
    try:
        recordings = web_analyzer.get_recordings_list()
        
        return jsonify({
            # Basic status (Azure expects these)
            "is_running": web_analyzer.is_running,
            "camera_available": CAMERA_AVAILABLE,
            "yolo_available": YOLO_AVAILABLE,
            "is_recording": web_analyzer.is_recording,
            "persons_detected": web_analyzer.session_stats.get('persons_detected', 0),
            "current_fps": web_analyzer.session_stats.get('current_fps', 0),
            
            # Enhanced info for debugging
            "recordings_count": len(recordings),
            "latest_recording": recordings[0]["filename"] if recordings else None,
            "session_duration": str(datetime.now() - web_analyzer.session_start_time) if web_analyzer.session_start_time else "0:00:00",
            "recording_duration": str(datetime.now() - web_analyzer.recording_start_time) if web_analyzer.recording_start_time else "0:00:00",
            
            # Network info
            "ngrok_compatible": True,
            "mobile_network_optimized": True,
            "websocket_status": "disabled_for_ngrok",
            "http_polling_available": True,
            
            # File system info
            "recordings_dir": str(web_analyzer.recordings_dir),
            "recordings_dir_exists": web_analyzer.recordings_dir.exists(),
            
            # Server info
            "server_version": "1.2.1",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Enhanced status error: {e}")
        return jsonify({
            "is_running": getattr(web_analyzer, 'is_running', False),
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/recording/start', methods=['POST'])
def legacy_start_recording():
    """NEW: Start recording endpoint - called by Azure pi-service"""
    try:
        result = web_analyzer.start_recording()
        
        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"❌ Error starting recording: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Internal error starting recording"
        }), 500

@app.route('/api/recording/stop', methods=['POST'])
def legacy_stop_recording():
    """NEW: Stop recording endpoint - called by Azure pi-service"""
    try:
        result = web_analyzer.stop_recording()
        
        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"❌ Error stopping recording: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Internal error stopping recording"
        }), 500

@app.route('/api/recordings')
def legacy_get_recordings():
    """Legacy recordings endpoint - called by Azure pi-service"""
    try:
        recordings = web_analyzer.get_recordings_list()
        
        return jsonify({
            "success": True,
            "recordings": recordings,
            "count": len(recordings)
        })
        
    except Exception as e:
        print(f"❌ Error getting recordings: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "recordings": [],
            "count": 0
        }), 500

@app.route('/api/pose_data')
def legacy_get_pose_data():
    """Legacy pose data endpoint - called by Azure pi-service"""
    return jsonify({
        "pose_data": web_analyzer.pose_data,
        "timestamp": datetime.now().isoformat(),
        "success": True
    })

@app.route('/api/download/<filename>')
def enhanced_download_recording(filename):
    """Enhanced download endpoint with better error handling for Azure transfer"""
    try:
        print(f"📥 Download request for: {filename} from {request.remote_addr}")
        
        file_path = web_analyzer.recordings_dir / filename
        
        if not file_path.exists() or not file_path.is_file():
            print(f"❌ File not found: {file_path}")
            return jsonify({"error": "File not found"}), 404
        
        if not filename.endswith('.mp4'):
            print(f"❌ Invalid file type: {filename}")
            return jsonify({"error": "Invalid file type"}), 400
        
        file_size = file_path.stat().st_size
        print(f"📁 File found: {filename} ({file_size} bytes)")
        
        # Add headers for better compatibility with Azure transfer
        response = send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'
        )
        
        # Add CORS and caching headers for Azure compatibility
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = '*'
        response.headers['Content-Length'] = str(file_size)
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Cache-Control'] = 'no-cache'
        
        print(f"✅ Sending file: {filename} ({file_size} bytes)")
        return response
        
    except Exception as e:
        error_msg = f"Download error for {filename}: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500

@app.route('/api/download-status/<filename>')
def get_download_status(filename):
    """Check if file is ready for download - helps Azure service verify before transfer"""
    try:
        file_path = web_analyzer.recordings_dir / filename
        
        if not file_path.exists():
            return jsonify({
                "exists": False,
                "error": "File not found"
            }), 404
        
        file_stats = file_path.stat()
        
        return jsonify({
            "exists": True,
            "filename": filename,
            "size": file_stats.st_size,
            "created": datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
            "download_url": f"/api/download/{filename}",
            "ready_for_transfer": True
        })
        
    except Exception as e:
        return jsonify({
            "exists": False,
            "error": str(e)
        }), 500
    
@app.route('/api/recordings/<filename>', methods=['DELETE'])
def legacy_delete_recording(filename):
    """Legacy delete endpoint - called by Azure pi-service"""
    try:
        file_path = web_analyzer.recordings_dir / filename
        
        if not file_path.exists():
            return jsonify({"error": "File not found"}), 404
        
        file_path.unlink()  # Delete the file
        
        return jsonify({
            "success": True,
            "message": f"File {filename} deleted successfully"
        })
        
    except Exception as e:
        print(f"❌ Delete error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/stream-events')
def get_stream_events():
    """HTTP polling replacement for WebSocket events"""
    try:
        if not web_analyzer.is_running:
            return jsonify({
                "event": "stream_stopped",
                "data": {"is_running": False}
            })
        
        return jsonify({
            "event": "stream_active",
            "data": {
                "is_running": True,
                "is_recording": web_analyzer.is_recording,
                "stats": web_analyzer.session_stats,
                "timestamp": int(time.time() * 1000)
            }
        })
        
    except Exception as e:
        return jsonify({
            "event": "error",
            "data": {"error": str(e)}
        }), 500
    
@app.route('/api/debug/recordings')
def debug_recordings_info():
    """Debug endpoint to help troubleshoot Azure transfer issues"""
    try:
        recordings_dir = web_analyzer.recordings_dir
        
        debug_info = {
            "recordings_directory": str(recordings_dir),
            "directory_exists": recordings_dir.exists(),
            "directory_permissions": oct(recordings_dir.stat().st_mode)[-3:] if recordings_dir.exists() else "N/A",
            "files_found": [],
            "total_size": 0
        }
        
        if recordings_dir.exists():
            for file_path in recordings_dir.glob("*.mp4"):
                file_stats = file_path.stat()
                file_info = {
                    "filename": file_path.name,
                    "size": file_stats.st_size,
                    "created": datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                    "permissions": oct(file_stats.st_mode)[-3:],
                    "readable": os.access(file_path, os.R_OK),
                    "download_url": f"/api/download/{file_path.name}"
                }
                debug_info["files_found"].append(file_info)
                debug_info["total_size"] += file_stats.st_size
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "recordings_directory": str(web_analyzer.recordings_dir)
        }), 500
    
# ADD OPTIONS HANDLER FOR CORS PREFLIGHT ===
@app.before_request
def handle_preflight():
    """Handle CORS preflight requests for Azure service compatibility"""
    if request.method == "OPTIONS":
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, ngrok-skip-browser-warning'
        response.headers['Access-Control-Max-Age'] = '3600'
        return response
    
# === HTTP POLLING FALLBACK (for frontend direct connection) ===
@app.route('/api/current_frame')
def get_current_frame_improved():
    """Improved current frame endpoint - optimized for ngrok and mobile networks"""
    try:
        # Add ngrok-skip-browser-warning header check
        ngrok_warning_skipped = request.headers.get('ngrok-skip-browser-warning') == 'true'
        if not ngrok_warning_skipped:
            print(f"⚠️ Request without ngrok-skip-browser-warning header from {request.remote_addr}")
        
        if not web_analyzer.is_running:
            return jsonify({
                "success": False,
                "error": "No active stream - stream not running",
                "is_running": False,
                "timestamp": int(time.time() * 1000)
            })
        
        if web_analyzer.current_frame is None:
            return jsonify({
                "success": False,
                "error": "No current frame available - stream just started", 
                "is_running": True,
                "timestamp": int(time.time() * 1000)
            })
        
        # Optimize image quality for mobile networks
        quality = 60  # Reduced quality for mobile
        if 'mobile' in request.headers.get('User-Agent', '').lower():
            quality = 50  # Even lower for mobile devices
        
        # Encode current frame with mobile optimization
        _, buffer = cv2.imencode('.jpg', web_analyzer.current_frame, 
                                [cv2.IMWRITE_JPEG_QUALITY, quality])
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        response_data = {
            "success": True,
            "image": frame_base64,
            "pose_data": web_analyzer.pose_data if web_analyzer.pose_data else [],
            "stats": web_analyzer.session_stats,
            "is_recording": web_analyzer.is_recording,
            "timestamp": int(time.time() * 1000),
            "frame_size": len(frame_base64),
            "quality": quality
        }
        
        # Add headers for better caching and CORS
        response = jsonify(response_data)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        error_msg = f"Error getting current frame: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({
            "success": False,
            "error": error_msg,
            "is_running": getattr(web_analyzer, 'is_running', False),
            "timestamp": int(time.time() * 1000)
        }), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint for ngrok and Azure service monitoring"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "ngrok_compatible": True,
        "services": {
            "camera": CAMERA_AVAILABLE,
            "yolo": YOLO_AVAILABLE,
            "streaming": web_analyzer.is_running,
            "recording": web_analyzer.is_recording
        },
        "recordings_available": len(web_analyzer.get_recordings_list()),
        "server_info": {
            "version": "1.2.1",
            "mobile_optimized": True,
            "websocket_disabled": True  # Using HTTP polling for ngrok
        }
    })

# === ADDITIONAL ENDPOINTS ===
@app.route('/api/stats')
def get_stats():
    """Get session statistics"""
    return jsonify(web_analyzer.session_stats)

@app.route('/api/ngrok_test')
def ngrok_test():
    """Simple test to verify ngrok forwarding"""
    return jsonify({
        "success": True,
        "message": "Ngrok is forwarding correctly to Pi web server",
        "timestamp": datetime.now().isoformat(),
        "remote_addr": request.remote_addr,
        "user_agent": request.headers.get('User-Agent', 'Unknown'),
        "is_running": web_analyzer.is_running,
        "is_recording": web_analyzer.is_recording
    })

# === WEBSOCKET EVENTS ===
def emit_frame_safely(frame_data):
    """Safely emit frame data with error handling"""
    try:
        socketio.emit('frame_update', frame_data)
        return True
    except Exception as e:
        print(f"❌ Error emitting frame: {e}")
        return False

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    try:
        print('✅ Client connected to Pi WebSocket')
        emit('status', {
            'connected': True,
            'camera_available': CAMERA_AVAILABLE,
            'yolo_available': YOLO_AVAILABLE,
            'is_running': web_analyzer.is_running,
            'is_recording': web_analyzer.is_recording,
            'message': 'Connected to Pi successfully'
        })
        return True
    except Exception as e:
        print(f"❌ Error in connect handler: {e}")
        return False

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('🔌 Client disconnected from Pi WebSocket')

@socketio.on_error_default
def default_error_handler(e):
    """Handle Socket.IO errors"""
    print(f"❌ Socket.IO error: {e}")
    return False

if __name__ == '__main__':
    print("=" * 60)
    print("🥋 Baduanjin Web Server v1.2 Starting...")
    print("=" * 60)
    print(f"📷 Camera Available: {CAMERA_AVAILABLE}")
    print(f"🤖 YOLO Available: {YOLO_AVAILABLE}")
    print(f"🌐 Local Access: http://172.20.10.6:5001")
    print(f"📁 Recordings Dir: {web_analyzer.recordings_dir}")
    print("=" * 60)
    print("🔗 Architecture:")
    print("  Frontend → Azure pi-service → Raspberry Pi web_server")
    print("=" * 60)
    print("📡 Azure pi-service compatible endpoints:")
    print("  POST /api/start              → Start streaming") 
    print("  POST /api/stop               → Stop streaming")
    print("  POST /api/recording/start    → Start recording")
    print("  POST /api/recording/stop     → Stop recording")
    print("  GET  /api/status             → Get status")
    print("  GET  /api/recordings         → List recordings")
    print("  GET  /api/download/<file>    → Download recording")
    print("=" * 60)
    print("🎥 Workflow:")
    print("  1. Azure calls /api/start → Streaming begins")
    print("  2. Azure calls /api/recording/start → Video recording starts")
    print("  3. User practices → Pose detection + video capture")
    print("  4. Azure calls /api/recording/stop → Video file saved")
    print("  5. Azure calls /api/stop → Session ends")
    print("  6. Azure calls /api/download → Transfer video to cloud")
    print("=" * 60)
    
    # Run server accessible from external IPs
    socketio.run(app, host='0.0.0.0', port=5001, debug=False, allow_unsafe_werkzeug=True)nj