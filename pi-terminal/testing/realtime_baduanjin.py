#!/usr/bin/env python3
"""
Real-time Baduanjin Pose Analysis for Raspberry Pi 5
Adapted from refined Cell 9 with symmetry correction and skeleton visualization
Author: Adapted for Pi5 real-time processing
"""

import cv2
import numpy as np
import time
import os
import sys
from typing import List, Tuple, Optional

class RealTimeBaduanjinAnalyzer:
    """
    Real-time Baduanjin pose analysis using Pi Camera and YOLOv8
    """
    
    def __init__(self, model_size: str = 'n', camera_resolution: Tuple[int, int] = (640, 480)):
        """
        Initialize the real-time analyzer
        
        Args:
            model_size: YOLO model size ('n'=nano, 's'=small, 'm'=medium)
            camera_resolution: Camera resolution tuple (width, height)
        """
        print("🥋 Initializing Baduanjin Real-time Analyzer...")
        
        self.camera_resolution = camera_resolution
        self.model = None
        self.use_yolo = False
        
        # Import required modules
        self._import_modules()
        
        # Initialize camera
        self._setup_camera()
        
        # Initialize YOLO model
        self._setup_yolo_model(model_size)
        
        # Define COCO pose skeleton connections (from your refined Cell 9)
        self.skeleton_connections = [
            # Head connections
            (0, 1), (0, 2), (1, 3), (2, 4),
            # Torso connections  
            (5, 6), (5, 11), (6, 12), (11, 12),
            # Left arm connections
            (5, 7), (7, 9),
            # Right arm connections
            (6, 8), (8, 10),
            # Left leg connections
            (11, 13), (13, 15),
            # Right leg connections
            (12, 14), (14, 16)
        ]
        
        # Keypoint names for display (COCO format)
        self.keypoint_names = {
            0: "Nose", 1: "Left Eye", 2: "Right Eye", 3: "Left Ear", 4: "Right Ear",
            5: "Left Shoulder", 6: "Right Shoulder", 7: "Left Elbow", 8: "Right Elbow",
            9: "Left Wrist", 10: "Right Wrist", 11: "Left Hip", 12: "Right Hip",
            13: "Left Knee", 14: "Right Knee", 15: "Left Ankle", 16: "Right Ankle"
        }
        
        # Performance tracking
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0.0
        
        # Display options
        self.show_keypoint_numbers = True
        self.show_skeleton = True
        self.show_symmetry_line = True
        
        print("✅ Initialization complete!")
    
    def _import_modules(self):
        """Import required modules with error handling"""
        try:
            from picamera2 import Picamera2
            self.Picamera2 = Picamera2
            print("✅ picamera2 imported successfully")
        except ImportError as e:
            print(f"❌ picamera2 import failed: {e}")
            print("💡 Install with: sudo apt install python3-picamera2")
            sys.exit(1)
        
        try:
            from ultralytics import YOLO
            self.YOLO = YOLO
            print("✅ ultralytics imported successfully")
        except ImportError as e:
            print(f"⚠️ ultralytics not available: {e}")
            print("💡 Install with: pip3 install --user ultralytics")
            print("📷 Will run in camera-only mode")
            self.YOLO = None
    
    def _setup_camera(self):
        """Initialize and configure the Pi camera"""
        try:
            self.picam2 = self.Picamera2()
            
            # Configure camera for optimal Pi5 performance
            config = self.picam2.create_preview_configuration(
                main={"format": 'XRGB8888', "size": self.camera_resolution}
            )
            self.picam2.configure(config)
            
            print(f"✅ Camera configured: {self.camera_resolution[0]}x{self.camera_resolution[1]}")
            
        except Exception as e:
            print(f"❌ Camera setup failed: {e}")
            sys.exit(1)
    
    def _setup_yolo_model(self, model_size: str):
        """Initialize YOLO model if available"""
        if self.YOLO is None:
            return
            
        try:
            model_name = f'yolov8{model_size}-pose.pt'
            print(f"🧠 Loading {model_name}...")
            
            self.model = self.YOLO(model_name)
            self.use_yolo = True
            
            print(f"✅ YOLOv8{model_size}-pose model loaded successfully")
            
        except Exception as e:
            print(f"⚠️ YOLO model loading failed: {e}")
            print("📷 Continuing in camera-only mode")
            self.model = None
            self.use_yolo = False
    
    def apply_symmetry_correction(self, keypoints: np.ndarray, confidences: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply symmetry correction using shoulder midpoint (from your Cell 9)
        
        Args:
            keypoints: Array of keypoint coordinates [17, 2]
            confidences: Array of confidence scores [17]
            
        Returns:
            Tuple of corrected keypoints and confidences
        """
        if len(keypoints) == 0:
            return keypoints, confidences
            
        # Keypoint indices (COCO format)
        left_shoulder_idx = 5
        right_shoulder_idx = 6
        
        # Calculate symmetry axis using shoulders
        if confidences[left_shoulder_idx] > 0.5 and confidences[right_shoulder_idx] > 0.5:
            x_sym = (keypoints[left_shoulder_idx, 0] + keypoints[right_shoulder_idx, 0]) / 2
            
            # Enhanced symmetry correction for multiple joint pairs (from your Cell 9)
            symmetric_pairs = [
                (9, 10),   # left_wrist, right_wrist
                (7, 8),    # left_elbow, right_elbow  
                (13, 14),  # left_knee, right_knee
                (15, 16),  # left_ankle, right_ankle
            ]
            
            corrected_kpts = keypoints.copy()
            
            for left_idx, right_idx in symmetric_pairs:
                c_l, c_r = confidences[left_idx], confidences[right_idx]
                p_l, p_r = keypoints[left_idx], keypoints[right_idx]
                
                # Adjust joints based on confidence (from your Cell 9)
                if c_l > 0.5 and c_r < 0.5:
                    # Adjust right joint using left joint symmetry
                    p_r_sym = np.array([2 * x_sym - p_l[0], p_l[1]])
                    alpha = c_r / (c_l + c_r) if c_l + c_r > 0 else 0
                    corrected_kpts[right_idx] = alpha * p_r + (1 - alpha) * p_r_sym
                    
                elif c_r > 0.5 and c_l < 0.5:
                    # Adjust left joint using right joint symmetry
                    p_l_sym = np.array([2 * x_sym - p_r[0], p_r[1]])
                    alpha = c_l / (c_r + c_l) if c_r + c_l > 0 else 0
                    corrected_kpts[left_idx] = alpha * p_l + (1 - alpha) * p_l_sym
            
            return corrected_kpts, confidences
        
        return keypoints, confidences
    
    def draw_pose(self, frame: np.ndarray, keypoints: np.ndarray, confidences: np.ndarray) -> np.ndarray:
        """
        Draw pose with skeleton and keypoints (from your refined Cell 9)
        
        Args:
            frame: Input frame
            keypoints: Keypoint coordinates [17, 2]  
            confidences: Confidence scores [17]
            
        Returns:
            Frame with pose visualization
        """
        # Draw keypoints with color coding (from your Cell 9)
        for i, (x, y) in enumerate(keypoints):
            if confidences[i] > 0.5:  # Only draw high-confidence keypoints
                # Color-code keypoints by body part (from your Cell 9)
                if i in [0, 1, 2, 3, 4]:  # Head keypoints
                    color = (255, 255, 0)  # Cyan for head
                elif i in [5, 6, 7, 8, 9, 10]:  # Upper body
                    color = (0, 255, 0)  # Green for upper body
                else:  # Lower body
                    color = (255, 0, 0)  # Blue for lower body
                    
                cv2.circle(frame, (int(x), int(y)), 6, color, -1)
                
                # Add keypoint index numbers (from your Cell 9)
                if self.show_keypoint_numbers:
                    cv2.putText(frame, str(i), (int(x)+8, int(y)), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
        
        # Draw skeleton connections (from your Cell 9)
        if self.show_skeleton:
            for connection in self.skeleton_connections:
                pt1_idx, pt2_idx = connection
                
                # Check if both keypoints are detected with sufficient confidence
                if confidences[pt1_idx] > 0.5 and confidences[pt2_idx] > 0.5:
                    pt1 = keypoints[pt1_idx]
                    pt2 = keypoints[pt2_idx]
                    
                    # Ensure coordinates are valid
                    if pt1[0] > 0 and pt1[1] > 0 and pt2[0] > 0 and pt2[1] > 0:
                        # Draw line between connected keypoints (red lines, from your Cell 9)
                        cv2.line(frame, 
                               (int(pt1[0]), int(pt1[1])), 
                               (int(pt2[0]), int(pt2[1])), 
                               (0, 0, 255), 3)  # Red lines for skeleton
        
        # Draw symmetry line (optional - helps visualize the symmetry axis)
        if self.show_symmetry_line:
            left_shoulder_idx = 5
            right_shoulder_idx = 6
            if confidences[left_shoulder_idx] > 0.5 and confidences[right_shoulder_idx] > 0.5:
                x_sym = (keypoints[left_shoulder_idx, 0] + keypoints[right_shoulder_idx, 0]) / 2
                cv2.line(frame, 
                       (int(x_sym), 0), 
                       (int(x_sym), frame.shape[0]), 
                       (255, 255, 255), 1)  # White symmetry line
        
        return frame
    
    def process_frame(self, frame: np.ndarray) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        Process frame for pose detection with Pi5 optimizations
        
        Args:
            frame: Input frame in BGR format
            
        Returns:
            List of (keypoints, confidences) tuples for each detected person
        """
        if not self.use_yolo:
            return []
            
        # Resize for better performance on Pi5 (maintain aspect ratio)
        height, width = frame.shape[:2]
        target_size = 416  # Optimal for YOLOv8
        scale = min(target_size/width, target_size/height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        frame_small = cv2.resize(frame, (new_width, new_height))
        
        # Run YOLO inference with Pi5 optimizations
        try:
            results = self.model(
                frame_small, 
                conf=0.5,      # Confidence threshold
                iou=0.7,       # NMS threshold
                verbose=False, # Reduce console output
                device='cpu'   # Explicit CPU for Pi5
            )
            
            processed_data = []
            
            for result in results:
                if result.keypoints is not None:
                    keypoints = result.keypoints.xy.cpu().numpy()
                    confidences = result.keypoints.conf.cpu().numpy()
                    
                    # Scale back to original frame size
                    scale_x = width / new_width
                    scale_y = height / new_height
                    
                    for person_idx in range(keypoints.shape[0]):
                        person_kpts = keypoints[person_idx] * [scale_x, scale_y]
                        person_confs = confidences[person_idx]
                        
                        # Apply symmetry correction (your Cell 9 logic)
                        corrected_kpts, corrected_confs = self.apply_symmetry_correction(
                            person_kpts, person_confs
                        )
                        
                        processed_data.append((corrected_kpts, corrected_confs))
            
            return processed_data
            
        except Exception as e:
            print(f"⚠️ Pose processing error: {e}")
            return []
    
    def calculate_fps(self) -> float:
        """Calculate and return current FPS"""
        self.fps_counter += 1
        if self.fps_counter % 30 == 0:  # Update every 30 frames
            elapsed = time.time() - self.fps_start_time
            self.current_fps = 30 / elapsed
            self.fps_start_time = time.time()
        return self.current_fps
    
    def draw_info_overlay(self, frame: np.ndarray, pose_data: List, fps: float) -> np.ndarray:
        """Draw information overlay on frame"""
        height, width = frame.shape[:2]
        
        # Title
        cv2.putText(frame, 'Baduanjin Real-time Analysis', (10, 30), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        
        # FPS
        cv2.putText(frame, f'FPS: {fps:.1f}', (10, 60), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Person count
        cv2.putText(frame, f'Persons: {len(pose_data)}', (10, 85), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Mode indicator
        mode_text = "YOLO Active" if self.use_yolo else "Camera Only"
        mode_color = (0, 255, 0) if self.use_yolo else (0, 255, 255)
        cv2.putText(frame, f'Mode: {mode_text}', (10, 110), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, mode_color, 2)
        
        # Controls (bottom of screen)
        controls_y = height - 40
        cv2.putText(frame, "Controls: Q=Quit | S=Save | F=FPS | N=Numbers | K=Skeleton | L=Symmetry", 
                  (10, controls_y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        cv2.putText(frame, "Made for Baduanjin Traditional Exercise Analysis", 
                  (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        return frame
    
    def save_screenshot(self, frame: np.ndarray) -> str:
        """Save screenshot with timestamp"""
        timestamp = int(time.time())
        filename = f'baduanjin_capture_{timestamp}.jpg'
        cv2.imwrite(filename, frame)
        return filename
    
    def start_analysis(self):
        """Main real-time analysis loop"""
        print("\n" + "="*60)
        print("🥋 BADUANJIN REAL-TIME ANALYSIS STARTED 🥋")
        print("="*60)
        print("📹 Camera Resolution:", f"{self.camera_resolution[0]}x{self.camera_resolution[1]}")
        print("🧠 YOLO Status:", "Active" if self.use_yolo else "Disabled")
        print("🎮 Controls:")
        print("  'q' - Quit analysis")
        print("  's' - Save screenshot") 
        print("  'f' - Toggle FPS display")
        print("  'n' - Toggle keypoint numbers")
        print("  'k' - Toggle skeleton lines")
        print("  'l' - Toggle symmetry line")
        print("="*60)
        
        # Start camera
        self.picam2.start()
        
        # Display flags
        show_fps = True
        
        try:
            while True:
                # Capture frame from Pi camera
                frame = self.picam2.capture_array()
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Process pose detection
                pose_data = self.process_frame(frame_bgr)
                
                # Draw pose detection results
                for keypoints, confidences in pose_data:
                    frame_bgr = self.draw_pose(frame_bgr, keypoints, confidences)
                
                # Calculate FPS
                fps = self.calculate_fps()
                
                # Draw information overlay
                if show_fps:
                    frame_bgr = self.draw_info_overlay(frame_bgr, pose_data, fps)
                
                # Display frame
                cv2.imshow('Baduanjin Real-time Analysis', frame_bgr)
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("🛑 Quitting analysis...")
                    break
                elif key == ord('s'):
                    filename = self.save_screenshot(frame_bgr)
                    print(f"📸 Screenshot saved: {filename}")
                elif key == ord('f'):
                    show_fps = not show_fps
                    print(f"📊 FPS display: {'ON' if show_fps else 'OFF'}")
                elif key == ord('n'):
                    self.show_keypoint_numbers = not self.show_keypoint_numbers
                    print(f"🔢 Keypoint numbers: {'ON' if self.show_keypoint_numbers else 'OFF'}")
                elif key == ord('k'):
                    self.show_skeleton = not self.show_skeleton
                    print(f"🦴 Skeleton lines: {'ON' if self.show_skeleton else 'OFF'}")
                elif key == ord('l'):
                    self.show_symmetry_line = not self.show_symmetry_line
                    print(f"📏 Symmetry line: {'ON' if self.show_symmetry_line else 'OFF'}")
                
        except KeyboardInterrupt:
            print("\n🛑 Analysis stopped by user (Ctrl+C)")
        
        except Exception as e:
            print(f"\n❌ Error during analysis: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            # Cleanup
            try:
                self.picam2.stop()
                cv2.destroyAllWindows()
                print("✅ Camera and display cleaned up")
            except:
                pass
            
            print("🏁 Analysis session completed")


def main():
    """Main function to run the analyzer"""
    print("🥋 Baduanjin Real-time Pose Analysis for Raspberry Pi 5")
    print("🎯 Adapted from refined Cell 9 with symmetry correction")
    print("🔬 Compatible with NoIR Camera Module v3")
    print()
    
    # Display system information
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if 'Model' in line:
                    print(f"🖥️  Hardware: {line.split(':')[1].strip()}")
                    break
    except:
        pass
    
    try:
        import psutil
        print(f"💾 Memory: {psutil.virtual_memory().total / (1024**3):.1f} GB")
    except:
        pass
    
    print()
    
    # Initialize and start analyzer
    try:
        # You can modify these parameters:
        # model_size: 'n' (nano), 's' (small), 'm' (medium) 
        # camera_resolution: (width, height)
        analyzer = RealTimeBaduanjinAnalyzer(
            model_size='n',  # Start with nano for best Pi5 performance
            camera_resolution=(640, 480)  # Good balance of quality and speed
        )
        
        analyzer.start_analysis()
        
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Failed to start analysis: {e}")
        print("💡 Make sure:")
        print("   - Camera is connected and not in use")
        print("   - Required packages are installed")
        print("   - You have sufficient permissions")


if __name__ == "__main__":
    main()