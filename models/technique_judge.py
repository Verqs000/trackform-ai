"""
Technique Judge - Production Ready
Analyzes track & field technique with robust scoring and coaching feedback
Supports: sprint, hurdles, shot_put, discus, javelin
"""

import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime


class TechniqueJudge:
    """Analyzes athletic technique for sprint, hurdles, and throwing events."""

    def __init__(self):
        self.pro_standards = {
            'sprint': {
                'ideal_block_torso_angle': 48,
                'min_block_torso_angle': 38,
                'ideal_drive_phase_frames': 18,
                'min_drive_phase_frames': 10,
                'good_knee_lift': 0.04,
                'max_arm_asymmetry': 18,
            },
            'hurdles': {
                'ideal_lead_leg_angle': 165,      # nearly straight at peak clearance
                'min_lead_leg_angle': 140,         # too bent = clipping hurdle
                'ideal_trail_leg_angle': 90,       # trail leg tucked tight
                'max_trail_leg_angle': 120,        # too open = dragging trail leg
                'ideal_torso_lean': 30,            # forward lean over hurdle
                'max_torso_lean': 55,              # too upright
                'ideal_takeoff_distance': 0.18,   # normalized to frame width
                'ideal_landing_distance': 0.12,
            },
            'shot_put': {
                'ideal_release_angle': 38,
                'release_tolerance': 7,
                'min_hip_shoulder_sep': 42,
                'ideal_hip_shoulder_sep': 52,
            },
            'discus': {
                'ideal_release_angle': 40,
                'release_tolerance': 8,
                'min_hip_shoulder_sep': 45,
            },
            'javelin': {
                'ideal_release_angle': 34,
                'release_tolerance': 6,
                'min_hip_shoulder_sep': 38,
                'min_arm_extension': 0.65,
            }
        }

    def analyze(self, poses: List[Dict], event: str = 'sprint', fps: float = 30.0) -> Dict:
        """Main analysis entry point. Accepts list of pose dicts directly."""
        if not poses or not isinstance(poses, list):
            return self._empty_result("No pose data provided")

        if len(poses) < 8:
            return self._empty_result("Video too short for meaningful analysis")

        phases  = self._detect_phases(poses, event)
        metrics = self._calculate_metrics(poses, phases, event, fps)
        errors  = self._identify_errors(metrics, phases, event)
        score   = self._calculate_score(metrics, errors, event)
        drills  = self._suggest_drills(errors)

        return {
            'event': event,
            'overall_score': round(score, 1),
            'metrics': {k: round(v, 3) if isinstance(v, float) else v for k, v in metrics.items()},
            'errors_found': len(errors),
            'errors': errors,
            'drills': drills,
            'summary': self._generate_summary(score, errors, event),
            'analyzed_at': datetime.now().isoformat()
        }

    # ─── PHASE DETECTION ─────────────────────────────────────────────────────

    def _detect_phases(self, poses: List[Dict], event: str) -> List[str]:
        phases = []
        for i, pose in enumerate(poses):
            if event == 'sprint':
                phases.append(self._detect_sprint_phase(pose, i, len(poses)))
            elif event == 'hurdles':
                phases.append(self._detect_hurdle_phase(pose, i, len(poses)))
            else:
                phases.append(self._detect_throw_phase(i, len(poses)))
        return phases

    def _detect_sprint_phase(self, pose: Dict, idx: int, total: int) -> str:
        torso = self._safe_torso_angle(pose)
        hip_y = self._get_point(pose, 'left_hip', 'y', 0.5)
        if idx < 10 and hip_y > 0.55 and torso > 30:
            return 'block_start'
        elif torso > 22:
            return 'drive_phase'
        else:
            return 'max_velocity'

    def _detect_hurdle_phase(self, pose: Dict, idx: int, total: int) -> str:
        """Detect hurdle clearance phases based on body position."""
        hip_y    = self._get_point(pose, 'left_hip', 'y', 0.5)
        knee_y   = self._get_point(pose, 'right_knee', 'y', 0.5)
        ankle_y  = self._get_point(pose, 'right_ankle', 'y', 0.5)

        # Airborne = both feet above typical ground level
        left_ankle_y  = self._get_point(pose, 'left_ankle', 'y', 0.9)
        right_ankle_y = self._get_point(pose, 'right_ankle', 'y', 0.9)
        avg_ankle_y   = (left_ankle_y + right_ankle_y) / 2

        if avg_ankle_y < 0.75:
            return 'clearance'       # Both feet off ground
        elif knee_y < hip_y - 0.05:
            return 'lead_leg_drive'  # Lead leg driving up
        else:
            return 'sprint'          # Between hurdles

    def _detect_throw_phase(self, idx: int, total: int) -> str:
        pct = idx / total
        if pct < 0.30:   return 'wind_up'
        elif pct < 0.60: return 'power_position'
        elif pct < 0.85: return 'delivery'
        else:            return 'release'

    # ─── SAFE HELPERS ────────────────────────────────────────────────────────

    def _get_point(self, pose: Dict, name: str, coord: str = 'y', default: float = 0.0) -> float:
        try:
            pt = pose.get('points', {}).get(name, {})
            if not pt.get('visible', False):
                return default
            return float(pt.get(coord, default))
        except:
            return default

    def _get_angle(self, pose: Dict, angle_name: str) -> Optional[float]:
        """Get precomputed angle from pose data if available."""
        try:
            return pose.get('angles', {}).get(angle_name)
        except:
            return None

    def _safe_torso_angle(self, pose: Dict) -> float:
        try:
            s  = pose['points']['left_shoulder']
            h  = pose['points']['left_hip']
            dx = s['x'] - h['x']
            dy = s['y'] - h['y']
            return float(np.degrees(np.arctan2(abs(dx), abs(dy))))
        except:
            return 0.0

    def _compute_angle(self, a, b, c) -> Optional[float]:
        """Compute angle at b given three (x,y) points."""
        try:
            v1 = np.array([a[0]-b[0], a[1]-b[1]])
            v2 = np.array([c[0]-b[0], c[1]-b[1]])
            cos = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
            return float(np.degrees(np.arccos(np.clip(cos, -1, 1))))
        except:
            return None

    # ─── METRICS CALCULATION ─────────────────────────────────────────────────

    def _calculate_metrics(self, poses: List[Dict], phases: List[str], event: str, fps: float) -> Dict:
        metrics = {}

        if event == 'sprint':
            metrics.update(self._sprint_metrics(poses, phases))

        elif event == 'hurdles':
            metrics.update(self._hurdles_metrics(poses, phases, fps))

        elif event in ['shot_put', 'discus', 'javelin']:
            metrics.update(self._throwing_metrics(poses, event))

        return metrics

    def _sprint_metrics(self, poses: List[Dict], phases: List[str]) -> Dict:
        m = {}
        block_frames = [i for i, p in enumerate(phases) if p == 'block_start']
        drive_frames = [i for i, p in enumerate(phases) if p == 'drive_phase']

        if block_frames:
            bp = poses[block_frames[0]]
            m['block_torso_angle'] = self._safe_torso_angle(bp)
            m['block_hip_height']  = self._get_point(bp, 'left_hip')

        m['drive_phase_duration_frames'] = len(drive_frames)

        if drive_frames:
            knee_lifts = []
            for i in drive_frames:
                knee_y = self._get_point(poses[i], 'left_knee')
                hip_y  = self._get_point(poses[i], 'left_hip')
                knee_lifts.append(hip_y - knee_y)
            m['avg_knee_lift'] = float(np.mean(knee_lifts)) if knee_lifts else 0.0

        return m

    def _hurdles_metrics(self, poses: List[Dict], phases: List[str], fps: float) -> Dict:
        m = {}
        clearance_frames = [i for i, p in enumerate(phases) if p == 'clearance']
        sprint_frames    = [i for i, p in enumerate(phases) if p == 'sprint']

        if not clearance_frames:
            # Fallback: estimate clearance as middle 20% of video
            mid = len(poses) // 2
            clearance_frames = list(range(max(0, mid-5), min(len(poses), mid+5)))

        # ── Lead leg angle at peak clearance ──
        lead_angles = []
        for i in clearance_frames:
            angle = self._get_angle(poses[i], 'lead_leg_angle')
            if angle is None:
                angle = self._get_angle(poses[i], 'right_knee_angle')
            if angle:
                lead_angles.append(angle)
        if lead_angles:
            m['lead_leg_angle'] = float(np.max(lead_angles))  # peak extension

        # ── Trail leg tuck angle ──
        trail_angles = []
        for i in clearance_frames:
            angle = self._get_angle(poses[i], 'trail_leg_angle')
            if angle is None:
                angle = self._get_angle(poses[i], 'left_knee_angle')
            if angle:
                trail_angles.append(angle)
        if trail_angles:
            m['trail_leg_angle'] = float(np.min(trail_angles))  # tightest tuck

        # ── Torso lean over hurdle ──
        torso_angles = []
        for i in clearance_frames:
            torso = self._safe_torso_angle(poses[i])
            if torso > 0:
                torso_angles.append(torso)
        if torso_angles:
            m['torso_lean_angle'] = float(np.mean(torso_angles))

        # ── Hip height during clearance (normalized) ──
        hip_heights = []
        for i in clearance_frames:
            hip_y = self._get_point(poses[i], 'left_hip', 'y', 0.5)
            hip_heights.append(hip_y)
        if hip_heights:
            m['clearance_hip_height'] = float(np.min(hip_heights))  # lowest = highest jump

        # ── Between-hurdle sprint quality ──
        if sprint_frames:
            knee_lifts = []
            for i in sprint_frames:
                knee_y = self._get_point(poses[i], 'left_knee', 'y')
                hip_y  = self._get_point(poses[i], 'left_hip', 'y')
                knee_lifts.append(hip_y - knee_y)
            m['sprint_knee_lift'] = float(np.mean(knee_lifts)) if knee_lifts else 0.0

        # ── Clearance duration (frames airborne) ──
        m['clearance_frames'] = len(clearance_frames)
        if fps > 0:
            m['clearance_duration_sec'] = round(len(clearance_frames) / fps, 3)

        return m

    def _throwing_metrics(self, poses: List[Dict], event: str) -> Dict:
        m = {}
        sep_values = []
        for p in poses:
            sep = self._hip_shoulder_separation(p)
            if sep > 10:
                sep_values.append(sep)
        m['hip_shoulder_separation'] = float(np.mean(sep_values)) if sep_values else 0.0

        if len(poses) > 5:
            last   = poses[-3:]
            angles = [self._release_angle(p) for p in last if self._release_angle(p) > 10]
            m['release_angle'] = float(np.mean(angles)) if angles else 0.0

        return m

    # ─── ANGLE HELPERS ───────────────────────────────────────────────────────

    def _hip_shoulder_separation(self, pose: Dict) -> float:
        try:
            ls = pose['points']['left_shoulder']
            rs = pose['points']['right_shoulder']
            lh = pose['points']['left_hip']
            rh = pose['points']['right_hip']
            shoulder_angle = np.arctan2(rs['y']-ls['y'], rs['x']-ls['x'])
            hip_angle      = np.arctan2(rh['y']-lh['y'], rh['x']-lh['x'])
            return float(np.degrees(abs(shoulder_angle - hip_angle)))
        except:
            return 0.0

    def _release_angle(self, pose: Dict) -> float:
        try:
            e  = pose['points']['right_elbow']
            w  = pose['points']['right_wrist']
            dy = w['y'] - e['y']
            dx = w['x'] - e['x']
            return float(np.degrees(np.arctan2(-dy, dx)))
        except:
            return 0.0

    # ─── ERROR IDENTIFICATION ─────────────────────────────────────────────────

    def _identify_errors(self, metrics: Dict, phases: List[str], event: str) -> List[Dict]:
        errors = []
        std    = self.pro_standards.get(event, {})

        if event == 'sprint':
            errors.extend(self._sprint_errors(metrics, std))
        elif event == 'hurdles':
            errors.extend(self._hurdles_errors(metrics, std))
        elif event in ['shot_put', 'discus', 'javelin']:
            errors.extend(self._throwing_errors(metrics, std, event))

        return errors

    def _sprint_errors(self, metrics: Dict, std: Dict) -> List[Dict]:
        errors = []
        angle  = metrics.get('block_torso_angle')
        if angle and angle < std.get('min_block_torso_angle', 38):
            errors.append({
                'type': 'poor_block_angle',
                'severity': 'high',
                'description': 'Popping up too early out of blocks',
                'fix': 'Drive chest toward the track and push the ground behind you.'
            })
        drive = metrics.get('drive_phase_duration_frames', 0)
        if drive < std.get('min_drive_phase_frames', 10):
            errors.append({
                'type': 'short_drive_phase',
                'severity': 'medium',
                'description': 'Coming upright too quickly',
                'fix': 'Stay low longer during acceleration phase. Aim for 30-40m before upright.'
            })
        return errors

    def _hurdles_errors(self, metrics: Dict, std: Dict) -> List[Dict]:
        errors = []

        # Lead leg too bent
        lead = metrics.get('lead_leg_angle')
        if lead is not None:
            if lead < std.get('min_lead_leg_angle', 140):
                errors.append({
                    'type': 'bent_lead_leg',
                    'severity': 'high',
                    'description': f'Lead leg too bent at clearance ({lead:.0f}°) — risk of clipping hurdle',
                    'fix': 'Attack the hurdle with a straighter lead leg. Drive your heel up and out aggressively.'
                })
            elif lead >= std.get('ideal_lead_leg_angle', 165):
                pass  # Perfect
            else:
                errors.append({
                    'type': 'lead_leg_suboptimal',
                    'severity': 'low',
                    'description': f'Lead leg extension good but can improve ({lead:.0f}°)',
                    'fix': 'Focus on snapping the lead leg straight at the peak of clearance.'
                })

        # Trail leg not tucked enough
        trail = metrics.get('trail_leg_angle')
        if trail is not None and trail > std.get('max_trail_leg_angle', 120):
            errors.append({
                'type': 'poor_trail_leg',
                'severity': 'high',
                'description': f'Trail leg not tucked tightly ({trail:.0f}°) — losing time over hurdle',
                'fix': 'Pull the trail leg through high and tight. Think knee to armpit.'
            })

        # Too upright over hurdle
        torso = metrics.get('torso_lean_angle')
        if torso is not None and torso > std.get('max_torso_lean', 55):
            errors.append({
                'type': 'insufficient_torso_lean',
                'severity': 'medium',
                'description': f'Not leaning forward enough over hurdle ({torso:.0f}°)',
                'fix': 'Drive your chest forward and down over the hurdle. Lead with your chin, not your chest.'
            })

        # Too much air time
        clearance_sec = metrics.get('clearance_duration_sec')
        if clearance_sec is not None and clearance_sec > 0.35:
            errors.append({
                'type': 'excessive_air_time',
                'severity': 'medium',
                'description': f'Spending too long in the air ({clearance_sec:.2f}s)',
                'fix': 'Attack the hurdle closer to minimize flight time. Think "step over" not "jump over".'
            })

        return errors

    def _throwing_errors(self, metrics: Dict, std: Dict, event: str) -> List[Dict]:
        errors = []
        sep   = metrics.get('hip_shoulder_separation', 0)
        min_sep = std.get('min_hip_shoulder_sep', 42)
        if sep < min_sep:
            errors.append({
                'type': 'insufficient_hip_shoulder_sep',
                'severity': 'high',
                'description': f'Not enough hip-shoulder separation ({sep:.0f}°)',
                'fix': 'Lead with your hips and delay the shoulder. Think "hips first, then throw."'
            })

        release = metrics.get('release_angle', 0)
        ideal   = std.get('ideal_release_angle', 38)
        tol     = std.get('release_tolerance', 7)
        if release > 0 and abs(release - ideal) > tol:
            direction = 'too high' if release > ideal else 'too low'
            errors.append({
                'type': 'poor_release_angle',
                'severity': 'medium',
                'description': f'Release angle {direction} ({release:.0f}° vs ideal {ideal}°)',
                'fix': f'Adjust release point to closer to {ideal}° for maximum distance.'
            })
        return errors

    # ─── SCORING ─────────────────────────────────────────────────────────────

    def _calculate_score(self, metrics: Dict, errors: List[Dict], event: str) -> float:
        score = 78.0

        if event == 'sprint':
            if metrics.get('block_torso_angle', 0) >= 45:
                score += 12
            if metrics.get('avg_knee_lift', 0) > 0.05:
                score += 8

        elif event == 'hurdles':
            lead = metrics.get('lead_leg_angle', 0)
            if lead >= 165:
                score += 12
            elif lead >= 150:
                score += 6

            trail = metrics.get('trail_leg_angle', 999)
            if trail <= 90:
                score += 10
            elif trail <= 110:
                score += 5

            torso = metrics.get('torso_lean_angle', 999)
            if torso <= 35:
                score += 8
            elif torso <= 45:
                score += 4

            clearance_sec = metrics.get('clearance_duration_sec', 999)
            if clearance_sec <= 0.25:
                score += 8
            elif clearance_sec <= 0.30:
                score += 4

        elif event in ['shot_put', 'discus', 'javelin']:
            if metrics.get('hip_shoulder_separation', 0) >= self.pro_standards[event].get('ideal_hip_shoulder_sep', 48):
                score += 10

        # Deduct for errors
        penalty = {'high': 22, 'medium': 12, 'low': 5}
        for error in errors:
            score -= penalty.get(error.get('severity', 'medium'), 10)

        return max(35, min(98, round(score, 1)))

    def _suggest_drills(self, errors: List[Dict]) -> List[str]:
        drill_map = {
            'bent_lead_leg':              'Lead leg wall drills — 3x10 each side',
            'lead_leg_suboptimal':        'Standing hurdle lead leg swings — 3x10',
            'poor_trail_leg':             'Trail leg cycles on a low hurdle — 3x8 each side',
            'insufficient_torso_lean':    'Lean drills over mini hurdles — focus on chin driving forward',
            'excessive_air_time':         'Quick step-over drills on 6-inch hurdles — fast feet',
            'poor_block_angle':           'Resisted sled starts — stay low for 20m',
            'short_drive_phase':          'Wall drive drills — 3x10 each leg',
            'insufficient_hip_shoulder_sep': 'Medicine ball rotational throws — 3x8',
            'poor_release_angle':         'Release angle shadow throws with coach feedback',
        }
        drills = []
        for error in errors:
            drill = drill_map.get(error.get('type'))
            if drill and drill not in drills:
                drills.append(drill)
            elif error.get('fix') and error['fix'] not in drills:
                drills.append(error['fix'])
        return drills

    def _generate_summary(self, score: float, errors: List[Dict], event: str = '') -> str:
        event_name = event.replace('_', ' ').title() if event else ''
        if score >= 85:
            return f"Excellent {event_name} technique! You're competing at a high level."
        elif score >= 72:
            return f"Good {event_name} foundation. Focus on the highlighted areas for quick gains."
        elif score >= 55:
            return f"Several important {event_name} technique issues. Consistent drill work will help a lot."
        else:
            return f"Major {event_name} technique faults detected. Start with fundamentals before adding speed/intensity."

    def _empty_result(self, reason: str) -> Dict:
        return {
            'event': 'unknown',
            'overall_score': 0,
            'metrics': {},
            'errors_found': 0,
            'errors': [],
            'drills': [],
            'summary': reason,
            'analyzed_at': datetime.now().isoformat()
        }


if __name__ == "__main__":
    judge = TechniqueJudge()
    print("✅ TechniqueJudge loaded successfully")
    print("Supported events: sprint, hurdles, shot_put, discus, javelin")