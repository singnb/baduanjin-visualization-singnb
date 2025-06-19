# ml_pipeline/pose_analyzer.py
# MMPose 1.3.2 compatibility 
# type ignore

import os
import subprocess
import uuid
from pathlib import Path
import time
import traceback
import sys
import datetime
import shutil

def preprocess_video_for_cpu_preserve_duration(input_video_path, output_video_path, target_fps=30, max_resolution=720):
    """
    Preprocess video for faster CPU analysis while preserving duration
    - Keep original frame rate and frame count
    - Only reduce resolution if needed
    """
    try:
        import cv2
        
        cap = cv2.VideoCapture(input_video_path)
        if not cap.isOpened():
            return False
            
        # Get original video properties
        original_fps = int(cap.get(cv2.CAP_PROP_FPS))
        original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"Original video: {original_width}x{original_height} @ {original_fps}fps, {total_frames} frames")
        
        # Calculate new dimensions (maintain aspect ratio) - only reduce resolution
        if original_width > max_resolution:
            scale_factor = max_resolution / original_width
            new_width = max_resolution
            new_height = int(original_height * scale_factor)
        else:
            new_width = original_width
            new_height = original_height
            
        # Keep original frame rate to preserve duration
        output_fps = original_fps
        
        print(f"Output video: {new_width}x{new_height} @ {output_fps}fps (resolution only)")
        
        # Set up video writer with original FPS
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_video_path, fourcc, output_fps, (new_width, new_height))
        
        frame_count = 0
        processed_frames = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Process ALL frames (no skipping to preserve duration)
            # Only resize if needed
            if new_width != original_width or new_height != original_height:
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            out.write(frame)
            processed_frames += 1
            frame_count += 1
            
            # Show progress every 100 frames
            if frame_count % 100 == 0:
                print(f"Preprocessing: {frame_count}/{total_frames} frames")
        
        cap.release()
        out.release()
        
        duration_preserved = processed_frames / output_fps
        print(f"Preprocessing complete: {processed_frames} frames, duration: {duration_preserved:.1f}s")
        return True
        
    except Exception as e:
        print(f"Error in video preprocessing: {e}")
        return False

def preprocess_video_for_cpu(input_video_path, output_video_path, target_fps=15, max_resolution=720):
    """
    Original preprocessing function - modified to be less aggressive
    - Reduce frame rate from 30fps to 15fps (2x speedup instead of 3x)
    - Reduce resolution more conservatively
    """
    try:
        import cv2
        
        cap = cv2.VideoCapture(input_video_path)
        if not cap.isOpened():
            return False
            
        # Get original video properties
        original_fps = int(cap.get(cv2.CAP_PROP_FPS))
        original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"Original video: {original_width}x{original_height} @ {original_fps}fps, {total_frames} frames")
        
        # Calculate new dimensions (maintain aspect ratio)
        if original_width > max_resolution:
            scale_factor = max_resolution / original_width
            new_width = max_resolution
            new_height = int(original_height * scale_factor)
        else:
            new_width = original_width
            new_height = original_height
            
        print(f"Optimized video: {new_width}x{new_height} @ {target_fps}fps")
        
        # Calculate frame skip rate (less aggressive)
        frame_skip = max(1, original_fps // target_fps)
        
        # Set up video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_video_path, fourcc, target_fps, (new_width, new_height))
        
        frame_count = 0
        processed_frames = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Skip frames to reduce FPS (but less aggressively)
            if frame_count % frame_skip == 0:
                # Resize frame
                if new_width != original_width or new_height != original_height:
                    frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
                
                out.write(frame)
                processed_frames += 1
                
            frame_count += 1
        
        cap.release()
        out.release()
        
        expected_duration = processed_frames / target_fps
        print(f"Preprocessing complete: {processed_frames} frames, expected duration: {expected_duration:.1f}s")
        return True
        
    except Exception as e:
        print(f"Error in video preprocessing: {e}")

def setup_cpu_optimizations():
    """
    Set environment variables for optimal CPU performance
    """
    import os
    
    # OpenMP optimizations for CPU
    os.environ['OMP_NUM_THREADS'] = str(os.cpu_count())  # Use all CPU cores
    os.environ['MKL_NUM_THREADS'] = str(os.cpu_count())  # Intel MKL optimization
    os.environ['NUMEXPR_NUM_THREADS'] = str(os.cpu_count())  # NumExpr optimization
    
    # PyTorch CPU optimizations
    os.environ['TORCH_NUM_THREADS'] = str(os.cpu_count())
    
    # Disable GPU memory allocation attempts
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    
    print(f"CPU optimization: Using {os.cpu_count()} CPU threads")
    print("DEBUG: CPU optimization setup complete")

def estimate_processing_time(video_path, target_minutes=10):
    """
    Estimate if video needs to be further optimized for target processing time
    """
    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        cap.release()
        
        # Rough estimation: 
        # - 1 frame takes ~0.5-2 seconds on CPU depending on resolution
        # - Higher resolution = more processing time
        
        complexity_factor = (width * height) / (640 * 480)  # Relative to 640x480
        estimated_seconds_per_frame = 1.0 * complexity_factor  # Base estimate
        
        # After frame skipping (every 3rd frame for 10fps from 30fps)
        effective_frames = total_frames // 3
        estimated_total_seconds = effective_frames * estimated_seconds_per_frame
        estimated_minutes = estimated_total_seconds / 60
        
        print(f"Estimation: {effective_frames} frames, ~{estimated_minutes:.1f} minutes")
        
        # If estimated time > target, suggest further optimizations
        if estimated_minutes > target_minutes:
            # Calculate required additional frame skipping
            required_skip_factor = estimated_minutes / target_minutes
            suggested_fps = max(5, 10 / required_skip_factor)
            
            print(f"WARNING: Estimated time {estimated_minutes:.1f}min > target {target_minutes}min")
            print(f"SUGGESTION: Reduce target FPS to {suggested_fps:.1f} or resolution further")
            
            return False, suggested_fps
        
        return True, 10  # OK with 10 FPS
        
    except Exception as e:
        print(f"Error estimating processing time: {e}")
        return True, 10  # Default to continue
    
def analyze_video(video_path, user_id, video_id):
    """
    Analyze a video with MMPose and return paths to results
    
    Args:
        video_path: Path to the input video
        user_id: User ID for organizing outputs
        video_id: Video ID for file naming
        
    Returns:
        dict: Paths to the output files
    """
    # STEP 1: Setup CPU optimizations
    setup_cpu_optimizations()
    
    # STEP 2: Setup directories and logging FIRST
    print("DEBUG: Setting up directories and logging...")
    
    # Get the root directory (backend)
    root_dir = os.getcwd()
    print(f"DEBUG: Root directory: {root_dir}")
    
    # Create debug log directory FIRST - before any debug_log references
    debug_dir = os.path.join(root_dir, "debug_logs")
    os.makedirs(debug_dir, exist_ok=True)
    debug_log = os.path.join(debug_dir, f"analysis_debug_{video_id}_{int(time.time())}.txt")
    print(f"DEBUG: Debug log created: {debug_log}")
    
    # Make video_path absolute and use forward slashes
    if not os.path.isabs(video_path):
        video_path = os.path.abspath(video_path)
    video_path = video_path.replace('\\', '/')
    print(f"DEBUG: Original video path: {video_path}")
    
    # Create output directories (with forward slashes)
    processed_dir = os.path.join(root_dir, "processed", "videos", str(user_id)).replace('\\', '/')
    outputs_json_dir = os.path.join(root_dir, "outputs_json", str(user_id), str(video_id)).replace('\\', '/')
    
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(outputs_json_dir, exist_ok=True)
    print(f"DEBUG: Output directory created: {outputs_json_dir}")
    
    # STEP 3: Video preprocessing
    print("DEBUG: Checking if preprocessing is needed...")

    original_video_path = video_path

    # Check video properties first
    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps
            cap.release()
            
            print(f"DEBUG: Original video - {width}x{height}, {fps}fps, {total_frames} frames, {duration:.1f}s")
            
            # Only preprocess if video is very large (to reduce processing time)
            needs_preprocessing = width > 1080 or height > 1080  # Only if larger than 1080p
            
            if needs_preprocessing:
                print("DEBUG: Video is large, applying resolution reduction only...")
                preprocessed_video_path = os.path.join(outputs_json_dir, f"preprocessed_{os.path.basename(video_path)}")
                
                # Reduce resolution but keep ALL frames and original FPS
                if preprocess_video_for_cpu_preserve_duration(original_video_path, preprocessed_video_path, 
                                                            target_fps=fps, max_resolution=720):  # Keep original FPS
                    video_path = preprocessed_video_path
                    print(f"DEBUG: Using resolution-reduced video: {video_path}")
                    with open(debug_log, 'a') as f:
                        f.write(f"Using resolution-reduced video: {video_path}\n")
                else:
                    print("DEBUG: Resolution reduction failed, using original video")
                    with open(debug_log, 'a') as f:
                        f.write(f"Resolution reduction failed, using original video\n")
            else:
                print("DEBUG: Video size is acceptable, skipping preprocessing")
                print("DEBUG: Frame reduction will be handled by demo script only")
                with open(debug_log, 'a') as f:
                    f.write(f"Skipping preprocessing - using original video for duration preservation\n")
                    
        else:
            print("DEBUG: Could not read video properties, using original video")
            
    except Exception as e:
        print(f"DEBUG: Error checking video properties: {e}")
        print("DEBUG: Using original video")
    
    # STEP 4: Setup remaining paths and logging
    print("DEBUG: Setting up MMPose paths...")
    
    # Log file setup
    log_file = os.path.join(outputs_json_dir, "analysis_log.txt").replace('\\', '/')
    
    # Set up paths correctly (with forward slashes)
    ml_pipeline_dir = os.path.join(root_dir, "ml_pipeline").replace('\\', '/')
    mmpose_demo_path = os.path.join(ml_pipeline_dir, "demo", "topdown_demo_mmdet_no_heatmap.py").replace('\\', '/')
    det_config_path = os.path.join(ml_pipeline_dir, "demo", "faster_rcnn_r50_fpn_coco.py").replace('\\', '/')
    
    print(f"DEBUG: MMPose demo path: {mmpose_demo_path}")
    print(f"DEBUG: Detection config path: {det_config_path}")
    
    # Check file existence
    with open(debug_log, 'a') as f:
        f.write(f"ML Pipeline directory: {ml_pipeline_dir}\n")
        f.write(f"MMPose demo path: {mmpose_demo_path}\n")
        f.write("\nFile existence checks:\n")
        f.write(f"- MMPose demo exists: {os.path.exists(mmpose_demo_path)}\n")
        f.write(f"- Detection config exists: {os.path.exists(det_config_path)}\n")
        f.write(f"- Video file exists: {os.path.exists(video_path)}\n")
        
        # Check CPU setup
        try:
            import torch
            f.write(f"\nPyTorch version: {torch.__version__}\n")
            f.write(f"CUDA available: {torch.cuda.is_available()}\n")
            f.write(f"Using device: CPU (forced)\n")
            if torch.cuda.is_available():
                f.write(f"CUDA device available but not used: {torch.cuda.get_device_name(0)}\n")
        except Exception as e:
            f.write(f"Error checking device: {str(e)}\n")
    
    # STEP 5: Prepare MMPose command
    print("DEBUG: Preparing MMPose command...")
    
    # Get Python executable
    python_executable = sys.executable.replace('\\', '/')
    
    # Get input video filename (base name without path)
    input_filename = os.path.basename(video_path)

    print("DEBUG: Preparing MMPose command (simplified approach)...")
    
    try:
        # Construct the MMPose 1.3.2 command format
        mmpose_cmd = [
            python_executable,
            mmpose_demo_path,
            det_config_path,
            "https://download.openmmlab.com/mmdetection/v2.0/faster_rcnn/faster_rcnn_r50_fpn_1x_coco/faster_rcnn_r50_fpn_1x_coco_20200130-047c8118.pth",
            "--pose-model", "human",  
            "--input", video_path,
            "--output-root", outputs_json_dir,
            "--device", "cpu",
            "--bbox-thr", "0.8",
            "--kpt-thr", "0.2", 
            "--nms-thr", "0.8",
            "--save-predictions"
        ]
        
        print("DEBUG: Command constructed successfully")
        print(f"DEBUG: Command has {len(mmpose_cmd)} arguments")
        
        # Log the command
        with open(log_file, 'w') as f:
            f.write(f"Command: {' '.join(mmpose_cmd)}\n")
        
        print("DEBUG: Moving to subprocess execution...")
        
        # STEP 6: Execute MMPose command (Windows-compatible)
        print("DEBUG: About to execute MMPose subprocess...")
        print("DEBUG: This may take several minutes for CPU processing...")

        try:
            print("DEBUG: Creating subprocess...")
            
            # Create subprocess with proper Windows environment
            process = subprocess.Popen(
                mmpose_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=root_dir,
                env=dict(os.environ, PYTHONIOENCODING='utf-8'),  # Fix encoding issues
                shell=False  # Don't use shell for security
            )
            
            print(f"DEBUG: Process started with PID: {process.pid}")
            
            # Simple initial check (Windows-compatible)
            print("DEBUG: Checking if process started correctly...")
            time.sleep(5)  # Give process 5 seconds to start
            
            poll_result = process.poll()
            if poll_result is not None:
                print(f"DEBUG: Process ended immediately with return code: {poll_result}")
                # Get any immediate output
                try:
                    stdout, stderr = process.communicate(timeout=10)
                    print(f"DEBUG: Immediate STDOUT: {stdout[:500]}...")
                    print(f"DEBUG: Immediate STDERR: {stderr[:500]}...")
                except:
                    print("DEBUG: Could not read immediate output")
                return None
            else:
                print("DEBUG: Process is running normally")
            
            # Wait for completion with progress updates
            print("DEBUG: Waiting for process completion...")
            print("DEBUG: (This is normal for CPU processing - may take 10-30 minutes)")
            
            start_time = time.time()
            last_update = start_time
            
            while True:
                # Check if process is still running
                poll_result = process.poll()
                
                # ADDED: Check if output files exist as completion indicator
                expected_json = os.path.join(outputs_json_dir, f"results_{os.path.splitext(input_filename)[0]}.json")
                json_exists = os.path.exists(expected_json)
                
                # print(f"DEBUG: Poll result: {poll_result}, JSON exists: {json_exists}")
                
                if poll_result is not None:
                    print(f"DEBUG: Process completed with return code: {poll_result}")
                    break
                
                # ADDED: Alternative completion check - if JSON exists and process seems stuck
                if json_exists:
                    print("DEBUG: Output files detected, checking if process is truly alive...")
                    try:
                        # Try to communicate with a short timeout
                        stdout, stderr = process.communicate(timeout=5)
                        print("DEBUG: Process completed (detected via timeout)")
                        break
                    except subprocess.TimeoutExpired:
                        # Process is still running, continue waiting
                        pass
                
                # Show progress every 2 minutes
                current_time = time.time()
                if current_time - last_update >= 120:  # 2 minutes
                    elapsed_minutes = (current_time - start_time) / 60
                    print(f"DEBUG: Still processing... {elapsed_minutes:.1f} minutes elapsed")
                    print(f"DEBUG: Output JSON exists: {json_exists}")
                    last_update = current_time
                
                # Check for timeout (30 minutes)
                if current_time - start_time > 1800:
                    print("DEBUG: Process timeout after 30 minutes")
                    process.kill()
                    return None
                
                time.sleep(10)  # Check every 10 seconds
            
            # Get final output
            try:
                print("DEBUG: Reading final output...")
                stdout, stderr = process.communicate(timeout=30)  # Short timeout since process is done
                return_code = process.returncode
            except subprocess.TimeoutExpired:
                print("DEBUG: Timeout reading final output")
                process.kill()
                stdout, stderr = process.communicate()
                return_code = -1
            
            print(f"DEBUG: Final return code: {return_code}")
            
            # Log output to files
            try:
                with open(debug_log, 'a') as f:
                    f.write("\n===== MMPOSE EXECUTION COMPLETE =====\n")
                    f.write(f"Return code: {return_code}\n")
                    f.write(f"Execution time: {(time.time() - start_time)/60:.1f} minutes\n")
                    f.write("\n===== STDOUT FROM MMPOSE =====\n")
                    f.write(stdout if stdout else "No stdout output")
                    f.write("\n===== STDERR FROM MMPOSE =====\n")
                    f.write(stderr if stderr else "No stderr output")
                    f.write("\n" + "="*50 + "\n")
                print("DEBUG: Output logged to debug file")
            except Exception as log_error:
                print(f"DEBUG: Error writing to debug log: {log_error}")
            
            # Check if successful
            if return_code != 0:
                print(f"DEBUG: MMPose failed with return code {return_code}")
                if stderr:
                    print(f"DEBUG: Error summary: {stderr[:200]}...")
                
                try:
                    with open(log_file, 'a') as f:
                        f.write(f"Error: Command failed with return code {return_code}\n")
                        f.write(f"Error message: {stderr[:1000] if stderr else 'No error message'}\n")
                except:
                    pass
                
                return None
            
            print("DEBUG: MMPose completed successfully!")
            print("DEBUG: Checking output files...")
            
        except Exception as subprocess_error:
            print(f"DEBUG: Exception during subprocess execution: {subprocess_error}")
            import traceback
            traceback.print_exc()
            return None
        
        # Check for results file with proper naming
        video_basename = os.path.splitext(input_filename)[0]
        results_json_filename = f"results_{video_basename}.json"
        results_json_path = os.path.join(outputs_json_dir, results_json_filename).replace('\\', '/')
        
        # Log results file check
        with open(debug_log, 'a') as f:
            f.write(f"\nChecking for results JSON: {results_json_path}\n")
            f.write(f"Results JSON exists: {os.path.exists(results_json_path)}\n")
            f.write("Files in outputs_json_dir:\n")
            if os.path.exists(outputs_json_dir):
                for file in os.listdir(outputs_json_dir):
                    f.write(f"- {file}\n")
        
        if not os.path.exists(results_json_path):
            print(f"DEBUG: Results JSON not found: {results_json_path}")
            with open(log_file, 'a') as f:
                f.write(f"Error: Results JSON file not found: {results_json_path}\n")
            return None
        
        print("DEBUG: Results JSON found, processing output files...")
        
        # Find MP4 files in output directory
        mp4_files = []
        if os.path.exists(outputs_json_dir):
            for file in os.listdir(outputs_json_dir):
                if file.lower().endswith('.mp4'):
                    mp4_files.append(file)
        
        with open(debug_log, 'a') as f:
            f.write(f"Found MP4 files: {mp4_files}\n")
        
        analyzed_video_path = None
        web_video_path = None
        
        if mp4_files:
            # Use the first MP4 file found
            original_output = os.path.join(outputs_json_dir, mp4_files[0])
            analyzed_video_path = original_output
            
            # Create web-compatible version
            output_basename = os.path.splitext(mp4_files[0])[0]
            web_video_filename = f"{output_basename}_web.mp4"
            web_video_path = os.path.join(outputs_json_dir, web_video_filename)
            
            # Enhanced FFmpeg conversion for web compatibility
            success = convert_to_web_format(original_output, web_video_path, debug_log, log_file)
            
            if success:
                with open(log_file, 'a') as f:
                    f.write(f"Web-compatible video created: {web_video_path}\n")
            else:
                with open(log_file, 'a') as f:
                    f.write(f"Web conversion failed, using original: {original_output}\n")
                web_video_path = original_output
        else:
            # No MP4 files found, this shouldn't happen but handle gracefully
            analyzed_video_path = video_path
            web_video_path = video_path
            with open(log_file, 'a') as f:
                f.write(f"No MP4 files found in output directory. Using original video.\n")

        # Analysis complete message
        with open(log_file, 'a') as f:
            f.write(f"Analysis completed successfully at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Results JSON: {results_json_path}\n")
            f.write(f"Analyzed video: {analyzed_video_path}\n")
            f.write(f"Web video: {web_video_path}\n")

        print("DEBUG: Creating return paths...")
        
        # Create relative paths for frontend
        video_filename = os.path.basename(original_video_path)  # Use original filename
        json_filename = os.path.basename(results_json_path)
        
        relative_json_path = f"outputs_json/{user_id}/{video_id}/{json_filename}"
        
        # For analyzed video path
        if analyzed_video_path and analyzed_video_path.startswith(outputs_json_dir):
            analyzed_filename = os.path.basename(analyzed_video_path)
            relative_analyzed_path = f"outputs_json/{user_id}/{video_id}/{analyzed_filename}"
        else:
            relative_analyzed_path = f"uploads/videos/{user_id}/{video_filename}"
        
        result = {
            "results_json": relative_json_path,
            "original_video": f"uploads/videos/{user_id}/{video_filename}",
            "analyzed_video_path": relative_analyzed_path,
            "keypoints_path": relative_json_path
        }
        
        print(f"DEBUG: Analysis complete! Returning: {result}")
        return result
    
    except Exception as e:
        # Catch any exceptions
        print(f"DEBUG: Exception occurred: {str(e)}")
        with open(debug_log, 'a') as f:
            f.write(f"Exception: {str(e)}\n")
            f.write(traceback.format_exc())
        with open(log_file, 'a') as f:
            f.write(f"Error: {str(e)}\n")
        return None

def convert_to_web_format(input_path, output_path, debug_log, log_file):
    """
    Convert video to web-compatible format using FFmpeg
    """
    try:
        with open(debug_log, 'a') as f:
            f.write(f"\nAttempting FFmpeg conversion for web compatibility\n")
            f.write(f"Input file: {input_path}\n")
            f.write(f"Output file: {output_path}\n")
        
        # Check if FFmpeg is available
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            with open(debug_log, 'a') as f:
                f.write("FFmpeg not found in PATH\n")
            return False
        
        # Enhanced FFmpeg command for better web compatibility
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", input_path,
            "-c:v", "libx264",           # H.264 video codec
            "-preset", "medium",         # Encoding speed/compression tradeoff
            "-profile:v", "main",        # H.264 profile for broad compatibility
            "-level", "4.0",            # H.264 level
            "-pix_fmt", "yuv420p",      # Pixel format for compatibility
            "-crf", "23",               # Constant rate factor (quality)
            "-maxrate", "2M",           # Maximum bitrate
            "-bufsize", "4M",           # Buffer size
            "-r", "30",                 # Frame rate
            "-movflags", "+faststart",   # Optimize for web streaming
            "-avoid_negative_ts", "make_zero",  # Fix timestamp issues
            "-y",                       # Overwrite output file
            output_path
        ]
        
        with open(log_file, 'a') as f:
            f.write(f"Running FFmpeg conversion:\n")
            f.write(f"Command: {' '.join(ffmpeg_cmd)}\n")
        
        with open(debug_log, 'a') as f:
            f.write(f"\nFFmpeg command:\n{' '.join(ffmpeg_cmd)}\n")
        
        # Run FFmpeg with timeout
        ffmpeg_process = subprocess.run(
            ffmpeg_cmd, 
            capture_output=True, 
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Log FFmpeg output
        with open(debug_log, 'a') as f:
            f.write(f"\nFFmpeg STDOUT:\n{ffmpeg_process.stdout}\n")
            f.write(f"FFmpeg STDERR:\n{ffmpeg_process.stderr}\n")
            f.write(f"FFmpeg return code: {ffmpeg_process.returncode}\n")
        
        # Check if conversion was successful
        if ffmpeg_process.returncode == 0 and os.path.exists(output_path):
            # Verify the output file is valid
            file_size = os.path.getsize(output_path)
            if file_size > 1000:  # File should be larger than 1KB
                with open(log_file, 'a') as f:
                    f.write(f"FFmpeg conversion successful. Output size: {file_size} bytes\n")
                return True
            else:
                with open(debug_log, 'a') as f:
                    f.write(f"FFmpeg output file too small: {file_size} bytes\n")
                return False
        else:
            with open(log_file, 'a') as f:
                f.write(f"FFmpeg conversion failed. Return code: {ffmpeg_process.returncode}\n")
                f.write(f"FFmpeg error: {ffmpeg_process.stderr}\n")
            return False
            
    except subprocess.TimeoutExpired:
        with open(debug_log, 'a') as f:
            f.write("FFmpeg conversion timed out\n")
        return False
    except Exception as e:
        with open(debug_log, 'a') as f:
            f.write(f"Exception during FFmpeg conversion: {str(e)}\n")
            f.write(traceback.format_exc())
        return False
    
def upload_all_analysis_results_to_azure(user_id, video_id, local_outputs_dir, local_analysis_dir=None):
    """
    Upload all analysis results to Azure following your exact structure
    """
    try:
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not connection_string:
            print("WARNING: Azure storage not configured, keeping local files")
            return None
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        uploaded_files = {}
        
        # Phase 1: Upload video outputs to videos container
        video_files_to_upload = []
        
        # Find all MP4 files in outputs directory
        if os.path.exists(local_outputs_dir):
            for file in os.listdir(local_outputs_dir):
                if file.endswith('.mp4'):
                    video_files_to_upload.append(file)
        
        print(f"Found video files to upload: {video_files_to_upload}")
        
        for filename in video_files_to_upload:
            local_file_path = os.path.join(local_outputs_dir, filename)
            
            if os.path.exists(local_file_path):
                try:
                    # Upload to videos container with nested path
                    blob_path = f"outputs_json/{user_id}/{video_id}/{filename}"
                    
                    with open(local_file_path, 'rb') as file:
                        file_content = file.read()
                    
                    blob_client = blob_service_client.get_blob_client(
                        container="videos",
                        blob=blob_path
                    )
                    
                    blob_client.upload_blob(
                        file_content,
                        overwrite=True,
                        content_type="video/mp4",
                        metadata={
                            "user_id": str(user_id),
                            "video_id": str(video_id),
                            "file_type": "analyzed_video",
                            "original_filename": filename
                        }
                    )
                    
                    azure_url = blob_client.url
                    uploaded_files[f"video_{filename}"] = azure_url
                    print(f"Uploaded {filename} to Azure videos: {azure_url}")
                    
                except Exception as e:
                    print(f"Error uploading video {filename} to Azure: {e}")
                    continue
        
        # Phase 2: Upload JSON results to results container
        json_files_to_upload = []
        
        # Find results JSON files
        if os.path.exists(local_outputs_dir):
            for file in os.listdir(local_outputs_dir):
                if file.startswith('results_') and file.endswith('.json'):
                    json_files_to_upload.append(file)
        
        print(f"Found JSON result files to upload: {json_files_to_upload}")
        
        for filename in json_files_to_upload:
            local_file_path = os.path.join(local_outputs_dir, filename)
            
            if os.path.exists(local_file_path):
                try:
                    # Upload to results container with nested path
                    blob_path = f"outputs_json/{user_id}/{video_id}/{filename}"
                    
                    with open(local_file_path, 'rb') as file:
                        file_content = file.read()
                    
                    blob_client = blob_service_client.get_blob_client(
                        container="results",
                        blob=blob_path
                    )
                    
                    blob_client.upload_blob(
                        file_content,
                        overwrite=True,
                        content_type="application/json",
                        metadata={
                            "user_id": str(user_id),
                            "video_id": str(video_id),
                            "file_type": "pose_results",
                            "original_filename": filename
                        }
                    )
                    
                    azure_url = blob_client.url
                    uploaded_files[f"json_{filename}"] = azure_url
                    print(f"Uploaded {filename} to Azure results: {azure_url}")
                    
                except Exception as e:
                    print(f"Error uploading JSON {filename} to Azure: {e}")
                    continue
        
        # Phase 3: Upload baduanjin_analysis files to results container
        if local_analysis_dir and os.path.exists(local_analysis_dir):
            analysis_files = [
                "analysis_report.txt",
                "balance_metrics.png",
                "com_trajectory.png", 
                "joint_angles.png",
                "key_poses.png",
                "learner_balance.json",
                "learner_joint_angles.json",
                "learner_recommendations.json",
                "learner_smoothness.json",
                "learner_symmetry.json",
                "movement_smoothness.png",
                "movement_symmetry.png"
            ]
            
            print(f"Uploading baduanjin_analysis files from: {local_analysis_dir}")
            
            for filename in analysis_files:
                local_file_path = os.path.join(local_analysis_dir, filename)
                
                if os.path.exists(local_file_path):
                    try:
                        # Upload to results container under baduanjin_analysis path
                        blob_path = f"baduanjin_analysis/{user_id}/{video_id}/{filename}"
                        
                        with open(local_file_path, 'rb') as file:
                            file_content = file.read()
                        
                        # Determine content type
                        if filename.endswith('.png'):
                            content_type = "image/png"
                        elif filename.endswith('.json'):
                            content_type = "application/json"
                        elif filename.endswith('.txt'):
                            content_type = "text/plain"
                        else:
                            content_type = "application/octet-stream"
                        
                        blob_client = blob_service_client.get_blob_client(
                            container="results",
                            blob=blob_path
                        )
                        
                        blob_client.upload_blob(
                            file_content,
                            overwrite=True,
                            content_type=content_type,
                            metadata={
                                "user_id": str(user_id),
                                "video_id": str(video_id),
                                "file_type": "analysis_detail",
                                "original_filename": filename
                            }
                        )
                        
                        azure_url = blob_client.url
                        uploaded_files[f"analysis_{filename}"] = azure_url
                        print(f"Uploaded analysis {filename} to Azure: {azure_url}")
                        
                    except Exception as e:
                        print(f"Error uploading analysis file {filename}: {e}")
                        continue
                else:
                    print(f"Analysis file not found: {local_file_path}")
        
        print(f"Azure upload completed: {len(uploaded_files)} files uploaded")
        return uploaded_files
        
    except Exception as e:
        print(f"Error in comprehensive Azure upload: {e}")
        import traceback
        traceback.print_exc()
        return None