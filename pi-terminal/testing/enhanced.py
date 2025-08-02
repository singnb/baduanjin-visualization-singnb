#!/usr/bin/env python3
"""
Enhanced version of your camera_test.py with performance metrics
Run this first for quick baseline assessment
"""

from picamera2 import Picamera2
import cv2
import time
import numpy as np

print("🎬 Enhanced Pi Camera Test with Performance Metrics")
print("=" * 50)

# Initialize camera
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"format": 'XRGB8888', "size": (640, 480)}
)
picam2.configure(config)
picam2.start()

print("📊 Camera started - Collecting metrics...")
print("Controls:")
print("  'q' - Quit")
print("  's' - Save screenshot")
print("  'f' - Show FPS stats")

# Performance tracking
frame_times = []
capture_times = []
frame_count = 0
start_time = time.time()

try:
    while True:
        # Measure capture time
        capture_start = time.time()
        frame = picam2.capture_array()
        capture_end = time.time()
        capture_time = (capture_end - capture_start) * 1000  # ms
        capture_times.append(capture_time)
        
        # Process frame
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Calculate current FPS
        current_time = time.time()
        if frame_count > 0:
            time_diff = current_time - frame_times[-1] if frame_times else 0
            current_fps = 1.0 / time_diff if time_diff > 0 else 0
        else:
            current_fps = 0
        
        frame_times.append(current_time)
        frame_count += 1
        
        # Calculate running averages (last 30 frames)
        if len(frame_times) > 30:
            frame_times = frame_times[-30:]
            capture_times = capture_times[-30:]
        
        if len(frame_times) > 1:
            recent_fps = len(frame_times) / (frame_times[-1] - frame_times[0]) if len(frame_times) > 1 else 0
            avg_capture_time = np.mean(capture_times[-30:])
        else:
            recent_fps = 0
            avg_capture_time = 0
        
        # Add performance overlay
        cv2.putText(frame_bgr, 'Pi Camera Test - Performance Monitor', 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.putText(frame_bgr, f'FPS: {recent_fps:.1f}', 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        cv2.putText(frame_bgr, f'Capture: {avg_capture_time:.1f}ms', 
                   (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        cv2.putText(frame_bgr, f'Frame: {frame_count}', 
                   (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        # Image quality info
        brightness = np.mean(frame)
        cv2.putText(frame_bgr, f'Brightness: {brightness:.0f}', 
                   (10, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        cv2.imshow('Enhanced Camera Test', frame_bgr)
        
        # Make sure window has focus for key detection
        cv2.setWindowProperty('Enhanced Camera Test', cv2.WND_PROP_TOPMOST, 1)
        
        key = cv2.waitKey(30) & 0xFF  # Increased wait time
        if key == ord('q') or key == 27:  # q or ESC
            print("🛑 Quit command received")
            break
        elif key == ord('s'):
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"camera_test_{timestamp}.jpg"
            cv2.imwrite(filename, frame_bgr)
            print(f"📸 Screenshot saved: {filename}")
        elif key == ord('f'):
            print(f"\n📊 Current Stats:")
            print(f"  FPS: {recent_fps:.2f}")
            print(f"  Avg Capture Time: {avg_capture_time:.2f}ms")
            print(f"  Total Frames: {frame_count}")
            print(f"  Running Time: {time.time() - start_time:.1f}s")
            print(f"  Image Brightness: {brightness:.1f}")
        
        # Auto-stats every 100 frames
        if frame_count % 100 == 0:
            print(f"📊 Frame {frame_count}: FPS={recent_fps:.1f}, Latency={avg_capture_time:.1f}ms")
            
except KeyboardInterrupt:
    print("\n⏹️  Stopping...")

finally:
    # Final statistics
    total_time = time.time() - start_time
    overall_fps = frame_count / total_time if total_time > 0 else 0
    
    print("\n📈 FINAL PERFORMANCE REPORT")
    print("=" * 40)
    print(f"Total Runtime: {total_time:.1f} seconds")
    print(f"Total Frames: {frame_count}")
    print(f"Overall FPS: {overall_fps:.2f}")
    print(f"Average Capture Time: {np.mean(capture_times):.2f}ms")
    print(f"Min Capture Time: {np.min(capture_times):.2f}ms")
    print(f"Max Capture Time: {np.max(capture_times):.2f}ms")
    
    # Performance rating
    if overall_fps >= 25:
        rating = "🟢 EXCELLENT"
    elif overall_fps >= 15:
        rating = "🟡 GOOD" 
    elif overall_fps >= 10:
        rating = "🟠 FAIR"
    else:
        rating = "🔴 NEEDS OPTIMIZATION"
    
    print(f"Performance Rating: {rating}")
    
    picam2.stop()
    cv2.destroyAllWindows()
    print("✅ Camera test completed")