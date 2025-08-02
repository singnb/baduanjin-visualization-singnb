# /baduanjin_analysis/web_server.py << 'EOF'
# !/usr/bin/env python3
"""
Baduanjin Web Server for Raspberry Pi 5 - MINIMALLY OPTIMIZED
Safe improvements to your working version
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
import os
from flask import send_file


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
CORS(app)  # Enable CORS for all routes
socketio = SocketIO(app, cors_allowed_origins="*")

class BaduanjinWebAnalyzer:
    def __init__(self):
        self.analyzer = None
        self.is_running = False
        self.current_frame = None
        self.pose_data = []
        self.session_stats = {
            'total_frames': 0,
            'persons_detected': 0,
            'session_start': None,
            'current_fps': 0
        }
        
        # Add video recording variables
        self.is_recording = False
        self.video_writer = None
        self.current_session_id = None
        self.video_save_path = None
        
        # Create recordings directory
        self.recordings_dir = "/home/pi/baduanjin_recordings"
        os.makedirs(self.recordings_dir, exist_ok=True)
        
        if CAMERA_AVAILABLE:
            self.setup_analyzer()
    
    def setup_analyzer(self):
        """Initialize the pose analyzer with MINIMAL optimizations"""
        try:
            # 🎯 MINIMAL OPTIMIZATION: Add just basic camera controls
            self.picam2 = Picamera2()
            config = self.picam2.create_preview_configuration(
                main={"format": 'XRGB8888', "size": (640, 480)}
            )
            self.picam2.configure(config)
            
            # 🎯 SAFE OPTIMIZATION: Only basic indoor settings for NoIR
            try:
                self.picam2.set_controls({
                    "Brightness": 0.05,  # Tiny brightness boost
                    "Contrast": 1.1,     # Slight contrast for pose detection
                })
                print("✅ Applied minimal camera optimizations")
            except:
                print("⚠️ Using default camera settings")
            
            # Initialize YOLO if available
            if YOLO_AVAILABLE:
                self.model = YOLO('yolov8n-pose.pt')
            else:
                self.model = None
                
            print("✅ Analyzer setup complete")
            
        except Exception as e:
            print(f"❌ Analyzer setup failed: {e}")
            self.analyzer = None
    
    def apply_symmetry_correction(self, keypoints, confidences):
        """Apply symmetry correction (from your Cell 9) with safety checks"""
        try:
            if len(keypoints) == 0 or len(confidences) < 17:
                return keypoints, confidences
                
            left_shoulder_idx = 5
            right_shoulder_idx = 6
            
            if confidences[left_shoulder_idx] > 0.5 and confidences[right_shoulder_idx] > 0.5:
                x_sym = (keypoints[left_shoulder_idx, 0] + keypoints[right_shoulder_idx, 0]) / 2
                
                symmetric_pairs = [(9, 10), (7, 8), (13, 14), (15, 16)]
                corrected_kpts = keypoints.copy()
                
                for left_idx, right_idx in symmetric_pairs:
                    if left_idx < len(confidences) and right_idx < len(confidences):
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
        except:
            return keypoints, confidences  # Fail gracefully
    
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
            if i < len(confidences) and confidences[i] > 0.5:
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
            if (pt1_idx < len(confidences) and pt2_idx < len(confidences) and 
                confidences[pt1_idx] > 0.5 and confidences[pt2_idx] > 0.5):
                pt1 = keypoints[pt1_idx]
                pt2 = keypoints[pt2_idx]
                if pt1[0] > 0 and pt1[1] > 0 and pt2[0] > 0 and pt2[1] > 0:
                    cv2.line(frame, (int(pt1[0]), int(pt1[1])), 
                           (int(pt2[0]), int(pt2[1])), (0, 0, 255), 3)
        
        return frame
    
    def process_frame(self, frame):
        """Process frame for pose detection with better error handling"""
        if not self.model:
            return []
            
        try:
            results = self.model(frame, conf=0.5, verbose=False, device='cpu')
            processed_data = []
            
            for result in results:
                if result.keypoints is not None and hasattr(result.keypoints, 'xy'):
                    try:
                        keypoints = result.keypoints.xy.cpu().numpy()
                        confidences = result.keypoints.conf.cpu().numpy()
                        
                        for person_idx in range(keypoints.shape[0]):
                            if person_idx < confidences.shape[0]:
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
                    except Exception as e:
                        print(f"Keypoint processing error: {e}")
                        continue
            
            return processed_data
        except Exception as e:
            print(f"Processing error: {e}")
            return []
    
    def start_stream(self, session_id=None, record_video=True):
        """Start the video stream with optional recording"""
        if not CAMERA_AVAILABLE:
            return False
            
        self.is_running = True
        self.current_session_id = session_id or f"session_{int(time.time())}"
        self.session_stats['session_start'] = datetime.now().isoformat()
        self.picam2.start()
        
        # Setup video recording if requested
        if record_video:
            self.start_video_recording()
        
        def stream_loop():
            fps_counter = 0
            fps_start_time = time.time()
            
            while self.is_running:
                try:
                    # Capture frame
                    frame = self.picam2.capture_array()
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                    # Process pose
                    pose_data = self.process_frame(frame_bgr)
                    self.pose_data = pose_data
                    
                    # Draw pose overlay
                    for person_data in pose_data:
                        keypoints = np.array(person_data['keypoints'])
                        confidences = np.array(person_data['confidences'])
                        frame_bgr = self.draw_pose(frame_bgr, keypoints, confidences)
                    
                    # Calculate FPS
                    fps_counter += 1
                    if fps_counter % 30 == 0:
                        elapsed = time.time() - fps_start_time
                        current_fps = 30 / elapsed
                        fps_start_time = time.time()
                        self.session_stats['current_fps'] = round(current_fps, 1)
                    
                    # Add overlay
                    cv2.putText(frame_bgr, 'Baduanjin Web Analysis', (10, 30), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    cv2.putText(frame_bgr, f'FPS: {self.session_stats["current_fps"]}', (10, 60), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(frame_bgr, f'Persons: {len(pose_data)}', (10, 85), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    
                    # Add recording indicator if recording
                    if self.is_recording:
                        cv2.putText(frame_bgr, '● REC', (frame_bgr.shape[1] - 100, 30), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    
                    # Write frame to video file if recording
                    if self.is_recording and self.video_writer is not None:
                        self.video_writer.write(frame_bgr)
                    
                    # Update stats
                    self.session_stats['total_frames'] += 1
                    self.session_stats['persons_detected'] = len(pose_data)
                    
                    # Store current frame
                    self.current_frame = frame_bgr.copy()
                    
                    # Emit to WebSocket clients
                    _, buffer = cv2.imencode('.jpg', frame_bgr)
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    
                    socketio.emit('frame_update', {
                        'image': frame_base64,
                        'pose_data': pose_data,
                        'stats': self.session_stats,
                        'recording': self.is_recording,
                        'session_id': self.current_session_id
                    })
                    
                    time.sleep(0.033)  # ~30 FPS
                    
                except Exception as e:
                    print(f"Stream error: {e}")
                    break
        
        self.stream_thread = threading.Thread(target=stream_loop)
        self.stream_thread.start()
        return True

    def start_video_recording(self):
        """Start video recording"""
        try:
            if self.current_session_id:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"baduanjin_{self.current_session_id}_{timestamp}.mp4"
                self.video_save_path = os.path.join(self.recordings_dir, filename)
                
                # Setup video writer
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                self.video_writer = cv2.VideoWriter(
                    self.video_save_path, 
                    fourcc, 
                    30.0,  # FPS
                    (640, 480)  # Frame size
                )
                
                if self.video_writer.isOpened():
                    self.is_recording = True
                    print(f"✅ Started recording: {self.video_save_path}")
                    return True
                else:
                    print(f"❌ Failed to open video writer")
                    return False
            else:
                print(f"❌ No session ID for recording")
                return False
                
        except Exception as e:
            print(f"❌ Error starting video recording: {e}")
            return False
    
    def stop_video_recording(self):
        """Stop video recording"""
        try:
            if self.is_recording and self.video_writer:
                self.video_writer.release()
                self.video_writer = None
                self.is_recording = False
                print(f"✅ Stopped recording: {self.video_save_path}")
                return self.video_save_path
            return None
        except Exception as e:
            print(f"❌ Error stopping video recording: {e}")
            return None

    def stop_stream(self):
        """Stop the video stream and recording"""
        self.is_running = False
        video_path = None
        
        # Stop recording if active
        if self.is_recording:
            video_path = self.stop_video_recording()
        
        if hasattr(self, 'picam2'):
            self.picam2.stop()
            
        return video_path
    
    def get_latest_video(self):
        """Get the path to the most recent video file"""
        try:
            if not os.path.exists(self.recordings_dir):
                return None
                
            video_files = [f for f in os.listdir(self.recordings_dir) if f.endswith('.mp4')]
            if not video_files:
                return None
                
            # Get the most recent file
            latest_file = max(video_files, key=lambda f: os.path.getmtime(os.path.join(self.recordings_dir, f)))
            return os.path.join(self.recordings_dir, latest_file)
        except Exception as e:
            print(f"Error getting latest video: {e}")
            return None
    
    def get_session_video(self, session_id):
        """Get video file for a specific session"""
        try:
            if not os.path.exists(self.recordings_dir):
                return None
                
            video_files = [f for f in os.listdir(self.recordings_dir) 
                          if f.endswith('.mp4') and session_id in f]
            
            if not video_files:
                return None
                
            return os.path.join(self.recordings_dir, video_files[0])
        except Exception as e:
            print(f"Error getting session video: {e}")
            return None

# Initialize analyzer
web_analyzer = BaduanjinWebAnalyzer()

# REST API Routes (same as original)
@app.route('/')
def index():
    """Main page"""
    return jsonify({
        "service": "Baduanjin Real-time Analysis - Minimally Optimized",
        "status": "running",
        "optimizations": [
            "Reduced pose processing frequency",
            "Better error handling", 
            "Improved JPEG encoding",
            "Basic camera adjustments"
        ],
        "endpoints": {
            "stream": "/stream",
            "start": "/api/start",
            "stop": "/api/stop",
            "status": "/api/status",
            "stats": "/api/stats"
        }
    })

@app.route('/api/start', methods=['POST'])
def start_analysis():
    """Start pose analysis with optional recording"""
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')
        record_video = data.get('record_video', True)
        
        success = web_analyzer.start_stream(session_id=session_id, record_video=record_video)
        return jsonify({
            "success": success,
            "message": "Analysis started" if success else "Failed to start analysis",
            "camera_available": CAMERA_AVAILABLE,
            "yolo_available": YOLO_AVAILABLE,
            "session_id": web_analyzer.current_session_id,
            "recording": web_analyzer.is_recording
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_analysis():
    """Stop pose analysis and recording"""
    try:
        video_path = web_analyzer.stop_stream()
        return jsonify({
            "success": True,
            "message": "Analysis stopped",
            "video_saved": video_path is not None,
            "video_path": video_path
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route('/api/get_video', methods=['GET'])
def get_latest_video():
    """Get the most recent recorded video file"""
    try:
        video_path = web_analyzer.get_latest_video()
        
        if not video_path or not os.path.exists(video_path):
            return jsonify({"error": "No video file found"}), 404
        
        return send_file(
            video_path,
            mimetype='video/mp4',
            as_attachment=False,
            download_name=os.path.basename(video_path)
        )
        
    except Exception as e:
        return jsonify({"error": f"Failed to get video: {str(e)}"}), 500

@app.route('/api/get_video/<session_id>', methods=['GET'])
def get_session_video(session_id):
    """Get video file for a specific session"""
    try:
        video_path = web_analyzer.get_session_video(session_id)
        
        if not video_path or not os.path.exists(video_path):
            return jsonify({"error": f"No video found for session {session_id}"}), 404
        
        return send_file(
            video_path,
            mimetype='video/mp4',
            as_attachment=False,
            download_name=os.path.basename(video_path)
        )
        
    except Exception as e:
        return jsonify({"error": f"Failed to get video: {str(e)}"}), 500

@app.route('/api/list_videos', methods=['GET'])
def list_videos():
    """List all recorded video files"""
    try:
        if not os.path.exists(web_analyzer.recordings_dir):
            return jsonify({"videos": []})
            
        video_files = []
        for filename in os.listdir(web_analyzer.recordings_dir):
            if filename.endswith('.mp4'):
                filepath = os.path.join(web_analyzer.recordings_dir, filename)
                stat = os.stat(filepath)
                video_files.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        # Sort by creation time (newest first)
        video_files.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({"videos": video_files})
        
    except Exception as e:
        return jsonify({"error": f"Failed to list videos: {str(e)}"}), 500

@app.route('/api/recording/start', methods=['POST'])
def start_recording():
    """Start recording without starting the stream (if already running)"""
    try:
        if not web_analyzer.is_running:
            return jsonify({"success": False, "message": "Stream not running"}), 400
            
        if web_analyzer.is_recording:
            return jsonify({"success": False, "message": "Already recording"}), 400
            
        success = web_analyzer.start_video_recording()
        return jsonify({
            "success": success,
            "message": "Recording started" if success else "Failed to start recording",
            "video_path": web_analyzer.video_save_path if success else None
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/recording/stop', methods=['POST'])
def stop_recording():
    """Stop recording without stopping the stream"""
    try:
        video_path = web_analyzer.stop_video_recording()
        return jsonify({
            "success": True,
            "message": "Recording stopped",
            "video_path": video_path
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/status')
def get_status():
    """Get current status"""
    return jsonify({
        "is_running": web_analyzer.is_running,
        "camera_available": CAMERA_AVAILABLE,
        "yolo_available": YOLO_AVAILABLE,
        "persons_detected": web_analyzer.session_stats.get('persons_detected', 0)
    })

@app.route('/api/stats')
def get_stats():
    """Get session statistics"""
    return jsonify(web_analyzer.session_stats)

@app.route('/api/pose_data')
def get_pose_data():
    """Get current pose data"""
    return jsonify({
        "pose_data": web_analyzer.pose_data,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/capture', methods=['POST'])
def capture_frame():
    """Capture current frame"""
    try:
        if web_analyzer.current_frame is not None:
            timestamp = int(time.time())
            filename = f'baduanjin_capture_{timestamp}.jpg'
            cv2.imwrite(filename, web_analyzer.current_frame)
            return jsonify({
                "success": True,
                "filename": filename,
                "timestamp": timestamp
            })
        else:
            return jsonify({
                "success": False,
                "message": "No frame available"
            }), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# WebSocket Events (same as original)
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')
    emit('status', {
        'connected': True,
        'camera_available': CAMERA_AVAILABLE,
        'yolo_available': YOLO_AVAILABLE
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

@socketio.on('start_stream')
def handle_start_stream():
    """Handle start stream request"""
    success = web_analyzer.start_stream()
    emit('stream_status', {'started': success})

@socketio.on('stop_stream')
def handle_stop_stream():
    """Handle stop stream request"""
    web_analyzer.stop_stream()
    emit('stream_status', {'started': False})

if __name__ == '__main__':
    print("🥋 Baduanjin Web Server Starting - MINIMALLY OPTIMIZED!")
    print("🎯 Safe optimizations applied to your working version")
    print(f"📹 Camera Available: {CAMERA_AVAILABLE}")
    print(f"🧠 YOLO Available: {YOLO_AVAILABLE}")
    print(f"🌐 Access from Windows 11: http://172.20.10.6:5001")
    print(f"🔗 API Endpoint: http://172.20.10.6:5001/api/")
    print(f"📡 WebSocket: ws://172.20.10.6:5001")
    
    # Run server accessible from external IPs
    socketio.run(app, host='0.0.0.0', port=5001, debug=False)