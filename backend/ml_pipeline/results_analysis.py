# ml_pipeline/results_analysis.py
# MMPose 1.3.2 JSON format compatibility - UPDATED VERSION
# type: ignore

import os
import numpy as np
import matplotlib.pyplot as plt
import json
import pandas as pd
from scipy.signal import savgol_filter
from scipy.spatial.distance import euclidean
import cv2
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D
import math
from sklearn.cluster import KMeans
import warnings

# Suppress sklearn warnings for cleaner output
warnings.filterwarnings('ignore', category=UserWarning)

class BaduanjinAnalyzer:
    def __init__(self, json_path, video_path=None):
        """
        Initialize the analyzer with path to pose estimation results
        
        Args:
            json_path: Path to the MMPose JSON results file
            video_path: Optional path to the original video for visualization
        """
        self.json_path = json_path
        self.video_path = video_path
        
        # Define keypoint mapping from index to human-readable names (COCO format)
        self.keypoint_mapping = {
            0: "Nose",
            1: "Left Eye", 
            2: "Right Eye",
            3: "Left Ear",
            4: "Right Ear",
            5: "Left Shoulder",
            6: "Right Shoulder", 
            7: "Left Elbow",
            8: "Right Elbow",
            9: "Left Wrist",
            10: "Right Wrist",
            11: "Left Hip",
            12: "Right Hip",
            13: "Left Knee", 
            14: "Right Knee",
            15: "Left Ankle",
            16: "Right Ankle"
        }
        
        # Load and validate pose estimation results
        print(f"Loading MMPose 1.3.2 results from: {json_path}")
        try:
            with open(json_path, 'r') as f:
                self.pose_data = json.load(f)
            print("✓ JSON file loaded successfully")
        except Exception as e:
            raise ValueError(f"Failed to load JSON file: {e}")
        
        # Validate JSON structure for MMPose 1.3.2
        self._validate_json_structure()
        
        # Extract metadata and pose keypoints (MMPose 1.3.2 format)
        self.meta_info = self.pose_data.get('meta_info', {})
        self.instance_info = self.pose_data.get('instance_info', [])
        
        # Get keypoint information
        self.keypoint_names = self.meta_info.get('keypoint_info', {})
        self.skeleton_info = self.meta_info.get('skeleton_info', {})
        
        print(f"✓ Found {len(self.instance_info)} frames in JSON data")
        print(f"✓ Dataset: {self.meta_info.get('dataset_name', 'unknown')}")
        
        # Store processed data
        self.joint_angles = {}
        self.trajectories = {}
        self.movement_segments = []
        self.balance_metrics = {}
        
        # Process data
        self._preprocess_pose_data()
    
    def _validate_json_structure(self):
        """Validate that the JSON has the expected MMPose 1.3.2 structure"""
        required_keys = ['meta_info', 'instance_info']
        
        for key in required_keys:
            if key not in self.pose_data:
                raise ValueError(f"Missing required key '{key}' in JSON. This may not be a valid MMPose 1.3.2 output file.")
        
        if not isinstance(self.pose_data['instance_info'], list):
            raise ValueError("'instance_info' should be a list of frame data")
        
        if len(self.pose_data['instance_info']) == 0:
            raise ValueError("No frame data found in 'instance_info'")
        
        # Check first frame structure
        first_frame = self.pose_data['instance_info'][0]
        if 'frame_id' not in first_frame:
            print("Warning: 'frame_id' not found in frame data, will use sequential numbering")
        
        if 'instances' not in first_frame:
            raise ValueError("No 'instances' found in frame data. Invalid MMPose 1.3.2 format.")
        
        print("✓ JSON structure validation passed")
    
    def _get_keypoint_name(self, keypoint_id):
        """Convert keypoint_X format to human-readable name"""
        if isinstance(keypoint_id, str) and keypoint_id.startswith('keypoint_'):
            try:
                idx = int(keypoint_id.split('_')[1])
                return self.keypoint_mapping.get(idx, keypoint_id)
            except (IndexError, ValueError):
                return keypoint_id
        elif isinstance(keypoint_id, int):
            return self.keypoint_mapping.get(keypoint_id, f"keypoint_{keypoint_id}")
        return keypoint_id
    
    def _preprocess_pose_data(self):
        """Extract keypoints for each frame and create clean data structures - MMPose 1.3.2 compatible"""
        all_frame_data = []
        processed_frames = 0
        skipped_frames = 0
        
        print(f"Processing {len(self.instance_info)} frames from MMPose 1.3.2 JSON...")
        
        for frame_idx, frame_data in enumerate(self.instance_info):
            try:
                # Get frame ID (use index if not available)
                frame_id = frame_data.get('frame_id', frame_idx + 1)
                instances = frame_data.get('instances', [])
                
                if not instances:
                    print(f"Warning: No instances found in frame {frame_id}")
                    skipped_frames += 1
                    continue
                
                # Get the best person instance (highest average keypoint confidence)
                best_instance = None
                best_confidence = -1
                
                for instance in instances:
                    keypoints = instance.get('keypoints', [])
                    scores = instance.get('keypoint_scores', [])
                    
                    if not keypoints or not scores:
                        continue
                    
                    # Calculate average confidence for this instance
                    valid_scores = [s for s in scores if s > 0]
                    if valid_scores:
                        avg_confidence = np.mean(valid_scores)
                        if avg_confidence > best_confidence:
                            best_confidence = avg_confidence
                            best_instance = instance
                
                if best_instance is None:
                    print(f"Warning: No valid instances in frame {frame_id}")
                    skipped_frames += 1
                    continue
                
                # Extract keypoints and scores from best instance
                keypoints = best_instance.get('keypoints', [])
                scores = best_instance.get('keypoint_scores', [])
                
                # Validate keypoints format
                if not self._validate_keypoints_format(keypoints, scores):
                    print(f"Warning: Invalid keypoints format in frame {frame_id}")
                    skipped_frames += 1
                    continue
                
                # Create frame dictionary
                frame_dict = {'frame_id': frame_id}
                
                # Process each keypoint (expecting 17 COCO keypoints)
                for i in range(min(len(keypoints), 17)):  # Limit to 17 COCO keypoints
                    try:
                        # Handle different keypoint formats
                        if isinstance(keypoints[i], (list, tuple)) and len(keypoints[i]) >= 2:
                            kpt_x, kpt_y = float(keypoints[i][0]), float(keypoints[i][1])
                        else:
                            print(f"Warning: Invalid keypoint format at index {i} in frame {frame_id}")
                            continue
                        
                        # Get confidence score
                        kpt_score = float(scores[i]) if i < len(scores) else 0.0
                        
                        # Store in expected format: [x, y, score]
                        kpt_name = f"keypoint_{i}"
                        frame_dict[kpt_name] = [kpt_x, kpt_y, kpt_score]
                        
                    except (IndexError, ValueError, TypeError) as e:
                        print(f"Warning: Error processing keypoint {i} in frame {frame_id}: {e}")
                        continue
                
                # Only add frame if we have at least some valid keypoints
                if len(frame_dict) > 1:  # More than just frame_id
                    all_frame_data.append(frame_dict)
                    processed_frames += 1
                else:
                    skipped_frames += 1
                    
            except Exception as e:
                print(f"Error processing frame {frame_idx}: {e}")
                skipped_frames += 1
                continue
        
        print(f"✓ Processed {processed_frames} frames successfully")
        if skipped_frames > 0:
            print(f"⚠ Skipped {skipped_frames} frames due to issues")
        
        # Create pandas DataFrame
        if all_frame_data:
            self.pose_df = pd.DataFrame(all_frame_data)
            self.pose_df.set_index('frame_id', inplace=True)
            print(f"✓ Created DataFrame with {len(self.pose_df)} frames and {len(self.pose_df.columns)} keypoints")
            
            # Print sample keypoints for debugging
            sample_keypoints = list(self.pose_df.columns)[:5]
            print(f"✓ Sample keypoints: {sample_keypoints}")
            
        else:
            raise ValueError("No valid pose data found in the JSON file. Check the file format and content.")
        
        # Apply smoothing to trajectories
        self._smooth_trajectories()
    
    def _validate_keypoints_format(self, keypoints, scores):
        """Validate that keypoints and scores have the expected format"""
        if not keypoints or not scores:
            return False
        
        if len(keypoints) != len(scores):
            print(f"Warning: Keypoints ({len(keypoints)}) and scores ({len(scores)}) length mismatch")
        
        # Check if keypoints are in the expected format
        try:
            for i, kpt in enumerate(keypoints[:3]):  # Check first 3 keypoints
                if isinstance(kpt, (list, tuple)) and len(kpt) >= 2:
                    float(kpt[0])  # x coordinate
                    float(kpt[1])  # y coordinate
                else:
                    return False
            return True
        except (ValueError, TypeError, IndexError):
            return False
    
    def _smooth_trajectories(self, window_length=15, poly_order=3):
        """Apply smoothing to keypoint trajectories to reduce noise - MMPose 1.3.2 compatible"""
        if self.pose_df.empty:
            print("No data to smooth")
            return
        
        print("Applying trajectory smoothing...")
        self.smoothed_data = {}
        
        # Get all keypoint columns
        keypoint_columns = [col for col in self.pose_df.columns if col.startswith('keypoint_')]
        
        for kpt in keypoint_columns:
            try:
                # Extract trajectory data
                n_frames = len(self.pose_df)
                x_values = np.zeros(n_frames)
                y_values = np.zeros(n_frames)
                scores = np.zeros(n_frames)
                
                for i, idx in enumerate(self.pose_df.index):
                    kpt_data = self.pose_df.loc[idx, kpt]
                    if isinstance(kpt_data, (list, tuple)) and len(kpt_data) >= 3:
                        x_values[i] = float(kpt_data[0])
                        y_values[i] = float(kpt_data[1])
                        scores[i] = float(kpt_data[2])
                    else:
                        # Handle missing or invalid data
                        x_values[i] = 0.0
                        y_values[i] = 0.0
                        scores[i] = 0.0
                
                # Apply smoothing if we have enough frames and the window is appropriate
                if n_frames > window_length and window_length % 2 == 1:  # Window must be odd
                    try:
                        # Only smooth points with reasonable confidence
                        valid_mask = scores > 0.3
                        
                        if np.sum(valid_mask) > window_length:
                            # Apply smoothing only to valid points, then interpolate
                            x_smooth = x_values.copy()
                            y_smooth = y_values.copy()
                            
                            if np.sum(valid_mask) > window_length:
                                x_smooth[valid_mask] = savgol_filter(x_values[valid_mask], 
                                                                   min(window_length, np.sum(valid_mask)), 
                                                                   poly_order)
                                y_smooth[valid_mask] = savgol_filter(y_values[valid_mask], 
                                                                   min(window_length, np.sum(valid_mask)), 
                                                                   poly_order)
                        else:
                            x_smooth = x_values
                            y_smooth = y_values
                    except Exception as e:
                        print(f"Warning: Smoothing failed for {kpt}: {e}")
                        x_smooth = x_values
                        y_smooth = y_values
                else:
                    x_smooth = x_values
                    y_smooth = y_values
                
                # Store smoothed data
                self.smoothed_data[kpt] = {
                    'x': x_smooth,
                    'y': y_smooth,
                    'score': scores
                }
                
            except Exception as e:
                print(f"Error processing keypoint {kpt}: {e}")
                continue
        
        print(f"✓ Smoothed trajectory data for {len(self.smoothed_data)} keypoints")

    def print_keypoint_info(self):
        """Print information about available keypoints to help with debugging"""
        print("\n=== Keypoint Information ===")
        print(f"Available keypoints: {list(self.smoothed_data.keys())}")
        
        if self.smoothed_data:
            sample_key = list(self.smoothed_data.keys())[0]
            sample_data = self.smoothed_data[sample_key]
            print(f"\nSample data for '{sample_key}':")
            print(f"  X values (first 5): {sample_data['x'][:5]}")
            print(f"  Y values (first 5): {sample_data['y'][:5]}")
            print(f"  Confidence scores (first 5): {sample_data['score'][:5]}")
            print(f"  Average confidence: {np.mean(sample_data['score']):.3f}")
        print("============================\n")
    
    def calculate_joint_angles(self):
        """Calculate important joint angles for Baduanjin analysis - MMPose 1.3.2 compatible"""
        print("Calculating joint angles...")
        self.print_keypoint_info()
        
        # Define angle mappings using COCO keypoint indices
        angle_definitions = {
            'Right Elbow': ['keypoint_6', 'keypoint_8', 'keypoint_10'],  # shoulder->elbow->wrist
            'Left Elbow': ['keypoint_5', 'keypoint_7', 'keypoint_9'],
            'Right Shoulder': ['keypoint_8', 'keypoint_6', 'keypoint_12'],  # elbow->shoulder->hip
            'Left Shoulder': ['keypoint_7', 'keypoint_5', 'keypoint_11'],
            'Right Hip': ['keypoint_6', 'keypoint_12', 'keypoint_14'],  # shoulder->hip->knee
            'Left Hip': ['keypoint_5', 'keypoint_11', 'keypoint_13'],
            'Right Knee': ['keypoint_12', 'keypoint_14', 'keypoint_16'],  # hip->knee->ankle
            'Left Knee': ['keypoint_11', 'keypoint_13', 'keypoint_15'],
            'Spine Top': ['keypoint_0', 'keypoint_5', 'keypoint_11'],  # nose->left_shoulder->left_hip
            'Spine Bottom': ['keypoint_5', 'keypoint_11', 'keypoint_12']  # left_shoulder->left_hip->right_hip
        }
        
        print(f"Calculating {len(angle_definitions)} joint angles...")
        
        # Initialize angle data storage
        angle_data = {angle_name: [] for angle_name in angle_definitions}
        frames = self.pose_df.index.tolist()
        successful_calculations = {angle_name: 0 for angle_name in angle_definitions}
        
        for frame_idx in range(len(frames)):
            for angle_name, (p1, p2, p3) in angle_definitions.items():
                try:
                    # Check if all required keypoints exist
                    if not all(p in self.smoothed_data for p in [p1, p2, p3]):
                        angle_data[angle_name].append(np.nan)
                        continue
                    
                    # Get keypoint coordinates and confidence scores
                    p1_data = self.smoothed_data[p1]
                    p2_data = self.smoothed_data[p2]
                    p3_data = self.smoothed_data[p3]
                    
                    # Check confidence scores
                    p1_conf = p1_data['score'][frame_idx]
                    p2_conf = p2_data['score'][frame_idx]
                    p3_conf = p3_data['score'][frame_idx]
                    
                    # Skip if any keypoint has low confidence
                    if min(p1_conf, p2_conf, p3_conf) < 0.3:
                        angle_data[angle_name].append(np.nan)
                        continue
                    
                    # Get coordinates
                    p1_coords = np.array([p1_data['x'][frame_idx], p1_data['y'][frame_idx]])
                    p2_coords = np.array([p2_data['x'][frame_idx], p2_data['y'][frame_idx]])
                    p3_coords = np.array([p3_data['x'][frame_idx], p3_data['y'][frame_idx]])
                    
                    # Calculate vectors from the middle point
                    v1 = p1_coords - p2_coords
                    v2 = p3_coords - p2_coords
                    
                    # Calculate angle
                    dot_product = np.dot(v1, v2)
                    norms = np.linalg.norm(v1) * np.linalg.norm(v2)
                    
                    if norms < 1e-6:
                        angle_data[angle_name].append(np.nan)
                        continue
                    
                    cos_angle = np.clip(dot_product / norms, -1.0, 1.0)
                    angle = np.degrees(np.arccos(cos_angle))
                    
                    angle_data[angle_name].append(angle)
                    successful_calculations[angle_name] += 1
                    
                except Exception as e:
                    angle_data[angle_name].append(np.nan)
                    continue
        
        # Create DataFrame
        self.joint_angles = pd.DataFrame(angle_data, index=frames)
        
        print(f"✓ Joint angle calculation completed")
        for angle_name, count in successful_calculations.items():
            success_rate = (count / len(frames)) * 100
            print(f"  {angle_name}: {count}/{len(frames)} frames ({success_rate:.1f}%)")
        
        return self.joint_angles
    
    def identify_key_poses(self, n_poses=8):
        """Identify key poses in the Baduanjin sequence using clustering - MMPose 1.3.2 compatible"""
        print(f"Identifying {n_poses} key poses...")
        
        # Ensure joint angles are calculated
        if not hasattr(self, 'joint_angles') or self.joint_angles.empty:
            self.calculate_joint_angles()
        
        # Prepare data for clustering
        angles_data = self.joint_angles.copy()
        
        # Remove columns with too many NaN values
        nan_ratios = angles_data.isna().mean()
        good_columns = nan_ratios[nan_ratios < 0.7].index.tolist()  # Allow up to 70% NaN
        
        if not good_columns:
            print("Warning: All joint angles have too many NaN values. Using all columns.")
            good_columns = angles_data.columns.tolist()
        
        print(f"Using {len(good_columns)} joint angles for clustering")
        angles_data = angles_data[good_columns]
        
        # Fill NaN values with column medians
        for col in angles_data.columns:
            median_val = angles_data[col].median()
            if pd.isna(median_val):
                median_val = 90.0  # Default angle
            angles_data[col] = angles_data[col].fillna(median_val)
        
        # Normalize data for better clustering
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        angles_normalized = scaler.fit_transform(angles_data)
        
        # Apply K-means clustering
        try:
            kmeans = KMeans(n_clusters=n_poses, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(angles_normalized)
            
            # Find representative frames for each cluster
            key_frames = []
            for i in range(n_poses):
                cluster_mask = clusters == i
                if np.sum(cluster_mask) == 0:
                    continue
                
                cluster_indices = np.where(cluster_mask)[0]
                center = kmeans.cluster_centers_[i]
                
                # Find frame closest to cluster center
                distances = []
                for idx in cluster_indices:
                    dist = np.linalg.norm(angles_normalized[idx] - center)
                    distances.append((angles_data.index[idx], dist))
                
                distances.sort(key=lambda x: x[1])
                key_frames.append((distances[0][0], i))
            
            # Sort by frame number
            key_frames.sort()
            self.key_frames = key_frames
            
            print(f"✓ Identified {len(key_frames)} key poses:")
            for i, (frame_id, cluster_id) in enumerate(key_frames):
                print(f"  Pose {i+1}: Frame {frame_id} (Cluster {cluster_id})")
            
        except Exception as e:
            print(f"Error in pose clustering: {e}")
            # Fallback: use evenly spaced frames
            frame_indices = np.linspace(0, len(angles_data)-1, n_poses, dtype=int)
            self.key_frames = [(angles_data.index[i], i) for i in frame_indices]
            print(f"✓ Using evenly spaced frames as key poses")
        
        return self.key_frames
    
    def visualize_key_poses(self, output_path="key_poses.png", figsize=(20, 10)):
        """Visualize the key poses - MMPose 1.3.2 compatible"""
        print(f"Creating key poses visualization...")
        
        if not hasattr(self, 'key_frames'):
            self.identify_key_poses()
        
        plt.figure(figsize=figsize)
        
        # If video is available, extract frames
        if self.video_path and os.path.exists(self.video_path):
            try:
                cap = cv2.VideoCapture(self.video_path)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                
                for i, (frame_idx, cluster_idx) in enumerate(self.key_frames[:8]):
                    # Convert frame_idx to video frame number if needed
                    video_frame = min(int(frame_idx), total_frames - 1)
                    
                    cap.set(cv2.CAP_PROP_POS_FRAMES, video_frame)
                    ret, frame = cap.read()
                    
                    if ret:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        
                        plt.subplot(2, 4, i+1)
                        plt.imshow(frame_rgb)
                        plt.title(f"Pose {i+1}\nFrame {frame_idx}", fontsize=12)
                        plt.axis('off')
                    else:
                        # Create placeholder if frame can't be read
                        plt.subplot(2, 4, i+1)
                        plt.text(0.5, 0.5, f"Pose {i+1}\nFrame {frame_idx}\n(Frame not available)", 
                                ha='center', va='center', transform=plt.gca().transAxes)
                        plt.axis('off')
                
                cap.release()
                
            except Exception as e:
                print(f"Error extracting video frames: {e}")
                # Fall back to text-based visualization
                self._create_text_pose_visualization(figsize)
        else:
            # Create text-based visualization
            self._create_text_pose_visualization(figsize)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Key poses visualization saved to {output_path}")
        return output_path
    
    def _create_text_pose_visualization(self, figsize):
        """Create text-based pose visualization when video is not available"""
        for i, (frame_idx, cluster_idx) in enumerate(self.key_frames[:8]):
            plt.subplot(2, 4, i+1)
            
            # Main pose info
            plt.text(0.5, 0.7, f"Pose {i+1}", ha='center', va='center', 
                    fontsize=16, fontweight='bold', transform=plt.gca().transAxes)
            plt.text(0.5, 0.5, f"Frame {frame_idx}", ha='center', va='center', 
                    fontsize=12, transform=plt.gca().transAxes)
            
            # Add joint angle information if available
            if hasattr(self, 'joint_angles') and frame_idx in self.joint_angles.index:
                angles = self.joint_angles.loc[frame_idx]
                valid_angles = angles.dropna()
                
                if len(valid_angles) > 0:
                    angle_text = []
                    for angle_name, angle_value in valid_angles.head(3).items():
                        angle_text.append(f"{angle_name}: {angle_value:.0f}°")
                    
                    plt.text(0.5, 0.2, '\n'.join(angle_text), ha='center', va='center', 
                            fontsize=8, transform=plt.gca().transAxes)
            
            plt.axis('off')
    
    def analyze_movement_smoothness(self):
        """Calculate movement smoothness metrics - MMPose 1.3.2 compatible"""
        print("Analyzing movement smoothness...")
        
        # Key joints for smoothness analysis
        key_joints = ['keypoint_9', 'keypoint_10', 'keypoint_15', 'keypoint_16']  # wrists and ankles
        jerk_metrics = {}
        
        for joint in key_joints:
            if joint not in self.smoothed_data:
                continue
            
            try:
                joint_data = self.smoothed_data[joint]
                
                # Check average confidence
                avg_confidence = np.mean(joint_data['score'])
                if avg_confidence < 0.4:
                    print(f"  Skipping {joint} (low confidence: {avg_confidence:.2f})")
                    continue
                
                # Get position data
                x_vals = np.array(joint_data['x'])
                y_vals = np.array(joint_data['y'])
                
                # Calculate jerk (third derivative of position)
                positions = np.column_stack((x_vals, y_vals))
                velocities = np.diff(positions, axis=0)
                accelerations = np.diff(velocities, axis=0)
                jerk = np.diff(accelerations, axis=0)
                
                # Calculate jerk magnitude
                jerk_magnitude = np.sqrt(jerk[:, 0]**2 + jerk[:, 1]**2)
                
                # Store with human-readable name
                joint_name = self._get_keypoint_name(joint)
                jerk_metrics[joint_name] = float(np.mean(jerk_magnitude))
                
                print(f"  {joint_name}: {jerk_metrics[joint_name]:.4f}")
                
            except Exception as e:
                print(f"  Error calculating smoothness for {joint}: {e}")
        
        self.movement_smoothness = jerk_metrics
        print(f"Movement smoothness calculated for {len(jerk_metrics)} joints")
        return jerk_metrics
    
    def analyze_movement_symmetry(self):
        """Analyze movement symmetry between left/right sides - MMPose 1.3.2 compatible"""
        print("Analyzing movement symmetry...")
        
        # Joint pairs for symmetry analysis
        joint_pairs = [
            ('keypoint_5', 'keypoint_6'),   # shoulders
            ('keypoint_7', 'keypoint_8'),   # elbows
            ('keypoint_9', 'keypoint_10'),  # wrists
            ('keypoint_11', 'keypoint_12'), # hips
            ('keypoint_13', 'keypoint_14'), # knees
            ('keypoint_15', 'keypoint_16')  # ankles
        ]
        
        symmetry_metrics = {}
        
        for left_joint, right_joint in joint_pairs:
            if left_joint not in self.smoothed_data or right_joint not in self.smoothed_data:
                continue
            
            try:
                left_data = self.smoothed_data[left_joint]
                right_data = self.smoothed_data[right_joint]
                
                # Check confidence
                left_conf = np.mean(left_data['score'])
                right_conf = np.mean(right_data['score'])
                
                if min(left_conf, right_conf) < 0.4:
                    print(f"  Skipping {left_joint}-{right_joint} pair (low confidence)")
                    continue
                
                # Get trajectories
                left_x = np.array(left_data['x'])
                left_y = np.array(left_data['y'])
                right_x = np.array(right_data['x'])
                right_y = np.array(right_data['y'])
                
                # Calculate reference point (nose or shoulder midpoint)
                ref_x = ref_y = None
                if 'keypoint_0' in self.smoothed_data:  # Use nose
                    ref_x = np.array(self.smoothed_data['keypoint_0']['x'])
                    ref_y = np.array(self.smoothed_data['keypoint_0']['y'])
                elif 'keypoint_5' in self.smoothed_data and 'keypoint_6' in self.smoothed_data:
                    # Use shoulder midpoint
                    ref_x = (np.array(self.smoothed_data['keypoint_5']['x']) + 
                            np.array(self.smoothed_data['keypoint_6']['x'])) / 2
                    ref_y = (np.array(self.smoothed_data['keypoint_5']['y']) + 
                            np.array(self.smoothed_data['keypoint_6']['y'])) / 2
                
                if ref_x is None:
                    print(f"  No reference point for {left_joint}-{right_joint}")
                    continue
                
                # Calculate relative trajectories
                left_rel_x = left_x - ref_x
                left_rel_y = left_y - ref_y
                right_rel_x = -(right_x - ref_x)  # Mirror right side
                right_rel_y = right_y - ref_y
                
                # Calculate frame-by-frame distances
                min_len = min(len(left_rel_x), len(right_rel_x))
                distances = []
                
                for i in range(min_len):
                    dist = np.sqrt((left_rel_x[i] - right_rel_x[i])**2 + 
                                  (left_rel_y[i] - right_rel_y[i])**2)
                    distances.append(dist)
                
                symmetry_score = float(np.mean(distances))
                
                # Create readable pair name
                left_name = self._get_keypoint_name(left_joint)
                right_name = self._get_keypoint_name(right_joint)
                pair_name = f"{left_name} - {right_name}"
                
                symmetry_metrics[pair_name] = symmetry_score
                print(f"  {pair_name}: {symmetry_score:.4f}")
                
            except Exception as e:
                print(f"  Error calculating symmetry for {left_joint}-{right_joint}: {e}")
        
        self.symmetry_metrics = symmetry_metrics
        print(f"Movement symmetry calculated for {len(symmetry_metrics)} joint pairs")
        return symmetry_metrics
    
    def calculate_balance_metrics(self):
        """Calculate balance and stability metrics - MMPose 1.3.2 compatible"""
        print("Calculating balance metrics...")
        
        # Body segment weights (approximate percentages)
        segment_weights = {
            'head': 0.08,
            'torso': 0.55,
            'left_arm': 0.05,
            'right_arm': 0.05,
            'left_leg': 0.135,
            'right_leg': 0.135
        }
        
        n_frames = len(self.pose_df)
        com_trajectory = []
        
        for frame_idx in range(n_frames):
            weighted_pos = np.zeros(2)
            total_weight = 0
            
            try:
                # Head (nose)
                if 'keypoint_0' in self.smoothed_data:
                    nose_data = self.smoothed_data['keypoint_0']
                    if nose_data['score'][frame_idx] > 0.5:
                        pos = np.array([nose_data['x'][frame_idx], nose_data['y'][frame_idx]])
                        weighted_pos += pos * segment_weights['head']
                        total_weight += segment_weights['head']
                
                # Torso (average of shoulders and hips)
                torso_keypoints = ['keypoint_5', 'keypoint_6', 'keypoint_11', 'keypoint_12']
                torso_pos = np.zeros(2)
                torso_count = 0
                
                for kpt in torso_keypoints:
                    if kpt in self.smoothed_data and self.smoothed_data[kpt]['score'][frame_idx] > 0.5:
                        pos = np.array([self.smoothed_data[kpt]['x'][frame_idx], 
                                       self.smoothed_data[kpt]['y'][frame_idx]])
                        torso_pos += pos
                        torso_count += 1
                
                if torso_count > 0:
                    torso_pos /= torso_count
                    weighted_pos += torso_pos * segment_weights['torso']
                    total_weight += segment_weights['torso']
                
                # Arms and legs
                limb_configs = [
                    (['keypoint_5', 'keypoint_7', 'keypoint_9'], 'left_arm'),
                    (['keypoint_6', 'keypoint_8', 'keypoint_10'], 'right_arm'),
                    (['keypoint_11', 'keypoint_13', 'keypoint_15'], 'left_leg'),
                    (['keypoint_12', 'keypoint_14', 'keypoint_16'], 'right_leg')
                ]
                
                for keypoints, segment_name in limb_configs:
                    limb_pos = np.zeros(2)
                    limb_count = 0
                    
                    for kpt in keypoints:
                        if (kpt in self.smoothed_data and 
                            self.smoothed_data[kpt]['score'][frame_idx] > 0.5):
                            pos = np.array([self.smoothed_data[kpt]['x'][frame_idx], 
                                           self.smoothed_data[kpt]['y'][frame_idx]])
                            limb_pos += pos
                            limb_count += 1
                    
                    if limb_count > 0:
                        limb_pos /= limb_count
                        weighted_pos += limb_pos * segment_weights[segment_name]
                        total_weight += segment_weights[segment_name]
                
                # Normalize
                if total_weight > 0:
                    com = weighted_pos / total_weight
                else:
                    # Fallback to hip midpoint
                    if ('keypoint_11' in self.smoothed_data and 
                        'keypoint_12' in self.smoothed_data):
                        left_hip = np.array([self.smoothed_data['keypoint_11']['x'][frame_idx],
                                           self.smoothed_data['keypoint_11']['y'][frame_idx]])
                        right_hip = np.array([self.smoothed_data['keypoint_12']['x'][frame_idx],
                                            self.smoothed_data['keypoint_12']['y'][frame_idx]])
                        com = (left_hip + right_hip) / 2
                    else:
                        com = np.array([0, 0])
                
                com_trajectory.append(com)
                
            except Exception as e:
                print(f"  Error calculating CoM for frame {frame_idx}: {e}")
                com_trajectory.append(np.array([0, 0]))
        
        self.com_trajectory = np.array(com_trajectory)
        
        # Calculate stability metrics
        balance_metrics = {}
        
        if len(self.com_trajectory) > 1:
            # Position stability
            com_std = np.std(self.com_trajectory, axis=0)
            balance_metrics['CoM Stability X'] = float(com_std[0])
            balance_metrics['CoM Stability Y'] = float(com_std[1])
            
            # Velocity stability
            com_velocity = np.diff(self.com_trajectory, axis=0)
            velocity_magnitude = np.sqrt(com_velocity[:, 0]**2 + com_velocity[:, 1]**2)
            balance_metrics['CoM Velocity Mean'] = float(np.mean(velocity_magnitude))
            balance_metrics['CoM Velocity Std'] = float(np.std(velocity_magnitude))
        
        self.balance_metrics = balance_metrics
        print(f"Balance metrics calculated: {list(balance_metrics.keys())}")
        return balance_metrics
    
    def generate_analysis_report(self, output_dir="baduanjin_analysis"):
        """Generate comprehensive analysis report with all visualizations - MMPose 1.3.2 compatible"""
        print(f"Generating analysis report in {output_dir}...")
        os.makedirs(output_dir, exist_ok=True)
        
        # Calculate all metrics
        if not hasattr(self, 'joint_angles') or self.joint_angles.empty:
            self.calculate_joint_angles()
        
        if not hasattr(self, 'key_frames'):
            self.identify_key_poses()
        
        if not hasattr(self, 'movement_smoothness'):
            self.analyze_movement_smoothness()
        
        if not hasattr(self, 'symmetry_metrics'):
            self.analyze_movement_symmetry()
        
        if not hasattr(self, 'balance_metrics'):
            self.calculate_balance_metrics()
        
        # 1. Key Poses Visualization
        key_poses_path = os.path.join(output_dir, "key_poses.png")
        self.visualize_key_poses(output_path=key_poses_path)
        
        # 2. Joint Angles Visualization
        self._create_joint_angles_plot(output_dir)
        
        # 3. Movement Smoothness Plot
        self._create_smoothness_plot(output_dir)
        
        # 4. Movement Symmetry Plot
        self._create_symmetry_plot(output_dir)
        
        # 5. Center of Mass Trajectory
        self._create_com_plot(output_dir)
        
        # 6. Balance Metrics Plot
        self._create_balance_plot(output_dir)
        
        # 7. Generate Text Report
        self._create_text_report(output_dir)
        
        print("Analysis report generation completed!")
        print("Generated files:")
        for filename in ["key_poses.png", "joint_angles.png", "movement_smoothness.png", 
                        "movement_symmetry.png", "com_trajectory.png", "balance_metrics.png", 
                        "analysis_report.txt"]:
            filepath = os.path.join(output_dir, filename)
            if os.path.exists(filepath):
                print(f" {filename}")
            else:
                print(f" {filename} (failed to create)")
        
        return output_dir
    
    def _create_joint_angles_plot(self, output_dir):
        """Create joint angles visualization"""
        try:
            plt.figure(figsize=(15, 10))
            
            valid_angles = self.joint_angles.dropna(axis=1, how='all')
            n_angles = min(len(valid_angles.columns), 12)
            
            for i, angle_name in enumerate(valid_angles.columns[:n_angles]):
                plt.subplot(3, 4, i+1)
                angle_data = valid_angles[angle_name].dropna()
                
                if len(angle_data) > 0:
                    plt.plot(angle_data.index, angle_data.values, 'b-', linewidth=1)
                    plt.title(angle_name, fontsize=10)
                    plt.xlabel("Frame")
                    plt.ylabel("Angle (°)")
                    
                    # Mark key poses
                    for frame_idx, _ in self.key_frames:
                        if frame_idx in angle_data.index:
                            plt.axvline(x=frame_idx, color='r', linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "joint_angles.png"), dpi=150, bbox_inches='tight')
            plt.close()
        except Exception as e:
            print(f"Error creating joint angles plot: {e}")
    
    def _create_smoothness_plot(self, output_dir):
        """Create movement smoothness plot"""
        try:
            if not self.movement_smoothness:
                print("No smoothness data to plot")
                return
            
            plt.figure(figsize=(12, 6))
            joints = list(self.movement_smoothness.keys())
            values = list(self.movement_smoothness.values())
            
            bars = plt.bar(joints, values, color='skyblue', edgecolor='navy')
            plt.title("Movement Smoothness Analysis\n(Lower values indicate smoother movement)", fontsize=14)
            plt.ylabel("Average Jerk", fontsize=12)
            plt.xlabel("Body Part", fontsize=12)
            plt.xticks(rotation=45, ha='right')
            
            # Add value labels
            for bar, value in zip(bars, values):
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.01,
                        f'{value:.3f}', ha='center', va='bottom', fontsize=10)
            
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "movement_smoothness.png"), dpi=150, bbox_inches='tight')
            plt.close()
        except Exception as e:
            print(f"Error creating smoothness plot: {e}")
    
    def _create_symmetry_plot(self, output_dir):
        """Create movement symmetry plot"""
        try:
            if not self.symmetry_metrics:
                print("No symmetry data to plot")
                return
            
            plt.figure(figsize=(14, 6))
            pairs = list(self.symmetry_metrics.keys())
            values = list(self.symmetry_metrics.values())
            
            bars = plt.bar(pairs, values, color='lightcoral', edgecolor='darkred')
            plt.title("Movement Symmetry Analysis\n(Lower values indicate better symmetry)", fontsize=14)
            plt.ylabel("Asymmetry Score", fontsize=12)
            plt.xlabel("Joint Pairs", fontsize=12)
            plt.xticks(rotation=45, ha='right')
            
            # Add value labels
            for bar, value in zip(bars, values):
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.01,
                        f'{value:.3f}', ha='center', va='bottom', fontsize=10)
            
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "movement_symmetry.png"), dpi=150, bbox_inches='tight')
            plt.close()
        except Exception as e:
            print(f"Error creating symmetry plot: {e}")
    
    def _create_com_plot(self, output_dir):
        """Create center of mass trajectory plot"""
        try:
            if not hasattr(self, 'com_trajectory') or len(self.com_trajectory) == 0:
                print("No CoM trajectory data to plot")
                return
            
            plt.figure(figsize=(10, 8))
            
            # Plot trajectory
            plt.plot(self.com_trajectory[:, 0], self.com_trajectory[:, 1], 'b-', linewidth=2, alpha=0.7)
            
            # Color-code by time
            scatter = plt.scatter(self.com_trajectory[:, 0], self.com_trajectory[:, 1], 
                                 c=range(len(self.com_trajectory)), cmap='viridis', s=20)
            
            plt.colorbar(scatter, label='Frame Number')
            plt.title("Center of Mass Trajectory", fontsize=14)
            plt.xlabel("X Position (pixels)", fontsize=12)
            plt.ylabel("Y Position (pixels)", fontsize=12)
            plt.grid(True, alpha=0.3)
            plt.axis('equal')
            
            # Mark start and end
            plt.plot(self.com_trajectory[0, 0], self.com_trajectory[0, 1], 'go', markersize=10, label='Start')
            plt.plot(self.com_trajectory[-1, 0], self.com_trajectory[-1, 1], 'ro', markersize=10, label='End')
            plt.legend()
            
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "com_trajectory.png"), dpi=150, bbox_inches='tight')
            plt.close()
        except Exception as e:
            print(f"Error creating CoM plot: {e}")
    
    def _create_balance_plot(self, output_dir):
        """Create balance metrics plot"""
        try:
            if not self.balance_metrics:
                print("No balance metrics to plot")
                return
            
            plt.figure(figsize=(10, 6))
            metrics = list(self.balance_metrics.keys())
            values = list(self.balance_metrics.values())
            
            bars = plt.bar(metrics, values, color='lightgreen', edgecolor='darkgreen')
            plt.title("Balance and Stability Metrics", fontsize=14)
            plt.ylabel("Value", fontsize=12)
            plt.xlabel("Metric", fontsize=12)
            plt.xticks(rotation=45, ha='right')
            
            # Add value labels
            for bar, value in zip(bars, values):
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.01,
                        f'{value:.3f}', ha='center', va='bottom', fontsize=10)
            
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "balance_metrics.png"), dpi=150, bbox_inches='tight')
            plt.close()
        except Exception as e:
            print(f"Error creating balance plot: {e}")
    
    def _create_text_report(self, output_dir):
        """Create the analysis report text file"""
        try:
            report_path = os.path.join(output_dir, "analysis_report.txt")
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("Baduanjin Movement Analysis Report\n")
                f.write("=" * 50 + "\n")
                f.write(f"Generated from: {os.path.basename(self.json_path)}\n")
                f.write(f"Total frames analyzed: {len(self.pose_df)}\n\n")
                
                # Key Poses Section
                f.write("Key Poses Detected\n")
                f.write("-" * 20 + "\n")
                for i, (frame_idx, cluster_idx) in enumerate(self.key_frames):
                    f.write(f"Pose {i+1}: Frame {frame_idx}\n")
                f.write("\n")
                
                # Joint Angles Section
                f.write("Joint Angles at Key Poses\n")
                f.write("-" * 25 + "\n")
                for i, (frame_idx, _) in enumerate(self.key_frames):
                    f.write(f"Pose {i+1} (Frame {frame_idx}):\n")
                    
                    if frame_idx in self.joint_angles.index:
                        angles = self.joint_angles.loc[frame_idx].dropna()
                        for angle_name, angle_value in angles.items():
                            f.write(f"  {angle_name}: {angle_value:.1f}°\n")
                    else:
                        f.write("  No joint angle data available\n")
                    f.write("\n")
                
                # Movement Smoothness Section
                f.write("Movement Smoothness\n")
                f.write("-" * 20 + "\n")
                if self.movement_smoothness:
                    for joint, jerk_value in self.movement_smoothness.items():
                        f.write(f"{joint}: {jerk_value:.4f}\n")
                else:
                    f.write("No smoothness data calculated\n")
                f.write("\n")
                
                # Movement Symmetry Section
                f.write("Movement Symmetry\n")
                f.write("-" * 17 + "\n")
                if self.symmetry_metrics:
                    for pair, symmetry_score in self.symmetry_metrics.items():
                        f.write(f"{pair}: {symmetry_score:.4f}\n")
                else:
                    f.write("No symmetry data calculated\n")
                f.write("\n")
                
                # Balance Metrics Section
                f.write("Balance Metrics\n")
                f.write("-" * 15 + "\n")
                if self.balance_metrics:
                    for metric, value in self.balance_metrics.items():
                        f.write(f"{metric}: {value:.4f}\n")
                else:
                    f.write("No balance metrics calculated\n")
                f.write("\n")
                
                # Teaching Recommendations Section
                f.write("Teaching Recommendations\n")
                f.write("-" * 25 + "\n")
                f.write("Based on this analysis, focus on:\n")
                f.write("1. Maintaining proper joint angles during key poses\n")
                f.write("2. Achieving smooth transitions between movements\n")
                f.write("3. Developing symmetrical movement patterns\n")
                f.write("4. Improving balance and stability throughout the sequence\n")
                f.write("5. Practicing slower movements to enhance control\n")
                
        except Exception as e:
            print(f"Error creating text report: {e}")

# Main execution
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze Baduanjin movements from MMPose 1.3.2 results')
    parser.add_argument('--pose_results', required=True, help='Path to MMPose JSON results file')
    parser.add_argument('--video', default=None, help='Path to original video file (optional)')
    parser.add_argument('--output_dir', default='baduanjin_analysis', help='Output directory')
    
    args = parser.parse_args()
    
    try:
        print("Starting Baduanjin analysis with MMPose 1.3.2 compatibility...")
        analyzer = BaduanjinAnalyzer(args.pose_results, args.video)
        analysis_dir = analyzer.generate_analysis_report(args.output_dir)
        print(f"\n🎉 Analysis completed successfully!")
        print(f"Results saved to: {analysis_dir}")
    except Exception as e:
        print(f"\n Analysis failed: {e}")
        import traceback
        traceback.print_exc()