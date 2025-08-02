import subprocess
import os
import tempfile
from pathlib import Path

def convert_video_for_web(input_path, output_path, target_fps=30, method="blend"):
    """
    Convert 15fps video to 30fps locally on Pi
    """
    try:
        print(f"🔄 Converting {input_path} from 15fps to {target_fps}fps")
        
        # Ensure output directory exists
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build FFmpeg command for Pi (optimized for ARM processor)
        cmd = [
            'ffmpeg', '-i', str(input_path),
            '-c:v', 'libx264',              # H.264 video codec
            '-profile:v', 'baseline',        # Baseline profile for maximum compatibility
            '-level', '3.0',                # Level 3.0 for wide device support
            '-pix_fmt', 'yuv420p',          # Pixel format compatible with all browsers
            '-c:a', 'aac',                  # AAC audio codec
            '-b:a', '128k',                 # Audio bitrate
            '-movflags', '+faststart',       # Move metadata to beginning for web streaming
            '-preset', 'ultrafast',         # Fast encoding for Pi
            '-crf', '28',                   # Higher CRF for smaller file/faster encoding on Pi
        ]
        
        # Add frame rate conversion based on method
        if method == "duplicate":
            # Simple frame duplication (fastest for Pi)
            cmd.extend(['-r', str(target_fps)])
            print(f"📹 Using frame duplication: 15fps → {target_fps}fps")
        elif method == "blend":
            # Frame blending (balanced quality/speed)
            fps_filter = f"fps={target_fps}"
            cmd.extend(['-vf', fps_filter])
            print(f"📹 Using frame blending: 15fps → {target_fps}fps")
        else:
            # Default to simple fps conversion
            cmd.extend(['-r', str(target_fps)])
            print(f"📹 Using default fps conversion: 15fps → {target_fps}fps")
        
        # Add output path and overwrite flag
        cmd.extend(['-y', str(output_path)])
        
        print(f"🔄 Running FFmpeg: {' '.join(cmd)}")
        
        # Execute conversion with timeout
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            # Check if output file was created and has reasonable size
            if Path(output_path).exists():
                output_size = Path(output_path).stat().st_size
                input_size = Path(input_path).stat().st_size
                
                print(f"✅ Conversion successful!")
                print(f"   Input:  {input_size / 1024:.1f} KB")
                print(f"   Output: {output_size / 1024:.1f} KB")
                
                return {
                    "success": True,
                    "output_path": str(output_path),
                    "input_size": input_size,
                    "output_size": output_size,
                    "compression_ratio": round(output_size / input_size, 2) if input_size > 0 else 1
                }
            else:
                raise Exception("Output file was not created")
                
        else:
            error_msg = result.stderr or "Unknown FFmpeg error"
            print(f"❌ FFmpeg conversion failed: {error_msg}")
            raise Exception(f"FFmpeg failed: {error_msg}")
            
    except subprocess.TimeoutExpired:
        raise Exception("Conversion timeout - file too large or Pi too slow")
    except FileNotFoundError:
        raise Exception("FFmpeg not found - install with: sudo apt install ffmpeg")
    except Exception as e:
        print(f"❌ Conversion error: {str(e)}")
        raise Exception(f"Conversion failed: {str(e)}")

def check_ffmpeg_available():
    """Check if FFmpeg is available on Pi"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except:
        return False