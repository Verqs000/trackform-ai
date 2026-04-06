"""
Pose Extractor - Tracks body points in videos
MediaPipe 0.10.33+ version (new API)
"""

import cv2
import numpy as np
import json
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions

class PoseExtractor:
    def __init__(self):
        # Set up the new MediaPipe Pose Landmarker
        base_options = BaseOptions(model_asset_path="pose_landmarker.task")
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.landmarker = vision.PoseLandmarker.create_from_options(options)
        
        # Body parts we track
        self.key_points = {
            'nose': 0,
            'left_shoulder': 11, 'right_shoulder': 12,
            'left_elbow': 13, 'right_elbow': 14,
            'left_wrist': 15, 'right_wrist': 16,
            'left_hip': 23, 'right_hip': 24,
            'left_knee': 25, 'right_knee': 26,
            'left_ankle': 27, 'right_ankle': 28,
        }
    
    def extract_from_video(self, video_path, sample_every=2):
        print(f"Opening video: {video_path}")
        
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"Video: {total_frames} frames, {fps:.1f} FPS")
        
        poses = []
        frame_num = 0
        
        while True:
            success, image = cap.read()
            if not success:
                break
            
            frame_num += 1
            if frame_num % sample_every != 0:
                continue
            
            # Convert to RGB and create MediaPipe Image
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
            
            # Get pose with timestamp
            timestamp_ms = int((frame_num / fps) * 1000)
            results = self.landmarker.detect_for_video(mp_image, timestamp_ms)
            
            if results.pose_landmarks:
                pose_data = self._extract_landmarks(results.pose_landmarks[0], frame_num, fps)
                poses.append(pose_data)
                
                if len(poses) % 30 == 0:
                    print(f"  Processed {len(poses)} poses...")
        
        cap.release()
        
        return {
            'poses': poses,
            'fps': fps,
            'total_frames': total_frames,
            'duration_seconds': total_frames / fps,
            'poses_extracted': len(poses)
        }
    
    def _extract_landmarks(self, pose_landmarks, frame_num, fps):
        data = {
            'frame': frame_num,
            'time': frame_num / fps,
            'points': {}
        }
        
        for name, idx in self.key_points.items():
            if idx < len(pose_landmarks):
                lm = pose_landmarks[idx]
                data['points'][name] = {
                    'x': lm.x,
                    'y': lm.y,
                    'z': lm.z,
                    'visible': lm.visibility > 0.5
                }
        
        return data
    
    def save(self, pose_data, output_path):
        with open(output_path, 'w') as f:
            json.dump(pose_data, f, indent=2)
        print(f"Saved to: {output_path}")


if __name__ == "__main__":
    print("PoseExtractor loaded for MediaPipe 0.10.33!")
    print("Tracking:", list(PoseExtractor().key_points.keys()))