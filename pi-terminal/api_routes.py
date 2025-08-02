"""
api_routes.py - API Route Handlers - ENHANCED with Baduanjin Exercise Tracking
"""

from flask import jsonify, request, send_file, Response
import cv2
import base64
import time
import os
import json
from datetime import datetime
from pathlib import Path
from config import Config
from video_converter import convert_video_for_web, check_ffmpeg_available

# Check imports
try:
    from picamera2 import Picamera2
    from ultralytics import YOLO
    CAMERA_AVAILABLE = True
    YOLO_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False
    YOLO_AVAILABLE = False

# 🚀 NEW: Check for enhanced tracking capabilities
try:
    from baduanjin_tracker import BaduanjinTracker
    ENHANCED_TRACKING_AVAILABLE = True
except ImportError:
    ENHANCED_TRACKING_AVAILABLE = False
    print("⚠️ baduanjin_tracker not available - exercise tracking disabled")

def register_api_routes(app, web_analyzer):
    """Register all API routes with the Flask app - ENHANCED with Exercise Tracking"""
    
    # MAIN ENDPOINTS
    @app.route('/')
    def index():
        """Main page"""
        base_info = {
            "service": "Baduanjin Real-time Analysis",
            "status": "running",
            "version": "2.0",
            "compatibility": "Azure pi-service compatible",
            "workflow": [
                "Azure pi-service calls /api/pi-live/start-session to begin session",
                "Azure pi-service calls /api/pi-live/recording/start for video recording",
                "Azure pi-service calls /api/pi-live/recording/stop to end recording", 
                "Azure pi-service calls /api/pi-live/stop-session to end session",
                "Azure pi-service calls /api/recordings to list files"
            ]
        }
        
        # 🚀 NEW: Add exercise tracking info if available
        if ENHANCED_TRACKING_AVAILABLE and hasattr(web_analyzer, 'baduanjin_tracker'):
            base_info.update({
                "enhanced_features": {
                    "exercise_tracking": True,
                    "real_time_feedback": True,
                    "form_analysis": True,
                    "8_baduanjin_exercises": True
                },
                "new_endpoints": [
                    "GET /api/baduanjin/exercises - List all 8 Baduanjin exercises",
                    "POST /api/baduanjin/start/<id> - Start exercise tracking",
                    "GET /api/baduanjin/feedback - Get real-time feedback",
                    "POST /api/baduanjin/stop - Stop tracking and get summary"
                ]
            })
        
        return jsonify(base_info)
    
    # ==================== EXISTING API ENDPOINTS (KEEP ALL AS-IS) ====================
    
    @app.route('/api/start', methods=['POST'])
    def legacy_start_stream():
        """Legacy start endpoint - called by Azure pi-service"""
        try:
            success = web_analyzer.start_stream()
            
            if success:
                return jsonify({
                    "success": True,
                    "message": "Live streaming started successfully",
                    "camera_available": CAMERA_AVAILABLE,
                    "yolo_available": YOLO_AVAILABLE,
                    "is_running": True,
                    "enhanced_tracking_available": ENHANCED_TRACKING_AVAILABLE  # 🚀 NEW
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "Failed to start streaming - camera not available",
                    "camera_available": CAMERA_AVAILABLE,
                    "yolo_available": YOLO_AVAILABLE
                }), 500
                
        except Exception as e:
            print(f"❌ Error in legacy start: {e}")
            return jsonify({
                "success": False,
                "error": str(e),
                "message": "Internal error starting streaming"
            }), 500

    @app.route('/api/stop', methods=['POST'])
    def legacy_stop_stream():
        """Legacy stop endpoint - called by Azure pi-service"""
        try:
            # 🚀 NEW: Auto-stop exercise tracking if enabled
            if ENHANCED_TRACKING_AVAILABLE and hasattr(web_analyzer, 'disable_exercise_tracking') and getattr(web_analyzer, 'tracking_enabled', False):
                try:
                    web_analyzer.disable_exercise_tracking()
                    print("🎯 Auto-stopped exercise tracking when stream ended")
                except Exception as tracking_error:
                    print(f"⚠️ Error auto-stopping tracking: {tracking_error}")
            
            web_analyzer.stop_stream()
            
            return jsonify({
                "success": True,
                "message": "Live streaming stopped successfully",
                "is_running": False,
                "exercise_tracking_stopped": True if ENHANCED_TRACKING_AVAILABLE else False  # 🚀 NEW
            })
            
        except Exception as e:
            print(f"❌ Error in legacy stop: {e}")
            return jsonify({
                "success": False,
                "error": str(e),
                "message": "Internal error stopping streaming"
            }), 500

    @app.route('/api/status')
    def enhanced_legacy_get_status():
        """Enhanced status endpoint with exercise tracking info - ENHANCED"""
        try:
            recordings = web_analyzer.get_recordings_list()
            
            # Handle both new dual video format and legacy single file format
            latest_recording_info = None
            if recordings:
                latest = recordings[0]
                if "files" in latest:  # New dual video format
                    # Create summary of latest dual recording
                    files_info = []
                    for file_type, file_data in latest["files"].items():
                        files_info.append(f"{file_type}: {file_data['filename']}")
                    latest_recording_info = f"Dual recording ({', '.join(files_info)})"
                elif "filename" in latest:  # Legacy single file format
                    latest_recording_info = latest["filename"]
                else:
                    latest_recording_info = f"Recording {latest.get('timestamp', 'unknown')}"
            
            base_status = {
                # Basic status (Azure expects these)
                "is_running": web_analyzer.is_running,
                "camera_available": CAMERA_AVAILABLE,
                "yolo_available": YOLO_AVAILABLE,
                "is_recording": web_analyzer.is_recording,
                "persons_detected": web_analyzer.session_stats.get('persons_detected', 0),
                "current_fps": web_analyzer.session_stats.get('current_fps', 0),
                
                # Enhanced info for debugging - FIXED for dual video
                "recordings_count": len(recordings),
                "latest_recording": latest_recording_info,
                "recording_format": "dual_video" if recordings and "files" in recordings[0] else "single_video",
                "session_duration": str(datetime.now() - web_analyzer.session_start_time) if web_analyzer.session_start_time else "0:00:00",
                "recording_duration": str(datetime.now() - web_analyzer.recording_start_time) if web_analyzer.recording_start_time else "0:00:00",
                
                # Network info
                "ngrok_compatible": True,
                "mobile_network_optimized": True,
                "websocket_status": "disabled_for_ngrok",
                "http_polling_available": True,
                
                # File system info
                "recordings_dir": str(web_analyzer.recordings_dir),
                "recordings_dir_exists": web_analyzer.recordings_dir.exists(),
                
                # Server info
                "server_version": "2.0",
                "dual_video_recording": True,
                "enhanced_tracking_available": ENHANCED_TRACKING_AVAILABLE,  # 🚀 NEW
                "timestamp": datetime.now().isoformat()
            }
            
            # 🚀 NEW: Add exercise tracking status if available
            if ENHANCED_TRACKING_AVAILABLE and hasattr(web_analyzer, 'baduanjin_tracker'):
                try:
                    tracking_status = {
                        "tracking_enabled": getattr(web_analyzer, 'tracking_enabled', False),
                        "current_exercise": None,
                        "current_phase": None,
                        "session_stats": None
                    }
                    
                    if getattr(web_analyzer, 'tracking_enabled', False):
                        if hasattr(web_analyzer, 'baduanjin_tracker') and web_analyzer.baduanjin_tracker.current_exercise:
                            exercise_info = web_analyzer.baduanjin_tracker.exercises[web_analyzer.baduanjin_tracker.current_exercise]
                            tracking_status.update({
                                "current_exercise": {
                                    "id": web_analyzer.baduanjin_tracker.current_exercise,
                                    "name": exercise_info["name"],
                                    "description": exercise_info["description"]
                                },
                                "current_phase": web_analyzer.baduanjin_tracker.current_phase,
                                "session_stats": web_analyzer.baduanjin_tracker.get_session_statistics()
                            })
                    
                    base_status["exercise_tracking"] = tracking_status
                
                except Exception as tracking_error:
                    base_status["exercise_tracking"] = {
                        "error": str(tracking_error),
                        "tracking_enabled": False
                    }
            
            return jsonify(base_status)
            
        except Exception as e:
            print(f"❌ Enhanced status error: {e}")
            import traceback
            traceback.print_exc()
            
            # Return minimal status if detailed status fails
            return jsonify({
                "is_running": getattr(web_analyzer, 'is_running', False),
                "camera_available": CAMERA_AVAILABLE,
                "yolo_available": YOLO_AVAILABLE,
                "is_recording": getattr(web_analyzer, 'is_recording', False),
                "enhanced_tracking_available": ENHANCED_TRACKING_AVAILABLE,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "status": "degraded"
            }), 200  # Return 200 instead of 500 for basic functionality

    # [KEEP ALL YOUR EXISTING ENDPOINTS - recording/start, recording/stop, recordings, download, etc.]
    # I'm including them below but they remain exactly the same as your original code:

    @app.route('/api/recording/start', methods=['POST'])
    def legacy_start_recording():
        """Start recording endpoint - called by Azure pi-service"""
        try:
            result = web_analyzer.start_recording()
            
            if result["success"]:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            print(f"❌ Error starting recording: {e}")
            return jsonify({
                "success": False,
                "error": str(e),
                "message": "Internal error starting recording"
            }), 500

    @app.route('/api/recording/stop', methods=['POST'])
    @app.route('/api/pi-live/recording/stop/<session_id>', methods=['POST'])  
    def enhanced_stop_recording(session_id=None):
        """ENHANCED: Stop recording and convert for web - REPLACES existing stop recording"""
        try:
            # Stop the recording first
            result = web_analyzer.stop_recording()
            
            if not result["success"]:
                return jsonify(result), 400
            
            # NEW: Auto-convert the recorded video for web compatibility
            if "filename" in result and result["filename"]:
                try:
                    original_file = web_analyzer.recordings_dir / result["filename"]
                    
                    if original_file.exists():
                        # Create web-compatible version filename
                        stem = original_file.stem
                        web_filename = f"{stem}_web.mp4"
                        web_file_path = web_analyzer.recordings_dir / web_filename
                        
                        print(f"🔄 Auto-converting {result['filename']} for web compatibility...")
                        
                        # Convert for web (15fps → 30fps)
                        conversion_result = convert_video_for_web(
                            input_path=original_file,
                            output_path=web_file_path,
                            target_fps=30,
                            method="blend"  # Balanced quality/speed
                        )
                        
                        if conversion_result["success"]:
                            # Update result to include web version info
                            result.update({
                                "web_version_created": True,
                                "web_filename": web_filename,
                                "original_size": conversion_result["input_size"],
                                "web_size": conversion_result["output_size"],
                                "conversion_method": "15fps_to_30fps_blend",
                                "both_versions_available": True
                            })
                            
                            print(f"✅ Web version created: {web_filename}")
                        else:
                            result["web_conversion_error"] = "Conversion failed"
                            
                except Exception as conversion_error:
                    print(f"⚠️ Web conversion failed: {conversion_error}")
                    result["web_conversion_error"] = str(conversion_error)
                    # Still return success for recording, even if conversion failed
            
            return jsonify(result)
            
        except Exception as e:
            print(f"❌ Error in enhanced stop recording: {e}")
            return jsonify({
                "success": False,
                "error": str(e),
                "message": "Internal error stopping recording"
            }), 500

    # [KEEP ALL YOUR OTHER EXISTING ENDPOINTS]
    # recordings, download, pi-live endpoints, etc. - they all remain the same
    # Adding them here for completeness but they're identical to your original:

    @app.route('/api/recordings')
    @app.route('/api/pi-live/recordings')
    def enhanced_get_recordings():
        """ENHANCED: Get recordings list with DUAL web version info"""
        try:
            recordings = web_analyzer.get_recordings_list()
            
            # ENHANCED: Add dual web version information to each recording
            enhanced_recordings = []
            
            for recording in recordings:
                if "timestamp" in recording:  # New dual video format
                    enhanced_recording = recording.copy()
                    
                    # Add convenience fields for Azure service
                    web_files = []
                    source_files = []
                    
                    for file_key, file_data in recording.get("files", {}).items():
                        if file_data.get("type") == "web_converted":
                            web_files.append({
                                "filename": file_data["filename"],
                                "source_type": file_data.get("source_type", "unknown"),
                                "size_mb": file_data.get("size_mb", 0)
                            })
                        elif file_data.get("type") == "source":
                            source_files.append({
                                "filename": file_data["filename"],
                                "size_mb": file_data.get("size_mb", 0)
                            })
                    
                    enhanced_recording.update({
                        "web_files_available": web_files,
                        "source_files_available": source_files,
                        "conversion_status": {
                            "both_converted": recording.get("has_both_web_versions", False),
                            "original_converted": recording.get("has_web_versions", {}).get("original", False),
                            "annotated_converted": recording.get("has_web_versions", {}).get("annotated", False),
                            "total_web_versions": recording.get("web_conversion_count", 0)
                        }
                    })
                    
                    enhanced_recordings.append(enhanced_recording)
                    
                elif "filename" in recording:  # Legacy single file format
                    original_file = web_analyzer.recordings_dir / recording["filename"]
                    
                    # Check for BOTH web versions (for legacy files that might have been converted)
                    stem = Path(recording["filename"]).stem
                    web_original_filename = f"{stem}_web.mp4"  # Standard web conversion
                    web_annotated_filename = f"{stem}_annotated_web.mp4"  # If someone manually converted annotated
                    
                    web_original_file = web_analyzer.recordings_dir / web_original_filename
                    web_annotated_file = web_analyzer.recordings_dir / web_annotated_filename
                    
                    enhanced_recording = recording.copy()
                    enhanced_recording.update({
                        "has_web_versions": {
                            "original": web_original_file.exists(),
                            "annotated": web_annotated_file.exists()
                        },
                        "web_files_available": [],
                        "conversion_status": {
                            "both_converted": False,
                            "original_converted": web_original_file.exists(),
                            "annotated_converted": web_annotated_file.exists(),
                            "total_web_versions": sum([web_original_file.exists(), web_annotated_file.exists()])
                        },
                        "recommended_for_transfer": web_original_file.exists(),
                        "transfer_filename": web_original_filename if web_original_file.exists() else recording["filename"]
                    })
                    
                    # Add web file info if they exist
                    if web_original_file.exists():
                        web_stats = web_original_file.stat()
                        enhanced_recording["web_files_available"].append({
                            "filename": web_original_filename,
                            "source_type": "original",
                            "size_mb": round(web_stats.st_size / 1024 / 1024, 2)
                        })
                        enhanced_recording.update({
                            "web_original_size": web_stats.st_size,
                            "web_original_created": datetime.fromtimestamp(web_stats.st_ctime).isoformat()
                        })
                    
                    if web_annotated_file.exists():
                        web_annotated_stats = web_annotated_file.stat()
                        enhanced_recording["web_files_available"].append({
                            "filename": web_annotated_filename,
                            "source_type": "annotated",
                            "size_mb": round(web_annotated_stats.st_size / 1024 / 1024, 2)
                        })
                    
                    enhanced_recordings.append(enhanced_recording)
                else:
                    # Unknown format, pass through
                    enhanced_recordings.append(recording)
            
            # Calculate overall conversion statistics
            total_recordings = len(enhanced_recordings)
            recordings_with_web = sum(1 for r in enhanced_recordings if r.get("conversion_status", {}).get("total_web_versions", 0) > 0)
            recordings_fully_converted = sum(1 for r in enhanced_recordings if r.get("conversion_status", {}).get("both_converted", False))
            
            return jsonify({
                "success": True,
                "recordings": enhanced_recordings,
                "count": total_recordings,
                "statistics": {
                    "total_recordings": total_recordings,
                    "recordings_with_web_versions": recordings_with_web,
                    "recordings_fully_converted": recordings_fully_converted,
                    "conversion_coverage": round((recordings_with_web / total_recordings * 100), 1) if total_recordings > 0 else 0
                },
                "web_conversion_available": check_ffmpeg_available(),
                "dual_conversion_supported": True,
                "enhanced_tracking_available": ENHANCED_TRACKING_AVAILABLE,  # 🚀 NEW
                "server_info": {
                    "auto_conversion_enabled": True,
                    "converts_both_videos": True,
                    "fps_upgrade": "15fps → 30fps",
                    "exercise_tracking": ENHANCED_TRACKING_AVAILABLE  # 🚀 NEW
                }
            })
            
        except Exception as e:
            print(f"❌ Error getting enhanced recordings: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "success": False,
                "error": str(e),
                "recordings": [],
                "count": 0
            }), 500

    # ==================== 🚀 NEW: BADUANJIN EXERCISE TRACKING ENDPOINTS ====================
    
    if ENHANCED_TRACKING_AVAILABLE:
        
        @app.route('/api/baduanjin/exercises', methods=['GET'])
        def get_baduanjin_exercises():
            """Get list of all 8 Baduanjin exercises"""
            try:
                if not hasattr(web_analyzer, 'baduanjin_tracker'):
                    return jsonify({"success": False, "error": "Exercise tracker not available"}), 500
                
                exercises = []
                for ex_id, ex_data in web_analyzer.baduanjin_tracker.exercises.items():
                    exercises.append({
                        "id": ex_id,
                        "name": ex_data["name"],
                        "description": ex_data["description"],
                        "phases": list(ex_data["key_poses"].keys()),
                        "common_mistakes": ex_data["common_mistakes"]
                    })
                
                return jsonify({
                    "success": True,
                    "exercises": exercises,
                    "total_exercises": len(exercises),
                    "server_version": "2.0",
                    "tracking_available": True
                })
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
        
        @app.route('/api/baduanjin/start/<int:exercise_id>', methods=['POST'])
        def start_baduanjin_exercise(exercise_id):
            """Start tracking specific Baduanjin exercise"""
            try:
                if not hasattr(web_analyzer, 'enable_exercise_tracking'):
                    return jsonify({"success": False, "error": "Enhanced analyzer not available"}), 500
                
                # Ensure streaming is active
                if not web_analyzer.is_running:
                    stream_result = web_analyzer.start_stream()
                    if not stream_result:
                        return jsonify({
                            "success": False, 
                            "error": "Failed to start camera stream"
                        }), 500
                
                # Start exercise tracking
                result = web_analyzer.enable_exercise_tracking(exercise_id)
                
                if result["success"]:
                    return jsonify({
                        "success": True,
                        "message": f"Started tracking {result['exercise_name']}",
                        "exercise_info": result,
                        "streaming_status": "active",
                        "real_time_feedback_available": True
                    })
                else:
                    return jsonify(result), 400
                    
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
        
        @app.route('/api/baduanjin/stop', methods=['POST'])
        def stop_baduanjin_exercise():
            """Stop current exercise tracking"""
            try:
                if not hasattr(web_analyzer, 'disable_exercise_tracking'):
                    return jsonify({"success": False, "error": "Enhanced analyzer not available"}), 500
                
                result = web_analyzer.disable_exercise_tracking()
                
                # Add session export if requested
                export_data = request.json or {}
                if export_data.get('export_session', False):
                    try:
                        export_result = web_analyzer.export_session_data()
                        result["session_export"] = export_result
                    except Exception as export_error:
                        result["export_error"] = str(export_error)
                
                return jsonify(result)
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
        
        @app.route('/api/baduanjin/feedback', methods=['GET'])
        def get_real_time_feedback():
            """Get current real-time feedback"""
            try:
                if not hasattr(web_analyzer, 'get_real_time_feedback'):
                    return jsonify({"success": False, "error": "Enhanced analyzer not available"}), 500
                
                feedback_data = web_analyzer.get_real_time_feedback()
                
                # Add streaming status
                feedback_data["streaming_status"] = {
                    "is_running": web_analyzer.is_running,
                    "is_recording": web_analyzer.is_recording,
                    "persons_detected": web_analyzer.session_stats.get('persons_detected', 0),
                    "current_fps": web_analyzer.session_stats.get('current_fps', 0)
                }
                
                return jsonify(feedback_data)
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
        
        @app.route('/api/baduanjin/status', methods=['GET'])
        def get_baduanjin_tracking_status():
            """Get current exercise tracking status"""
            try:
                if not hasattr(web_analyzer, 'baduanjin_tracker'):
                    return jsonify({"success": False, "error": "Exercise tracker not available"}), 500
                
                status = {
                    "streaming_active": web_analyzer.is_running,
                    "tracking_enabled": getattr(web_analyzer, 'tracking_enabled', False),
                    "current_exercise": None,
                    "session_active": web_analyzer.session_start_time is not None,
                    "recording_active": web_analyzer.is_recording
                }
                
                if getattr(web_analyzer, 'tracking_enabled', False) and hasattr(web_analyzer, 'baduanjin_tracker') and web_analyzer.baduanjin_tracker.current_exercise:
                    exercise_info = web_analyzer.baduanjin_tracker.exercises[web_analyzer.baduanjin_tracker.current_exercise]
                    status["current_exercise"] = {
                        "id": web_analyzer.baduanjin_tracker.current_exercise,
                        "name": exercise_info["name"],
                        "phase": web_analyzer.baduanjin_tracker.current_phase,
                        "description": exercise_info["description"]
                    }
                
                return jsonify({"success": True, "status": status})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
        
        @app.route('/api/baduanjin/session-summary', methods=['GET'])
        def get_baduanjin_session_summary():
            """Get comprehensive session summary"""
            try:
                if not hasattr(web_analyzer, 'get_session_summary'):
                    return jsonify({"success": False, "error": "Enhanced analyzer not available"}), 500
                
                result = web_analyzer.get_session_summary()
                return jsonify(result)
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
        
        @app.route('/api/baduanjin/export', methods=['POST'])
        def export_baduanjin_session():
            """Export complete session data with exercise analytics"""
            try:
                if not hasattr(web_analyzer, 'export_session_data'):
                    return jsonify({"success": False, "error": "Enhanced analyzer not available"}), 500
                
                result = web_analyzer.export_session_data()
                return jsonify(result)
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

    # ==================== KEEP ALL YOUR EXISTING ENDPOINTS ====================
    # (pi-live, download, utility endpoints, etc. - they remain exactly the same)
    
    @app.route('/api/pi-live/start-session', methods=['POST'])
    def api_start_session():
        """Session start endpoint that Azure pi-service expects"""
        try:
            data = request.json or {}
            session_name = data.get('session_name', 'Live Practice Session')
            
            # This should just start streaming (Azure handles session management)
            success = web_analyzer.start_stream()
            
            if success:
                # Generate a session ID for Pi tracking
                session_id = f"pi_session_{int(time.time())}"
                web_analyzer.current_session = session_id
                
                return jsonify({
                    "success": True,
                    "session_id": session_id,
                    "message": "Pi streaming started for session",
                    "session_name": session_name,
                    "start_time": datetime.now().isoformat(),
                    "enhanced_tracking_available": ENHANCED_TRACKING_AVAILABLE  # 🚀 NEW
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "Failed to start Pi streaming"
                }), 500
                
        except Exception as e:
            print(f"❌ API start session error: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/pi-live/stop-session/<session_id>', methods=['POST'])
    def api_stop_session(session_id):
        """Session stop endpoint that Azure pi-service expects"""
        try:
            # 🚀 NEW: Auto-stop exercise tracking if enabled
            session_summary = {}
            if ENHANCED_TRACKING_AVAILABLE and hasattr(web_analyzer, 'disable_exercise_tracking') and getattr(web_analyzer, 'tracking_enabled', False):
                try:
                    tracking_summary = web_analyzer.disable_exercise_tracking()
                    session_summary["exercise_tracking"] = tracking_summary
                    print("🎯 Auto-stopped exercise tracking when session ended")
                except Exception as tracking_error:
                    print(f"⚠️ Error auto-stopping tracking: {tracking_error}")
                    session_summary["exercise_tracking_error"] = str(tracking_error)
            
            # Stop streaming and any recording
            web_analyzer.stop_stream()
            web_analyzer.current_session = None
            
            response_data = {
                "success": True,
                "message": "Pi session stopped successfully",
                "session_id": session_id
            }
            
            if session_summary:
                response_data["session_summary"] = session_summary
            
            return jsonify(response_data)
            
        except Exception as e:
            print(f"❌ API stop session error: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/pi-live/recording/start/<session_id>', methods=['POST'])
    def api_start_recording(session_id):
        """Recording start endpoint that Azure pi-service expects"""
        try:
            result = web_analyzer.start_recording()
            
            # 🚀 NEW: Add exercise tracking info if active
            if ENHANCED_TRACKING_AVAILABLE and getattr(web_analyzer, 'tracking_enabled', False):
                if hasattr(web_analyzer, 'baduanjin_tracker') and web_analyzer.baduanjin_tracker.current_exercise:
                    exercise_info = web_analyzer.baduanjin_tracker.exercises[web_analyzer.baduanjin_tracker.current_exercise]
                    result["exercise_tracking"] = {
                        "active": True,
                        "exercise_id": web_analyzer.baduanjin_tracker.current_exercise,
                        "exercise_name": exercise_info["name"],
                        "current_phase": web_analyzer.baduanjin_tracker.current_phase
                    }
                else:
                    result["exercise_tracking"] = {"active": False}
            
            return jsonify(result)
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/pi-live/recording/stop/<session_id>', methods=['POST'])  
    def api_stop_recording(session_id):
        """Recording stop endpoint that Azure pi-service expects"""
        try:
            result = web_analyzer.stop_recording()
            return jsonify(result)
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/pi-live/status')
    def api_get_status():
        """Status endpoint that Azure pi-service expects - ENHANCED"""
        base_status = {
            "pi_connected": CAMERA_AVAILABLE,
            "is_running": web_analyzer.is_running,
            "is_recording": web_analyzer.is_recording,
            "current_session": web_analyzer.current_session,
            "camera_available": CAMERA_AVAILABLE,
            "yolo_available": YOLO_AVAILABLE,
            "persons_detected": web_analyzer.session_stats.get('persons_detected', 0),
            "current_fps": web_analyzer.session_stats.get('current_fps', 0),
            "enhanced_tracking_available": ENHANCED_TRACKING_AVAILABLE  # 🚀 NEW
        }
        
        # 🚀 NEW: Add exercise tracking status
        if ENHANCED_TRACKING_AVAILABLE and hasattr(web_analyzer, 'baduanjin_tracker'):
            base_status["exercise_tracking"] = {
                "enabled": getattr(web_analyzer, 'tracking_enabled', False),
                "current_exercise": None
            }
            
            if getattr(web_analyzer, 'tracking_enabled', False) and web_analyzer.baduanjin_tracker.current_exercise:
                exercise_info = web_analyzer.baduanjin_tracker.exercises[web_analyzer.baduanjin_tracker.current_exercise]
                base_status["exercise_tracking"]["current_exercise"] = {
                    "id": web_analyzer.baduanjin_tracker.current_exercise,
                    "name": exercise_info["name"],
                    "phase": web_analyzer.baduanjin_tracker.current_phase
                }
        
        return jsonify(base_status)

    @app.route('/api/pi-live/current-pose')
    def api_get_current_pose():
        """Current pose endpoint that Azure pi-service expects"""
        return jsonify({
            "success": True,
            "pose_data": web_analyzer.pose_data,
            "timestamp": datetime.now().isoformat()
        })

    @app.route('/api/pi-live/recordings')
    def api_get_recordings():
        """Recordings endpoint that Azure pi-service expects"""
        try:
            recordings = web_analyzer.get_recordings_list()
            return jsonify({
                "success": True,
                "recordings": recordings,
                "count": len(recordings)
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e),
                "recordings": [],
                "count": 0
            }), 500

    # DOWNLOAD ENDPOINTS (keep all as-is)
    
    @app.route('/api/download/<filename>')
    def enhanced_download_recording(filename):
        """ENHANCED: Download with web version preference - REPLACES existing download"""
        try:
            print(f"📥 Download request for: {filename}")
            
            # NEW: Check if this is a request for original, but web version exists
            original_path = web_analyzer.recordings_dir / filename
            
            # Check for web version (prefer it for transfers)
            if not filename.endswith('_web.mp4'):
                stem = Path(filename).stem
                web_filename = f"{stem}_web.mp4"
                web_path = web_analyzer.recordings_dir / web_filename
                
                # If web version exists and is newer, suggest it
                if web_path.exists():
                    print(f"💡 Web version available: {web_filename}")
                    
                    # For Azure transfer, automatically serve web version
                    user_agent = request.headers.get('User-Agent', '')
                    if 'python-requests' in user_agent.lower() or 'main-backend' in user_agent.lower():
                        print(f"🔄 Auto-serving web version for transfer: {web_filename}")
                        filename = web_filename
                        original_path = web_path
            
            file_path = web_analyzer.recordings_dir / filename
            
            if not file_path.exists() or not file_path.is_file():
                return jsonify({"error": "File not found"}), 404
            
            if not filename.endswith('.mp4'):
                return jsonify({"error": "Invalid file type"}), 400
            
            file_size = file_path.stat().st_size
            print(f"✅ Serving: {filename} ({file_size} bytes)")
            
            # Send file with transfer-optimized headers
            response = send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='video/mp4'
            )
            
            # Add headers for Azure transfer compatibility
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Content-Length'] = str(file_size)
            response.headers['Accept-Ranges'] = 'bytes'
            response.headers['X-Web-Optimized'] = 'true' if '_web' in filename else 'false'
            response.headers['X-Enhanced-Tracking'] = 'true' if ENHANCED_TRACKING_AVAILABLE else 'false'  # 🚀 NEW
            
            return response
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # [KEEP ALL OTHER EXISTING ENDPOINTS - download-status, delete, current_frame, health, etc.]
    
    @app.route('/api/current_frame')
    def get_current_frame_improved():
        """Improved current frame endpoint - optimized for ngrok and mobile networks - ENHANCED"""
        try:
            # Add ngrok-skip-browser-warning header check
            ngrok_warning_skipped = request.headers.get('ngrok-skip-browser-warning') == 'true'
            if not ngrok_warning_skipped:
                print(f"⚠️ Request without ngrok-skip-browser-warning header from {request.remote_addr}")
            
            if not web_analyzer.is_running:
                return jsonify({
                    "success": False,
                    "error": "No active stream - stream not running",
                    "is_running": False,
                    "timestamp": int(time.time() * 1000)
                })
            
            if web_analyzer.current_frame is None:
                return jsonify({
                    "success": False,
                    "error": "No current frame available - stream just started", 
                    "is_running": True,
                    "timestamp": int(time.time() * 1000)
                })
            
            # Optimize image quality for mobile networks
            quality = Config.VIDEO_QUALITY  # 80% default
            if 'mobile' in request.headers.get('User-Agent', '').lower():
                quality = Config.MOBILE_VIDEO_QUALITY  # 50% for mobile
            
            # Encode current frame with mobile optimization
            _, buffer = cv2.imencode('.jpg', web_analyzer.current_frame, 
                                    [cv2.IMWRITE_JPEG_QUALITY, quality])
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            response_data = {
                "success": True,
                "image": frame_base64,
                "pose_data": web_analyzer.pose_data if web_analyzer.pose_data else [],
                "stats": web_analyzer.session_stats,
                "is_recording": web_analyzer.is_recording,
                "timestamp": int(time.time() * 1000),
                "frame_size": len(frame_base64),
                "quality": quality,
                "enhanced_tracking_available": ENHANCED_TRACKING_AVAILABLE  # 🚀 NEW
            }
            
            # 🚀 NEW: Add exercise feedback overlay data if tracking is active
            if ENHANCED_TRACKING_AVAILABLE and getattr(web_analyzer, 'tracking_enabled', False):
                if hasattr(web_analyzer, 'current_feedback') and web_analyzer.current_feedback:
                    response_data["exercise_feedback"] = {
                        "exercise_name": web_analyzer.current_feedback.exercise_name,
                        "current_phase": web_analyzer.current_feedback.current_phase,
                        "form_score": web_analyzer.current_feedback.form_score,
                        "completion_percentage": web_analyzer.current_feedback.completion_percentage,
                        "feedback_messages": web_analyzer.current_feedback.feedback_messages[:2],  # Top 2
                        "corrections": web_analyzer.current_feedback.corrections[:2]  # Top 2
                    }
            
            # Add headers for better caching and CORS
            response = jsonify(response_data)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            
            return response
            
        except Exception as e:
            error_msg = f"Error getting current frame: {str(e)}"
            print(f"❌ {error_msg}")
            return jsonify({
                "success": False,
                "error": error_msg,
                "is_running": getattr(web_analyzer, 'is_running', False),
                "timestamp": int(time.time() * 1000)
            }), 500

    @app.route('/api/health')
    def health_check():
        """Health check endpoint for ngrok and Azure service monitoring - ENHANCED"""
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "ngrok_compatible": True,
            "services": {
                "camera": CAMERA_AVAILABLE,
                "yolo": YOLO_AVAILABLE,
                "streaming": web_analyzer.is_running,
                "recording": web_analyzer.is_recording,
                "exercise_tracking": ENHANCED_TRACKING_AVAILABLE  # 🚀 NEW
            },
            "recordings_available": len(web_analyzer.get_recordings_list()),
            "server_info": {
                "version": "2.0",
                "mobile_optimized": True,
                "websocket_disabled": True,  # Using HTTP polling for ngrok
                "enhanced_baduanjin_tracking": ENHANCED_TRACKING_AVAILABLE  # 🚀 NEW
            }
        })

    # [KEEP ALL OTHER EXISTING ENDPOINTS - stats, ngrok_test, debug, convert, etc.]
    # I'm not duplicating them all here to save space, but they remain exactly the same

    # CORS PREFLIGHT HANDLER (keep exactly as-is)
    @app.before_request
    def handle_preflight():
        """Handle CORS preflight requests for Azure service compatibility"""
        if request.method == "OPTIONS":
            response = Response()
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, ngrok-skip-browser-warning'
            response.headers['Access-Control-Max-Age'] = '3600'
            return response

    return app

    @app.route('/api/pose_data', methods=['GET'])
    def get_pose_data():
        """Get current pose data (called by Azure service)"""
        try:
            return jsonify({
                "success": True,
                "pose_data": web_analyzer.pose_data if web_analyzer.pose_data else [],
                "timestamp": datetime.now().isoformat(),
                "stats": {
                    "current_fps": web_analyzer.session_stats.get('current_fps', 0),
                    "persons_detected": len(web_analyzer.pose_data) if web_analyzer.pose_data else 0,
                    "total_frames": web_analyzer.session_stats.get('total_frames', 0)
                }
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e),
                "pose_data": []
            }), 500