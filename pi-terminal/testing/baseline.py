#!/usr/bin/env python3
"""
Comprehensive Camera Testing Suite for Pi 5 + NoIR Camera v3
Run these tests to establish baseline performance before optimization
"""

from picamera2 import Picamera2
import cv2
import time
import numpy as np
import json
from datetime import datetime

class CameraPerformanceTester:
    def __init__(self):
        self.picam2 = Picamera2()
        self.test_results = {}
        
    def test_resolutions(self):
        """Test different resolutions and measure FPS"""
        print("\n=== RESOLUTION & FPS TESTING ===")
        
        resolutions = [
            (320, 240),   # Low
            (640, 480),   # Current
            (800, 600),   # Medium
            (1280, 720),  # HD
            (1920, 1080), # Full HD
        ]
        
        formats = ['XRGB8888', 'YUV420', 'RGB888']
        
        for resolution in resolutions:
            for fmt in formats:
                try:
                    print(f"\nTesting {resolution[0]}x{resolution[1]} - {fmt}")
                    
                    config = self.picam2.create_preview_configuration(
                        main={"format": fmt, "size": resolution}
                    )
                    self.picam2.configure(config)
                    self.picam2.start()
                    
                    # Warm up
                    for _ in range(10):
                        frame = self.picam2.capture_array()
                    
                    # Measure FPS
                    start_time = time.time()
                    frame_count = 0
                    test_duration = 5  # seconds
                    
                    while time.time() - start_time < test_duration:
                        frame = self.picam2.capture_array()
                        frame_count += 1
                    
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed
                    
                    key = f"{resolution[0]}x{resolution[1]}_{fmt}"
                    self.test_results[key] = {
                        'fps': round(fps, 2),
                        'resolution': resolution,
                        'format': fmt
                    }
                    
                    print(f"  FPS: {fps:.2f}")
                    
                    self.picam2.stop()
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"  Failed: {e}")
                    if self.picam2.started:
                        self.picam2.stop()
    
    def test_latency(self):
        """Test capture latency"""
        print("\n=== LATENCY TESTING ===")
        
        config = self.picam2.create_preview_configuration(
            main={"format": 'XRGB8888', "size": (640, 480)}
        )
        self.picam2.configure(config)
        self.picam2.start()
        
        latencies = []
        
        for i in range(50):
            start = time.time()
            frame = self.picam2.capture_array()
            end = time.time()
            latency = (end - start) * 1000  # ms
            latencies.append(latency)
        
        avg_latency = np.mean(latencies)
        min_latency = np.min(latencies)
        max_latency = np.max(latencies)
        
        print(f"Average Latency: {avg_latency:.2f}ms")
        print(f"Min Latency: {min_latency:.2f}ms")
        print(f"Max Latency: {max_latency:.2f}ms")
        
        self.test_results['latency'] = {
            'avg_ms': round(avg_latency, 2),
            'min_ms': round(min_latency, 2),
            'max_ms': round(max_latency, 2)
        }
        
        self.picam2.stop()
    
    def test_camera_controls(self):
        """Test different camera control settings"""
        print("\n=== CAMERA CONTROLS TESTING ===")
        
        config = self.picam2.create_preview_configuration(
            main={"format": 'XRGB8888', "size": (640, 480)}
        )
        self.picam2.configure(config)
        self.picam2.start()
        
        # Test different brightness levels
        brightness_levels = [0.0, 0.2, 0.5, 0.8, 1.0]
        print("Testing brightness levels...")
        
        for brightness in brightness_levels:
            self.picam2.set_controls({"Brightness": brightness})
            time.sleep(1)  # Allow adjustment
            frame = self.picam2.capture_array()
            avg_brightness = np.mean(frame)
            print(f"  Brightness {brightness}: Avg pixel value = {avg_brightness:.1f}")
        
        # Test contrast
        contrast_levels = [0.5, 1.0, 1.5, 2.0]
        print("Testing contrast levels...")
        
        for contrast in contrast_levels:
            self.picam2.set_controls({"Contrast": contrast})
            time.sleep(1)
            frame = self.picam2.capture_array()
            std_dev = np.std(frame)
            print(f"  Contrast {contrast}: Std deviation = {std_dev:.1f}")
        
        # Reset to defaults
        self.picam2.set_controls({"Brightness": 0.0, "Contrast": 1.0})
        
        self.picam2.stop()
    
    def test_exposure_modes(self):
        """Test different exposure settings for indoor use"""
        print("\n=== EXPOSURE MODES TESTING ===")
        
        config = self.picam2.create_preview_configuration(
            main={"format": 'XRGB8888', "size": (640, 480)}
        )
        self.picam2.configure(config)
        self.picam2.start()
        
        # Test manual exposure times (microseconds)
        exposure_times = [1000, 5000, 10000, 20000, 33333]  # Up to 30fps limit
        
        print("Testing exposure times (for indoor lighting)...")
        
        for exp_time in exposure_times:
            try:
                self.picam2.set_controls({
                    "ExposureTime": exp_time,
                    "AnalogueGain": 1.0
                })
                time.sleep(1)
                
                frame = self.picam2.capture_array()
                avg_brightness = np.mean(frame)
                print(f"  Exposure {exp_time}μs: Avg brightness = {avg_brightness:.1f}")
                
            except Exception as e:
                print(f"  Exposure {exp_time}μs: Failed - {e}")
        
        self.picam2.stop()
    
    def test_cpu_usage(self):
        """Test CPU usage during capture"""
        print("\n=== CPU USAGE TESTING ===")
        
        import psutil
        
        config = self.picam2.create_preview_configuration(
            main={"format": 'XRGB8888', "size": (640, 480)}
        )
        self.picam2.configure(config)
        self.picam2.start()
        
        # Monitor CPU for 10 seconds
        cpu_readings = []
        start_time = time.time()
        
        while time.time() - start_time < 10:
            frame = self.picam2.capture_array()
            cpu_percent = psutil.cpu_percent()
            cpu_readings.append(cpu_percent)
            time.sleep(0.1)
        
        avg_cpu = np.mean(cpu_readings)
        max_cpu = np.max(cpu_readings)
        
        print(f"Average CPU Usage: {avg_cpu:.1f}%")
        print(f"Peak CPU Usage: {max_cpu:.1f}%")
        
        self.test_results['cpu_usage'] = {
            'avg_percent': round(avg_cpu, 1),
            'peak_percent': round(max_cpu, 1)
        }
        
        self.picam2.stop()
    
    def test_memory_usage(self):
        """Test memory usage patterns"""
        print("\n=== MEMORY USAGE TESTING ===")
        
        import psutil
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        config = self.picam2.create_preview_configuration(
            main={"format": 'XRGB8888', "size": (640, 480)}
        )
        self.picam2.configure(config)
        self.picam2.start()
        
        # Capture frames for memory monitoring
        for i in range(100):
            frame = self.picam2.capture_array()
            if i % 20 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                print(f"  Frame {i}: Memory usage = {current_memory:.1f}MB")
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        print(f"Initial Memory: {initial_memory:.1f}MB")
        print(f"Final Memory: {final_memory:.1f}MB")
        print(f"Memory Increase: {memory_increase:.1f}MB")
        
        self.test_results['memory_usage'] = {
            'initial_mb': round(initial_memory, 1),
            'final_mb': round(final_memory, 1),
            'increase_mb': round(memory_increase, 1)
        }
        
        self.picam2.stop()
    
    def save_results(self):
        """Save test results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"camera_baseline_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"\n=== RESULTS SAVED ===")
        print(f"Results saved to: {filename}")
        
        # Print summary
        print("\n=== PERFORMANCE SUMMARY ===")
        print("Best performing configurations:")
        
        # Find best FPS for each resolution
        fps_results = {k: v for k, v in self.test_results.items() 
                      if isinstance(v, dict) and 'fps' in v}
        
        for res_fmt, data in sorted(fps_results.items(), 
                                   key=lambda x: x[1]['fps'], reverse=True)[:5]:
            print(f"  {res_fmt}: {data['fps']} FPS")
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("🎬 STARTING CAMERA PERFORMANCE BASELINE TESTS")
        print("=" * 50)
        
        try:
            self.test_resolutions()
            self.test_latency()
            self.test_camera_controls()
            self.test_exposure_modes()
            self.test_cpu_usage()
            self.test_memory_usage()
            self.save_results()
            
        except Exception as e:
            print(f"Test suite error: {e}")
            if hasattr(self, 'picam2') and self.picam2.started:
                self.picam2.stop()
        
        print("\n🎉 BASELINE TESTING COMPLETE!")
        print("Review the results to identify optimization opportunities.")

if __name__ == "__main__":
    tester = CameraPerformanceTester()
    tester.run_all_tests()