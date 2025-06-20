#!/usr/bin/env python3
"""
Socket.IO Connection Diagnostic for Pi Server - FIXED VERSION
Tests the Flask-SocketIO configuration and compatibility with proper CORS testing
"""

import requests
import time
import json

PI_URL = "http://172.20.10.5:5001"

def print_status(message, status="INFO"):
    colors = {"OK": "\033[92m", "ERROR": "\033[91m", "INFO": "\033[94m"}
    end_color = "\033[0m"
    color = colors.get(status, "")
    print(f"{color}[{status}]{end_color} {message}")

def test_pi_connection():
    """Test basic Pi connection"""
    print_status("Testing Pi Connection...", "INFO")
    
    try:
        response = requests.get(f"{PI_URL}/api/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_status("Pi connected successfully", "OK")
            print_status(f"   Camera available: {data.get('camera_available', False)}", "INFO")
            print_status(f"   YOLO available: {data.get('yolo_available', False)}", "INFO")
            print_status(f"   Currently running: {data.get('is_running', False)}", "INFO")
            print_status(f"   Currently recording: {data.get('is_recording', False)}", "INFO")
            return True, data
        else:
            print_status(f"Pi responded with status {response.status_code}", "ERROR")
            return False, None
    except requests.exceptions.RequestException as e:
        print_status(f"Cannot connect to Pi: {e}", "ERROR")
        print_status(f"   Make sure Pi is running at {PI_URL}", "ERROR")
        return False, None

def test_socketio_endpoint():
    """Test Socket.IO endpoint"""
    print_status("Testing Socket.IO endpoint...", "INFO")
    
    try:
        socketio_url = f"{PI_URL}/socket.io/"
        response = requests.get(f"{socketio_url}?EIO=4&transport=polling", timeout=5)
        print_status(f"Socket.IO handshake response: {response.status_code}", "INFO")
        
        if response.status_code == 200:
            print_status("Socket.IO endpoint accessible", "OK")
            content_preview = response.text[:100] + "..." if len(response.text) > 100 else response.text
            print_status(f"   Response content: {content_preview}", "INFO")
            return True
        else:
            print_status(f"Socket.IO endpoint failed: {response.status_code}", "ERROR")
            return False
            
    except Exception as e:
        print_status(f"Socket.IO endpoint test failed: {e}", "ERROR")
        return False

def test_cors_headers():
    """Test CORS headers - FIXED VERSION"""
    print_status("Testing CORS headers...", "INFO")
    
    try:
        # 🔧 FIXED: Send proper CORS preflight request headers
        cors_headers = {
            'Origin': 'http://localhost:3000',  # Simulate frontend origin
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'Content-Type'
        }
        
        # Test multiple endpoints
        test_endpoints = [
            f"{PI_URL}/api/status",
            f"{PI_URL}/socket.io/",
            f"{PI_URL}/"
        ]
        
        cors_working = False
        
        for endpoint in test_endpoints:
            try:
                print_status(f"   Testing CORS on: {endpoint}", "INFO")
                response = requests.options(endpoint, headers=cors_headers, timeout=5)
                
                cors_response_headers = {
                    'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                    'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                    'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
                }
                
                print_status(f"     Status: {response.status_code}", "INFO")
                print_status(f"     CORS headers: {cors_response_headers}", "INFO")
                
                # Check if CORS headers are present
                if cors_response_headers['Access-Control-Allow-Origin']:
                    print_status(f"     ✅ CORS working on {endpoint}", "OK")
                    cors_working = True
                    break
                else:
                    print_status(f"     ❌ No CORS headers on {endpoint}", "ERROR")
                    
            except Exception as e:
                print_status(f"     ❌ Error testing {endpoint}: {e}", "ERROR")
        
        if cors_working:
            print_status("CORS properly configured", "OK")
            return True
        else:
            print_status("CORS not properly configured", "ERROR")
            return False
            
    except Exception as e:
        print_status(f"CORS test failed: {e}", "ERROR")
        return False

def test_frontend_simulation():
    """Simulate actual frontend request"""
    print_status("Simulating frontend request...", "INFO")
    
    try:
        # Simulate what the browser does
        headers = {
            'Origin': 'http://localhost:3000',
            'User-Agent': 'Mozilla/5.0 (compatible; Baduanjin-Test)',
            'Accept': 'application/json'
        }
        
        response = requests.get(f"{PI_URL}/api/status", headers=headers, timeout=5)
        
        print_status(f"   Status: {response.status_code}", "INFO")
        print_status(f"   Response CORS headers:", "INFO")
        print_status(f"     Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin')}", "INFO")
        print_status(f"     Access-Control-Allow-Methods: {response.headers.get('Access-Control-Allow-Methods')}", "INFO")
        print_status(f"     Access-Control-Allow-Headers: {response.headers.get('Access-Control-Allow-Headers')}", "INFO")
        
        if response.headers.get('Access-Control-Allow-Origin'):
            print_status("Frontend simulation: CORS working!", "OK")
            return True
        else:
            print_status("Frontend simulation: CORS not working", "ERROR")
            return False
            
    except Exception as e:
        print_status(f"Frontend simulation failed: {e}", "ERROR")
        return False

def main():
    """Main diagnostic function"""
    print("🔧 Baduanjin Socket.IO Diagnostic Tool - FIXED VERSION")
    print("=" * 60)
    
    # Test 1: Basic connection
    print("\n📡 Test 1: Basic HTTP connectivity...")
    connected, status_data = test_pi_connection()
    if not connected:
        print_status("Cannot proceed without Pi connection", "ERROR")
        return
    
    # Test 2: Socket.IO endpoint
    print("\n🔌 Test 2: Socket.IO endpoint...")
    socketio_ok = test_socketio_endpoint()
    
    # Test 3: CORS headers (FIXED)
    print("\n🌐 Test 3: CORS headers (Fixed Method)...")
    cors_ok = test_cors_headers()
    
    # Test 4: Frontend simulation
    print("\n🎯 Test 4: Frontend request simulation...")
    frontend_ok = test_frontend_simulation()
    
    # Summary
    print(f"\n📊 DIAGNOSTIC SUMMARY")
    print("=" * 30)
    
    tests = [
        ("Pi Connection", connected),
        ("Socket.IO Endpoint", socketio_ok),
        ("CORS Configuration", cors_ok),
        ("Frontend Simulation", frontend_ok)
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for test_name, result in tests:
        status_icon = "✅ PASS" if result else "❌ FAIL"
        print_status(f"{test_name}: {status_icon}", "OK" if result else "ERROR")
    
    print(f"\n🎯 Result: {passed}/{total} tests passed")
    
    if cors_ok and frontend_ok:
        print_status("🎉 CORS is working! Frontend should connect successfully.", "OK")
        print_status("If frontend still fails, check:", "INFO")
        print_status("  1. Browser cache (clear it)", "INFO")
        print_status("  2. Frontend Socket.IO client version", "INFO")
        print_status("  3. Browser console for specific errors", "INFO")
    elif not cors_ok:
        print_status("🚨 CORS issue detected", "ERROR")
        print_status("Apply the CORS fix to web_server.py and restart", "ERROR")
    else:
        print_status("🔍 Mixed results - check individual test details above", "INFO")

if __name__ == "__main__":
    main()