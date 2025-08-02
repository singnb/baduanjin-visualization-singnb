#!/usr/bin/env python3
"""
test_stream.py - Quick test script to debug live stream issues
Run this on your Pi to test each component individually
"""

import requests
import json
import time
import base64
from datetime import datetime

# Your ngrok URL
NGROK_URL = "https://mongoose-hardy-caiman.ngrok-free.app"

def test_health():
    """Test 1: Basic health check"""
    print("🔍 Test 1: Health Check")
    try:
        response = requests.get(f"{NGROK_URL}/api/health", timeout=10)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Camera Available: {data.get('services', {}).get('camera', 'Unknown')}")
        print(f"Streaming: {data.get('services', {}).get('streaming', 'Unknown')}")
        print("✅ Health check passed\n")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}\n")
        return False

def test_session_start():
    """Test 2: Start session"""
    print("🔍 Test 2: Start Session")
    try:
        headers = {
            'Content-Type': 'application/json',
            'ngrok-skip-browser-warning': 'true'
        }
        data = {"session_name": "Test Debug Session"}
        
        response = requests.post(f"{NGROK_URL}/api/pi-live/start-session", 
                                headers=headers, json=data, timeout=15)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Success: {result.get('success', False)}")
        if result.get('success'):
            print(f"Session ID: {result.get('session_id', 'Unknown')}")
            print("✅ Session start passed\n")
            return True
        else:
            print(f"Error: {result.get('message', 'Unknown error')}")
            print("❌ Session start failed\n")
            return False
    except Exception as e:
        print(f"❌ Session start failed: {e}\n")
        return False

def test_current_frame():
    """Test 3: Get current frame"""
    print("🔍 Test 3: Current Frame")
    try:
        headers = {'ngrok-skip-browser-warning': 'true'}
        response = requests.get(f"{NGROK_URL}/api/current_frame", 
                               headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success', False)}")
            print(f"Is Running: {data.get('is_running', False)}")
            
            if data.get('success') and data.get('image'):
                image_size = len(data['image'])
                print(f"Image Data Size: {image_size} characters")
                print(f"Pose Data: {len(data.get('pose_data', []))} persons")
                print(f"Recording: {data.get('is_recording', False)}")
                print("✅ Frame test passed\n")
                return True
            else:
                print(f"Error: {data.get('error', 'No image data')}")
                print("❌ Frame test failed\n")
                return False
        else:
            print(f"HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            print("❌ Frame test failed\n")
            return False
    except Exception as e:
        print(f"❌ Frame test failed: {e}\n")
        return False

def test_status():
    """Test 4: Get status"""
    print("🔍 Test 4: Status Check")
    try:
        headers = {'ngrok-skip-browser-warning': 'true'}
        response = requests.get(f"{NGROK_URL}/api/status", 
                               headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Is Running: {data.get('is_running', False)}")
        print(f"Camera Available: {data.get('camera_available', False)}")
        print(f"YOLO Available: {data.get('yolo_available', False)}")
        print(f"Is Recording: {data.get('is_recording', False)}")
        print(f"Current FPS: {data.get('current_fps', 0)}")
        print("✅ Status check passed\n")
        return True
    except Exception as e:
        print(f"❌ Status check failed: {e}\n")
        return False

def continuous_frame_test(duration=30):
    """Test 5: Continuous frame polling"""
    print(f"🔍 Test 5: Continuous Frame Test ({duration}s)")
    headers = {'ngrok-skip-browser-warning': 'true'}
    success_count = 0
    total_requests = 0
    
    start_time = time.time()
    while time.time() - start_time < duration:
        try:
            total_requests += 1
            response = requests.get(f"{NGROK_URL}/api/current_frame", 
                                   headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('image'):
                    success_count += 1
                    if total_requests % 10 == 0:  # Log every 10th request
                        print(f"📊 Request {total_requests}: ✅ Success ({len(data['image'])} chars)")
                else:
                    print(f"📊 Request {total_requests}: ❌ No image data")
            else:
                print(f"📊 Request {total_requests}: ❌ HTTP {response.status_code}")
                
        except Exception as e:
            print(f"📊 Request {total_requests}: ❌ Error: {e}")
        
        time.sleep(1)  # Wait 1 second between requests
    
    success_rate = (success_count / total_requests) * 100 if total_requests > 0 else 0
    print(f"\n📊 Continuous Test Results:")
    print(f"   Total Requests: {total_requests}")
    print(f"   Successful: {success_count}")
    print(f"   Success Rate: {success_rate:.1f}%")
    
    if success_rate > 80:
        print("✅ Continuous test passed\n")
        return True
    else:
        print("❌ Continuous test failed\n")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Pi Live Stream Debug Test")
    print("=" * 60)
    print(f"Testing: {NGROK_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)
    
    tests = [
        ("Health Check", test_health),
        ("Session Start", test_session_start),
        ("Status Check", test_status),
        ("Current Frame", test_current_frame),
        ("Continuous Frames", lambda: continuous_frame_test(10))  # 10 second test
    ]
    
    results = {}
    for test_name, test_func in tests:
        results[test_name] = test_func()
    
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print("=" * 60)
    
    # Diagnosis
    all_passed = all(results.values())
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("💡 If frontend still shows 'Waiting for video stream...', check:")
        print("   1. Frontend is using correct ngrok URL")
        print("   2. Frontend is calling /api/current_frame endpoint")
        print("   3. Browser network tab for failed requests")
    else:
        print("🚨 SOME TESTS FAILED!")
        print("💡 Check the failed tests above and:")
        print("   1. Ensure camera is not in use by other processes")
        print("   2. Check Pi server console for error messages")
        print("   3. Verify ngrok tunnel is active")
        
if __name__ == "__main__":
    main()