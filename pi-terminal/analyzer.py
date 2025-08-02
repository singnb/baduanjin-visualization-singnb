"""
analyzer.py - Pose Analysis and Video Recording Module
"""

from pathlib import Path
import cv2
import numpy as np
import time
import threading
import base64
from datetime import datetime
from config import Config

# Import with error handling
try:
    from picamera2 import Picamera2
    from ultralytics import YOLO
    from video_converter import convert_video_for_web
    CAMERA_AVAILABLE = True
    YOLO_AVAILABLE = True
    CONVERSION_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    CAMERA_AVAILABLE = False
    YOLO_AVAILABLE = False
    CONVERSION_AVAILABLE = False
    print("⚠️ video_converter not available - auto-conversion disabled")

class BaduanjinWebAnalyzer:
    def __init__(self):
        self.analyzer = None
        
        # Session State (tracks what Azure pi-service thinks is happening)
        self.is_running = False  # Streaming state for Azure pi-service
        self.current_session = None
        self.session_start_time = None
        
        # Recording State (ENHANCED - dual video recording)
        self.is_recording = False
        self.current_recording = None
        self.video_writer_original = None      # NEW: Original video writer
        self.video_writer_annotated = None     # NEW: Annotated video writer
        self.recording_start_time = None
        self.recordings_dir = Config.RECORDINGS_DIR
        
        # Frame and Data State
        self.current_frame = None
        self.pose_data = []
        self.session_stats = {
            'total_frames': 0,
            'persons_detected': 0,
            'session_start': None,
            'current_fps': 0
        }
        
        # Initialize directories
        Config.init_directories()
        
        if CAMERA_AVAILABLE:
            self.setup_analyzer()

    
    def setup_analyzer(self):
        """Initialize the pose analyzer - FIXED MODEL PATH"""
        try:
            # Initialize camera
            self.picam2 = Picamera2()
            config = self.picam2.create_preview_configuration(
                main={"format": 'XRGB8888', "size": (Config.CAMERA_WIDTH, Config.CAMERA_HEIGHT)}
            )
            self.picam2.configure(config)
            
            # Initialize YOLO with models folder path
            if YOLO_AVAILABLE:
                model_path = Config.YOLO_MODEL_PATH
                if not model_path.exists():
                    # Fallback to root directory
                    model_path = Path("yolov8n-pose.pt")
                    if not model_path.exists():
                        print(f"❌ YOLO model not found in models/ or root directory")
                        self.model = None
                        return
                
                print(f"📦 Loading YOLO model from: {model_path}")
                self.model = YOLO(str(model_path))
                print(f"✅ YOLO model loaded successfully")
            else:
                self.model = None
                
            print("✅ Analyzer setup complete")
            
        except Exception as e:
            print(f"❌ Analyzer setup failed: {e}")
            self.analyzer = None
    
    def apply_symmetry_correction(self, keypoints, confidences):
        """Apply symmetry correction"""
        if len(keypoints) == 0:
            return keypoints, confidences
            
        left_shoulder_idx = 5
        right_shoulder_idx = 6
        
        if confidences[left_shoulder_idx] > 0.5 and confidences[right_shoulder_idx] > 0.5:
            x_sym = (keypoints[left_shoulder_idx, 0] + keypoints[right_shoulder_idx, 0]) / 2
            
            symmetric_pairs = [(9, 10), (7, 8), (13, 14), (15, 16)]
            corrected_kpts = keypoints.copy()
            
            for left_idx, right_idx in symmetric_pairs:
                c_l, c_r = confidences[left_idx], confidences[right_idx]
                p_l, p_r = keypoints[left_idx], keypoints[right_idx]
                
                if c_l > 0.5 and c_r < 0.5:
                    p_r_sym = np.array([2 * x_sym - p_l[0], p_l[1]])
                    alpha = c_r / (c_l + c_r) if c_l + c_r > 0 else 0
                    corrected_kpts[right_idx] = alpha * p_r + (1 - alpha) * p_r_sym
                elif c_r > 0.5 and c_l < 0.5:
                    p_l_sym = np.array([2 * x_sym - p_r[0], p_r[1]])
                    alpha = c_l / (c_r + c_l) if c_r + c_l > 0 else 0
                    corrected_kpts[left_idx] = alpha * p_l + (1 - alpha) * p_l_sym
            
            return corrected_kpts, confidences
        return keypoints, confidences
    
    def draw_pose(self, frame, keypoints, confidences):
        """Draw pose with skeleton"""
        skeleton_connections = [
            (0, 1), (0, 2), (1, 3), (2, 4),  # Head
            (5, 6), (5, 11), (6, 12), (11, 12),  # Torso
            (5, 7), (7, 9), (6, 8), (8, 10),  # Arms
            (11, 13), (13, 15), (12, 14), (14, 16)  # Legs
        ]
        
        # Draw keypoints
        for i, (x, y) in enumerate(keypoints):
            if confidences[i] > 0.5:
                if i in [0, 1, 2, 3, 4]:  # Head
                    color = (255, 255, 0)
                elif i in [5, 6, 7, 8, 9, 10]:  # Upper body
                    color = (0, 255, 0)
                else:  # Lower body
                    color = (255, 0, 0)
                    
                cv2.circle(frame, (int(x), int(y)), 6, color, -1)
                cv2.putText(frame, str(i), (int(x)+8, int(y)), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
        
        # Draw skeleton
        for connection in skeleton_connections:
            pt1_idx, pt2_idx = connection
            if confidences[pt1_idx] > 0.5 and confidences[pt2_idx] > 0.5:
                pt1 = keypoints[pt1_idx]
                pt2 = keypoints[pt2_idx]
                if pt1[0] > 0 and pt1[1] > 0 and pt2[0] > 0 and pt2[1] > 0:
                    cv2.line(frame, (int(pt1[0]), int(pt1[1])), 
                           (int(pt2[0]), int(pt2[1])), (0, 0, 255), 3)
        
        return frame
    
    def process_frame(self, frame):
        """Process frame for pose detection"""
        if not self.model:
            return []
            
        try:
            results = self.model(frame, conf=Config.YOLO_CONFIDENCE, verbose=False, device='cpu')
            processed_data = []
            
            for result in results:
                if result.keypoints is not None:
                    keypoints = result.keypoints.xy.cpu().numpy()
                    confidences = result.keypoints.conf.cpu().numpy()
                    
                    for person_idx in range(keypoints.shape[0]):
                        person_kpts = keypoints[person_idx]
                        person_confs = confidences[person_idx]
                        
                        corrected_kpts, corrected_confs = self.apply_symmetry_correction(
                            person_kpts, person_confs
                        )
                        processed_data.append({
                            'keypoints': corrected_kpts.tolist(),
                            'confidences': corrected_confs.tolist(),
                            'person_id': person_idx
                        })
            
            return processed_data
        except Exception as e:
            print(f"❌ Processing error: {e}")
            return []
    
    # Recording management
    def start_recording(self):
        """🔧 FIXED: Start dual video recording with better error handling"""
        try:
            print(f"🔴 FIXED: start_recording() called")
            print(f"🔴 DEBUG: is_running = {self.is_running}")
            print(f"🔴 DEBUG: is_recording = {self.is_recording}")
            print(f"🔴 DEBUG: picam2 exists = {hasattr(self, 'picam2') and self.picam2 is not None}")
            
            if not self.is_running:
                print("❌ FIXED: Cannot start recording - no active session")
                return {
                    "success": False,
                    "message": "Cannot start recording - no active session. Start streaming first."
                }
            
            # 🔧 FIXED: Check if camera is available
            if not hasattr(self, 'picam2') or self.picam2 is None:
                print("❌ FIXED: picam2 is None - camera not initialized!")
                return {
                    "success": False,
                    "message": "Camera not available for recording"
                }
            
            if self.is_recording:
                print("⚠️ FIXED: Recording already active")
                return {
                    "success": True,
                    "message": "Recording already active",
                    "was_already_recording": True
                }
            
            # 🔧 FIXED: Generate recording filenames with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_filename = f"baduanjin_original_{timestamp}.mp4"
            annotated_filename = f"baduanjin_annotated_{timestamp}.mp4"
            
            original_filepath = self.recordings_dir / original_filename
            annotated_filepath = self.recordings_dir / annotated_filename
            
            print(f"🎬 FIXED: Creating video files:")
            print(f"   📹 Original: {original_filepath}")
            print(f"   🤖 Annotated: {annotated_filepath}")
            
            # 🔧 FIXED: Try different codecs if mp4v fails
            codecs_to_try = ['mp4v', 'XVID', 'MJPG']
            successful_codec = None
            
            for codec in codecs_to_try:
                try:
                    print(f"🔧 FIXED: Trying codec: {codec}")
                    fourcc = cv2.VideoWriter_fourcc(*codec)
                    
                    # Test with original video writer first
                    test_writer = cv2.VideoWriter(
                        str(original_filepath), fourcc, Config.VIDEO_FPS, 
                        (Config.CAMERA_WIDTH, Config.CAMERA_HEIGHT)
                    )
                    
                    if test_writer.isOpened():
                        print(f"✅ FIXED: Codec {codec} works!")
                        test_writer.release()  # Release test writer
                        successful_codec = codec
                        break
                    else:
                        print(f"❌ FIXED: Codec {codec} failed")
                        test_writer.release()
                        
                except Exception as codec_error:
                    print(f"❌ FIXED: Codec {codec} exception: {codec_error}")
                    continue
            
            if not successful_codec:
                print("❌ FIXED: No working codec found")
                return {
                    "success": False,
                    "message": "No compatible video codec available. Install ffmpeg or try different format."
                }
            
            # 🔧 FIXED: Initialize video writers with working codec
            print(f"🎬 FIXED: Initializing video writers with codec: {successful_codec}")
            fourcc = cv2.VideoWriter_fourcc(*successful_codec)
            
            # Initialize both video writers
            self.video_writer_original = cv2.VideoWriter(
                str(original_filepath), fourcc, Config.VIDEO_FPS, 
                (Config.CAMERA_WIDTH, Config.CAMERA_HEIGHT)
            )
            
            self.video_writer_annotated = cv2.VideoWriter(
                str(annotated_filepath), fourcc, Config.VIDEO_FPS, 
                (Config.CAMERA_WIDTH, Config.CAMERA_HEIGHT)
            )
            
            # 🔧 FIXED: Verify both writers opened successfully
            if not self.video_writer_original.isOpened():
                print("❌ FIXED: Failed to open original video writer")
                if self.video_writer_annotated:
                    self.video_writer_annotated.release()
                return {
                    "success": False,
                    "message": f"Failed to initialize original video writer with codec {successful_codec}"
                }
            
            if not self.video_writer_annotated.isOpened():
                print("❌ FIXED: Failed to open annotated video writer")
                self.video_writer_original.release()
                return {
                    "success": False,
                    "message": f"Failed to initialize annotated video writer with codec {successful_codec}"
                }
            
            # 🔧 FIXED: Set recording state only after successful initialization
            self.is_recording = True
            self.recording_start_time = datetime.now()
            self.current_recording = {
                "files": {
                    "original": {
                        "filename": original_filename,
                        "filepath": str(original_filepath),
                        "description": "Clean original video without pose overlay"
                    },
                    "annotated": {
                        "filename": annotated_filename,
                        "filepath": str(annotated_filepath),
                        "description": "Video with pose estimation overlay"
                    }
                },
                "start_time": self.recording_start_time.isoformat(),
                "codec_used": successful_codec
            }
            
            print(f"🔴 ✅ FIXED: Dual recording started successfully!")
            print(f"   📹 Original: {original_filename}")
            print(f"   🤖 Annotated: {annotated_filename}")
            print(f"   🎬 Codec: {successful_codec}")
            
            return {
                "success": True,
                "message": "Dual video recording started successfully",
                "recording_info": {
                    "original_filename": original_filename,
                    "annotated_filename": annotated_filename,
                    "start_time": self.recording_start_time.isoformat(),
                    "recording_type": "dual_video",
                    "codec_used": successful_codec
                }
            }
            
        except Exception as e:
            print(f"❌ FIXED: Error starting dual recording: {e}")
            import traceback
            traceback.print_exc()
            
            # 🔧 FIXED: Clean up any partially created writers
            if hasattr(self, 'video_writer_original') and self.video_writer_original:
                try:
                    self.video_writer_original.release()
                except:
                    pass
                self.video_writer_original = None
                
            if hasattr(self, 'video_writer_annotated') and self.video_writer_annotated:
                try:
                    self.video_writer_annotated.release()
                except:
                    pass
                self.video_writer_annotated = None
            
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to start dual recording"
            }
    
    def stop_recording(self):
        """Stop dual video recording + AUTO-CONVERT BOTH videos for web"""
        try:
            if not self.is_recording:
                return {
                    "success": False,
                    "message": "No active recording to stop"
                }
            
            recording_info = {}
            if self.current_recording:
                recording_info = self.current_recording.copy()
            
            recording_duration = 0
            
            # Calculate recording duration
            if self.recording_start_time:
                recording_duration = (datetime.now() - self.recording_start_time).total_seconds()
            
            # Close both video writers
            files_created = []
            
            if self.video_writer_original:
                self.video_writer_original.release()
                self.video_writer_original = None
                files_created.append("original")
            
            if self.video_writer_annotated:
                self.video_writer_annotated.release()
                self.video_writer_annotated = None
                files_created.append("annotated")
            
            # Update recording info
            recording_info.update({
                "end_time": datetime.now().isoformat(),
                "duration_seconds": round(recording_duration, 2),
                "status": "completed",
                "files_created": files_created
            })
            
            # Clear recording state
            self.is_recording = False
            self.recording_start_time = None
            
            # Verify files were created and get sizes
            files_status = {}
            total_size = 0
            original_file_path = None
            annotated_file_path = None  # NEW: Store annotated file path too
            
            if self.current_recording and "files" in self.current_recording:
                for file_type, file_info in self.current_recording["files"].items():
                    filepath = Path(file_info["filepath"])
                    if filepath.exists():
                        file_size = filepath.stat().st_size
                        files_status[file_type] = {
                            "filename": file_info["filename"],
                            "size": file_size,
                            "size_mb": round(file_size / 1024 / 1024, 2),
                            "exists": True,
                            "description": file_info["description"]
                        }
                        total_size += file_size
                        
                        # Store both file paths for conversion
                        if file_type == "original":
                            original_file_path = filepath
                        elif file_type == "annotated":  # NEW: Also store annotated path
                            annotated_file_path = filepath
                        
                        print(f"✅ {file_type.title()} video saved: {file_info['filename']} ({file_size:,} bytes)")
                    else:
                        files_status[file_type] = {
                            "filename": file_info["filename"],
                            "exists": False,
                            "error": "File not found after recording"
                        }
                        print(f"⚠️ {file_type.title()} video not found: {file_info['filename']}")
            
            recording_info["files_status"] = files_status
            recording_info["total_size"] = total_size
            
            # 🚀 ENHANCED: AUTO-CONVERSION FOR BOTH VIDEOS
            conversion_results = {"attempted": 0, "successful": 0, "details": {}}
            
            # List of files to convert
            files_to_convert = []
            if original_file_path and original_file_path.exists():
                files_to_convert.append(("original", original_file_path))
            if annotated_file_path and annotated_file_path.exists():
                files_to_convert.append(("annotated", annotated_file_path))
            
            if files_to_convert:
                try:
                    # Import conversion function
                    from video_converter import convert_video_for_web
                    
                    print(f"🔄 AUTO-CONVERTING {len(files_to_convert)} videos from 15fps to 30fps...")
                    
                    for file_type, file_path in files_to_convert:
                        conversion_results["attempted"] += 1
                        
                        try:
                            # Create web version filename
                            stem = file_path.stem
                            web_filename = f"{stem}_web.mp4"
                            web_file_path = self.recordings_dir / web_filename
                            
                            print(f"🔄 Converting {file_type}: {file_path.name} → {web_filename}")
                            
                            # Convert video for web compatibility
                            conversion_result = convert_video_for_web(
                                input_path=file_path,
                                output_path=web_file_path,
                                target_fps=30,
                                method="blend"  # Balanced quality/speed
                            )
                            
                            if conversion_result["success"]:
                                conversion_results["successful"] += 1
                                web_size = conversion_result["output_size"]
                                
                                # Add web version to files_status
                                web_key = f"web_{file_type}"  # "web_original" or "web_annotated"
                                files_status[web_key] = {
                                    "filename": web_filename,
                                    "size": web_size,
                                    "size_mb": round(web_size / 1024 / 1024, 2),
                                    "exists": True,
                                    "description": f"Web-optimized {file_type} (30fps)",
                                    "fps": 30,
                                    "conversion_method": "15fps_to_30fps_blend",
                                    "source_type": file_type
                                }
                                
                                # Store conversion details
                                conversion_results["details"][file_type] = {
                                    "success": True,
                                    "web_filename": web_filename,
                                    "original_size": conversion_result.get("input_size", files_status[file_type]["size"]),
                                    "web_size": web_size,
                                    "compression_ratio": conversion_result.get("compression_ratio", 1.0),
                                    "fps_change": "15fps → 30fps",
                                    "method": "blend"
                                }
                                
                                total_size += web_size
                                
                                print(f"✅ {file_type.upper()} WEB CONVERSION SUCCESSFUL!")
                                print(f"   📹 Original: {files_status[file_type]['filename']} ({files_status[file_type]['size_mb']} MB)")
                                print(f"   🌐 Web:      {web_filename} ({files_status[web_key]['size_mb']} MB)")
                                print(f"   📊 Compression: {conversion_result.get('compression_ratio', 1.0):.2f}x")
                            else:
                                print(f"❌ {file_type} web conversion failed")
                                conversion_results["details"][file_type] = {
                                    "success": False,
                                    "error": "Conversion failed"
                                }
                        
                        except Exception as file_conv_error:
                            print(f"❌ {file_type} conversion error: {file_conv_error}")
                            conversion_results["details"][file_type] = {
                                "success": False,
                                "error": str(file_conv_error)
                            }
                    
                    # Update recording info with ALL conversion details
                    recording_info["total_size"] = total_size
                    recording_info["web_conversion"] = {
                        "enabled": True,
                        "attempted": conversion_results["attempted"],
                        "successful": conversion_results["successful"],
                        "conversion_details": conversion_results["details"],
                        "fps_upgrade": "15fps → 30fps",
                        "method": "blend",
                        "both_videos_converted": conversion_results["successful"] == 2
                    }
                    
                    print(f"🎯 CONVERSION SUMMARY:")
                    print(f"   📊 Files attempted: {conversion_results['attempted']}")
                    print(f"   ✅ Files successful: {conversion_results['successful']}")
                    print(f"   🎬 Both videos converted: {'YES' if conversion_results['successful'] == 2 else 'NO'}")
                        
                except ImportError:
                    print(f"⚠️ video_converter module not found - skipping auto-conversion")
                    recording_info["web_conversion"] = {
                        "success": False,
                        "error": "video_converter module not available",
                        "note": "Check if video_converter.py exists and is imported"
                    }
                except Exception as conv_error:
                    print(f"❌ Auto-conversion setup error: {conv_error}")
                    recording_info["web_conversion"] = {
                        "success": False,
                        "error": str(conv_error),
                        "attempted": conversion_results["attempted"],
                        "successful": conversion_results["successful"]
                    }
            
            self.current_recording = None
            
            print(f"✅ RECORDING COMPLETE:")
            print(f"   ⏱️  Duration: {recording_duration:.1f}s")
            print(f"   📊 Total size: {total_size:,} bytes")
            print(f"   📁 Files: {len(files_status)} created")
            conversion_status = "✅ SUCCESS" if conversion_results.get("successful", 0) > 0 else "❌ FAILED" if conversion_results.get("attempted", 0) > 0 else "⏭️ SKIPPED"
            print(f"   🔄 Conversion: {conversion_status} ({conversion_results.get('successful', 0)}/{conversion_results.get('attempted', 0)})")
            
            return {
                "success": True,
                "message": f"Recording stopped with {conversion_results.get('successful', 0)}/{conversion_results.get('attempted', 0)} web conversions",
                "recording_info": recording_info,
                "auto_conversion_enabled": True,
                "dual_conversion": True
            }
            
        except Exception as e:
            print(f"❌ Error stopping recording: {e}")
            
            # Force cleanup
            self.is_recording = False
            self.recording_start_time = None
            self.current_recording = None
            
            if self.video_writer_original:
                self.video_writer_original.release()
                self.video_writer_original = None
            if self.video_writer_annotated:
                self.video_writer_annotated.release()
                self.video_writer_annotated = None
            
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to stop recording"
            }

    
    # Streaming management
    def start_stream(self):
        """Start the video stream - ENHANCED DEBUG VERSION"""
        try:
            print("🚀 DEBUG: start_stream() called")
            
            if not CAMERA_AVAILABLE:
                print("❌ DEBUG: Camera not available - CAMERA_AVAILABLE = False")
                return False
                
            if self.is_running:
                print("⚠️ DEBUG: Stream already running")
                return True
                
            print("🔍 DEBUG: Checking camera initialization...")
            # Initialize camera if not already done
            if not hasattr(self, 'picam2') or self.picam2 is None:
                print("🔍 DEBUG: Setting up analyzer...")
                self.setup_analyzer()
                
            if not hasattr(self, 'picam2') or self.picam2 is None:
                print("❌ DEBUG: Failed to initialize camera - picam2 is None")
                return False
            
            print("🔍 DEBUG: Trying to start camera...")
            # Set running flag (this is what Azure pi-service checks)
            self.is_running = True
            self.session_start_time = datetime.now()
            self.session_stats['session_start'] = self.session_start_time.isoformat()
            
            # Start camera
            try:
                print("📷 DEBUG: Calling picam2.start()...")
                self.picam2.start()
                print("✅ DEBUG: Camera started successfully")
            except Exception as cam_error:
                print(f"❌ DEBUG: Camera start error: {cam_error}")
                print(f"❌ DEBUG: Camera start error type: {type(cam_error)}")
                self.is_running = False
                return False
            
            # Start stream loop in separate thread
            print("🎬 DEBUG: Starting stream thread...")
            self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
            self.stream_thread.start()
            
            print("✅ DEBUG: Stream started successfully")
            return True
            
        except Exception as e:
            print(f"❌ DEBUG: Error starting stream: {e}")
            print(f"❌ DEBUG: Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            self.is_running = False
            return False
        
    def _stream_loop_debug(self):
        """Internal stream loop method - ENHANCED DEBUG VERSION"""
        fps_counter = 0
        fps_start_time = time.time()
        frame_count = 0
        
        print("🎥 DEBUG: Stream loop started!")
        
        try:
            while self.is_running:
                try:
                    frame_count += 1
                    if frame_count % 30 == 0:  # Log every 30 frames
                        print(f"🎬 DEBUG: Processing frame {frame_count}")
                    
                    # Capture frame
                    if not hasattr(self, 'picam2') or self.picam2 is None:
                        print("❌ DEBUG: picam2 is None in stream loop")
                        break
                    
                    try:
                        frame = self.picam2.capture_array()
                        if frame_count <= 3:  # Log first few frames
                            print(f"📸 DEBUG: Frame {frame_count} captured, shape: {frame.shape}")
                    except Exception as capture_error:
                        print(f"❌ DEBUG: Frame capture error: {capture_error}")
                        time.sleep(0.1)
                        continue
                    
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                    # Process pose (with error handling)
                    try:
                        pose_data = self.process_frame(frame_bgr)
                        self.pose_data = pose_data
                        if frame_count <= 3:
                            print(f"🤖 DEBUG: Frame {frame_count} - {len(pose_data)} persons detected")
                    except Exception as pose_error:
                        print(f"❌ DEBUG: Pose processing error: {pose_error}")
                        pose_data = []
                        self.pose_data = []
                    
                    # Draw pose overlay
                    display_frame = frame_bgr.copy()
                    try:
                        for person_data in pose_data:
                            keypoints = np.array(person_data['keypoints'])
                            confidences = np.array(person_data['confidences'])
                            display_frame = self.draw_pose(display_frame, keypoints, confidences)
                    except Exception as draw_error:
                        print(f"❌ DEBUG: Draw pose error: {draw_error}")
                    
                    # Add overlay info
                    try:
                        cv2.putText(display_frame, 'Baduanjin Live Analysis', (10, 30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                        cv2.putText(display_frame, f'FPS: {self.session_stats.get("current_fps", 0)}', (10, 60), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        cv2.putText(display_frame, f'Persons: {len(pose_data)}', (10, 85), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        cv2.putText(display_frame, f'Frame: {frame_count}', (10, 110), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    except Exception as text_error:
                        print(f"❌ DEBUG: Text overlay error: {text_error}")
                    
                    # Add recording indicator and save frame if recording
                    if self.is_recording:
                        try:
                            cv2.putText(display_frame, '🔴 REC', (10, 135), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                            # Save frame to video file (save original without overlay)
                            if self.video_writer and self.video_writer.isOpened():
                                self.video_writer.write(frame_bgr)
                        except Exception as rec_error:
                            print(f"❌ DEBUG: Recording error: {rec_error}")
                    
                    # Calculate FPS
                    fps_counter += 1
                    if fps_counter % 30 == 0:
                        elapsed = time.time() - fps_start_time
                        current_fps = 30 / elapsed if elapsed > 0 else 0
                        fps_start_time = time.time()
                        self.session_stats['current_fps'] = round(current_fps, 1)
                        print(f"📊 DEBUG: FPS calculated: {current_fps:.1f}")
                    
                    # Update stats
                    self.session_stats['total_frames'] = self.session_stats.get('total_frames', 0) + 1
                    self.session_stats['persons_detected'] = len(pose_data)
                    
                    # Store current frame (with overlay for display)
                    self.current_frame = display_frame.copy()
                    
                    if frame_count <= 3:
                        print(f"✅ DEBUG: Frame {frame_count} processed and stored")
                    
                    time.sleep(0.033)  # ~30 FPS
                    
                except Exception as loop_error:
                    print(f"❌ DEBUG: Stream loop iteration error: {loop_error}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(0.1)
                    
                    if not self.is_running:  # Exit if stop was called
                        break
        
        except Exception as fatal_error:
            print(f"❌ DEBUG: Fatal stream loop error: {fatal_error}")
            import traceback
            traceback.print_exc()
        
        print("🏁 DEBUG: Stream loop ended")

    # setup_analyzer debug 
    def setup_analyzer(self):
        """Initialize the pose analyzer - ENHANCED DEBUG VERSION"""
        try:
            print("🔍 DEBUG: setup_analyzer() called")
            
            # Check if picamera2 is available
            try:
                from picamera2 import Picamera2
                print("✅ DEBUG: Picamera2 import successful")
            except ImportError as e:
                print(f"❌ DEBUG: Picamera2 import failed: {e}")
                return
            
            # Initialize camera
            print("📷 DEBUG: Initializing camera...")
            try:
                self.picam2 = Picamera2()
                print("✅ DEBUG: Picamera2 object created")
            except Exception as e:
                print(f"❌ DEBUG: Picamera2 creation failed: {e}")
                return
            
            try:
                config = self.picam2.create_preview_configuration(
                    main={"format": 'XRGB8888', "size": (Config.CAMERA_WIDTH, Config.CAMERA_HEIGHT)}
                )
                print(f"✅ DEBUG: Camera config created: {Config.CAMERA_WIDTH}x{Config.CAMERA_HEIGHT}")
            except Exception as e:
                print(f"❌ DEBUG: Camera config creation failed: {e}")
                return
            
            try:
                self.picam2.configure(config)
                print("✅ DEBUG: Camera configured")
            except Exception as e:
                print(f"❌ DEBUG: Camera configuration failed: {e}")
                return
            
            # Initialize YOLO with models folder path
            if YOLO_AVAILABLE:
                print("🤖 DEBUG: Initializing YOLO...")
                model_path = Config.YOLO_MODEL_PATH
                print(f"🔍 DEBUG: Looking for YOLO model at: {model_path}")
                
                if not model_path.exists():
                    print(f"⚠️ DEBUG: Model not found at {model_path}, trying fallback...")
                    # Fallback to root directory
                    model_path = Path("yolov8n-pose.pt")
                    print(f"🔍 DEBUG: Trying fallback path: {model_path}")
                    
                    if not model_path.exists():
                        print(f"❌ DEBUG: YOLO model not found in models/ or root directory")
                        print("💡 DEBUG: Download with: wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt -O models/yolov8n-pose.pt")
                        self.model = None
                        return
                
                print(f"📦 DEBUG: Loading YOLO model from: {model_path}")
                try:
                    self.model = YOLO(str(model_path))
                    print(f"✅ DEBUG: YOLO model loaded successfully")
                except Exception as e:
                    print(f"❌ DEBUG: YOLO model loading failed: {e}")
                    self.model = None
            else:
                print("⚠️ DEBUG: YOLO not available")
                self.model = None
                
            print("✅ DEBUG: Analyzer setup complete")
            
        except Exception as e:
            print(f"❌ DEBUG: Analyzer setup failed: {e}")
            import traceback
            traceback.print_exc()
            self.analyzer = None
    
    def stop_stream(self):
        """Stop the video stream (called by Azure pi-service via /api/stop)"""
        try:
            print("🛑 Stopping stream...")
            self.is_running = False
            
            # Stop any active recording
            if self.is_recording:
                print("⚠️ Auto-stopping recording when stream ends...")
                self.stop_recording()
            
            if hasattr(self, 'picam2') and self.picam2 is not None:
                try:
                    self.picam2.stop()
                    print("✅ Camera stopped")
                except Exception as cam_error:
                    print(f"⚠️ Camera stop warning: {cam_error}")
            
            # Wait for thread to finish
            if hasattr(self, 'stream_thread') and self.stream_thread.is_alive():
                self.stream_thread.join(timeout=2.0)
            
            # Clear session state
            self.current_frame = None
            self.pose_data = []
            self.session_start_time = None
            
            print("✅ Stream stopped successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error stopping stream: {e}")
            return False
    
    def _stream_loop(self):
        """Stream loop with dual video recording capability"""
        fps_counter = 0
        fps_start_time = time.time()
        frame_count = 0
        
        print("🎥 DEBUG: Stream loop started!")
        
        try:
            while self.is_running:
                try:
                    frame_count += 1
                    if frame_count % 30 == 0:  # Log every 30 frames
                        print(f"🎬 DEBUG: Processing frame {frame_count}")
                    
                    # Capture frame
                    if not hasattr(self, 'picam2') or self.picam2 is None:
                        print("❌ DEBUG: picam2 is None in stream loop")
                        break
                    
                    try:
                        frame = self.picam2.capture_array()
                        if frame_count <= 3:  # Log first few frames
                            print(f"📸 DEBUG: Frame {frame_count} captured, shape: {frame.shape}")
                    except Exception as capture_error:
                        print(f"❌ DEBUG: Frame capture error: {capture_error}")
                        time.sleep(0.1)
                        continue
                    
                    # Convert to BGR for OpenCV
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                    # Process pose (with error handling)
                    try:
                        pose_data = self.process_frame(frame_bgr)
                        self.pose_data = pose_data
                        if frame_count <= 3:
                            print(f"🤖 DEBUG: Frame {frame_count} - {len(pose_data)} persons detected")
                    except Exception as pose_error:
                        print(f"❌ DEBUG: Pose processing error: {pose_error}")
                        pose_data = []
                        self.pose_data = []
                    
                    # Create annotated frame (with pose overlay)
                    annotated_frame = frame_bgr.copy()
                    try:
                        for person_data in pose_data:
                            keypoints = np.array(person_data['keypoints'])
                            confidences = np.array(person_data['confidences'])
                            annotated_frame = self.draw_pose(annotated_frame, keypoints, confidences)
                    except Exception as draw_error:
                        print(f"❌ DEBUG: Draw pose error: {draw_error}")
                    
                    # Add text overlays to annotated frame
                    try:
                        cv2.putText(annotated_frame, 'Baduanjin Live Analysis', (10, 30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                        cv2.putText(annotated_frame, f'FPS: {self.session_stats.get("current_fps", 0)}', (10, 60), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        cv2.putText(annotated_frame, f'Persons: {len(pose_data)}', (10, 85), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        cv2.putText(annotated_frame, f'Frame: {frame_count}', (10, 110), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        
                        # Add recording indicator
                        if self.is_recording:
                            cv2.putText(annotated_frame, '🔴 REC', (10, 135), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                            
                            # DUAL RECORDING: Save both versions
                            if self.video_writer_original and self.video_writer_original.isOpened():
                                self.video_writer_original.write(frame_bgr)  # Original (clean)
                            
                            if self.video_writer_annotated and self.video_writer_annotated.isOpened():
                                self.video_writer_annotated.write(annotated_frame)  # Annotated (with poses)
                            
                            if frame_count % 60 == 0:  # Log every 60 frames during recording
                                print(f"📹 Recording frame {frame_count} (dual video)")
                                
                    except Exception as overlay_error:
                        print(f"❌ DEBUG: Overlay error: {overlay_error}")
                    
                    # Calculate FPS
                    fps_counter += 1
                    if fps_counter % 30 == 0:
                        elapsed = time.time() - fps_start_time
                        current_fps = 30 / elapsed if elapsed > 0 else 0
                        fps_start_time = time.time()
                        self.session_stats['current_fps'] = round(current_fps, 1)
                        if frame_count <= 90:  # Only log FPS for first 90 frames
                            print(f"📊 DEBUG: FPS calculated: {current_fps:.1f}")
                    
                    # Update stats
                    self.session_stats['total_frames'] = self.session_stats.get('total_frames', 0) + 1
                    self.session_stats['persons_detected'] = len(pose_data)
                    
                    # Store current frame (annotated version for display)
                    self.current_frame = annotated_frame.copy()
                    
                    if frame_count <= 3:
                        print(f"✅ DEBUG: Frame {frame_count} processed and stored")
                    
                    time.sleep(0.033)  # ~30 FPS
                    
                except Exception as loop_error:
                    print(f"❌ DEBUG: Stream loop iteration error: {loop_error}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(0.1)
                    
                    if not self.is_running:  # Exit if stop was called
                        break
        
        except Exception as fatal_error:
            print(f"❌ DEBUG: Fatal stream loop error: {fatal_error}")
            import traceback
            traceback.print_exc()
        
        print("🏁 DEBUG: Stream loop ended")

    
    # File management 
    def get_recordings_list(self):
        """Get list of recordings with DUAL web version info - ENHANCED"""
        try:
            recordings = []
            processed_timestamps = set()
            
            for file_path in self.recordings_dir.glob("*.mp4"):
                file_stats = file_path.stat()
                filename = file_path.name
                
                # Extract timestamp and type from filename
                if filename.startswith("baduanjin_"):
                    parts = filename.replace("baduanjin_", "").replace(".mp4", "").split("_")
                    if len(parts) >= 3:  # original/annotated/web_YYYYMMDD_HHMMSS
                        video_type = parts[0]  # "original", "annotated", or "web"
                        timestamp = "_".join(parts[1:])  # "YYYYMMDD_HHMMSS"
                        
                        if timestamp not in processed_timestamps:
                            processed_timestamps.add(timestamp)
                            
                            # Look for all file types with this timestamp
                            original_file = self.recordings_dir / f"baduanjin_original_{timestamp}.mp4"
                            annotated_file = self.recordings_dir / f"baduanjin_annotated_{timestamp}.mp4"
                            web_original_file = self.recordings_dir / f"baduanjin_original_{timestamp}_web.mp4"  # Web version of original
                            web_annotated_file = self.recordings_dir / f"baduanjin_annotated_{timestamp}_web.mp4"  # NEW: Web version of annotated
                            
                            recording_entry = {
                                "timestamp": timestamp,
                                "created": datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                                "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                                "files": {},
                                "has_web_versions": {  # NEW: Track both web versions
                                    "original": web_original_file.exists(),
                                    "annotated": web_annotated_file.exists()
                                },
                                "web_conversion_count": 0,  # NEW: Count of web versions
                                "recommended_for_transfer": False  # Will be determined below
                            }
                            
                            total_size = 0
                            web_version_count = 0
                            
                            # Check original file
                            if original_file.exists():
                                original_stats = original_file.stat()
                                recording_entry["files"]["original"] = {
                                    "filename": original_file.name,
                                    "size": original_stats.st_size,
                                    "size_mb": round(original_stats.st_size / 1024 / 1024, 2),
                                    "description": "Clean original video (15fps)",
                                    "fps": 15,
                                    "type": "source"
                                }
                                total_size += original_stats.st_size
                            
                            # Check annotated file
                            if annotated_file.exists():
                                annotated_stats = annotated_file.stat()
                                recording_entry["files"]["annotated"] = {
                                    "filename": annotated_file.name,
                                    "size": annotated_stats.st_size,
                                    "size_mb": round(annotated_stats.st_size / 1024 / 1024, 2),
                                    "description": "Video with pose overlay (15fps)",
                                    "fps": 15,
                                    "type": "source"
                                }
                                total_size += annotated_stats.st_size
                            
                            # NEW: Check web version of original
                            if web_original_file.exists():
                                web_original_stats = web_original_file.stat()
                                recording_entry["files"]["web_original"] = {
                                    "filename": web_original_file.name,
                                    "size": web_original_stats.st_size,
                                    "size_mb": round(web_original_stats.st_size / 1024 / 1024, 2),
                                    "description": "Web-optimized original (30fps)",
                                    "fps": 30,
                                    "type": "web_converted",
                                    "source_type": "original",
                                    "web_optimized": True
                                }
                                total_size += web_original_stats.st_size
                                web_version_count += 1
                            
                            # NEW: Check web version of annotated
                            if web_annotated_file.exists():
                                web_annotated_stats = web_annotated_file.stat()
                                recording_entry["files"]["web_annotated"] = {
                                    "filename": web_annotated_file.name,
                                    "size": web_annotated_stats.st_size,
                                    "size_mb": round(web_annotated_stats.st_size / 1024 / 1024, 2),
                                    "description": "Web-optimized annotated (30fps)",
                                    "fps": 30,
                                    "type": "web_converted",
                                    "source_type": "annotated",
                                    "web_optimized": True
                                }
                                total_size += web_annotated_stats.st_size
                                web_version_count += 1
                            
                            # Update web conversion info
                            recording_entry["web_conversion_count"] = web_version_count
                            recording_entry["has_any_web_version"] = web_version_count > 0
                            recording_entry["has_both_web_versions"] = web_version_count == 2
                            recording_entry["recommended_for_transfer"] = web_version_count > 0  # Prefer any web version
                            
                            # Add transfer recommendations
                            transfer_recommendations = []
                            if web_original_file.exists():
                                transfer_recommendations.append({
                                    "filename": web_original_file.name,
                                    "type": "web_original",
                                    "priority": "high",
                                    "reason": "30fps web-optimized clean video"
                                })
                            if web_annotated_file.exists():
                                transfer_recommendations.append({
                                    "filename": web_annotated_file.name,
                                    "type": "web_annotated", 
                                    "priority": "high",
                                    "reason": "30fps web-optimized with pose analysis"
                                })
                            
                            # Fallback to original files if no web versions
                            if not transfer_recommendations:
                                if original_file.exists():
                                    transfer_recommendations.append({
                                        "filename": original_file.name,
                                        "type": "original",
                                        "priority": "medium",
                                        "reason": "Original 15fps video"
                                    })
                                if annotated_file.exists():
                                    transfer_recommendations.append({
                                        "filename": annotated_file.name,
                                        "type": "annotated",
                                        "priority": "medium", 
                                        "reason": "15fps with pose analysis"
                                    })
                            
                            recording_entry["transfer_recommendations"] = transfer_recommendations
                            recording_entry["total_size"] = total_size
                            recording_entry["file_count"] = len(recording_entry["files"])
                            
                            # Add summary for easy viewing
                            recording_entry["summary"] = {
                                "source_files": sum(1 for f in recording_entry["files"].values() if f.get("type") == "source"),
                                "web_files": web_version_count,
                                "total_files": len(recording_entry["files"]),
                                "best_for_transfer": transfer_recommendations[0]["filename"] if transfer_recommendations else None
                            }
                            
                            recordings.append(recording_entry)
                else:
                    # Handle legacy single files
                    recordings.append({
                        "filename": filename,
                        "size": file_stats.st_size,
                        "size_mb": round(file_stats.st_size / 1024 / 1024, 2),
                        "created": datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                        "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                        "legacy": True,
                        "has_web_versions": {"original": False, "annotated": False},
                        "has_any_web_version": False,
                        "recommended_for_transfer": True  # Legacy files are transferred as-is
                    })
            
            # Sort by creation time (newest first)
            recordings.sort(key=lambda x: x.get("created", ""), reverse=True)
            
            return recordings
            
        except Exception as e:
            print(f"❌ Error getting recordings list: {e}")
            return []