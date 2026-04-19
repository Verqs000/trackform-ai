"""
Pose Extractor - Production Ready
Uses YOLOv8n-pose (Ultralytics) — no external model file required
Supports: sprint, hurdles, shot_put, discus, javelin
"""

import cv2
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime


# COCO 17-point keypoint index → name mapping
_COCO_KP_NAMES = [
    'nose',           # 0
    'left_eye',       # 1
    'right_eye',      # 2
    'left_ear',       # 3
    'right_ear',      # 4
    'left_shoulder',  # 5
    'right_shoulder', # 6
    'left_elbow',     # 7
    'right_elbow',    # 8
    'left_wrist',     # 9
    'right_wrist',    # 10
    'left_hip',       # 11
    'right_hip',      # 12
    'left_knee',      # 13
    'right_knee',     # 14
    'left_ankle',     # 15
    'right_ankle',    # 16
]

# Subset we actually track — matches the old MediaPipe key_points dict
# (minus heel/foot_index which COCO doesn't have; those are gracefully absent)
_TRACKED = {
    'nose':            0,
    'left_shoulder':   5,  'right_shoulder':  6,
    'left_elbow':      7,  'right_elbow':     8,
    'left_wrist':      9,  'right_wrist':     10,
    'left_hip':        11, 'right_hip':        12,
    'left_knee':       13, 'right_knee':       14,
    'left_ankle':      15, 'right_ankle':      16,
    # COCO has no heel/foot_index — these keys simply won't appear in points,
    # and TechniqueJudge already guards against missing keys gracefully.
}

# Confidence threshold below which a keypoint is marked not visible
_CONF_THRESHOLD = 0.5


class PoseExtractor:
    """Pose Extractor using YOLOv8n-pose (Ultralytics)."""

    def __init__(self, model_path: str = "yolov8n-pose.pt"):
        """
        model_path: path to a local .pt file, or a YOLOv8 model name
                    (e.g. 'yolov8n-pose.pt') which will be auto-downloaded
                    on first use from the Ultralytics CDN.
        """
        self.model = None
        self.key_points = _TRACKED
        self._initialize(model_path)

    def _initialize(self, model_path: str):
        try:
            from ultralytics import YOLO
        except ImportError:
            raise ImportError(
                "ultralytics is not installed. Add 'ultralytics' to requirements.txt."
            )

        self.model = YOLO(model_path)  # downloads automatically if not found locally
        print("✅ PoseExtractor initialized successfully (YOLOv8n-pose)")

    # ─── PUBLIC API ───────────────────────────────────────────────────────────

    def extract_from_video(
        self,
        video_path: str,
        event: str = "sprint",
        sample_every: int = 2,
        show_progress: bool = True
    ) -> Tuple[List[Dict], float]:
        """
        Extract poses from video.
        Returns: (list_of_pose_data, fps)
        """
        if self.model is None:
            raise RuntimeError("Model not initialized.")

        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        fps          = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        print(f"📹 Processing: {video_path.name} | {total_frames} frames @ {fps:.1f} FPS | Event: {event}")

        poses           = []
        frame_num       = 0
        processed_count = 0

        progress_bar = None
        if show_progress:
            try:
                import streamlit as st
                progress_bar = st.progress(0)
            except Exception:
                pass

        while True:
            success, image = cap.read()
            if not success:
                break

            frame_num += 1
            if frame_num % sample_every != 0:
                continue

            try:
                results = self.model(image, verbose=False)
            except Exception as e:
                print(f"⚠️ Frame {frame_num} detection error: {e}")
                continue

            # Pick the first detected person (highest confidence box)
            kps = self._get_best_person_keypoints(results)
            if kps is not None:
                pose_data = self._extract_landmarks(kps, frame_num, fps, event)
                poses.append(pose_data)
                processed_count += 1

            if progress_bar and frame_num % 10 == 0:
                progress = min(int((frame_num / total_frames) * 100), 100)
                progress_bar.progress(progress)

            if processed_count % 50 == 0 and processed_count > 0:
                print(f"   → Extracted {processed_count} poses...")

        cap.release()

        if progress_bar:
            progress_bar.progress(100)

        print(f"✅ Pose extraction complete: {len(poses)} poses from {frame_num} frames")

        if len(poses) == 0:
            raise ValueError(
                "No poses detected in video. Make sure the athlete is clearly "
                "visible and the video is not too dark or blurry."
            )

        return poses, float(fps)

    # ─── INTERNAL ─────────────────────────────────────────────────────────────

    def _get_best_person_keypoints(self, results) -> Optional[np.ndarray]:
        """
        Return keypoints array (17, 3) for the highest-confidence person,
        or None if no person detected.
        Each row: [x_norm, y_norm, confidence]
        """
        try:
            result = results[0]
            if result.keypoints is None or len(result.keypoints.data) == 0:
                return None

            # result.boxes.conf gives per-person confidence; pick argmax
            if result.boxes is not None and len(result.boxes.conf) > 0:
                best_idx = int(result.boxes.conf.argmax())
            else:
                best_idx = 0

            kps_raw = result.keypoints.data[best_idx]  # shape (17, 3) tensor

            # Normalize x,y to [0,1] relative to image dimensions
            h, w = result.orig_shape
            kps_norm = kps_raw.cpu().numpy().astype(float)
            kps_norm[:, 0] /= w   # x → [0,1]
            kps_norm[:, 1] /= h   # y → [0,1]
            # column 2 is already confidence in [0,1]

            return kps_norm
        except Exception:
            return None

    def _extract_landmarks(
        self,
        kps: np.ndarray,
        frame_num: int,
        fps: float,
        event: str = "sprint"
    ) -> Dict:
        """Build a pose dict from a (17,3) COCO keypoints array."""
        data = {
            'frame': frame_num,
            'time':  round(frame_num / fps, 3),
            'event': event,
            'points': {}
        }

        for name, idx in _TRACKED.items():
            if idx < len(kps):
                x, y, conf = kps[idx]
                data['points'][name] = {
                    'x':        round(float(x),    4),
                    'y':        round(float(y),    4),
                    'z':        0.0,                   # YOLO 2-D; z always 0
                    'visible':  float(conf) >= _CONF_THRESHOLD,
                    'presence': float(conf) >= _CONF_THRESHOLD,
                }

        data['angles'] = self._compute_angles(data['points'], event)
        return data

    def _compute_angles(self, points: Dict, event: str) -> Dict:
        """Compute biomechanical angles — identical logic to old MediaPipe version."""
        angles = {}

        def angle_between(a, b, c) -> Optional[float]:
            try:
                if not all(k in points for k in [a, b, c]):
                    return None
                if not all(points[k].get('visible', False) for k in [a, b, c]):
                    return None
                pa = np.array([points[a]['x'], points[a]['y']])
                pb = np.array([points[b]['x'], points[b]['y']])
                pc = np.array([points[c]['x'], points[c]['y']])
                v1 = pa - pb
                v2 = pc - pb
                cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
                return round(float(np.degrees(np.arccos(np.clip(cos_angle, -1, 1)))), 2)
            except Exception:
                return None

        # Universal angles
        angles['left_knee_angle']   = angle_between('left_hip',       'left_knee',   'left_ankle')
        angles['right_knee_angle']  = angle_between('right_hip',      'right_knee',  'right_ankle')
        angles['left_elbow_angle']  = angle_between('left_shoulder',  'left_elbow',  'left_wrist')
        angles['right_elbow_angle'] = angle_between('right_shoulder', 'right_elbow', 'right_wrist')
        angles['left_hip_angle']    = angle_between('left_shoulder',  'left_hip',    'left_knee')
        angles['right_hip_angle']   = angle_between('right_shoulder', 'right_hip',   'right_knee')

        if event == 'hurdles':
            angles['lead_leg_angle']   = angle_between('right_hip',  'right_knee', 'right_ankle')
            angles['trail_leg_angle']  = angle_between('left_hip',   'left_knee',  'left_ankle')
            angles['torso_lean']       = angle_between('nose',        'left_shoulder', 'left_hip')
            # COCO has no foot_index — ankle_flex omitted (judge handles missing angles)

        elif event == 'sprint':
            angles['trunk_angle'] = angle_between('left_shoulder', 'left_hip', 'left_knee')

        elif event in ['shot_put', 'discus', 'javelin']:
            angles['throwing_arm_angle']    = angle_between('right_shoulder', 'right_elbow', 'right_wrist')
            angles['shoulder_hip_rotation'] = angle_between('left_shoulder',  'right_shoulder', 'right_hip')

        return {k: v for k, v in angles.items() if v is not None}

    # ─── PERSISTENCE ─────────────────────────────────────────────────────────

    def save_poses(self, poses: List[Dict], output_path: str):
        """Save extracted poses to JSON."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump({
                'metadata': {
                    'extracted_at': datetime.now().isoformat(),
                    'total_poses':  len(poses),
                    'event':        poses[0].get('event', 'unknown') if poses else 'unknown'
                },
                'poses': poses
            }, f, indent=2)

        print(f"💾 Saved poses to: {output_path}")


if __name__ == "__main__":
    extractor = PoseExtractor()
    print("✅ PoseExtractor initialized successfully")
    print("Tracking keypoints:", list(extractor.key_points.keys()))