#!/usr/bin/env python3
"""
Reliable FPS Optimization Test - Fixed camera resource management
"""

from picamera2 import Picamera2
import cv2
import time
import numpy as np
import gc

def test_single_configuration(resolution, target_fps, format_type, test_name):
    """Test a single camera configuration safely"""
    print(f"\n🔧 {test_name}")
    print(f"   {resolution[0]}x{resolution[1]} @ {target_fps}FPS ({format_type})")
    
    picam2 = None
    try:
        # Create fresh camera instance
        picam2 = Picamera2()
        
        # Basic configuration first
        config = picam2.create_preview_configuration(
            main={
                "format": format_type, 
                "size": resolution
            }
        )
        
        # Apply configuration
        picam2.configure(config)
        
        # Set frame rate control after configuration
        picam2.set_controls({"FrameRate": target_fps})
        
        # Start camera
        picam2.start()
        
        # Warm up period
        print("   Warming up...")
        for _ in range(20):
            frame = picam2.capture_array()
            time.sleep(0.01)
        
        # Measure performance
        print("   Measuring performance...")
        start_time = time.time()
        frame_count = 0
        capture_times = []
        
        test_duration = 8  # seconds
        while time.time() - start_time < test_duration:
            capture_start = time.time()
            frame = picam2.capture_array()
            capture_end = time.time()
            
            capture_times.append((capture_end - capture_start) * 1000)
            frame_count += 1
        
        elapsed = time.time() - start_time
        actual_fps = frame_count / elapsed
        avg_latency = np.mean(capture_times)
        min_latency = np.min(capture_times)
        max_latency = np.max(capture_times)
        
        # Calculate efficiency
        efficiency = (actual_fps / target_fps) * 100 if target_fps > 0 else 0
        
        print(f"   Results:")
        print(f"     Target FPS: {target_fps}")
        print(f"     Actual FPS: {actual_fps:.2f} ({efficiency:.1f}% efficiency)")
        print(f"     Avg Latency: {avg_latency:.2f}ms")
        print(f"     Latency Range: {min_latency:.1f} - {max_latency:.1f}ms")
        
        # Performance rating
        if actual_fps >= target_fps * 0.9:
            rating = "🟢 EXCELLENT"
        elif actual_fps >= target_fps * 0.7:
            rating = "🟡 GOOD"
        elif actual_fps >= target_fps * 0.5:
            rating = "🟠 FAIR"
        else:
            rating = "🔴 POOR"
        
        print(f"     Rating: {rating}")
        
        return {
            'name': test_name,
            'resolution': resolution,
            'target_fps': target_fps,
            'actual_fps': round(actual_fps, 2),
            'format': format_type,
            'avg_latency_ms': round(avg_latency, 2),
            'min_latency_ms': round(min_latency, 2),
            'max_latency_ms': round(max_latency, 2),
            'efficiency': round(efficiency, 1),
            'rating': rating
        }
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return None
        
    finally:
        # Ensure proper cleanup
        if picam2 is not None:
            try:
                if picam2.started:
                    picam2.stop()
                picam2.close()
            except:
                pass
        
        # Force cleanup
        gc.collect()
        time.sleep(1)  # Give system time to release resources

def test_optimal_configurations():
    """Test the most promising configurations for your Baduanjin app"""
    print("🎯 TESTING OPTIMAL CONFIGURATIONS FOR BADUANJIN")
    print("=" * 60)
    
    # Conservative, tested configurations
    test_configs = [
        # (resolution, target_fps, format, test_name)
        ((640, 480), 20, "XRGB8888", "Current Baseline+"),
        ((640, 480), 25, "XRGB8888", "Target Performance"),
        ((640, 480), 30, "XRGB8888", "High Performance"),
        ((640, 480), 25, "YUV420", "YUV Format Test"),
        ((800, 600), 20, "XRGB8888", "Higher Resolution"),
        ((320, 240), 30, "XRGB8888", "Speed Test"),
    ]
    
    results = []
    
    for resolution, target_fps, format_type, test_name in test_configs:
        result = test_single_configuration(resolution, target_fps, format_type, test_name)
        if result:
            results.append(result)
        
        # Pause between tests
        print("   💤 Cooling down...")
        time.sleep(2)
    
    return results

def find_best_configuration(results):
    """Analyze results and recommend best configuration"""
    print(f"\n🏆 CONFIGURATION ANALYSIS")
    print("=" * 60)
    
    if not results:
        print("❌ No successful tests to analyze")
        return
    
    # Print all results in table format
    print(f"{'Configuration':<25} {'FPS':<8} {'Target':<8} {'Latency':<10} {'Rating'}")
    print("-" * 70)
    
    for result in results:
        res_str = f"{result['resolution'][0]}x{result['resolution'][1]} {result['format']}"
        print(f"{res_str:<25} {result['actual_fps']:<8} {result['target_fps']:<8} {result['avg_latency_ms']:<10} {result['rating']}")
    
    # Find best performers
    print(f"\n🥇 BEST PERFORMERS:")
    
    # Best FPS
    best_fps = max(results, key=lambda x: x['actual_fps'])
    print(f"Highest FPS: {best_fps['name']} - {best_fps['actual_fps']} FPS")
    
    # Best latency
    best_latency = min(results, key=lambda x: x['avg_latency_ms'])
    print(f"Lowest Latency: {best_latency['name']} - {best_latency['avg_latency_ms']}ms")
    
    # Best efficiency
    best_efficiency = max(results, key=lambda x: x['efficiency'])
    print(f"Best Efficiency: {best_efficiency['name']} - {best_efficiency['efficiency']}%")
    
    # Recommend for Baduanjin (balance of FPS and latency)
    baduanjin_scores = []
    for result in results:
        # Score based on: 70% FPS achievement, 30% low latency
        fps_score = min(result['actual_fps'] / 25, 1.0) * 70  # 25 FPS target
        latency_score = max(0, (100 - result['avg_latency_ms']) / 100) * 30
        total_score = fps_score + latency_score
        baduanjin_scores.append((result, total_score))
    
    best_for_baduanjin = max(baduanjin_scores, key=lambda x: x[1])
    
    print(f"\n🎯 RECOMMENDED FOR BADUANJIN:")
    rec = best_for_baduanjin[0]
    print(f"Configuration: {rec['resolution'][0]}x{rec['resolution'][1]} {rec['format']}")
    print(f"Performance: {rec['actual_fps']} FPS, {rec['avg_latency_ms']}ms latency")
    print(f"Rating: {rec['rating']}")
    print(f"Score: {best_for_baduanjin[1]:.1f}/100")
    
    return rec

def generate_production_config(recommended):
    """Generate production-ready camera configuration"""
    if not recommended:
        return
    
    print(f"\n🚀 PRODUCTION CONFIGURATION CODE")
    print("=" * 60)
    
    config_code = f'''
# Optimized camera configuration for Baduanjin pose detection
# Based on performance testing results

def setup_optimized_camera():
    picam2 = Picamera2()
    
    config = picam2.create_preview_configuration(
        main={{
            "format": '{recommended['format']}',
            "size": {recommended['resolution']}
        }}
    )
    
    picam2.configure(config)
    
    # Optimized controls for indoor NoIR camera
    picam2.set_controls({{
        "FrameRate": {recommended['target_fps']},
        "ExposureTime": {int(1000000 / recommended['target_fps'] * 0.8)},  # 80% of frame time
        "AnalogueGain": 1.5,        # Boost for NoIR indoor use
        "Brightness": 0.1,          # Slight brightness increase
        "Contrast": 1.3,            # Better edge definition for pose detection
        "Saturation": 0.8,          # Reduced saturation
    }})
    
    picam2.start()
    return picam2

# Expected Performance:
# - FPS: {recommended['actual_fps']}
# - Latency: {recommended['avg_latency_ms']}ms
# - Rating: {recommended['rating']}
'''
    
    print(config_code)
    
    # Save to file
    with open('optimized_camera_config.py', 'w') as f:
        f.write(config_code)
    
    print(f"💾 Configuration saved to: optimized_camera_config.py")

if __name__ == "__main__":
    print("🎬 RELIABLE FPS OPTIMIZATION TEST")
    print("🔧 Fixed camera resource management")
    print("⏱️  This will take about 2-3 minutes...")
    print("=" * 60)
    
    try:
        # Run optimized tests
        results = test_optimal_configurations()
        
        # Analyze and recommend
        recommended = find_best_configuration(results)
        
        # Generate production config
        generate_production_config(recommended)
        
        print(f"\n✅ OPTIMIZATION COMPLETE!")
        print(f"Check 'optimized_camera_config.py' for your production settings.")
        
    except Exception as e:
        print(f"❌ Test suite error: {e}")
        print("Try running individual configurations manually if issues persist.")