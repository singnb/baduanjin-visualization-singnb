# test_pi_integration.py
"""
Test script to verify Pi integration is working
Run this after setting up the integration
"""

import requests
import json
import time

# Configuration
BACKEND_URL = "http://localhost:8000"
PI_URL = "http://192.168.0.4:5001"
# PI_URL = "http://172.20.10.5:5001"

def test_pi_direct():
    """Test direct Pi connection"""
    print("🔍 Testing direct Pi connection...")
    try:
        response = requests.get(f"{PI_URL}/api/status", timeout=5)
        print(f"✅ Pi Direct Status: {response.status_code}")
        print(f"   Data: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Pi Direct Failed: {e}")
        return False

def test_backend_pi_status():
    """Test Pi status through backend"""
    print("\n🔍 Testing Pi status through backend...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/pi-status", timeout=5)
        print(f"✅ Backend Pi Status: {response.status_code}")
        print(f"   Data: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Backend Pi Status Failed: {e}")
        return False

def test_live_endpoints():
    """Test live session endpoints (requires auth token)"""
    print("\n🔍 Testing live session endpoints...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/pi-live/status", timeout=5)
        print(f"✅ Live Status Endpoint: {response.status_code}")
        print(f"   Data: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Live Status Failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Starting Pi Integration Tests\n")
    
    # Test 1: Direct Pi connection
    pi_direct = test_pi_direct()
    
    # Test 2: Backend Pi status
    backend_pi = test_backend_pi_status()
    
    # Test 3: Live endpoints
    live_endpoints = test_live_endpoints()
    
    # Summary
    print("\n📊 Test Results Summary:")
    print(f"   Direct Pi Connection: {'✅' if pi_direct else '❌'}")
    print(f"   Backend Pi Status: {'✅' if backend_pi else '❌'}")
    print(f"   Live Endpoints: {'✅' if live_endpoints else '❌'}")
    
    if all([pi_direct, backend_pi, live_endpoints]):
        print("\n🎉 All tests passed! Integration is working correctly.")
        print("\n📋 Next steps:")
        print("   1. Test with authenticated user")
        print("   2. Start a live session")
        print("   3. Test pose data capture")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        print("\n🔧 Troubleshooting:")
        if not pi_direct:
            print("   - Ensure Pi is running: python3 web_server.py")
            print("   - Check Pi IP: should be 192.168.0.4:5001")
            # print("   - Check Pi IP: should be 172.20.10.5:5001")
        if not backend_pi:
            print("   - Ensure FastAPI backend is running: uvicorn main:app --reload")
            print("   - Check backend port: should be localhost:8000")

if __name__ == "__main__":
    main()