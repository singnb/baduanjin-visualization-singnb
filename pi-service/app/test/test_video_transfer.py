#!/usr/bin/env python3
"""
Test script for video transfer functionality
Run this to test if video transfer from Pi to backend works
"""

import asyncio
import httpx
import aiofiles
from pathlib import Path
import time

# Configuration
PI_URL = "http://172.20.10.5:5001"
TEST_DOWNLOAD_DIR = Path("test_downloads")

async def test_video_transfer():
    """Test video transfer from Pi"""
    
    print("🧪 Testing Video Transfer from Pi")
    print("=" * 50)
    
    # Create test directory
    TEST_DOWNLOAD_DIR.mkdir(exist_ok=True)
    
    try:
        # Step 1: Get list of recordings from Pi
        print("\n📋 Step 1: Getting recordings list...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{PI_URL}/api/recordings")
            
        if response.status_code != 200:
            print(f"❌ Failed to get recordings: {response.status_code}")
            return
        
        data = response.json()
        if not data.get('success'):
            print(f"❌ Recordings API failed: {data}")
            return
        
        recordings = data.get('recordings', [])
        if not recordings:
            print("❌ No recordings available on Pi")
            print("💡 Create a test recording first:")
            print("   1. Start live session")
            print("   2. Click 'Start Recording'")
            print("   3. Wait 10 seconds")
            print("   4. Click 'Stop Recording'")
            return
        
        print(f"✅ Found {len(recordings)} recordings")
        for i, rec in enumerate(recordings[:3]):  # Show first 3
            size_mb = rec.get('size', 0) / 1024 / 1024
            print(f"   {i+1}. {rec.get('filename')} - {size_mb:.2f}MB")
        
        # Step 2: Test download the first recording
        test_recording = recordings[0]
        filename = test_recording['filename']
        expected_size = test_recording.get('size', 0)
        
        print(f"\n⬇️ Step 2: Testing download of {filename}...")
        print(f"   Expected size: {expected_size / 1024 / 1024:.2f}MB")
        
        local_path = TEST_DOWNLOAD_DIR / f"test_{filename}"
        download_url = f"{PI_URL}/api/download/{filename}"
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                # Method 1: Try streaming
                print("   Trying streaming download...")
                async with client.stream('GET', download_url) as response:
                    response.raise_for_status()
                    
                    downloaded_size = 0
                    async with aiofiles.open(local_path, 'wb') as f:
                        try:
                            # Try with chunk size (newer httpx)
                            async for chunk in response.aiter_bytes(8192):
                                await f.write(chunk)
                                downloaded_size += len(chunk)
                        except TypeError:
                            # Fallback without chunk size (older httpx)
                            print("   Using compatibility mode...")
                            async for chunk in response.aiter_bytes():
                                await f.write(chunk)
                                downloaded_size += len(chunk)
                
                download_time = time.time() - start_time
                
                # Verify download
                if local_path.exists():
                    actual_size = local_path.stat().st_size
                    speed_mbps = (actual_size / 1024 / 1024) / download_time
                    
                    print(f"✅ Download completed!")
                    print(f"   File: {local_path}")
                    print(f"   Size: {actual_size / 1024 / 1024:.2f}MB")
                    print(f"   Time: {download_time:.2f}s")
                    print(f"   Speed: {speed_mbps:.2f}MB/s")
                    
                    if actual_size == expected_size:
                        print("✅ File size matches expected size")
                    else:
                        print(f"⚠️ Size mismatch: expected {expected_size}, got {actual_size}")
                    
                    # Cleanup
                    local_path.unlink()
                    print("🧹 Test file cleaned up")
                    
                else:
                    print("❌ Downloaded file not found")
                
            except Exception as e:
                print(f"❌ Download failed: {e}")
                
                # Try fallback method
                print("\n🔄 Trying fallback download method...")
                try:
                    response = await client.get(download_url)
                    response.raise_for_status()
                    
                    async with aiofiles.open(local_path, 'wb') as f:
                        await f.write(response.content)
                    
                    if local_path.exists():
                        actual_size = local_path.stat().st_size
                        print(f"✅ Fallback download succeeded: {actual_size / 1024 / 1024:.2f}MB")
                        local_path.unlink()
                        print("🧹 Test file cleaned up")
                    else:
                        print("❌ Fallback download also failed")
                        
                except Exception as fallback_error:
                    print(f"❌ Fallback also failed: {fallback_error}")
        
        print(f"\n🎉 Transfer test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

async def test_pi_connection():
    """Test basic Pi connection"""
    print("🔌 Testing Pi Connection...")
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{PI_URL}/api/status")
            
        if response.status_code == 200:
            data = response.json()
            print("✅ Pi connection successful")
            print(f"   Camera: {data.get('camera_available', False)}")
            print(f"   YOLO: {data.get('yolo_available', False)}")
            print(f"   Running: {data.get('is_running', False)}")
            print(f"   Recording: {data.get('is_recording', False)}")
            return True
        else:
            print(f"❌ Pi connection failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Pi connection error: {e}")
        print(f"   Make sure Pi is running at {PI_URL}")
        return False

async def main():
    """Main test function"""
    print("🎥 Baduanjin Video Transfer Test")
    print("=" * 50)
    
    # Test Pi connection first
    if await test_pi_connection():
        print()
        await test_video_transfer()
    else:
        print("\n❌ Cannot proceed without Pi connection")
        print("\nTroubleshooting:")
        print("1. Check Pi IP address in script")
        print("2. Ensure Pi server is running")
        print("3. Check network connectivity")

if __name__ == "__main__":
    asyncio.run(main())