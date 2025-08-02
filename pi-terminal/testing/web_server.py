#!/usr/bin/env python3
"""
Enhanced Baduanjin Web Server for Raspberry Pi 5
Provides REST API, WebSocket streaming, and video recording for full-stack integration
"""

from flask import Flask, Response, jsonify, render_template, request, send_file
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import cv2
import numpy as np
import time
import json
import threading
import base64
import io
import os
from datetime import datetime
import sys
import site
import glob
from pathlib import Path

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

# 🔧 EXPLICIT CORS FIX
CORS(app, 
     origins="*",
     methods=["GET", "POST", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"])

# 🔧 EXPLICIT Socket.IO CORS FIX  
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   cors_credentials=True)

# 🔧 MANDATORY: Add explicit CORS headers
@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return response

# 🔧 MANDATORY: Handle OPTIONS requests
@app.route('/socket.io/', methods=['OPTIONS'])
def handle_socket_options():
    response = jsonify({'status': 'ok'})
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

class BaduanjinWebAnalyzer:
    def __init__(self):
        self.analyzer = None
        self.is_running = False
        self.is_recording = False
        self.current_frame = None
        self.pose_data = []
        self.video_writer = None
        self.recording_filename = None
        self.recording_start_time = None
        
        # Create recordings directory
        self.recordings_dir = Path("recordings")
        self.recordings_dir.mkdir(exist_ok=True)
        
        self.session_stats = {
            'total_frames': 0,
            'persons_detected': 0,
            'session_start': None,
            'current_fps': 0,
            'recording_duration': 0
        }
        
        if CAMERA_AVAILABLE:
            self.setup_analyzer()
    
    def setup_analyzer(self):
        """Initialize the pose analyzer"""
        try:
            # Initialize camera
            self.picam2 = Picamera2()
            config = self.picam2.create_preview_configuration(
                main={"format": 'XRGB8888', "size": (640, 480)}
            )
            self.picam2.configure(config)
            
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
            print(f"Processing error: {e}")
            return []
    
    def start_recording(self):
        """Start video recording"""
        if not self.is_running:
            return False, "Stream must be running to start recording"
        
        if self.is_recording:
            return False, "Recording already in progress"
        
        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.recording_filename = f"baduanjin_recording_{timestamp}.mp4"
            filepath = self.recordings_dir / self.recording_filename
            
            # Initialize video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(
                str(filepath), fourcc, 30.0, (640, 480)
            )
            
            if not self.video_writer.isOpened():
                return False, "Failed to initialize video writer"
            
            self.is_recording = True
            self.recording_start_time = time.time()
            
            print(f"📹 Recording started: {self.recording_filename}")
            return True, f"Recording started: {self.recording_filename}"
            
        except Exception as e:
            print(f"❌ Recording start failed: {e}")
            return False, f"Recording failed: {str(e)}"
    
    def stop_recording(self):
        """Stop video recording"""
        if not self.is_recording:
            return False, "No recording in progress"
        
        try:
            self.is_recording = False
            
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            
            duration = time.time() - self.recording_start_time if self.recording_start_time else 0
            recording_info = {
                'filename': self.recording_filename,
                'duration': round(duration, 2),
                'filepath': str(self.recordings_dir / self.recording_filename)
            }
            
            print(f"🛑 Recording stopped: {self.recording_filename} ({duration:.2f}s)")
            
            self.recording_filename = None
            self.recording_start_time = None
            
            return True, recording_info
            
        except Exception as e:
            print(f"❌ Recording stop failed: {e}")
            return False, f"Stop recording failed: {str(e)}"
    
    def get_recordings_list(self):
        """Get list of recorded videos"""
        try:
            recordings = []
            for mp4_file in self.recordings_dir.glob("*.mp4"):
                stat = mp4_file.stat()
                recordings.append({
                    'filename': mp4_file.name,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            
            # Sort by creation time (newest first)
            recordings.sort(key=lambda x: x['created'], reverse=True)
            return recordings
            
        except Exception as e:
            print(f"❌ Failed to list recordings: {e}")
            return []
    
    def delete_recording(self, filename):
        """Delete a recording file"""
        try:
            filepath = self.recordings_dir / filename
            if filepath.exists() and filepath.suffix == '.mp4':
                filepath.unlink()
                return True, f"Deleted: {filename}"
            else:
                return False, "File not found"
        except Exception as e:
            return False, f"Delete failed: {str(e)}"
    
    def start_stream(self):
        """Start the video stream"""
        if not CAMERA_AVAILABLE:
            return False
            
        self.is_running = True
        self.session_stats['session_start'] = datetime.now().isoformat()
        self.picam2.start()
        
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
                    
                    # Recording indicator
                    if self.is_recording:
                        cv2.circle(frame_bgr, (600, 30), 10, (0, 0, 255), -1)
                        cv2.putText(frame_bgr, 'REC', (580, 50), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                        
                        # Update recording duration
                        if self.recording_start_time:
                            duration = time.time() - self.recording_start_time
                            self.session_stats['recording_duration'] = round(duration, 1)
                    
                    # Write frame to video if recording
                    if self.is_recording and self.video_writer:
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
                        'is_recording': self.is_recording
                    })
                    
                    time.sleep(0.033)  # ~30 FPS
                    
                except Exception as e:
                    print(f"Stream error: {e}")
                    break
        
        self.stream_thread = threading.Thread(target=stream_loop)
        self.stream_thread.start()
        return True
    
    def stop_stream(self):
        """Stop the video stream"""
        self.is_running = False
        
        # Stop recording if active
        if self.is_recording:
            self.stop_recording()
        
        if hasattr(self, 'picam2'):
            self.picam2.stop()

# Initialize analyzer
web_analyzer = BaduanjinWebAnalyzer()

# REST API Routes
@app.route('/')
def index():
    """Main page"""
    return jsonify({
        "service": "Baduanjin Real-time Analysis with Recording",
        "status": "running",
        "endpoints": {
            "stream": "/stream",
            "start": "/api/start",
            "stop": "/api/stop",
            "status": "/api/status",
            "stats": "/api/stats",
            "start_recording": "/api/recording/start",
            "stop_recording": "/api/recording/stop",
            "recordings": "/api/recordings",
            "download": "/api/download/<filename>"
        }
    })

@app.route('/api/start', methods=['POST'])
def start_analysis():
    """Start pose analysis streaming"""
    try:
        success = web_analyzer.start_stream()
        return jsonify({
            "success": success,
            "message": "Live streaming started" if success else "Failed to start streaming",
            "camera_available": CAMERA_AVAILABLE,
            "yolo_available": YOLO_AVAILABLE
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_analysis():
    """Stop pose analysis streaming"""
    try:
        web_analyzer.stop_stream()
        return jsonify({
            "success": True,
            "message": "Live streaming stopped"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/recording/start', methods=['POST'])
def start_recording():
    """Start video recording"""
    try:
        success, message = web_analyzer.start_recording()
        return jsonify({
            "success": success,
            "message": message,
            "is_recording": web_analyzer.is_recording
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/recording/stop', methods=['POST'])
def stop_recording():
    """Stop video recording"""
    try:
        success, result = web_analyzer.stop_recording()
        return jsonify({
            "success": success,
            "message": "Recording stopped" if success else result,
            "recording_info": result if success else None,
            "is_recording": web_analyzer.is_recording
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/recordings')
def get_recordings():
    """Get list of recorded videos"""
    try:
        recordings = web_analyzer.get_recordings_list()
        return jsonify({
            "success": True,
            "recordings": recordings,
            "count": len(recordings)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/recordings/<filename>', methods=['DELETE'])
def delete_recording(filename):
    """Delete a recording"""
    try:
        success, message = web_analyzer.delete_recording(filename)
        return jsonify({
            "success": success,
            "message": message
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/download/<filename>')
def download_recording(filename):
    """Download a recording file"""
    try:
        filepath = web_analyzer.recordings_dir / filename
        if filepath.exists() and filepath.suffix == '.mp4':
            return send_file(
                str(filepath),
                as_attachment=True,
                download_name=filename,
                mimetype='video/mp4'
            )
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/status')
def get_status():
    """Get current status"""
    return jsonify({
        "is_running": web_analyzer.is_running,
        "is_recording": web_analyzer.is_recording,
        "camera_available": CAMERA_AVAILABLE,
        "yolo_available": YOLO_AVAILABLE,
        "persons_detected": web_analyzer.session_stats.get('persons_detected', 0),
        "current_recording": web_analyzer.recording_filename
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

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f'✅ Client connected: {request.sid}')
    emit('status', {
        'connected': True,
        'camera_available': CAMERA_AVAILABLE,
        'yolo_available': YOLO_AVAILABLE,
        'server_time': datetime.now().isoformat(),
        'message': 'Connected to Baduanjin Pi Server'
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f'❌ Client disconnected: {request.sid}')

@socketio.on('connect_error')
def handle_connect_error(error):
    """Handle connection errors"""
    print(f'🔴 Connection error: {error}')

@socketio.on('start_stream')
def handle_start_stream():
    """Handle start stream request"""
    print('📡 WebSocket: Start stream request received')
    success = web_analyzer.start_stream()
    emit('stream_status', {
        'started': success,
        'message': 'Stream started' if success else 'Failed to start stream'
    })

@socketio.on('stop_stream')
def handle_stop_stream():
    """Handle stop stream request"""
    print('🛑 WebSocket: Stop stream request received')
    web_analyzer.stop_stream()
    emit('stream_status', {
        'started': False,
        'message': 'Stream stopped'
    })


@socketio.on('start_recording')
def handle_start_recording():
    """Handle start recording request"""
    print('🔴 WebSocket: Start recording request received')
    success, message = web_analyzer.start_recording()
    emit('recording_status', {
        'recording': success,
        'message': message
    })

@socketio.on('stop_recording')
def handle_stop_recording():
    """Handle stop recording request"""
    print('⏹️ WebSocket: Stop recording request received')
    success, result = web_analyzer.stop_recording()
    emit('recording_status', {
        'recording': False,
        'message': result if not success else "Recording stopped",
        'recording_info': result if success else None
    })

def emit_frame_safely(frame_bgr, pose_data, session_stats, is_recording):
    """Safely emit frame with error handling"""
    try:
        # Encode frame with optimized quality
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 80]  # Reduce quality slightly for speed
        _, buffer = cv2.imencode('.jpg', frame_bgr, encode_params)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # Emit with enhanced data
        socketio.emit('frame_update', {
            'image': frame_base64,
            'pose_data': pose_data,
            'stats': session_stats,
            'is_recording': is_recording,
            'timestamp': int(time.time() * 1000),  # For latency calculation
            'frame_size': len(buffer)
        })
        
    except Exception as e:
        print(f"❌ Frame emission error: {e}")

# main server startup:
if __name__ == '__main__':
    print("🥋 Baduanjin Web Server Starting...")
    print(f"📹 Camera Available: {CAMERA_AVAILABLE}")
    print(f"🧠 YOLO Available: {YOLO_AVAILABLE}")
    print(f"🔌 Socket.IO: CORS Fixed")
    print(f"🌐 Access URL: http://172.20.10.5:5001")
    print(f"📡 WebSocket: ws://172.20.10.5:5001")
    
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=5001, 
        debug=False,
        allow_unsafe_werkzeug=True
    )