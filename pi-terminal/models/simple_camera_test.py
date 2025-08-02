#!/usr/bin/env python3
"""
simple_camera_test.py - Test camera directly
"""

import cv2
import time
from datetime import datetime

def test_camera():
    """Test camera directly without Flask"""
    print("🔍 Testing camera directly...")
    
    try:
        from picamera2 import Picamera2
        print("✅ Picamera2 imported successfully")
    except ImportError as e:
        print(f"❌ Picamera2 import failed: {e}")
        return False
    
    try:
        # Initialize camera
        picam2 = Picamera2()
        print("✅ Picamera2 object created")
        
        # Configure camera
        config = picam2.create_preview_configuration(
            main={"format": 'XRGB8888', "size": (640, 480)}
        )
        picam2.configure(config)
        print("✅ Camera configured")
        
        # Start camera
        picam2.start()
        print("✅ Camera started")
        
        # Capture a few frames
        for i in range(5):
            print(f"📸 Capturing frame {i+1}...")
            frame = picam2.capture_array()
            print(f"✅ Frame {i+1} captured, shape: {frame.shape}")
            
            # Convert to BGR for OpenCV
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            print(f"✅ Frame {i+1} converted to BGR")
            
            # Save frame to file
            filename = f"test_frame_{i+1}.jpg"
            cv2.imwrite(filename, frame_bgr)
            print(f"✅ Frame {i+1} saved as {filename}")
            
            time.sleep(1)
        
        # Stop camera
        picam2.stop()
        print("✅ Camera stopped")
        
        print("\n🎉 Camera test PASSED!")
        print("📁 Check for test_frame_*.jpg files")
        return True
        
    except Exception as e:
        print(f"❌ Camera test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("📷 Simple Camera Test")
    print("=" * 50)
    success = test_camera()
    if success:
        print("\n💡 Camera works! The issue is likely in the Flask stream loop.")
    else:
        print("\n🚨 Camera doesn't work! Fix camera issues first.")
    print("=" * 50)