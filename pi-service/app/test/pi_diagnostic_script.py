#!/usr/bin/env python3
"""
Baduanjin Pi Recording Diagnostic Script
Tests all recording functionality and reports issues
"""

import requests
import time
import json
import sys
from datetime import datetime
from pathlib import Path

# Configuration
PI_URL = "http://172.20.10.5:5001"  # Update to your Pi's IP
TEST_DURATION = 10  # seconds

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_status(message, status="INFO"):
    color = Colors.GREEN if status == "OK" else Colors.RED if status == "ERROR" else Colors.YELLOW
    print(f"{color}[{status}]{Colors.END} {message}")

def print_step(step_num, message):
    print(f"\n{Colors.BLUE}{Colors.BOLD}Step {step_num}: {message}{Colors.END}")

def test_pi_connection():
    """Test basic Pi connection"""
    print_step(1, "Testing Pi Connection")
    
    try:
        response = requests.get(f"{PI_URL}/api/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_status(f"✅ Pi connected at {PI_URL}", "OK")
            print_status(f"   Camera available: {data.get('camera_available', False)}", "INFO")
            print_status(f"   YOLO available: {data.get('yolo_available', False)}", "INFO")
            print_status(f"   Currently running: {data.get('is_running', False)}", "INFO")
            print_status(f"   Currently recording: {data.get('is_recording', False)}", "INFO")
            return True, data
        else:
            print_status(f"❌ Pi responded with status {response.status_code}", "ERROR")
            return False, None
    except requests.exceptions.RequestException as e:
        print_status(f"❌ Cannot connect to Pi: {e}", "ERROR")
        print_status(f"   Make sure Pi is running at {PI_URL}", "ERROR")
        return False, None

def test_streaming():
    """Test streaming functionality"""
    print_step(2, "Testing Streaming")
    
    try:
        # Start streaming
        print_status("Starting streaming...", "INFO")
        response = requests.post(f"{PI_URL}/api/start", timeout=10)
        if response.status_code == 200 and response.json().get('success'):
            print_status("✅ Streaming started successfully", "OK")
            
            # Wait a moment
            time.sleep(2)
            
            # Check status
            status_response = requests.get(f"{PI_URL}/api/status", timeout=5)
            if status_response.status_code == 200:
                data = status_response.json()
                if data.get('is_running'):
                    print_status("✅ Streaming is active", "OK")
                    return True
                else:
                    print_status("❌ Streaming not active", "ERROR")
                    return False
            else:
                print_status("❌ Cannot check streaming status", "ERROR")
                return False
        else:
            print_status(f"❌ Failed to start streaming: {response.json()}", "ERROR")
            return False
    except requests.exceptions.RequestException as e:
        print_status(f"❌ Streaming test failed: {e}", "ERROR")
        return False

def test_recording():
    """Test recording functionality"""
    print_step(3, "Testing Recording")
    
    try:
        # Start recording
        print_status("Starting recording...", "INFO")
        start_response = requests.post(f"{PI_URL}/api/recording/start", timeout=10)
        
        if start_response.status_code == 200:
            start_data = start_response.json()
            if start_data.get('success'):
                print_status("✅ Recording started successfully", "OK")
                
                # Wait for recording
                print_status(f"Recording for {TEST_DURATION} seconds...", "INFO")
                for i in range(TEST_DURATION):
                    print(f"   Recording... {i+1}/{TEST_DURATION}s", end='\r')
                    time.sleep(1)
                print()  # New line
                
                # Stop recording
                print_status("Stopping recording...", "INFO")
                stop_response = requests.post(f"{PI_URL}/api/recording/stop", timeout=15)
                
                if stop_response.status_code == 200:
                    stop_data = stop_response.json()
                    if stop_data.get('success'):
                        recording_info = stop_data.get('recording_info', {})
                        filename = recording_info.get('filename', 'Unknown')
                        duration = recording_info.get('duration', 0)
                        
                        print_status("✅ Recording stopped successfully", "OK")
                        print_status(f"   Filename: {filename}", "INFO")
                        print_status(f"   Duration: {duration}s", "INFO")
                        
                        return True, filename
                    else:
                        print_status(f"❌ Failed to stop recording: {stop_data}", "ERROR")
                        return False, None
                else:
                    print_status(f"❌ Stop recording request failed: {stop_response.status_code}", "ERROR")
                    return False, None
            else:
                print_status(f"❌ Failed to start recording: {start_data}", "ERROR")
                return False, None
        else:
            print_status(f"❌ Start recording request failed: {start_response.status_code}", "ERROR")
            return False, None
            
    except requests.exceptions.RequestException as e:
        print_status(f"❌ Recording test failed: {e}", "ERROR")
        return False, None

def test_recordings_list():
    """Test recordings list functionality"""
    print_step(4, "Testing Recordings List")
    
    try:
        response = requests.get(f"{PI_URL}/api/recordings", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                recordings = data.get('recordings', [])
                print_status(f"✅ Found {len(recordings)} recordings", "OK")
                
                for i, recording in enumerate(recordings[:5]):  # Show first 5
                    filename = recording.get('filename', 'Unknown')
                    size = recording.get('size', 0)
                    created = recording.get('created', 'Unknown')
                    print_status(f"   {i+1}. {filename} - {size/1024/1024:.2f}MB - {created}", "INFO")
                
                if len(recordings) > 5:
                    print_status(f"   ... and {len(recordings)-5} more", "INFO")
                
                return True, recordings
            else:
                print_status(f"❌ Failed to get recordings: {data}", "ERROR")
                return False, []
        else:
            print_status(f"❌ Recordings request failed: {response.status_code}", "ERROR")
            return False, []
    except requests.exceptions.RequestException as e:
        print_status(f"❌ Recordings list test failed: {e}", "ERROR")
        return False, []

def test_download(filename):
    """Test downloading a recording"""
    print_step(5, f"Testing Download: {filename}")
    
    try:
        response = requests.get(f"{PI_URL}/api/download/{filename}", timeout=30, stream=True)
        if response.status_code == 200:
            content_length = response.headers.get('content-length')
            if content_length:
                size = int(content_length)
                print_status(f"✅ Download started - File size: {size/1024/1024:.2f}MB", "OK")
                
                # Download first chunk to verify
                chunk = next(response.iter_content(chunk_size=8192))
                if chunk:
                    print_status("✅ Download working - received data", "OK")
                    return True
                else:
                    print_status("❌ Download failed - no data received", "ERROR")
                    return False
            else:
                print_status("❌ Download failed - no content length", "ERROR")
                return False
        else:
            print_status(f"❌ Download failed: {response.status_code}", "ERROR")
            return False
    except requests.exceptions.RequestException as e:
        print_status(f"❌ Download test failed: {e}", "ERROR")
        return False

def test_cleanup(filename):
    """Test deleting a test recording"""
    print_step(6, f"Testing Cleanup: {filename}")
    
    try:
        response = requests.delete(f"{PI_URL}/api/recordings/{filename}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print_status("✅ Test recording deleted successfully", "OK")
                return True
            else:
                print_status(f"❌ Failed to delete recording: {data}", "ERROR")
                return False
        else:
            print_status(f"❌ Delete request failed: {response.status_code}", "ERROR")
            return False
    except requests.exceptions.RequestException as e:
        print_status(f"❌ Cleanup test failed: {e}", "ERROR")
        return False

def check_pi_disk_space():
    """Check disk space on Pi"""
    print_step(7, "Checking Pi Disk Space")
    
    try:
        response = requests.get(f"{PI_URL}/api/stats", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_status("✅ Pi stats retrieved", "OK")
            print_status(f"   Total frames: {data.get('total_frames', 0)}", "INFO")
            print_status(f"   Current FPS: {data.get('current_fps', 0)}", "INFO")
            print_status(f"   Recording duration: {data.get('recording_duration', 0)}s", "INFO")
            return True
        else:
            print_status(f"❌ Stats request failed: {response.status_code}", "ERROR")
            return False
    except requests.exceptions.RequestException as e:
        print_status(f"❌ Stats check failed: {e}", "ERROR")
        return False

def main():
    print(f"{Colors.BOLD}🥋 Baduanjin Pi Recording Diagnostic{Colors.END}")
    print(f"Testing Pi at: {PI_URL}")
    print(f"Test duration: {TEST_DURATION} seconds")
    print("=" * 50)
    
    # Test 1: Basic connection
    connected, status_data = test_pi_connection()
    if not connected:
        print_status("❌ Cannot proceed without Pi connection", "ERROR")
        sys.exit(1)
    
    # Test 2: Streaming
    streaming_ok = test_streaming()
    if not streaming_ok:
        print_status("⚠️  Streaming failed - recording may not work", "ERROR")
    
    # Test 3: Recording
    recording_ok, test_filename = test_recording()
    if not recording_ok:
        print_status("❌ Recording failed - this is the main issue", "ERROR")
        test_filename = None
    
    # Test 4: List recordings
    list_ok, recordings = test_recordings_list()
    
    # Test 5: Download (if we have a test file)
    download_ok = False
    if test_filename and list_ok:
        # Check if our test file is in the list
        test_file_found = any(r.get('filename') == test_filename for r in recordings)
        if test_file_found:
            download_ok = test_download(test_filename)
        else:
            print_status(f"⚠️  Test file {test_filename} not found in recordings list", "ERROR")
    
    # Test 6: Cleanup (if we have a test file)
    cleanup_ok = False
    if test_filename and recording_ok:
        cleanup_ok = test_cleanup(test_filename)
    
    # Test 7: Disk space
    stats_ok = check_pi_disk_space()
    
    # Stop streaming
    try:
        requests.post(f"{PI_URL}/api/stop", timeout=10)
        print_status("🛑 Streaming stopped", "INFO")
    except:
        pass
    
    # Summary
    print(f"\n{Colors.BOLD}📊 DIAGNOSTIC SUMMARY{Colors.END}")
    print("=" * 50)
    
    tests = [
        ("Pi Connection", connected),
        ("Streaming", streaming_ok),
        ("Recording", recording_ok),
        ("Recordings List", list_ok),
        ("Download", download_ok or not test_filename),
        ("Cleanup", cleanup_ok or not test_filename),
        ("Pi Stats", stats_ok)
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print_status(f"{test_name}: {status}", "OK" if result else "ERROR")
    
    print(f"\n{Colors.BOLD}Result: {passed}/{total} tests passed{Colors.END}")
    
    if not recording_ok:
        print(f"\n{Colors.RED}{Colors.BOLD}🚨 RECORDING ISSUE DETECTED{Colors.END}")
        print("Possible causes:")
        print("1. Camera not properly connected or enabled")
        print("2. Insufficient disk space on Pi")
        print("3. Permissions issue with recordings directory")
        print("4. OpenCV/video encoding libraries missing")
        print("5. Pi camera module not properly configured")
        print("\nRecommended actions:")
        print("1. Check camera: sudo raspistill -o test.jpg")
        print("2. Check disk space: df -h")
        print("3. Check logs: tail -f /var/log/syslog | grep python")
        print("4. Enable camera: sudo raspi-config")
        print("5. Restart Pi server")
    
    elif not list_ok:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  RECORDINGS LIST ISSUE{Colors.END}")
        print("Recording works but listing fails - check API endpoint")
    
    else:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED{Colors.END}")
        print("Recording functionality is working correctly!")
        print(f"Your session should be able to record videos.")

if __name__ == "__main__":
    main()