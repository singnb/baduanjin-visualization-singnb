#!/usr/bin/env python3
"""
main.py - Main Flask Application Entry Point
Baduanjin Web Server for Raspberry Pi 5 - ENHANCED with Exercise Tracking
"""

from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from pathlib import Path
import sys
import site

# Add user site-packages to path
sys.path.append(site.getusersitepackages())

# Import modules
from config import Config

# 🚀 ENHANCED: Try to import enhanced analyzer, fallback to regular one
try:
    from analyzer_integration import EnhancedBaduanjinAnalyzer
    ENHANCED_TRACKING_AVAILABLE = True
    print("✅ Enhanced Baduanjin tracking available")
except ImportError as e:
    print(f"⚠️ Enhanced tracking not available, falling back to regular analyzer: {e}")
    from analyzer import BaduanjinWebAnalyzer as EnhancedBaduanjinAnalyzer
    ENHANCED_TRACKING_AVAILABLE = False

from api_routes import register_api_routes
from websocket_handlers import register_websocket_handlers

# Check imports
try:
    from picamera2 import Picamera2
    from ultralytics import YOLO
    CAMERA_AVAILABLE = True
    YOLO_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    CAMERA_AVAILABLE = False
    YOLO_AVAILABLE = False

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # CORS configuration
    CORS(app, cors_allowed_origins="*")
    
    # SocketIO configuration (ngrok-optimized)
    socketio = SocketIO(app, 
        cors_allowed_origins="*",
        async_mode='threading',
        logger=False,  # Disabled for ngrok
        engineio_logger=False,  # Disabled for ngrok
        
        # Ngrok-optimized settings
        ping_timeout=300,  # Longer timeout for mobile network
        ping_interval=120,  # Less frequent pings for mobile
        
        # Force HTTP polling for ngrok compatibility
        transports=['polling'],  # 🔥 KEY FIX: No WebSocket
        allow_upgrades=False,    # 🔥 KEY FIX: Prevent WebSocket upgrade
        
        # Additional stability settings
        max_http_buffer_size=1e6  # 1MB buffer for larger frames
    )
    
    return app, socketio

def main():
    """Main application entry point"""
    # Create app and socketio
    app, socketio = create_app()
    
    # 🚀 ENHANCED: Initialize enhanced analyzer (will fallback to regular if needed)
    web_analyzer = EnhancedBaduanjinAnalyzer()
    
    # Store analyzer in app context for access by routes
    app.web_analyzer = web_analyzer
    
    # Register routes and handlers
    register_api_routes(app, web_analyzer)
    register_websocket_handlers(socketio, web_analyzer)
    
    # Print startup info
    print("=" * 60)
    print("Baduanjin Web Server v2.0 Starting...")
    if ENHANCED_TRACKING_AVAILABLE:
        print("🎯 WITH ENHANCED EXERCISE TRACKING! 🎯")
    print("=" * 60)
    print(f"Camera Available: {CAMERA_AVAILABLE}")
    print(f"YOLO Available: {YOLO_AVAILABLE}")
    print(f"Exercise Tracking: {ENHANCED_TRACKING_AVAILABLE}")
    print(f"Local Access: http://172.20.10.6:5001")
    print(f"Recordings Dir: {web_analyzer.recordings_dir}")
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
    
    # 🚀 NEW: Exercise tracking endpoints
    if ENHANCED_TRACKING_AVAILABLE:
        print("=" * 60)
        print("🎯 NEW: Baduanjin Exercise Tracking Endpoints:")
        print("  GET  /api/baduanjin/exercises     → List all exercises")
        print("  POST /api/baduanjin/start/<id>    → Start exercise tracking")
        print("  POST /api/baduanjin/stop          → Stop exercise tracking")
        print("  GET  /api/baduanjin/feedback      → Get real-time feedback")
        print("  GET  /api/baduanjin/status        → Get tracking status")
        print("  GET  /api/baduanjin/session-summary → Get session summary")
        print("  POST /api/baduanjin/export        → Export session data")
    
    print("=" * 60)
    print("🎥 Session Management:")
    print("  POST /api/pi-live/start-session     → Start session")
    print("  POST /api/pi-live/stop-session      → Stop session")
    print("  POST /api/pi-live/recording/start   → Start recording")
    print("  POST /api/pi-live/recording/stop    → Stop recording")
    print("  GET  /api/pi-live/status            → Get status")
    print("=" * 60)
    print("🎥 Enhanced Workflow:")
    print("  1. Azure calls /api/pi-live/start-session → Session begins")
    print("  2. OPTIONAL: Call /api/baduanjin/start/<exercise_id> → Start tracking")
    print("  3. Azure calls /api/pi-live/recording/start → Video recording starts")
    print("  4. User practices → Pose detection + video capture + 🆕 REAL-TIME FEEDBACK")
    print("  5. Azure calls /api/pi-live/recording/stop → Video file saved")
    print("  6. OPTIONAL: Call /api/baduanjin/export → Export exercise analytics")
    print("  7. Azure calls /api/pi-live/stop-session → Session ends")
    print("  8. Azure calls /api/download → Transfer video to cloud")
    print("=" * 60)
    
    # Run server accessible from external IPs
    socketio.run(app, host='0.0.0.0', port=5001, debug=False, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    main()