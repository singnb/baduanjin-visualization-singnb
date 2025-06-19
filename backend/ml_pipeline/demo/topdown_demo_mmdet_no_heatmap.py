# Copyright (c) OpenMMLab. All rights reserved.
# type: ignore

import mimetypes
import os
import time
from argparse import ArgumentParser

import cv2
import json_tricks as json
import mmcv
import mmengine
import numpy as np

# Updated imports for mmpose 1.3.2
from mmpose.apis import MMPoseInferencer
from mmpose.evaluation.functional import nms

try:
    from mmdet.apis import inference_detector, init_detector
    has_mmdet = True
except (ImportError, ModuleNotFoundError):
    has_mmdet = False

def process_one_image(args,
                      img,
                      detector,
                      pose_inferencer,
                      show_interval=0):
    """Process one image with pose estimation."""
    
    try:
        # predict bbox using mmdet
        det_result = inference_detector(detector, img)
        pred_instance = det_result.pred_instances.cpu().numpy()
        bboxes = np.concatenate(
            (pred_instance.bboxes, pred_instance.scores[:, None]), axis=1)
        bboxes = bboxes[np.logical_and(pred_instance.labels == args.det_cat_id,
                                       pred_instance.scores > args.bbox_thr)]
        bboxes = bboxes[nms(bboxes, args.nms_thr), :4]

        # Handle image input and fix paths for Windows
        if isinstance(img, str):
            # Use the input image path directly
            img_path = os.path.normpath(img)  # Normalize path for Windows
            img_array = mmcv.imread(img, channel_order='rgb')
        else:
            # Create temporary image with proper Windows path handling
            temp_dir = os.path.normpath(args.output_root) if args.output_root else "temp"
            os.makedirs(temp_dir, exist_ok=True)
            img_path = os.path.join(temp_dir, 'temp_frame.jpg')
            img_path = os.path.normpath(img_path)  # Normalize for Windows
            
            cv2.imwrite(img_path, img)
            img_array = mmcv.bgr2rgb(img)

        # Run pose estimation with Windows-compatible path
        try:
            # Simple approach - just run MMPoseInferencer without complex output dir
            result_generator = pose_inferencer(img_path, show=False)
            results = next(result_generator)
            
            # Extract predictions
            if isinstance(results, dict) and 'predictions' in results:
                predictions = results['predictions'][0] if results['predictions'] else []
            else:
                predictions = []
            
            if len(predictions) > 0:
                print(f"Found {len(predictions)} predictions")
            
            # Return predictions in format compatible with results_analysis.py
            return predictions, img_array
            
        except Exception as e:
            print(f"Error in MMPoseInferencer: {e}")
            # Return empty predictions but still return the image
            return [], img_array
    
    except Exception as e:
        print(f"Error in process_one_image: {e}")
        # Always return something to avoid None unpacking error
        if isinstance(img, str):
            img_array = mmcv.imread(img, channel_order='rgb')
        else:
            img_array = mmcv.bgr2rgb(img)
        return [], img_array

def convert_predictions_to_results_format(predictions):
    """Convert MMPoseInferencer predictions to format expected by results_analysis.py"""
    converted = []
    for pred in predictions:
        try:
            # Ensure keypoints are in the right format [[x1, y1], [x2, y2], ...]
            keypoints = pred.get('keypoints', [])
            if isinstance(keypoints, np.ndarray):
                keypoints = keypoints.tolist()
            
            # Ensure keypoint_scores are in the right format [score1, score2, ...]
            keypoint_scores = pred.get('keypoint_scores', [])
            if isinstance(keypoint_scores, np.ndarray):
                keypoint_scores = keypoint_scores.tolist()
            
            # Ensure bbox is in the right format [x1, y1, x2, y2]
            bbox = pred.get('bbox', [])
            if isinstance(bbox, np.ndarray):
                bbox = bbox.tolist()
            
            converted_pred = {
                'keypoints': keypoints,
                'keypoint_scores': keypoint_scores,
                'bbox': bbox
            }
            converted.append(converted_pred)
        except Exception as e:
            print(f"Warning: Error converting prediction: {e}")
            continue
    return converted

def visualize_pose(img, predictions, kpt_thr=0.3):
    """Simple pose visualization function."""
    img_vis = img.copy()
    
    # COCO skeleton connections
    skeleton = [
        [15, 13], [13, 11], [16, 14], [14, 12], [11, 12],
        [5, 11], [6, 12], [5, 6], [5, 7], [6, 8],
        [7, 9], [8, 10], [1, 2], [0, 1], [0, 2],
        [1, 3], [2, 4], [3, 5], [4, 6]
    ]
    
    for pred in predictions:
        keypoints = pred.get('keypoints', [])
        scores = pred.get('keypoint_scores', [])
        
        if not keypoints or not scores:
            continue
            
        # Draw keypoints
        for i, (x, y) in enumerate(keypoints):
            if i < len(scores) and scores[i] > kpt_thr:
                cv2.circle(img_vis, (int(x), int(y)), 3, (0, 255, 0), -1)
        
        # Draw skeleton
        for connection in skeleton:
            pt1_idx, pt2_idx = connection
            if (pt1_idx < len(keypoints) and pt2_idx < len(keypoints) and 
                pt1_idx < len(scores) and pt2_idx < len(scores) and
                scores[pt1_idx] > kpt_thr and scores[pt2_idx] > kpt_thr):
                
                pt1 = (int(keypoints[pt1_idx][0]), int(keypoints[pt1_idx][1]))
                pt2 = (int(keypoints[pt2_idx][0]), int(keypoints[pt2_idx][1]))
                cv2.line(img_vis, pt1, pt2, (255, 0, 0), 2)
    
    return img_vis

def main():
    """Visualize the demo images.
    Using mmdet to detect the human and mmpose 1.3.2 for pose estimation.
    """
    parser = ArgumentParser()
    parser.add_argument('det_config', help='Config file for detection')
    parser.add_argument('det_checkpoint', help='Checkpoint file for detection')
    parser.add_argument(
        '--pose-model', 
        type=str, 
        default='human', 
        help='Pose model type (human, hand, face, animal, wholebody)')
    parser.add_argument(
        '--input', type=str, default='', help='Image/Video file')
    parser.add_argument(
        '--show',
        action='store_true',
        default=False,
        help='whether to show img')
    parser.add_argument(
        '--output-root',
        type=str,
        default='',
        help='root of the output img file. '
        'Default not saving the visualization images.')
    parser.add_argument(
        '--save-predictions',
        action='store_true',
        default=False,
        help='whether to save predicted results')
    # parser.add_argument(
    #     '--device', default='cuda:0', help='Device used for inference')
    parser.add_argument(
        '--device', default='cpu', help='Device used for inference')
    parser.add_argument(
        '--det-cat-id',
        type=int,
        default=0,
        help='Category id for bounding box detection model')
    parser.add_argument(
        '--bbox-thr',
        type=float,
        default=0.3,
        help='Bounding box score threshold')
    parser.add_argument(
        '--nms-thr',
        type=float,
        default=0.3,
        help='IoU threshold for bounding box NMS')
    parser.add_argument(
        '--kpt-thr',
        type=float,
        default=0.3,
        help='Visualizing keypoint thresholds')
    parser.add_argument(
        '--show-kpt-idx',
        action='store_true',
        default=False,
        help='Whether to show the index of keypoints')
    parser.add_argument(
        '--skeleton-style',
        default='mmpose',
        type=str,
        choices=['mmpose', 'openpose'],
        help='Skeleton style selection')
    parser.add_argument(
        '--radius',
        type=int,
        default=3,
        help='Keypoint radius for visualization')
    parser.add_argument(
        '--thickness',
        type=int,
        default=1,
        help='Link thickness for visualization')
    parser.add_argument(
        '--show-interval', type=int, default=0, help='Sleep seconds per frame')
    parser.add_argument(
        '--alpha', type=float, default=0.8, help='The transparency of bboxes')
    parser.add_argument(
        '--draw-bbox', action='store_true', help='Draw bboxes of instances')

    assert has_mmdet, 'Please install mmdet to run the demo.'

    args = parser.parse_args()

    assert args.show or (args.output_root != '')
    assert args.input != ''
    assert args.det_config is not None
    assert args.det_checkpoint is not None

    # Fix Windows path handling
    if args.output_root:
        args.output_root = os.path.normpath(args.output_root)
        mmengine.mkdir_or_exist(args.output_root)
        
    if args.input:
        args.input = os.path.normpath(args.input)

    output_file = None
    if args.output_root:
        output_file = os.path.join(args.output_root, os.path.basename(args.input))
        output_file = os.path.normpath(output_file)

    if args.save_predictions:
        assert args.output_root != ''
        args.pred_save_path = os.path.join(args.output_root, f'results_{os.path.splitext(os.path.basename(args.input))[0]}.json')
        args.pred_save_path = os.path.normpath(args.pred_save_path)

    # build detector
    detector = init_detector(
        args.det_config, args.det_checkpoint, device=args.device)
    
    # build pose estimator using new API - simplified initialization
    try:
        pose_inferencer = MMPoseInferencer('human')  # Simplest approach
        print("MMPoseInferencer initialized successfully")
    except Exception as e:
        print(f"Error initializing MMPoseInferencer: {e}")
        return

    # Determine input type (removed webcam support as requested)
    input_type = mimetypes.guess_type(args.input)[0]
    if input_type:
        input_type = input_type.split('/')[0]
    else:
        # Default to video for uploaded files
        input_type = 'video'

    if input_type == 'image':
        # inference
        try:
            predictions, img_array = process_one_image(
                args, args.input, detector, pose_inferencer)

            print(f"Detected {len(predictions)} pose instances")
            
            if args.save_predictions:
                # Convert predictions to format expected by results_analysis.py
                pred_instances_list = convert_predictions_to_results_format(predictions)
                
                # Create frame data in the format expected by results_analysis.py
                frame_data = {
                    "frame_id": 1,
                    "instances": pred_instances_list
                }

                # Create metadata compatible with results_analysis.py
                meta_info = {
                    'dataset_name': 'coco',
                    'paper_info': {'title': 'Microsoft COCO: Common Objects in Context'},
                    'keypoint_info': {
                        # Create keypoint info that results_analysis.py expects
                        'keypoint_0': {'name': 'nose', 'id': 0},
                        'keypoint_1': {'name': 'left_eye', 'id': 1},
                        'keypoint_2': {'name': 'right_eye', 'id': 2},
                        'keypoint_3': {'name': 'left_ear', 'id': 3},
                        'keypoint_4': {'name': 'right_ear', 'id': 4},
                        'keypoint_5': {'name': 'left_shoulder', 'id': 5},
                        'keypoint_6': {'name': 'right_shoulder', 'id': 6},
                        'keypoint_7': {'name': 'left_elbow', 'id': 7},
                        'keypoint_8': {'name': 'right_elbow', 'id': 8},
                        'keypoint_9': {'name': 'left_wrist', 'id': 9},
                        'keypoint_10': {'name': 'right_wrist', 'id': 10},
                        'keypoint_11': {'name': 'left_hip', 'id': 11},
                        'keypoint_12': {'name': 'right_hip', 'id': 12},
                        'keypoint_13': {'name': 'left_knee', 'id': 13},
                        'keypoint_14': {'name': 'right_knee', 'id': 14},
                        'keypoint_15': {'name': 'left_ankle', 'id': 15},
                        'keypoint_16': {'name': 'right_ankle', 'id': 16}
                    }
                }
                
                # Save in format expected by results_analysis.py
                final_data = {
                    "meta_info": meta_info,
                    "instance_info": [frame_data]
                }
                
                with open(args.pred_save_path, 'w') as f:
                    json.dump(final_data, f, indent='\t')
                print(f'Predictions saved at {args.pred_save_path}')
        
        except Exception as e:
            print(f"Error processing image: {e}")
            import traceback
            traceback.print_exc()

    elif input_type == 'video':
        print(f"Starting video processing: {args.input}")
        
        # Open the uploaded video file
        cap = cv2.VideoCapture(args.input)

        if not cap.isOpened():
            print(f"Error: Could not open video {args.input}")
            return

        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"Video info: {total_frames} frames, {fps} FPS, {width}x{height}")

        # ========== ADD THIS: CPU OPTIMIZATION LOGIC ==========
        # Calculate frame skip for target FPS (e.g., 10 FPS from 30 FPS = skip 2 frames, process 1)
        target_fps = 10  # Target processing FPS for faster analysis
        frame_skip = max(1, fps // target_fps)
        print(f"CPU optimization: Processing every {frame_skip} frames (target {target_fps} FPS)")
        # ======================================================

        video_writer = None
        pred_instances_list = []
        frame_idx = 0
        processed_frames = 0  # ADD THIS: Track actually processed frames

        # Process each frame of the uploaded video
        while cap.isOpened():
            success, frame = cap.read()
            frame_idx += 1

            if not success:
                print(f"Finished processing video at frame {frame_idx-1}")
                break

            # ========== ADD THIS: FRAME SKIPPING LOGIC ==========
            # Skip frames to reduce processing load
            if (frame_idx - 1) % frame_skip != 0:  # frame_idx starts at 1, so subtract 1
                continue  # Skip this frame, go to next iteration
            # ===================================================

            # Show progress every 30 PROCESSED frames (not total frames)
            if processed_frames % 30 == 0 and processed_frames > 0:  # MODIFY THIS LINE
                print(f"Processing frame {frame_idx}/{total_frames} (processed: {processed_frames})")

            try:
                # Pose estimation for current frame
                predictions, img_array = process_one_image(
                    args, frame, detector, pose_inferencer, 0)

                if args.save_predictions and predictions:
                    # Convert predictions to format expected by results_analysis.py
                    converted_predictions = convert_predictions_to_results_format(predictions)
                    
                    # Save prediction results for this frame in the correct format
                    frame_data = {
                        "frame_id": frame_idx,  # Keep original frame number for timing
                        "instances": converted_predictions
                    }
                    pred_instances_list.append(frame_data)

                # Create visualization with pose overlay
                frame_vis = visualize_pose(frame, predictions, args.kpt_thr)

                # Save output video with pose analysis
                if output_file:
                    if video_writer is None:
                        # ========== MODIFY THIS: Use target FPS for output ==========
                        # Initialize video writer for output with reduced FPS
                        output_fps = min(fps, target_fps)  # Use target FPS for output
                        codecs_to_try = ['mp4v', 'XVID', 'MJPG', 'X264']
                        video_writer = None
                        
                        for codec in codecs_to_try:
                            try:
                                fourcc = cv2.VideoWriter_fourcc(*codec)
                                temp_writer = cv2.VideoWriter(
                                    output_file,
                                    fourcc,
                                    output_fps,  # Use reduced FPS
                                    (frame_vis.shape[1], frame_vis.shape[0]))
                                
                                if temp_writer.isOpened():
                                    video_writer = temp_writer
                                    print(f"Creating output video with {codec} codec at {output_fps} FPS: {output_file}")
                                    break
                                else:
                                    temp_writer.release()
                            except:
                                continue
                        
                        if video_writer is None:
                            print("Warning: Could not initialize video writer with any codec")
                            continue
                        # ============================================================

                    video_writer.write(frame_vis)

                processed_frames += 1  # ADD THIS: Increment processed frame counter

            except Exception as e:
                print(f"Error processing frame {frame_idx}: {e}")

            time.sleep(args.show_interval)

        # Clean up video processing
        if video_writer:
            video_writer.release()
            print(f"Output video saved: {output_file}")

        cap.release()
        print(f"Video processing complete: {processed_frames}/{total_frames} frames processed ({processed_frames/total_frames*100:.1f}%)") 

        # Save predictions in format expected by results_analysis.py
        if args.save_predictions and pred_instances_list:
            # Create metadata compatible with results_analysis.py
            meta_info = {
                'dataset_name': 'coco',  
                'paper_info': {'title': 'Microsoft COCO: Common Objects in Context'},
                'keypoint_info': {
                    # Create keypoint info mapping that results_analysis.py expects
                    'keypoint_0': {'name': 'nose', 'id': 0},
                    'keypoint_1': {'name': 'left_eye', 'id': 1},
                    'keypoint_2': {'name': 'right_eye', 'id': 2},
                    'keypoint_3': {'name': 'left_ear', 'id': 3},
                    'keypoint_4': {'name': 'right_ear', 'id': 4},
                    'keypoint_5': {'name': 'left_shoulder', 'id': 5},
                    'keypoint_6': {'name': 'right_shoulder', 'id': 6},
                    'keypoint_7': {'name': 'left_elbow', 'id': 7},
                    'keypoint_8': {'name': 'right_elbow', 'id': 8},
                    'keypoint_9': {'name': 'left_wrist', 'id': 9},
                    'keypoint_10': {'name': 'right_wrist', 'id': 10},
                    'keypoint_11': {'name': 'left_hip', 'id': 11},
                    'keypoint_12': {'name': 'right_hip', 'id': 12},
                    'keypoint_13': {'name': 'left_knee', 'id': 13},
                    'keypoint_14': {'name': 'right_knee', 'id': 14},
                    'keypoint_15': {'name': 'left_ankle', 'id': 15},
                    'keypoint_16': {'name': 'right_ankle', 'id': 16}
                }
            }
            
            # Final JSON structure that results_analysis.py expects
            final_data = {
                "meta_info": meta_info,
                "instance_info": pred_instances_list
            }
            
            with open(args.pred_save_path, 'w') as f:
                json.dump(final_data, f, indent='\t')
            print(f'Predictions saved: {args.pred_save_path}')
            print(f'Total frames with predictions: {len(pred_instances_list)}')
        
    else:
        raise ValueError(f'file {os.path.basename(args.input)} has invalid format.')

if __name__ == '__main__':
    main()
