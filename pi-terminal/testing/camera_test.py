#!/usr/bin/env python3
from picamera2 import Picamera2
import cv2
import time

print("Testing Pi Camera...")

# Initialize camera
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"format": 'XRGB8888', "size": (640, 480)}
)
picam2.configure(config)
picam2.start()

print("Camera started - Press 'q' to quit")

try:
    while True:
        frame = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        cv2.putText(frame_bgr, 'Pi Camera Test', (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow('Camera Test', frame_bgr)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
except KeyboardInterrupt:
    print("Stopping...")

finally:
    picam2.stop()
    cv2.destroyAllWindows()
    print("Camera test completed")
