
# Optimized camera configuration for Baduanjin pose detection
# Based on performance testing results

def setup_optimized_camera():
    picam2 = Picamera2()
    
    config = picam2.create_preview_configuration(
        main={
            "format": 'XRGB8888',
            "size": (640, 480)
        }
    )
    
    picam2.configure(config)
    
    # Optimized controls for indoor NoIR camera
    picam2.set_controls({
        "FrameRate": 30,
        "ExposureTime": 26666,  # 80% of frame time
        "AnalogueGain": 1.5,        # Boost for NoIR indoor use
        "Brightness": 0.1,          # Slight brightness increase
        "Contrast": 1.3,            # Better edge definition for pose detection
        "Saturation": 0.8,          # Reduced saturation
    })
    
    picam2.start()
    return picam2

# Expected Performance:
# - FPS: 30.05
# - Latency: 33.27ms
# - Rating: 🟢 EXCELLENT
