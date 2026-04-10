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
                'ideal_block_torso_angle':   48,
                'min_block_torso_angle':     38,
                'ideal_drive_phase_frames':  18,
                'min_drive_phase_frames':    10,
                'good_knee_lift':            0.04,
                'max_arm_asymmetry':         18,
            },
            'hurdles': {
                'ideal_lead_leg_angle':      165,
                'min_lead_leg_angle':        140,
                'ideal_trail_leg_angle':     90,
                'max_trail_leg_angle':       120,
                'ideal_torso_lean':          30,
                'max_torso_lean':            55,
            },
            'shot_put': {
                'ideal_release_angle':       38,
                'release_tolerance':         7,
                'min_hip_shoulder_sep':      42,
                'ideal_hip_shoulder_sep':    52,
                'min_elbow_height':          0.35,   # elbow above hip line
                'ideal_knee_bend':           110,    # glide stance
                'min_trunk_rotation':        40,     # degrees of trunk turn
            },
            'discus': {
                'ideal_release_angle':       40,
                'release_tolerance':         8,
                'min_hip_shoulder_sep':      45,
                'ideal_hip_shoulder_sep':    55,
                'min_trunk_rotation':        50,
                'ideal_knee_bend':           115,
            },
            'javelin': {
                'ideal_release_angle':       34,
                'release_tolerance':         6,
                'min_hip_shoulder_sep':      38,
                'ideal_hip_shoulder_sep':    48,
                'min_arm_extension':         155,    # degrees at elbow at release
                'min_trunk_lean_back':       15,     # backward lean at power pos
                'ideal_elbow_height':        0.3,    # elbow above shoulder line
            }
        }

    def analyze(self, poses: List[Dict], event: str = 'sprint', fps: float = 30.0) -> Dict:
        if not poses or not isinstance(poses, list):
            return self._empty_result("No pose data provided")
        if len(poses) < 8:
            return self._empty_result("Video too short for meaningful analysis")

        phases  = self._detect_phases(poses, event)
        metrics = self._calculate_metrics(poses, phases, event, fps)
        errors  = self._identify_errors(metrics, phases, event)
        score   = self._calculate_score(metrics, errors, event)
        drills  = self._suggest_drills(errors, event)

        return {
            'event':         event,
            'overall_score': round(score, 1),
            'metrics':       {k: round(v, 3) if isinstance(v, float) else v for k, v in metrics.items()},
            'errors_found':  len(errors),
            'errors':        errors,
            'drills':        drills,
            'summary':       self._generate_summary(score, errors, event),
            'analyzed_at':   datetime.now().isoformat()
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
        left_ankle_y  = self._get_point(pose, 'left_ankle',  'y', 0.9)
        right_ankle_y = self._get_point(pose, 'right_ankle', 'y', 0.9)
        avg_ankle_y   = (left_ankle_y + right_ankle_y) / 2
        knee_y        = self._get_point(pose, 'right_knee', 'y', 0.5)
        hip_y         = self._get_point(pose, 'left_hip',   'y', 0.5)
        if avg_ankle_y < 0.75:
            return 'clearance'
        elif knee_y < hip_y - 0.05:
            return 'lead_leg_drive'
        else:
            return 'sprint'

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

    def _get_point_raw(self, pose: Dict, name: str) -> Optional[Dict]:
        """Return full point dict (x,y,z,visible) or None."""
        try:
            pt = pose.get('points', {}).get(name, {})
            if pt.get('visible', False):
                return pt
            return None
        except:
            return None

    def _get_angle(self, pose: Dict, angle_name: str) -> Optional[float]:
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

    def _compute_angle_pts(self, a, b, c) -> Optional[float]:
        """Compute angle at b given three (x,y) tuples."""
        try:
            v1  = np.array([a[0]-b[0], a[1]-b[1]])
            v2  = np.array([c[0]-b[0], c[1]-b[1]])
            cos = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
            return float(np.degrees(np.arccos(np.clip(cos, -1, 1))))
        except:
            return None

    def _pt_to_tuple(self, pt: Dict) -> Tuple[float, float]:
        return (float(pt['x']), float(pt['y']))

    # ─── METRICS CALCULATION ─────────────────────────────────────────────────

    def _calculate_metrics(self, poses: List[Dict], phases: List[str], event: str, fps: float) -> Dict:
        if event == 'sprint':
            return self._sprint_metrics(poses, phases)
        elif event == 'hurdles':
            return self._hurdles_metrics(poses, phases, fps)
        elif event == 'shot_put':
            return self._shot_put_metrics(poses, phases)
        elif event == 'discus':
            return self._discus_metrics(poses, phases)
        elif event == 'javelin':
            return self._javelin_metrics(poses, phases)
        return {}

    # ── SPRINT ───────────────────────────────────────────────────────────────

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
            arm_diffs  = []
            for i in drive_frames:
                pose   = poses[i]
                knee_y = self._get_point(pose, 'left_knee')
                hip_y  = self._get_point(pose, 'left_hip')
                knee_lifts.append(hip_y - knee_y)

                le = self._get_angle(pose, 'left_elbow_angle')
                re = self._get_angle(pose, 'right_elbow_angle')
                if le and re:
                    arm_diffs.append(abs(le - re))

            m['avg_knee_lift']      = float(np.mean(knee_lifts)) if knee_lifts else 0.0
            m['arm_asymmetry_deg']  = float(np.mean(arm_diffs))  if arm_diffs  else 0.0

        # Trunk lean at max velocity
        max_vel = [i for i, p in enumerate(phases) if p == 'max_velocity']
        if max_vel:
            leans = [self._safe_torso_angle(poses[i]) for i in max_vel]
            m['max_velocity_trunk_lean'] = float(np.mean(leans))

        return m

    # ── HURDLES ──────────────────────────────────────────────────────────────

    def _hurdles_metrics(self, poses: List[Dict], phases: List[str], fps: float) -> Dict:
        m = {}
        clearance_frames = [i for i, p in enumerate(phases) if p == 'clearance']

        if not clearance_frames:
            mid = len(poses) // 2
            clearance_frames = list(range(max(0, mid-5), min(len(poses), mid+5)))

        lead_angles, trail_angles, torso_angles, hip_heights = [], [], [], []

        for i in clearance_frames:
            pose = poses[i]

            a = self._get_angle(pose, 'lead_leg_angle') or self._get_angle(pose, 'right_knee_angle')
            if a: lead_angles.append(a)

            t = self._get_angle(pose, 'trail_leg_angle') or self._get_angle(pose, 'left_knee_angle')
            if t: trail_angles.append(t)

            torso = self._safe_torso_angle(pose)
            if torso > 0: torso_angles.append(torso)

            hip_y = self._get_point(pose, 'left_hip', 'y', 0.5)
            hip_heights.append(hip_y)

        if lead_angles:  m['lead_leg_angle']      = float(np.max(lead_angles))
        if trail_angles: m['trail_leg_angle']      = float(np.min(trail_angles))
        if torso_angles: m['torso_lean_angle']     = float(np.mean(torso_angles))
        if hip_heights:  m['clearance_hip_height'] = float(np.min(hip_heights))

        m['clearance_frames'] = len(clearance_frames)
        if fps > 0:
            m['clearance_duration_sec'] = round(len(clearance_frames) / fps, 3)

        sprint_frames = [i for i, p in enumerate(phases) if p == 'sprint']
        if sprint_frames:
            knee_lifts = []
            for i in sprint_frames:
                ky = self._get_point(poses[i], 'left_knee', 'y')
                hy = self._get_point(poses[i], 'left_hip',  'y')
                knee_lifts.append(hy - ky)
            m['sprint_knee_lift'] = float(np.mean(knee_lifts)) if knee_lifts else 0.0

        return m

    # ── SHOT PUT ─────────────────────────────────────────────────────────────

    def _shot_put_metrics(self, poses: List[Dict], phases: List[str]) -> Dict:
        m = {}

        # Hip-shoulder separation across whole throw
        sep_vals = [self._hip_shoulder_separation(p) for p in poses if self._hip_shoulder_separation(p) > 5]
        if sep_vals:
            m['hip_shoulder_separation'] = float(np.percentile(sep_vals, 75))

        # Release angle — use delivery/release phase
        release_frames = [i for i, ph in enumerate(phases) if ph in ('delivery', 'release')]
        if not release_frames:
            release_frames = list(range(max(0, len(poses)-6), len(poses)))

        angles = []
        elbow_heights = []
        for i in release_frames:
            pose = poses[i]
            a = self._wrist_release_angle(pose)
            if a > 5:
                angles.append(a)
            # Elbow height relative to hip
            elbow_y  = self._get_point(pose, 'right_elbow', 'y', 1.0)
            hip_y    = self._get_point(pose, 'right_hip',   'y', 1.0)
            shoulder_y = self._get_point(pose, 'right_shoulder', 'y', 1.0)
            if elbow_y < 1.0 and hip_y < 1.0:
                elbow_heights.append(hip_y - elbow_y)   # positive = elbow above hip

        if angles:       m['release_angle']  = float(np.mean(angles))
        if elbow_heights: m['elbow_height_vs_hip'] = float(np.mean(elbow_heights))

        # Knee bend at power position
        power_frames = [i for i, ph in enumerate(phases) if ph == 'power_position']
        if power_frames:
            knee_angles = []
            for i in power_frames:
                ka = self._get_angle(poses[i], 'right_knee_angle')
                if ka: knee_angles.append(ka)
            if knee_angles:
                m['power_position_knee_bend'] = float(np.mean(knee_angles))

        # Trunk rotation: difference between shoulder angle and hip angle
        trunk_rots = [self._trunk_rotation(p) for p in poses if self._trunk_rotation(p) > 5]
        if trunk_rots:
            m['max_trunk_rotation'] = float(np.percentile(trunk_rots, 90))

        # Arm extension at elbow during delivery
        delivery_frames = [i for i, ph in enumerate(phases) if ph == 'delivery']
        if delivery_frames:
            ext_angles = []
            for i in delivery_frames:
                ea = self._get_angle(poses[i], 'right_elbow_angle') or \
                     self._get_angle(poses[i], 'throwing_arm_angle')
                if ea: ext_angles.append(ea)
            if ext_angles:
                m['delivery_arm_extension'] = float(np.max(ext_angles))

        return m

    # ── DISCUS ───────────────────────────────────────────────────────────────

    def _discus_metrics(self, poses: List[Dict], phases: List[str]) -> Dict:
        m = {}

        sep_vals = [self._hip_shoulder_separation(p) for p in poses if self._hip_shoulder_separation(p) > 5]
        if sep_vals:
            m['hip_shoulder_separation'] = float(np.percentile(sep_vals, 75))

        trunk_rots = [self._trunk_rotation(p) for p in poses if self._trunk_rotation(p) > 5]
        if trunk_rots:
            m['max_trunk_rotation'] = float(np.percentile(trunk_rots, 90))

        release_frames = [i for i, ph in enumerate(phases) if ph in ('delivery', 'release')]
        if not release_frames:
            release_frames = list(range(max(0, len(poses)-6), len(poses)))

        angles = []
        for i in release_frames:
            a = self._wrist_release_angle(poses[i])
            if a > 5:
                angles.append(a)
        if angles:
            m['release_angle'] = float(np.mean(angles))

        # Arm sweep width: wrist x-distance from body center during wind-up
        wind_up_frames = [i for i, ph in enumerate(phases) if ph == 'wind_up']
        if wind_up_frames:
            sweep_vals = []
            for i in wind_up_frames:
                pose  = poses[i]
                wx    = self._get_point(pose, 'right_wrist', 'x', -1)
                hipx  = self._get_point(pose, 'right_hip',   'x', -1)
                if wx > 0 and hipx > 0:
                    sweep_vals.append(abs(wx - hipx))
            if sweep_vals:
                m['throwing_arm_sweep'] = float(np.mean(sweep_vals))

        # Balance: lateral sway of center of mass
        hip_x_vals = [self._get_point(p, 'left_hip', 'x') for p in poses]
        hip_x_vals = [v for v in hip_x_vals if v > 0]
        if hip_x_vals:
            m['lateral_sway'] = float(np.std(hip_x_vals))

        return m

    # ── JAVELIN ──────────────────────────────────────────────────────────────

    def _javelin_metrics(self, poses: List[Dict], phases: List[str]) -> Dict:
        m = {}

        sep_vals = [self._hip_shoulder_separation(p) for p in poses if self._hip_shoulder_separation(p) > 5]
        if sep_vals:
            m['hip_shoulder_separation'] = float(np.percentile(sep_vals, 75))

        # Elbow height at release: should be at or above shoulder
        release_frames = [i for i, ph in enumerate(phases) if ph in ('delivery', 'release')]
        if not release_frames:
            release_frames = list(range(max(0, len(poses)-8), len(poses)))

        release_angles, elbow_heights, arm_extensions = [], [], []

        for i in release_frames:
            pose = poses[i]

            a = self._wrist_release_angle(pose)
            if a > 5:
                release_angles.append(a)

            elbow_y    = self._get_point(pose, 'right_elbow',    'y', 1.0)
            shoulder_y = self._get_point(pose, 'right_shoulder', 'y', 1.0)
            if elbow_y < 1.0 and shoulder_y < 1.0:
                # negative = elbow ABOVE shoulder (y increases downward in image coords)
                elbow_heights.append(shoulder_y - elbow_y)

            ea = self._get_angle(pose, 'right_elbow_angle') or \
                 self._get_angle(pose, 'throwing_arm_angle')
            if ea:
                arm_extensions.append(ea)

        if release_angles: m['release_angle']        = float(np.mean(release_angles))
        if elbow_heights:  m['elbow_above_shoulder'] = float(np.mean(elbow_heights))
        if arm_extensions: m['arm_extension_angle']  = float(np.max(arm_extensions))

        # Trunk lean backward at power position (athlete leans back before throw)
        power_frames = [i for i, ph in enumerate(phases) if ph == 'power_position']
        if power_frames:
            lean_vals = [self._safe_torso_angle(poses[i]) for i in power_frames]
            m['power_position_trunk_lean'] = float(np.mean(lean_vals))

        # Crossover steps: horizontal distance between feet during approach
        wind_up_frames = [i for i, ph in enumerate(phases) if ph == 'wind_up']
        if wind_up_frames:
            stride_widths = []
            for i in wind_up_frames:
                lax = self._get_point(poses[i], 'left_ankle',  'x', -1)
                rax = self._get_point(poses[i], 'right_ankle', 'x', -1)
                if lax > 0 and rax > 0:
                    stride_widths.append(abs(lax - rax))
            if stride_widths:
                m['approach_stride_width'] = float(np.mean(stride_widths))

        return m

    # ─── ANGLE / GEOMETRY HELPERS ─────────────────────────────────────────────

    def _hip_shoulder_separation(self, pose: Dict) -> float:
        try:
            ls = pose['points']['left_shoulder']
            rs = pose['points']['right_shoulder']
            lh = pose['points']['left_hip']
            rh = pose['points']['right_hip']
            if not all(p.get('visible', False) for p in [ls, rs, lh, rh]):
                return 0.0
            shoulder_angle = np.arctan2(rs['y']-ls['y'], rs['x']-ls['x'])
            hip_angle      = np.arctan2(rh['y']-lh['y'], rh['x']-lh['x'])
            return float(np.degrees(abs(shoulder_angle - hip_angle)))
        except:
            return 0.0

    def _trunk_rotation(self, pose: Dict) -> float:
        """How much the torso is rotated relative to neutral facing (degrees)."""
        try:
            ls = pose['points']['left_shoulder']
            rs = pose['points']['right_shoulder']
            if not ls.get('visible') or not rs.get('visible'):
                return 0.0
            angle = np.degrees(np.arctan2(rs['y']-ls['y'], rs['x']-ls['x']))
            return float(abs(angle))
        except:
            return 0.0

    def _wrist_release_angle(self, pose: Dict) -> float:
        """
        Estimate release angle from the elbow→wrist vector direction.
        Positive = upward trajectory from the hand.
        """
        try:
            e = pose['points'].get('right_elbow')
            w = pose['points'].get('right_wrist')
            if not e or not w:
                return 0.0
            if not e.get('visible') or not w.get('visible'):
                return 0.0
            dx = w['x'] - e['x']
            dy = w['y'] - e['y']   # image coords: y increases downward
            # Angle above horizontal: negative dy = wrist above elbow = positive release angle
            angle = float(np.degrees(np.arctan2(-dy, abs(dx) + 1e-6)))
            return max(0.0, angle)
        except:
            return 0.0

    # ─── ERROR IDENTIFICATION ─────────────────────────────────────────────────

    def _identify_errors(self, metrics: Dict, phases: List[str], event: str) -> List[Dict]:
        std = self.pro_standards.get(event, {})
        if event == 'sprint':
            return self._sprint_errors(metrics, std)
        elif event == 'hurdles':
            return self._hurdles_errors(metrics, std)
        elif event == 'shot_put':
            return self._shot_put_errors(metrics, std)
        elif event == 'discus':
            return self._discus_errors(metrics, std)
        elif event == 'javelin':
            return self._javelin_errors(metrics, std)
        return []

    def _sprint_errors(self, metrics: Dict, std: Dict) -> List[Dict]:
        errors = []
        angle = metrics.get('block_torso_angle')
        if angle is not None and angle < std.get('min_block_torso_angle', 38):
            errors.append({
                'type': 'poor_block_angle', 'severity': 'high',
                'description': f'Popping up too early out of blocks (torso {angle:.0f}°, want ≥{std["min_block_torso_angle"]}°)',
                'fix': 'Drive your chest toward the track. Keep hips low and push the ground behind you for the first 10 steps.'
            })
        drive = metrics.get('drive_phase_duration_frames', 0)
        if drive < std.get('min_drive_phase_frames', 10):
            errors.append({
                'type': 'short_drive_phase', 'severity': 'medium',
                'description': f'Coming upright too quickly — only {drive} drive frames detected',
                'fix': 'Stay low and drive at a 45° angle for at least 20-30m. Count your steps — you should be low for the first 8–10 strides.'
            })
        knee_lift = metrics.get('avg_knee_lift', 0)
        if knee_lift < std.get('good_knee_lift', 0.04):
            errors.append({
                'type': 'low_knee_lift', 'severity': 'medium',
                'description': 'Knee drive is too low — reduced stride length and power',
                'fix': 'Drive your knee up so your thigh is parallel to the ground on each stride. Think "punch the knee through."'
            })
        arm_asym = metrics.get('arm_asymmetry_deg', 0)
        if arm_asym > std.get('max_arm_asymmetry', 18):
            errors.append({
                'type': 'arm_asymmetry', 'severity': 'low',
                'description': f'Arms are asymmetrical ({arm_asym:.0f}° difference between elbows)',
                'fix': 'Keep elbows at 90° on both sides. Arms should drive straight forward and back, not across the body.'
            })
        return errors

    def _hurdles_errors(self, metrics: Dict, std: Dict) -> List[Dict]:
        errors = []
        lead = metrics.get('lead_leg_angle')
        if lead is not None:
            if lead < std.get('min_lead_leg_angle', 140):
                errors.append({
                    'type': 'bent_lead_leg', 'severity': 'high',
                    'description': f'Lead leg too bent at clearance ({lead:.0f}° — want ≥{std["min_lead_leg_angle"]}°). Risk of clipping hurdle.',
                    'fix': 'Attack the hurdle with a straighter lead leg. Drive your heel up and snap it straight at the peak. Practice high-knee lead leg swings daily.'
                })
            elif lead < std.get('ideal_lead_leg_angle', 165):
                errors.append({
                    'type': 'lead_leg_suboptimal', 'severity': 'low',
                    'description': f'Lead leg extension is decent but not full ({lead:.0f}° — target ≥{std["ideal_lead_leg_angle"]}°)',
                    'fix': 'Snap the lead leg to full extension at the peak of clearance. The hurdle should feel like a "step over" not a "leap."'
                })
        trail = metrics.get('trail_leg_angle')
        if trail is not None and trail > std.get('max_trail_leg_angle', 120):
            errors.append({
                'type': 'poor_trail_leg', 'severity': 'high',
                'description': f'Trail leg not tucked tightly ({trail:.0f}° — want ≤{std["max_trail_leg_angle"]}°). Losing significant time.',
                'fix': 'Pull the trail leg knee up to your armpit as you cross the hurdle. The trail knee should be at hip height or higher, horizontal to the bar.'
            })
        torso = metrics.get('torso_lean_angle')
        if torso is not None and torso > std.get('max_torso_lean', 55):
            errors.append({
                'type': 'insufficient_torso_lean', 'severity': 'medium',
                'description': f'Not leaning forward enough over hurdle ({torso:.0f}° — want ≤{std["max_torso_lean"]}°)',
                'fix': 'Drive your chest forward and chin down toward the lead leg as you clear. Imagine your chest trying to touch your knee.'
            })
        clearance_sec = metrics.get('clearance_duration_sec')
        if clearance_sec is not None and clearance_sec > 0.35:
            errors.append({
                'type': 'excessive_air_time', 'severity': 'medium',
                'description': f'Too long in the air ({clearance_sec:.2f}s — elite is ≤0.25s)',
                'fix': 'Take off closer to the hurdle (approx 6–7 feet) and land closer on the other side. Think "step over" rather than "jump over."'
            })
        return errors

    def _shot_put_errors(self, metrics: Dict, std: Dict) -> List[Dict]:
        errors = []

        # Hip-shoulder separation
        sep     = metrics.get('hip_shoulder_separation', 0)
        min_sep = std.get('min_hip_shoulder_sep', 42)
        if sep < min_sep:
            errors.append({
                'type': 'insufficient_hip_shoulder_sep', 'severity': 'high',
                'description': f'Insufficient hip-shoulder separation ({sep:.0f}° — want ≥{min_sep}°). You are arm-putting, not full-body throwing.',
                'fix': 'Initiate the throw by driving your right hip toward the toe board BEFORE your shoulder rotates. Your hips should beat your shoulders by 45–90°.'
            })

        # Release angle
        release = metrics.get('release_angle', 0)
        ideal   = std.get('ideal_release_angle', 38)
        tol     = std.get('release_tolerance', 7)
        if release > 0:
            if release > ideal + tol:
                errors.append({
                    'type': 'release_angle_too_high', 'severity': 'medium',
                    'description': f'Release angle too high ({release:.0f}° — ideal is {ideal}±{tol}°). Shot climbing too steeply, losing distance.',
                    'fix': f'Release with a flatter trajectory. Your put hand should finish pointing toward the landing zone at roughly {ideal}° above horizontal.'
                })
            elif release > 0 and release < ideal - tol:
                errors.append({
                    'type': 'release_angle_too_low', 'severity': 'medium',
                    'description': f'Release angle too low ({release:.0f}° — ideal is {ideal}±{tol}°). Shot dropping short of potential.',
                    'fix': f'Drive upward more aggressively through the put. Get full hip extension before releasing.'
                })

        # Elbow height
        elbow_h = metrics.get('elbow_height_vs_hip', -1)
        if elbow_h != -1 and elbow_h < std.get('min_elbow_height', 0.35):
            errors.append({
                'type': 'low_elbow', 'severity': 'high',
                'description': f'Elbow dropping below hip level during delivery — loss of power and risk of injury.',
                'fix': 'Keep your putting elbow AT or ABOVE shoulder height throughout the delivery. A dropped elbow leaks all your rotational energy.'
            })

        # Knee bend at power position
        knee = metrics.get('power_position_knee_bend', 0)
        ideal_knee = std.get('ideal_knee_bend', 110)
        if knee > 0 and knee > ideal_knee + 20:
            errors.append({
                'type': 'insufficient_knee_bend', 'severity': 'medium',
                'description': f'Not getting low enough at power position (knee {knee:.0f}° — want ~{ideal_knee}°). Losing leg drive.',
                'fix': 'Bend your right knee deeper on the glide so you can explosively push upward. Your knee should be directly over your foot, weight on the ball.'
            })

        # Trunk rotation
        trunk = metrics.get('max_trunk_rotation', 0)
        min_rot = std.get('min_trunk_rotation', 40)
        if trunk > 0 and trunk < min_rot:
            errors.append({
                'type': 'limited_trunk_rotation', 'severity': 'medium',
                'description': f'Limited trunk rotation ({trunk:.0f}° — want ≥{min_rot}°). Losing power from your core.',
                'fix': 'Wind up more aggressively in the back of the circle. Your shoulders should be turned 90–180° from the direction of the throw before you start the delivery.'
            })

        return errors

    def _discus_errors(self, metrics: Dict, std: Dict) -> List[Dict]:
        errors = []

        sep     = metrics.get('hip_shoulder_separation', 0)
        min_sep = std.get('min_hip_shoulder_sep', 45)
        if sep < min_sep:
            errors.append({
                'type': 'insufficient_hip_shoulder_sep', 'severity': 'high',
                'description': f'Hip-shoulder separation too small ({sep:.0f}° — want ≥{min_sep}°). Throwing with your arm only.',
                'fix': 'Lead every throw with your left hip (right-handed). The discus should feel like it is being dragged behind your rotating hips. Hips first, always.'
            })

        release = metrics.get('release_angle', 0)
        ideal   = std.get('ideal_release_angle', 40)
        tol     = std.get('release_tolerance', 8)
        if release > 0:
            if release > ideal + tol:
                errors.append({
                    'type': 'release_angle_too_high', 'severity': 'medium',
                    'description': f'Release angle too high ({release:.0f}° — ideal {ideal}±{tol}°)',
                    'fix': 'Drive the discus off your index finger at a flatter angle. Think of the discus leaving your hand on a line, not arcing up.'
                })
            elif release < ideal - tol:
                errors.append({
                    'type': 'release_angle_too_low', 'severity': 'medium',
                    'description': f'Release angle too low ({release:.0f}° — ideal {ideal}±{tol}°)',
                    'fix': 'Get more leg push at release to drive the discus upward. Your releasing shoulder should be rising as you let go.'
                })

        trunk = metrics.get('max_trunk_rotation', 0)
        if trunk > 0 and trunk < std.get('min_trunk_rotation', 50):
            errors.append({
                'type': 'limited_trunk_rotation', 'severity': 'high',
                'description': f'Trunk rotation is limited ({trunk:.0f}° — want ≥{std["min_trunk_rotation"]}°). This is the main power source in discus.',
                'fix': 'During the wind-up, rotate your shoulders 180° from the throwing direction. Think of coiling a spring — the more you wind, the further you throw.'
            })

        sweep = metrics.get('throwing_arm_sweep', 0)
        if sweep > 0 and sweep < 0.15:
            errors.append({
                'type': 'narrow_arm_sweep', 'severity': 'medium',
                'description': 'Throwing arm staying too close to the body during wind-up — losing centrifugal force.',
                'fix': 'Keep your throwing arm long and sweeping wide during the wind-up. The discus should travel the longest possible arc before release.'
            })

        sway = metrics.get('lateral_sway', 0)
        if sway > 0.06:
            errors.append({
                'type': 'excessive_lateral_sway', 'severity': 'low',
                'description': f'Too much lateral movement of your hips during the throw (sway score: {sway:.3f})',
                'fix': 'Keep your center of mass moving toward the sector, not side to side. Plant your left foot firmly and pivot over it.'
            })

        return errors

    def _javelin_errors(self, metrics: Dict, std: Dict) -> List[Dict]:
        errors = []

        sep     = metrics.get('hip_shoulder_separation', 0)
        min_sep = std.get('min_hip_shoulder_sep', 38)
        if sep < min_sep:
            errors.append({
                'type': 'insufficient_hip_shoulder_sep', 'severity': 'high',
                'description': f'Not enough hip-shoulder separation ({sep:.0f}° — want ≥{min_sep}°). Throwing with your arm, not your whole body.',
                'fix': 'At the power position, your hips should be square to the sector while your shoulders are still sideways. Pull through with your left side before releasing your right arm.'
            })

        release = metrics.get('release_angle', 0)
        ideal   = std.get('ideal_release_angle', 34)
        tol     = std.get('release_tolerance', 6)
        if release > 0:
            if release > ideal + tol:
                errors.append({
                    'type': 'release_angle_too_high', 'severity': 'high',
                    'description': f'Release angle too high ({release:.0f}° — ideal is {ideal}±{tol}°). Javelin climbing too steeply, losing distance.',
                    'fix': f'Release the javelin at a flatter angle, roughly {ideal}°. A high release angle causes the javelin to stall and drop nose-up.'
                })
            elif release < ideal - tol:
                errors.append({
                    'type': 'release_angle_too_low', 'severity': 'high',
                    'description': f'Release angle too low ({release:.0f}° — ideal is {ideal}±{tol}°). Javelin diving into the ground.',
                    'fix': f'Drive your elbow high and release the javelin with upward force. Aim to release at {ideal}° above horizontal.'
                })

        # Elbow position at release
        elbow_h = metrics.get('elbow_above_shoulder', None)
        if elbow_h is not None and elbow_h < std.get('ideal_elbow_height', 0.0):
            errors.append({
                'type': 'low_elbow_at_release', 'severity': 'high',
                'description': 'Elbow dropping below shoulder at release — this causes elbow stress and loss of power.',
                'fix': 'Keep your elbow HIGH and lead the throw with your elbow, not your hand. Your elbow should travel past your ear before you extend.'
            })

        # Arm extension
        arm_ext = metrics.get('arm_extension_angle', 0)
        min_ext = std.get('min_arm_extension', 155)
        if arm_ext > 0 and arm_ext < min_ext:
            errors.append({
                'type': 'incomplete_arm_extension', 'severity': 'medium',
                'description': f'Arm not fully extending at release ({arm_ext:.0f}° — want ≥{min_ext}°). Losing the final acceleration phase.',
                'fix': 'Fully straighten your throwing arm at the moment of release. Think of snapping a whip — the final extension is where the velocity is added.'
            })

        # Trunk lean (should lean back at power position)
        trunk_lean = metrics.get('power_position_trunk_lean', 0)
        min_lean   = std.get('min_trunk_lean_back', 15)
        if trunk_lean > 0 and trunk_lean < min_lean:
            errors.append({
                'type': 'insufficient_trunk_lean', 'severity': 'medium',
                'description': f'Not leaning back enough at power position ({trunk_lean:.0f}° — want ≥{min_lean}°). Losing the bow-and-arrow stretch.',
                'fix': 'At the penultimate step, lean your upper body BACK and away from the throw direction. This loads your trunk like a bow before the explosive forward drive.'
            })

        # Approach stride width — too wide = blocking, too narrow = no separation
        stride_w = metrics.get('approach_stride_width', -1)
        if stride_w > 0 and stride_w > 0.35:
            errors.append({
                'type': 'wide_approach_strides', 'severity': 'low',
                'description': 'Approach strides appear too wide — may be causing lateral blocking.',
                'fix': 'Keep your approach strides in line with your throwing direction. Wide strides rotate you away from the sector before you have power.'
            })

        return errors

    # ─── SCORING ─────────────────────────────────────────────────────────────

    def _calculate_score(self, metrics: Dict, errors: List[Dict], event: str) -> float:
        score = 75.0

        if event == 'sprint':
            if metrics.get('block_torso_angle', 0) >= 45:      score += 10
            if metrics.get('avg_knee_lift', 0) > 0.05:         score += 8
            if metrics.get('arm_asymmetry_deg', 99) < 12:      score += 5
            if metrics.get('drive_phase_duration_frames', 0) >= 15: score += 5

        elif event == 'hurdles':
            lead = metrics.get('lead_leg_angle', 0)
            if lead >= 165:        score += 12
            elif lead >= 150:      score += 6
            trail = metrics.get('trail_leg_angle', 999)
            if trail <= 90:        score += 10
            elif trail <= 110:     score += 5
            torso = metrics.get('torso_lean_angle', 999)
            if torso <= 35:        score += 8
            elif torso <= 45:      score += 4
            cs = metrics.get('clearance_duration_sec', 999)
            if cs <= 0.25:         score += 8
            elif cs <= 0.30:       score += 4

        elif event in ['shot_put', 'discus', 'javelin']:
            std = self.pro_standards.get(event, {})

            sep = metrics.get('hip_shoulder_separation', 0)
            if sep >= std.get('ideal_hip_shoulder_sep', 50):    score += 12
            elif sep >= std.get('min_hip_shoulder_sep', 40):    score += 6

            release = metrics.get('release_angle', 0)
            ideal_r = std.get('ideal_release_angle', 38)
            tol_r   = std.get('release_tolerance', 7)
            if release > 0 and abs(release - ideal_r) <= tol_r:  score += 10
            elif release > 0 and abs(release - ideal_r) <= tol_r * 2: score += 5

            trunk = metrics.get('max_trunk_rotation', 0)
            if trunk >= std.get('min_trunk_rotation', 40):       score += 8

            if event == 'javelin':
                arm_ext = metrics.get('arm_extension_angle', 0)
                if arm_ext >= std.get('min_arm_extension', 155): score += 5

        # Deductions
        penalty = {'high': 20, 'medium': 10, 'low': 4}
        for error in errors:
            score -= penalty.get(error.get('severity', 'medium'), 10)

        return max(35, min(98, round(score, 1)))

    # ─── DRILLS ──────────────────────────────────────────────────────────────

    def _suggest_drills(self, errors: List[Dict], event: str) -> List[str]:
        drill_map = {
            # Sprint
            'poor_block_angle':              '🏃 Sled resisted starts — stay low for 20m, 6×20m reps',
            'short_drive_phase':             '🏃 Wall drive drills — 3×10 each leg, focus on 45° body angle',
            'low_knee_lift':                 '🏃 High-knee A-skips — 4×20m, knee punching up past parallel',
            'arm_asymmetry':                 '🏃 Mirror arm drive drills — 90° elbows, straight forward-back, 3×30s',
            # Hurdles
            'bent_lead_leg':                 '🚧 Lead leg wall swings — 3×10, snap straight at peak. Also: hurdle lead leg drills over low barriers',
            'lead_leg_suboptimal':           '🚧 Standing hurdle lead leg snaps — 3×10 each side',
            'poor_trail_leg':                '🚧 Trail leg cycles on low hurdle — knee to armpit, 3×8 each side',
            'insufficient_torso_lean':       '🚧 Lean drills over mini hurdles — chin driving forward and down, 3×5',
            'excessive_air_time':            '🚧 Quick step-over drills on 6-inch hurdles — fast feet, 4×30m',
            # Shot put
            'insufficient_hip_shoulder_sep': '🏋️ Med ball hip-turn throws against wall — 3×10, hips beat shoulders every rep',
            'release_angle_too_high':        '🏋️ Flat release shadow puts — practice finishing at {ideal}°, 3×10',
            'release_angle_too_low':         '🏋️ Upward drive puts — focus on leg push at release, 3×8',
            'low_elbow':                     '🏋️ Elbow height mirror drill — put hand stays at shoulder height, 3×10',
            'insufficient_knee_bend':        '🏋️ Power position holds — get low, hold 3s, explosive push, 4×6',
            'limited_trunk_rotation':        '🏋️ Standing rotational med ball throws — wind-up 180°, 3×10',
            # Discus
            'narrow_arm_sweep':              '💿 Long-arm wind-up drill — keep arm extended through full sweep, 3×8',
            'excessive_lateral_sway':        '💿 Left-foot pivot balance drill — plant and pivot without swaying, 3×10',
            # Javelin
            'low_elbow_at_release':          '🏹 Elbow-lead pull-through drill — elbow past ear before extending, 3×10',
            'incomplete_arm_extension':      '🏹 Full extension shadow throws — snap fully straight every rep, 3×10',
            'insufficient_trunk_lean':       '🏹 Power position lean holds — lean back, hold 2s, drive forward, 4×6',
            'wide_approach_strides':         '🏹 Straight-line approach drill — strides on a painted line, 4×approach',
        }

        # Universal good-practice drills by event
        base_drills = {
            'sprint':   ['🏃 Sprint ABC drills (A-skip, B-skip, C-skip) — 4×20m each, warmup every session'],
            'hurdles':  ['🚧 Sprint 3-step rhythm between hurdles — keep stride count consistent'],
            'shot_put': ['🏋️ Glide technique practice with lightweight shot — 10 reps focusing on footwork'],
            'discus':   ['💿 Standing throws focusing on hip-shoulder sequence — 10 reps, no spin'],
            'javelin':  ['🏹 5-step approach throws — no full run-up until technique is clean'],
        }

        drills = []
        seen   = set()
        for error in errors:
            d = drill_map.get(error.get('type'))
            if d and d not in seen:
                drills.append(d)
                seen.add(d)

        for d in base_drills.get(event, []):
            if d not in seen:
                drills.append(d)
                seen.add(d)

        return drills

    # ─── SUMMARY ─────────────────────────────────────────────────────────────

    def _generate_summary(self, score: float, errors: List[Dict], event: str = '') -> str:
        event_name = event.replace('_', ' ').title() if event else ''
        high_errors = [e for e in errors if e.get('severity') == 'high']
        if score >= 85:
            return f"Excellent {event_name} technique! You're competing at a high level. Minor refinements only."
        elif score >= 72:
            if high_errors:
                main = high_errors[0]['description']
                return f"Solid {event_name} foundation. Main priority: {main}"
            return f"Good {event_name} technique. Focus on the highlighted areas for quick performance gains."
        elif score >= 55:
            count = len(high_errors)
            return f"Several important {event_name} technique faults ({count} high-priority). Work through the drills below consistently — you'll see fast improvement."
        else:
            return f"Major {event_name} technique faults detected. Start with the fundamentals: footwork and body position first, speed and distance second."

    def _empty_result(self, reason: str) -> Dict:
        return {
            'event': 'unknown', 'overall_score': 0, 'metrics': {},
            'errors_found': 0, 'errors': [], 'drills': [],
            'summary': reason, 'analyzed_at': datetime.now().isoformat()
        }


if __name__ == "__main__":
    judge = TechniqueJudge()
    print("✅ TechniqueJudge loaded successfully")
    print("Supported events: sprint, hurdles, shot_put, discus, javelin")