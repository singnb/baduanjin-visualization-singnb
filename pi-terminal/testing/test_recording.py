# test_recording.py - Debug script for Pi recording issues

import cv2
from pathlib import Path
from config import Config

def test_recording_setup():
    """Test recording setup to identify issues"""
    print("🔍 Testing Pi recording setup...")
    
    # Test 1: Check recordings directory
    print(f"📁 Recordings directory: {Config.RECORDINGS_DIR}")
    print(f"📁 Directory exists: {Config.RECORDINGS_DIR.exists()}")
    
    if not Config.RECORDINGS_DIR.exists():
        try:
            Config.RECORDINGS_DIR.mkdir(exist_ok=True)
            print("✅ Created recordings directory")
        except Exception as e:
            print(f"❌ Cannot create recordings directory: {e}")
            return False
    
    # Test 2: Check write permissions
    test_file = Config.RECORDINGS_DIR / "test_write.txt"
    try:
        with open(test_file, 'w') as f:
            f.write("test")
        test_file.unlink()  # Delete test file
        print("✅ Write permissions OK")
    except Exception as e:
        print(f"❌ Write permission failed: {e}")
        return False
    
    # Test 3: Test video codec
    test_video_path = Config.RECORDINGS_DIR / "test_video.mp4"
    try:
        fourcc = cv2.VideoWriter_fourcc(*Config.VIDEO_CODEC)
        print(f"📹 Testing codec: {Config.VIDEO_CODEC}")
        
        video_writer = cv2.VideoWriter(
            str(test_video_path), fourcc, Config.VIDEO_FPS, 
            (Config.CAMERA_WIDTH, Config.CAMERA_HEIGHT)
        )
        
        if video_writer.isOpened():
            print("✅ Video writer opened successfully")
            video_writer.release()
            
            # Clean up test file
            if test_video_path.exists():
                test_video_path.unlink()
            
            return True
        else:
            print("❌ Video writer failed to open")
            return False
            
    except Exception as e:
        print(f"❌ Video codec test failed: {e}")
        return False

def test_camera_format():
    """Test camera frame format compatibility"""
    try:
        from picamera2 import Picamera2
        import numpy as np
        
        print("📷 Testing camera format...")
        
        picam2 = Picamera2()
        config = picam2.create_preview_configuration(
            main={"format": 'XRGB8888', "size": (Config.CAMERA_WIDTH, Config.CAMERA_HEIGHT)}
        )
        picam2.configure(config)
        picam2.start()
        
        # Capture test frame
        frame = picam2.capture_array()
        print(f"📸 Frame shape: {frame.shape}")
        print(f"📸 Frame dtype: {frame.dtype}")
        
        # Convert to BGR
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        print(f"📸 BGR frame shape: {frame_bgr.shape}")
        
        picam2.stop()
        print("✅ Camera format test passed")
        return True
        
    except Exception as e:
        print(f"❌ Camera format test failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🔍 Pi Recording Debug Test")
    print("=" * 50)
    
    # Run tests
    recording_ok = test_recording_setup()
    camera_ok = test_camera_format()
    
    print("=" * 50)
    print("📊 Test Results:")
    print(f"📹 Recording setup: {'✅ PASS' if recording_ok else '❌ FAIL'}")
    print(f"📷 Camera format: {'✅ PASS' if camera_ok else '❌ FAIL'}")
    
    if recording_ok and camera_ok:
        print("🎉 All tests passed! Recording should work.")
    else:
        print("⚠️ Issues found. Check errors above.")
    
    print("=" * 50)