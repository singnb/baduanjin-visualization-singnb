#!/usr/bin/env python3
"""
Test both servers to compare CORS configuration
"""

import requests

def test_cors_headers(url, server_name):
    """Test CORS headers for a specific server"""
    print(f"\n🧪 Testing {server_name} at {url}")
    print("=" * 50)
    
    try:
        # Test OPTIONS request with CORS headers
        headers = {
            'Origin': 'http://localhost:3000',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'Content-Type'
        }
        
        response = requests.options(url, headers=headers, timeout=5)
        print(f"   Status Code: {response.status_code}")
        
        # Check CORS headers
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
            'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials')
        }
        
        print(f"   CORS Headers: {cors_headers}")
        
        # Check if CORS is properly configured
        has_origin = cors_headers['Access-Control-Allow-Origin'] is not None
        has_methods = cors_headers['Access-Control-Allow-Methods'] is not None
        
        if has_origin and has_methods:
            print(f"   ✅ CORS properly configured for {server_name}")
            return True
        else:
            print(f"   ❌ CORS missing for {server_name}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing {server_name}: {e}")
        return False

def test_socket_io_endpoint(url, server_name):
    """Test Socket.IO endpoint specifically"""
    print(f"\n🔌 Testing Socket.IO endpoint for {server_name}")
    print("=" * 50)
    
    try:
        socketio_url = f"{url}/socket.io/"
        response = requests.get(f"{socketio_url}?EIO=4&transport=polling", timeout=5)
        print(f"   Socket.IO Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ Socket.IO endpoint working for {server_name}")
            return True
        else:
            print(f"   ❌ Socket.IO endpoint failed for {server_name}")
            return False
            
    except Exception as e:
        print(f"   ❌ Socket.IO test failed for {server_name}: {e}")
        return False

def main():
    """Test both servers"""
    print("🔬 Dual Server CORS Comparison Test")
    print("=" * 50)
    
    # Test the test server (port 5002)
    test_server_working = test_cors_headers("http://172.20.10.5:5002", "Test Server (5002)")
    test_socketio_working = test_socket_io_endpoint("http://172.20.10.5:5002", "Test Server")
    
    # Test the main server (port 5001)
    main_server_working = test_cors_headers("http://172.20.10.5:5001", "Main Server (5001)")
    main_socketio_working = test_socket_io_endpoint("http://172.20.10.5:5001", "Main Server")
    
    print(f"\n📊 RESULTS SUMMARY")
    print("=" * 30)
    print(f"Test Server (5002) CORS:     {'✅ Working' if test_server_working else '❌ Failed'}")
    print(f"Test Server (5002) Socket.IO: {'✅ Working' if test_socketio_working else '❌ Failed'}")
    print(f"Main Server (5001) CORS:     {'✅ Working' if main_server_working else '❌ Failed'}")
    print(f"Main Server (5001) Socket.IO: {'✅ Working' if main_socketio_working else '❌ Failed'}")
    
    if test_server_working and not main_server_working:
        print(f"\n💡 DIAGNOSIS: Test server works, main server needs CORS fix!")
        print("   → Apply the same CORS configuration to web_server.py")
    elif test_server_working and main_server_working:
        print(f"\n🎉 DIAGNOSIS: Both servers working! Frontend issue or different problem.")
    else:
        print(f"\n🔍 DIAGNOSIS: Need to investigate further...")

if __name__ == "__main__":
    main()