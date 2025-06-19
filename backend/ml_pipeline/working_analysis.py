# ml_pipeline/working_analysis.py
# Real analysis script that calculates actual metrics from pose data

import os
import json
import argparse
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import signal
from scipy.spatial.distance import euclidean
import cv2
from PIL import Image, ImageDraw, ImageFont

# COCO-17 keypoint indices
KEYPOINT_NAMES = [
    'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
    'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
    'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
    'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
]

KEYPOINT_INDICES = {name: i for i, name in enumerate(KEYPOINT_NAMES)}

def extract_pose_data(json_path):
    """Extract pose data from MMPose JSON format"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    frames = data.get('instance_info', [])
    pose_sequence = []
    
    for frame_idx, frame in enumerate(frames):
        instances = frame.get('instances', [])
        if instances:
            # Take the first (highest confidence) instance
            instance = instances[0]
            keypoints = instance.get('keypoints', [])
            scores = instance.get('keypoint_scores', [])
            
            if len(keypoints) >= 17 and len(scores) >= 17:
                # Reshape keypoints to (17, 2) format
                kpts = np.array(keypoints).reshape(-1, 2)
                pose_sequence.append({
                    'frame': frame_idx,
                    'keypoints': kpts,
                    'scores': np.array(scores),
                    'avg_confidence': np.mean(scores)
                })
    
    return pose_sequence

def calculate_angle(p1, p2, p3):
    """Calculate angle at point p2 formed by p1-p2-p3"""
    v1 = p1 - p2
    v2 = p3 - p2
    
    # Calculate angle using dot product
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    cos_angle = np.clip(cos_angle, -1.0, 1.0)  # Handle numerical errors
    angle = np.arccos(cos_angle)
    return np.degrees(angle)

def calculate_joint_angles(pose_data):
    """Calculate joint angles for each frame"""
    angles_sequence = []
    
    for pose in pose_data:
        kpts = pose['keypoints']
        scores = pose['scores']
        
        # Only calculate if keypoints are visible (confidence > 0.3)
        angles = {}
        
        # Right elbow angle: right_shoulder - right_elbow - right_wrist
        if (scores[KEYPOINT_INDICES['right_shoulder']] > 0.3 and 
            scores[KEYPOINT_INDICES['right_elbow']] > 0.3 and 
            scores[KEYPOINT_INDICES['right_wrist']] > 0.3):
            angles['right_elbow'] = calculate_angle(
                kpts[KEYPOINT_INDICES['right_shoulder']],
                kpts[KEYPOINT_INDICES['right_elbow']],
                kpts[KEYPOINT_INDICES['right_wrist']]
            )
        
        # Left elbow angle: left_shoulder - left_elbow - left_wrist
        if (scores[KEYPOINT_INDICES['left_shoulder']] > 0.3 and 
            scores[KEYPOINT_INDICES['left_elbow']] > 0.3 and 
            scores[KEYPOINT_INDICES['left_wrist']] > 0.3):
            angles['left_elbow'] = calculate_angle(
                kpts[KEYPOINT_INDICES['left_shoulder']],
                kpts[KEYPOINT_INDICES['left_elbow']],
                kpts[KEYPOINT_INDICES['left_wrist']]
            )
        
        # Right shoulder angle: right_elbow - right_shoulder - left_shoulder
        if (scores[KEYPOINT_INDICES['right_elbow']] > 0.3 and 
            scores[KEYPOINT_INDICES['right_shoulder']] > 0.3 and 
            scores[KEYPOINT_INDICES['left_shoulder']] > 0.3):
            angles['right_shoulder'] = calculate_angle(
                kpts[KEYPOINT_INDICES['right_elbow']],
                kpts[KEYPOINT_INDICES['right_shoulder']],
                kpts[KEYPOINT_INDICES['left_shoulder']]
            )
        
        # Left shoulder angle: left_elbow - left_shoulder - right_shoulder
        if (scores[KEYPOINT_INDICES['left_elbow']] > 0.3 and 
            scores[KEYPOINT_INDICES['left_shoulder']] > 0.3 and 
            scores[KEYPOINT_INDICES['right_shoulder']] > 0.3):
            angles['left_shoulder'] = calculate_angle(
                kpts[KEYPOINT_INDICES['left_elbow']],
                kpts[KEYPOINT_INDICES['left_shoulder']],
                kpts[KEYPOINT_INDICES['right_shoulder']]
            )
        
        angles_sequence.append(angles)
    
    return angles_sequence

def detect_key_poses(pose_data, num_poses=5):
    """Detect key poses based on movement variation"""
    if len(pose_data) < num_poses:
        # If not enough frames, just distribute evenly
        indices = np.linspace(0, len(pose_data)-1, num_poses, dtype=int)
        return [(i, pose_data[i]) for i in indices]
    
    # Calculate movement magnitude for each frame
    movement_magnitudes = []
    
    for i in range(1, len(pose_data)):
        prev_kpts = pose_data[i-1]['keypoints']
        curr_kpts = pose_data[i]['keypoints']
        
        # Calculate total movement of all keypoints
        movement = np.sum(np.linalg.norm(curr_kpts - prev_kpts, axis=1))
        movement_magnitudes.append(movement)
    
    # Find local minima (poses with least movement)
    # Smooth the signal first
    if len(movement_magnitudes) > 10:
        smoothed = signal.savgol_filter(movement_magnitudes, 
                                      min(11, len(movement_magnitudes)//2*2+1), 3)
    else:
        smoothed = movement_magnitudes
    
    # Find peaks (high movement) and valleys (low movement/stable poses)
    peaks, _ = signal.find_peaks(-np.array(smoothed), distance=len(smoothed)//num_poses)
    
    if len(peaks) < num_poses:
        # Fallback to even distribution
        indices = np.linspace(0, len(pose_data)-1, num_poses, dtype=int)
    else:
        # Select the most significant peaks
        peak_values = [-smoothed[p] for p in peaks]
        sorted_peaks = sorted(zip(peaks, peak_values), key=lambda x: x[1], reverse=True)
        indices = sorted([p[0] for p in sorted_peaks[:num_poses]])
    
    return [(i, pose_data[i]) for i in indices]

def calculate_movement_smoothness(pose_data):
    """Calculate movement smoothness using jerk (third derivative)"""
    smoothness_metrics = {}
    
    joints_to_analyze = ['left_wrist', 'right_wrist', 'left_ankle', 'right_ankle']
    
    for joint in joints_to_analyze:
        joint_idx = KEYPOINT_INDICES[joint]
        positions = []
        
        for pose in pose_data:
            if pose['scores'][joint_idx] > 0.3:
                positions.append(pose['keypoints'][joint_idx])
        
        if len(positions) < 10:  # Need enough data points
            smoothness_metrics[joint] = 0.0
            continue
            
        positions = np.array(positions)
        
        # Calculate velocity (first derivative)
        velocity = np.diff(positions, axis=0)
        
        # Calculate acceleration (second derivative)
        acceleration = np.diff(velocity, axis=0)
        
        # Calculate jerk (third derivative)
        jerk = np.diff(acceleration, axis=0)
        
        # Calculate jerk magnitude
        jerk_magnitude = np.linalg.norm(jerk, axis=1)
        
        # Smoothness is inverse of mean jerk (lower jerk = smoother movement)
        mean_jerk = np.mean(jerk_magnitude)
        smoothness_metrics[joint] = mean_jerk
    
    return smoothness_metrics

def calculate_movement_symmetry(pose_data):
    """Calculate bilateral symmetry between left and right sides"""
    symmetry_metrics = {}
    
    joint_pairs = [
        ('left_shoulder', 'right_shoulder'),
        ('left_elbow', 'right_elbow'),
        ('left_wrist', 'right_wrist'),
        ('left_hip', 'right_hip'),
        ('left_knee', 'right_knee'),
        ('left_ankle', 'right_ankle')
    ]
    
    for left_joint, right_joint in joint_pairs:
        left_idx = KEYPOINT_INDICES[left_joint]
        right_idx = KEYPOINT_INDICES[right_joint]
        
        left_positions = []
        right_positions = []
        
        for pose in pose_data:
            if (pose['scores'][left_idx] > 0.3 and pose['scores'][right_idx] > 0.3):
                left_positions.append(pose['keypoints'][left_idx])
                right_positions.append(pose['keypoints'][right_idx])
        
        if len(left_positions) < 10:
            symmetry_metrics[f"{left_joint} - {right_joint}"] = 0.0
            continue
        
        left_positions = np.array(left_positions)
        right_positions = np.array(right_positions)
        
        # Calculate velocity for both sides
        left_velocity = np.diff(left_positions, axis=0)
        right_velocity = np.diff(right_positions, axis=0)
        
        # Mirror right side velocity (flip x-coordinate)
        right_velocity_mirrored = right_velocity.copy()
        right_velocity_mirrored[:, 0] = -right_velocity_mirrored[:, 0]
        
        # Calculate asymmetry as mean difference between velocities
        asymmetry = np.mean(np.linalg.norm(left_velocity - right_velocity_mirrored, axis=1))
        symmetry_metrics[f"{left_joint} - {right_joint}"] = asymmetry
    
    return symmetry_metrics

def calculate_balance_metrics(pose_data):
    """Calculate center of mass and balance metrics"""
    com_positions = []
    
    # Define approximate body segment weights (from biomechanics literature)
    segment_weights = {
        'head': 0.081,
        'trunk': 0.497,
        'upper_arm': 0.028,
        'forearm': 0.016,
        'hand': 0.006,
        'thigh': 0.100,
        'shank': 0.0465,
        'foot': 0.0145
    }
    
    for pose in pose_data:
        kpts = pose['keypoints']
        scores = pose['scores']
        
        # Calculate approximate center of mass
        # Simplified to use key points with good visibility
        weighted_positions = []
        total_weight = 0
        
        # Head (nose)
        if scores[KEYPOINT_INDICES['nose']] > 0.3:
            weighted_positions.append(kpts[KEYPOINT_INDICES['nose']] * segment_weights['head'])
            total_weight += segment_weights['head']
        
        # Trunk (midpoint of shoulders)
        if (scores[KEYPOINT_INDICES['left_shoulder']] > 0.3 and 
            scores[KEYPOINT_INDICES['right_shoulder']] > 0.3):
            trunk_pos = (kpts[KEYPOINT_INDICES['left_shoulder']] + 
                        kpts[KEYPOINT_INDICES['right_shoulder']]) / 2
            weighted_positions.append(trunk_pos * segment_weights['trunk'])
            total_weight += segment_weights['trunk']
        
        # Arms and legs (simplified)
        limb_joints = ['left_wrist', 'right_wrist', 'left_ankle', 'right_ankle']
        limb_weight = 0.05  # Simplified weight for each limb endpoint
        
        for joint in limb_joints:
            joint_idx = KEYPOINT_INDICES[joint]
            if scores[joint_idx] > 0.3:
                weighted_positions.append(kpts[joint_idx] * limb_weight)
                total_weight += limb_weight
        
        if weighted_positions and total_weight > 0:
            com = np.sum(weighted_positions, axis=0) / total_weight
            com_positions.append(com)
    
    if len(com_positions) < 10:
        return {
            'CoM Stability X': 0.0,
            'CoM Stability Y': 0.0,
            'CoM Velocity Mean': 0.0,
            'CoM Velocity Std': 0.0
        }
    
    com_positions = np.array(com_positions)
    
    # Calculate stability (standard deviation of position)
    com_stability_x = np.std(com_positions[:, 0])
    com_stability_y = np.std(com_positions[:, 1])
    
    # Calculate velocity
    com_velocity = np.diff(com_positions, axis=0)
    com_velocity_magnitude = np.linalg.norm(com_velocity, axis=1)
    
    velocity_mean = np.mean(com_velocity_magnitude)
    velocity_std = np.std(com_velocity_magnitude)
    
    return {
        'CoM Stability X': com_stability_x,
        'CoM Stability Y': com_stability_y,
        'CoM Velocity Mean': velocity_mean,
        'CoM Velocity Std': velocity_std
    }

def extract_video_frames(video_path, frame_numbers):
    """Extract specific frames from video file"""
    if not os.path.exists(video_path):
        print(f"Warning: Video file not found at {video_path}")
        return []
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        return []
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Video has {total_frames} total frames")
    
    extracted_frames = []
    
    for frame_num in frame_numbers:
        # Convert to 0-based indexing
        frame_idx = frame_num - 1
        
        if frame_idx >= total_frames:
            print(f"Warning: Frame {frame_num} exceeds video length ({total_frames})")
            continue
            
        # Set frame position
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        
        if ret:
            # Convert BGR to RGB for PIL
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            extracted_frames.append((frame_num, frame_rgb))
            print(f"Extracted frame {frame_num}")
        else:
            print(f"Error: Could not read frame {frame_num}")
    
    cap.release()
    return extracted_frames

def create_key_poses_composite(extracted_frames, output_path):
    """Create a composite image of key poses"""
    if not extracted_frames:
        print("No frames extracted, creating placeholder image")
        # Create a placeholder image
        img = Image.new('RGB', (800, 400), color='lightgray')
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        draw.text((400, 200), "No video frames available", fill='black', 
                 font=font, anchor='mm')
        img.save(output_path)
        return
    
    # Determine layout based on number of frames
    num_frames = len(extracted_frames)
    if num_frames <= 3:
        cols = num_frames
        rows = 1
    else:
        cols = 3
        rows = (num_frames + cols - 1) // cols
    
    # Get frame dimensions
    sample_frame = extracted_frames[0][1]
    frame_height, frame_width = sample_frame.shape[:2]
    
    # Calculate thumbnail size to fit nicely
    max_thumb_width = 300
    max_thumb_height = 200
    
    # Calculate scale to maintain aspect ratio
    scale_w = max_thumb_width / frame_width
    scale_h = max_thumb_height / frame_height
    scale = min(scale_w, scale_h)
    
    thumb_width = int(frame_width * scale)
    thumb_height = int(frame_height * scale)
    
    # Add padding and space for labels
    padding = 20
    label_height = 30
    
    # Calculate composite image size
    composite_width = cols * (thumb_width + padding) + padding
    composite_height = rows * (thumb_height + label_height + padding) + padding
    
    # Create composite image
    composite = Image.new('RGB', (composite_width, composite_height), color='white')
    
    try:
        font = ImageFont.truetype("arial.ttf", 12)
        title_font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()
    
    draw = ImageDraw.Draw(composite)
    
    # Add title
    title = "Key Poses Detected"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(((composite_width - title_width) // 2, 10), title, 
             fill='black', font=title_font)
    
    # Place each frame
    start_y = 50  # Account for title
    
    for i, (frame_num, frame) in enumerate(extracted_frames):
        row = i // cols
        col = i % cols
        
        # Calculate position
        x = col * (thumb_width + padding) + padding
        y = start_y + row * (thumb_height + label_height + padding)
        
        # Resize frame
        frame_pil = Image.fromarray(frame)
        frame_resized = frame_pil.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
        
        # Paste frame
        composite.paste(frame_resized, (x, y))
        
        # Add frame border
        draw.rectangle([x-1, y-1, x+thumb_width, y+thumb_height], 
                      outline='black', width=2)
        
        # Add label
        label = f"Pose {i+1}"
        label_bbox = draw.textbbox((0, 0), label, font=font)
        label_width = label_bbox[2] - label_bbox[0]
        label_x = x + (thumb_width - label_width) // 2
        label_y = y + thumb_height + 5
        
        draw.text((label_x, label_y), label, fill='black', font=font)
    
    # Save composite image
    composite.save(output_path, 'PNG', quality=95)
    print(f"Created key poses composite: {output_path}")

def find_video_file(json_path):
    """Find the corresponding video file for the JSON results"""
    # Extract directory and filename
    json_dir = os.path.dirname(json_path)
    json_filename = os.path.basename(json_path)
    
    # Extract UUID from filename (assuming format: results_{UUID}.json)
    if json_filename.startswith('results_') and json_filename.endswith('.json'):
        uuid_part = json_filename[8:-5]  # Remove 'results_' and '.json'
        video_filename = f"{uuid_part}.mp4"
        video_path = os.path.join(json_dir, video_filename)
        
        if os.path.exists(video_path):
            return video_path
        else:
            print(f"Video file not found: {video_path}")
    
    # Fallback: look for any .mp4 file in the same directory
    if os.path.exists(json_dir):
        for file in os.listdir(json_dir):
            if file.endswith('.mp4'):
                video_path = os.path.join(json_dir, file)
                print(f"Found video file: {video_path}")
                return video_path
    
    print("No video file found in the same directory as JSON")
    return None

def analyze_video_data(json_path, output_dir):
    """Create analysis from MMPose JSON format"""
    
    print(f"Analyzing video data from {json_path}")
    
    # Extract pose data
    pose_data = extract_pose_data(json_path)
    
    if not pose_data:
        raise ValueError("No valid pose data found in JSON file")
    
    print(f"Processing {len(pose_data)} frames with valid poses")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Perform analyses
    key_poses = detect_key_poses(pose_data, num_poses=5)
    joint_angles_sequence = calculate_joint_angles(pose_data)
    smoothness_metrics = calculate_movement_smoothness(pose_data)
    symmetry_metrics = calculate_movement_symmetry(pose_data)
    balance_metrics = calculate_balance_metrics(pose_data)
    
    # Calculate statistics
    total_frames = len(pose_data)
    avg_confidence = np.mean([pose['avg_confidence'] for pose in pose_data])
    
    # Create analysis report
    report_path = os.path.join(output_dir, "analysis_report.txt")
    with open(report_path, 'w') as f:
        f.write("Baduanjin Movement Analysis Report\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated from: {os.path.basename(json_path)}\n")
        f.write(f"Total frames analyzed: {total_frames}\n")
        f.write(f"Frames with detected poses: {len(pose_data)}\n")
        f.write(f"Average keypoint confidence: {avg_confidence:.3f}\n\n")
        
        f.write("Key Poses Detected\n")
        f.write("-" * 20 + "\n")
        for i, (frame_idx, pose) in enumerate(key_poses):
            f.write(f"Pose {i+1}: Frame {frame_idx + 1}\n")
        f.write("\n")
        
        f.write("Joint Angles at Key Poses\n")
        f.write("-" * 25 + "\n")
        for i, (frame_idx, pose) in enumerate(key_poses):
            angles = joint_angles_sequence[frame_idx] if frame_idx < len(joint_angles_sequence) else {}
            f.write(f"Pose {i+1} (Frame {frame_idx + 1}):\n")
            
            angle_names = ['right_elbow', 'left_elbow', 'right_shoulder', 'left_shoulder']
            display_names = ['Right Elbow', 'Left Elbow', 'Right Shoulder', 'Left Shoulder']
            
            for angle_name, display_name in zip(angle_names, display_names):
                if angle_name in angles:
                    f.write(f"  {display_name}: {angles[angle_name]:.1f}°\n")
                else:
                    f.write(f"  {display_name}: N/A\n")
            f.write("\n")
        
        f.write("Movement Smoothness\n")
        f.write("-" * 20 + "\n")
        for joint, value in smoothness_metrics.items():
            joint_display = joint.replace('_', ' ').title()
            f.write(f"{joint_display}: {value:.4f}\n")
        f.write("\n")
        
        f.write("Movement Symmetry\n")
        f.write("-" * 17 + "\n")
        for pair, value in symmetry_metrics.items():
            f.write(f"{pair}: {value:.4f}\n")
        f.write("\n")
        
        f.write("Balance Metrics\n")
        f.write("-" * 15 + "\n")
        for metric, value in balance_metrics.items():
            f.write(f"{metric}: {value:.4f}\n")
        f.write("\n")
        
        f.write("Teaching Recommendations\n")
        f.write("-" * 25 + "\n")
        f.write("Based on this analysis, focus on:\n")
        
        # Generate specific recommendations based on metrics
        recommendations = []
        
        if any(v > 0.02 for v in smoothness_metrics.values()):
            recommendations.append("Work on smoother transitions - some joints show jerky movements")
        
        if any(v > 0.015 for v in symmetry_metrics.values()):
            recommendations.append("Practice bilateral symmetry - focus on coordinating left and right sides")
        
        if balance_metrics['CoM Stability X'] > 10 or balance_metrics['CoM Stability Y'] > 10:
            recommendations.append("Improve balance and postural stability")
        
        if balance_metrics['CoM Velocity Mean'] > 3:
            recommendations.append("Practice slower, more controlled movements")
        
        # Add default recommendations
        if not recommendations:
            recommendations = [
                "Maintain proper joint angles during key poses",
                "Continue practicing smooth transitions between movements",
                "Keep developing symmetrical movement patterns",
                "Maintain good balance throughout the sequence"
            ]
        else:
            recommendations.extend([
                "Focus on breath coordination with movements",
                "Practice individual poses before combining sequences"
            ])
        
        for i, rec in enumerate(recommendations[:5], 1):
            f.write(f"{i}. {rec}\n")
    
    print(f"Created analysis report: {report_path}")
    
    # Find and extract video frames for key poses
    video_path = find_video_file(json_path)
    key_pose_frames = []
    
    if video_path:
        frame_numbers = [frame_idx + 1 for frame_idx, _ in key_poses]  # Convert to 1-based
        key_pose_frames = extract_video_frames(video_path, frame_numbers)
    
    # Create key poses composite image
    key_poses_path = os.path.join(output_dir, "key_poses.png")
    create_key_poses_composite(key_pose_frames, key_poses_path)
    
    # Create analysis charts with real data
    create_analysis_charts(pose_data, key_poses, joint_angles_sequence, 
                          smoothness_metrics, symmetry_metrics, balance_metrics, output_dir)
    
    print("Analysis completed successfully!")
    return True

def remove_outliers(data, z_threshold=2.5):
    """Remove outliers using Z-score method"""
    if len(data) < 10:
        return data
    
    data = np.array(data)
    
    # Calculate Z-scores for both x and y coordinates
    z_scores_x = np.abs((data[:, 0] - np.mean(data[:, 0])) / np.std(data[:, 0]))
    z_scores_y = np.abs((data[:, 1] - np.mean(data[:, 1])) / np.std(data[:, 1]))
    
    # Keep points where both x and y Z-scores are below threshold
    mask = (z_scores_x < z_threshold) & (z_scores_y < z_threshold)
    
    return data[mask]

def create_analysis_charts(pose_data, key_poses, joint_angles_sequence, 
                          smoothness_metrics, symmetry_metrics, balance_metrics, output_dir):
    """Create analysis charts with real data (excluding key poses which is handled separately)"""
    
    # 1. Joint Angles Over Time
    plt.figure(figsize=(12, 6))
    angles_to_plot = ['right_elbow', 'left_elbow', 'right_shoulder', 'left_shoulder']
    colors = ['red', 'blue', 'green', 'purple']
    
    for angle_name, color in zip(angles_to_plot, colors):
        frames = []
        angles = []
        
        for i, angle_data in enumerate(joint_angles_sequence):
            if angle_name in angle_data:
                frames.append(i + 1)
                angles.append(angle_data[angle_name])
        
        if frames:
            plt.plot(frames, angles, label=angle_name.replace('_', ' ').title(), 
                    color=color, linewidth=2, alpha=0.8)
    
    plt.xlabel("Frame")
    plt.ylabel("Angle (degrees)")
    plt.title("Joint Angles Over Time", fontsize=14)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "joint_angles.png"), dpi=150, bbox_inches='tight')
    plt.close()
    
    # 2. Movement Smoothness
    plt.figure(figsize=(10, 6))
    joints = [joint.replace('_', ' ').title() for joint in smoothness_metrics.keys()]
    values = list(smoothness_metrics.values())
    
    plt.bar(joints, values, color='skyblue', edgecolor='navy')
    plt.title("Movement Smoothness Analysis (Lower is better)", fontsize=14)
    plt.ylabel("Jerk Value (lower = smoother)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "movement_smoothness.png"), dpi=150, bbox_inches='tight')
    plt.close()
    
    # 3. Movement Symmetry
    plt.figure(figsize=(12, 6))
    pairs = list(symmetry_metrics.keys())
    values = list(symmetry_metrics.values())
    
    plt.bar(range(len(pairs)), values, color='lightcoral', edgecolor='darkred')
    plt.title("Movement Symmetry Analysis (Lower is better)", fontsize=14)
    plt.ylabel("Asymmetry Score (lower = more symmetric)")
    plt.xticks(range(len(pairs)), [p.split(' - ')[0].replace('_', ' ').title() for p in pairs], rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "movement_symmetry.png"), dpi=150, bbox_inches='tight')
    plt.close()
    
    # 4. Center of Mass Trajectory
    """Create Center of Mass Trajectory chart with outlier removal"""
    plt.figure(figsize=(10, 8))
    com_positions = []
    
    for pose in pose_data:
        kpts = pose['keypoints']
        scores = pose['scores']
        
        # Simple CoM approximation using torso keypoints
        torso_points = []
        torso_indices = [KEYPOINT_INDICES['left_shoulder'], KEYPOINT_INDICES['right_shoulder'],
                        KEYPOINT_INDICES['left_hip'], KEYPOINT_INDICES['right_hip']]
        
        for idx in torso_indices:
            if scores[idx] > 0.3:
                torso_points.append(kpts[idx])
        
        if len(torso_points) >= 2:
            com = np.mean(torso_points, axis=0)
            com_positions.append(com)
    
    if len(com_positions) > 10:
        com_positions = np.array(com_positions)
        
        # Remove outliers
        com_positions_clean = remove_outliers(com_positions, z_threshold=2.5)
        
        print(f"Removed {len(com_positions) - len(com_positions_clean)} outlier points from CoM trajectory")
        
        if len(com_positions_clean) > 5:
            # Create time indices for the cleaned data
            time_indices = np.linspace(0, len(pose_data)-1, len(com_positions_clean))
            
            plt.scatter(com_positions_clean[:, 0], com_positions_clean[:, 1], 
                       c=time_indices, cmap='viridis', s=20, alpha=0.7)
            plt.plot(com_positions_clean[:, 0], com_positions_clean[:, 1], 'b-', alpha=0.3)
            plt.colorbar(label='Time (frame)')
            plt.xlabel("X Position (pixels)")
            plt.ylabel("Y Position (pixels)")
            plt.title("Center of Mass Trajectory (Outliers Removed)", fontsize=14)
            plt.axis('equal')
        else:
            plt.text(0.5, 0.5, 'Insufficient data after outlier removal', 
                    ha='center', va='center', transform=plt.gca().transAxes)
            plt.title("Center of Mass Trajectory", fontsize=14)
    else:
        plt.text(0.5, 0.5, 'Insufficient data for CoM trajectory', 
                ha='center', va='center', transform=plt.gca().transAxes)
        plt.title("Center of Mass Trajectory", fontsize=14)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "com_trajectory.png"), dpi=150, bbox_inches='tight')
    plt.close()
    
    # 5. Balance Metrics
    plt.figure(figsize=(10, 6))
    metrics = list(balance_metrics.keys())
    values = list(balance_metrics.values())
    
    plt.bar(metrics, values, color='lightgreen', edgecolor='darkgreen')
    plt.title("Balance and Stability Metrics", fontsize=14)
    plt.ylabel("Value")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "balance_metrics.png"), dpi=150, bbox_inches='tight')
    plt.close()

def main():
    parser = argparse.ArgumentParser(description='Baduanjin movement analysis')
    parser.add_argument('--pose_results', required=True, help='Path to MMPose JSON results file')
    parser.add_argument('--output_dir', required=True, help='Output directory')
    parser.add_argument('--video', help='Video file (optional)')
    
    args = parser.parse_args()
    
    try:
        success = analyze_video_data(args.pose_results, args.output_dir)
        return success
    except Exception as e:
        print(f"Error in analysis: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)