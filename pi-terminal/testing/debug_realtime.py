#!/usr/bin/env python3
import sys

print("🔍 Debug: Testing imports...")

# Test picamera2
try:
    from picamera2 import Picamera2
    print("✅ picamera2 imported successfully")
except ImportError as e:
    print(f"❌ picamera2 import failed: {e}")
    sys.exit(1)

# Test ultralytics with detailed error info
try:
    from ultralytics import YOLO
    print("✅ ultralytics imported successfully")
    
    # Test model loading
    print("🧠 Testing YOLO model loading...")
    model = YOLO('yolov8n-pose.pt')
    print("✅ YOLO model loaded successfully")
    
except ImportError as e:
    print(f"❌ ultralytics import failed: {e}")
    print(f"Python path: {sys.path}")
except Exception as e:
    print(f"❌ YOLO model loading failed: {e}")
    import traceback
    traceback.print_exc()

print("🔍 Debug completed")
