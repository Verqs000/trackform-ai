"""
Technique Judge - Analyzes track & field technique
Fixed version: proper scoring, more errors detected, works for all events
"""

import numpy as np

class TechniqueJudge:

    def __init__(self, event_type):
        self.event_type = event_type
        self.pro_standards = {
            'sprint': {
                'ideal_block_torso_angle': 50,    # degrees forward lean out of blocks
                'min_block_torso_angle': 38,       # anything below = popping up
                'ideal_drive_phase_frames': 20,    # frames spent in drive phase
                'min_drive_phase_frames': 10,      # below = coming upright too soon
                'ideal_shin_angle': 45,
                'ideal_knee_lift': 0.3,            # how high knee comes up (normalized)
            },
            'shot_put': {
                'ideal_release_angle': 38,
                'release_angle_tolerance': 6,
                'min_hip_shoulder_separation': 40,
                'ideal_hip_shoulder_separation': 50,
            },
            'discus': {
                'ideal_release_angle': 40,
                'release_angle_tolerance': 8,
                'min_hip_shoulder_separation': 45,
                'ideal_orbit_radius': 0.3,
            },
            'javelin': {
                'ideal_release_angle': 34,
                'release_angle_tolerance': 6,
                'ideal_crossstep_hip_angle': 30,
                'min_arm_pull_through': 0.4,
            }
        }

    def analyze(self, pose_data):
        poses = pose_data['poses']

        if len(poses) < 5:
            return self._empty_result("Video too short to analyze")

        phases = self._detect_phases(poses)
        metrics = self._calculate_metrics(poses, phases)
        errors = self._identify_errors(metrics, phases, poses)
        score = self._calculate_score(errors, metrics)
        drills = self._suggest_drills(errors)

        return {
            'event': self.event_type,
            'overall_score': score,
            'phases_detected': phases,
            'metrics': metrics,
            'errors_found': len(errors),
            'errors': errors,
            'recommended_drills': drills,
            'summary': self._generate_summary(errors, score)
        }

    # ─── PHASE DETECTION ─────────────────────────────────────────────────────

    def _detect_phases(self, poses):
        phases = []
        for i, pose in enumerate(poses):
            if self.event_type == 'sprint':
                phases.append(self._sprint_phase(pose, i, poses))
            elif self.event_type in ['shot_put', 'discus', 'javelin']:
                phases.append(self._throw_phase(pose, i, poses))
            else:
                phases.append('unknown')
        return phases

    def _sprint_phase(self, pose, idx, all_poses):
        torso = self._torso_angle(pose)
        hip_y = pose['points']['left_hip']['y']

        # First few frames + low hip + forward lean = block start
        if idx < 8 and hip_y > 0.60 and torso > 25:
            return 'block_start'
        elif torso > 20:
            return 'drive_phase'
        else:
            return 'max_velocity'

    def _throw_phase(self, pose, idx, all_poses):
        total = len(all_poses)
        pct = idx / total
        if pct < 0.25:
            return 'entry_windup'
        elif pct < 0.55:
            return 'delivery'
        elif pct < 0.80:
            return 'power_position'
        else:
            return 'release'

    # ─── METRICS ─────────────────────────────────────────────────────────────

    def _calculate_metrics(self, poses, phases):
        metrics = {}

        if self.event_type == 'sprint':
            block_frames = [i for i, p in enumerate(phases) if p == 'block_start']
            drive_frames = [i for i, p in enumerate(phases) if p == 'drive_phase']

            if block_frames:
                bp = poses[block_frames[0]]
                metrics['block_torso_angle'] = self._torso_angle(bp)
                metrics['block_hip_height'] = bp['points']['left_hip']['y']

            metrics['drive_phase_duration'] = len(drive_frames)

            if drive_frames:
                # Check if knee gets high enough during drive
                knee_heights = [poses[i]['points']['left_knee']['y'] for i in drive_frames]
                hip_heights  = [poses[i]['points']['left_hip']['y']  for i in drive_frames]
                # knee above hip = good knee drive (lower y = higher in frame)
                metrics['avg_knee_lift'] = float(np.mean(
                    [h - k for h, k in zip(hip_heights, knee_heights)]
                ))

                # Shin angle at first drive step
                first = poses[drive_frames[0]]
                metrics['first_step_shin_angle'] = self._shin_angle(first)

            # Arm symmetry check across all frames
            arm_diffs = []
            for p in poses:
                la = self._arm_angle(p, 'left')
                ra = self._arm_angle(p, 'right')
                arm_diffs.append(abs(la - ra))
            metrics['arm_asymmetry'] = float(np.mean(arm_diffs))

        elif self.event_type in ['shot_put', 'discus', 'javelin']:
            power_frames  = [i for i, p in enumerate(phases) if p == 'power_position']
            release_frames = [i for i, p in enumerate(phases) if p == 'release']

            if power_frames:
                pp = poses[power_frames[0]]
                metrics['hip_shoulder_separation'] = self._hip_shoulder_separation(pp)
                metrics['power_position_hip_height'] = pp['points']['left_hip']['y']

            if release_frames:
                rp = poses[release_frames[-1]]
                metrics['release_angle'] = self._release_angle(rp)
                metrics['release_arm_extension'] = max(
                    self._arm_extension(rp, 'left'),
                    self._arm_extension(rp, 'right')
                )

            # Balance / weight shift
            hip_x = [p['points']['left_hip']['x'] for p in poses]
            metrics['lateral_sway'] = float(max(hip_x) - min(hip_x))

        return metrics

    # ─── ANGLE HELPERS ───────────────────────────────────────────────────────

    def _torso_angle(self, pose):
        s = pose['points']['left_shoulder']
        h = pose['points']['left_hip']
        dx = s['x'] - h['x']
        dy = s['y'] - h['y']
        return float(np.degrees(np.arctan2(abs(dx), abs(dy))))

    def _shin_angle(self, pose):
        knee  = pose['points']['left_knee']
        ankle = pose['points']['left_ankle']
        dx = ankle['x'] - knee['x']
        dy = ankle['y'] - knee['y']
        return float(np.degrees(np.arctan2(abs(dx), abs(dy))))

    def _arm_angle(self, pose, side):
        s = pose['points'][f'{side}_shoulder']
        e = pose['points'][f'{side}_elbow']
        dx = e['x'] - s['x']
        dy = e['y'] - s['y']
        return float(np.degrees(np.arctan2(dy, dx)))

    def _arm_extension(self, pose, side):
        s = pose['points'][f'{side}_shoulder']
        e = pose['points'][f'{side}_elbow']
        w = pose['points'][f'{side}_wrist']
        ux, uy = e['x']-s['x'], e['y']-s['y']
        lx, ly = w['x']-e['x'], w['y']-e['y']
        dot = ux*lx + uy*ly
        mag = (np.sqrt(ux**2+uy**2) * np.sqrt(lx**2+ly**2)) + 1e-6
        return float(dot / mag)

    def _hip_shoulder_separation(self, pose):
        ls = pose['points']['left_shoulder']
        rs = pose['points']['right_shoulder']
        lh = pose['points']['left_hip']
        rh = pose['points']['right_hip']
        sa = np.arctan2(rs['y']-ls['y'], rs['x']-ls['x'])
        ha = np.arctan2(rh['y']-lh['y'], rh['x']-lh['x'])
        return float(np.degrees(abs(sa - ha)))

    def _release_angle(self, pose):
        e = pose['points']['right_elbow']
        w = pose['points']['right_wrist']
        dy = w['y'] - e['y']
        dx = w['x'] - e['x']
        return float(np.degrees(np.arctan2(-dy, dx)))

    # ─── ERROR DETECTION ─────────────────────────────────────────────────────

    def _identify_errors(self, metrics, phases, poses):
        errors = []

        if self.event_type == 'sprint':
            errors += self._sprint_errors(metrics, phases)
        elif self.event_type == 'shot_put':
            errors += self._shot_put_errors(metrics)
        elif self.event_type == 'discus':
            errors += self._discus_errors(metrics)
        elif self.event_type == 'javelin':
            errors += self._javelin_errors(metrics)

        return errors

    def _sprint_errors(self, metrics, phases):
        errors = []
        std = self.pro_standards['sprint']

        # 1. Block clearance angle
        angle = metrics.get('block_torso_angle')
        if angle is not None:
            if angle < std['min_block_torso_angle']:
                errors.append({
                    'type': 'vertical_block_clearance',
                    'severity': 'high',
                    'description': 'Popping straight up out of the blocks',
                    'your_value': f"{angle:.1f}° forward lean",
                    'ideal_value': f"{std['ideal_block_torso_angle']}° forward lean",
                    'fix': 'Push the ground behind you, not down. Drive your chest toward the track for the first 3 steps.',
                    'drills': ['Wall drive drill', '3-point start holds (hold 3 sec)', 'Sled march (heavy resistance)']
                })
        else:
            # No block start detected at all — flag it
            errors.append({
                'type': 'no_block_start_detected',
                'severity': 'medium',
                'description': 'Could not detect a clear block start position',
                'your_value': 'N/A',
                'ideal_value': 'Hips low, forward lean > 38°',
                'fix': 'Make sure your hips are low in the blocks and your body is leaning forward before the start.',
                'drills': ['Block drills (set position holds)', 'Push-up start practice']
            })

        # 2. Drive phase too short
        drive_dur = metrics.get('drive_phase_duration', 0)
        if drive_dur < std['min_drive_phase_frames']:
            errors.append({
                'type': 'early_upright',
                'severity': 'medium',
                'description': 'Coming upright too quickly after the start',
                'your_value': f"{drive_dur} frames in drive phase",
                'ideal_value': f"{std['ideal_drive_phase_frames']}+ frames (~0.7 sec)",
                'fix': 'Stay low through 20-30 meters. Imagine running under a low ceiling for the first 10 steps.',
                'drills': ['Hill sprints (natural lean)', 'Sled pulls (forces you low)', 'Wicket runs']
            })

        # 3. Knee drive
        knee_lift = metrics.get('avg_knee_lift')
        if knee_lift is not None and knee_lift < 0.02:
            errors.append({
                'type': 'insufficient_knee_drive',
                'severity': 'medium',
                'description': 'Knee not driving high enough during acceleration',
                'your_value': f"{knee_lift:.3f} (low)",
                'ideal_value': '> 0.05 (knee clearly above hip level)',
                'fix': 'Drive your knee toward your chest aggressively on each step. High knees = more power.',
                'drills': ['High knee drills', 'A-skips', 'Bounding drills']
            })

        # 4. Arm asymmetry
        arm_asym = metrics.get('arm_asymmetry')
        if arm_asym is not None and arm_asym > 25:
            errors.append({
                'type': 'arm_asymmetry',
                'severity': 'low',
                'description': 'Arms not moving symmetrically',
                'your_value': f"{arm_asym:.1f}° difference",
                'ideal_value': '< 15° difference',
                'fix': 'Keep arms at 90° and drive elbows straight back, not across your body.',
                'drills': ['Seated arm swing drill', 'Mirror arm drill', 'Standing arm drives']
            })

        return errors

    def _shot_put_errors(self, metrics):
        errors = []
        std = self.pro_standards['shot_put']

        sep = metrics.get('hip_shoulder_separation')
        if sep is not None:
            if sep < std['min_hip_shoulder_separation']:
                errors.append({
                    'type': 'poor_hip_shoulder_separation',
                    'severity': 'high',
                    'description': 'Hips and shoulders rotating at the same time',
                    'your_value': f"{sep:.1f}° separation",
                    'ideal_value': f"{std['ideal_hip_shoulder_separation']}°+ separation",
                    'fix': 'Hips must fire first, then shoulders. Pause at power position and feel the stretch.',
                    'drills': ['Standing throw with pause', 'Hip isolation drills', 'Wall separation holds']
                })

        ra = metrics.get('release_angle')
        if ra is not None:
            ideal = std['ideal_release_angle']
            tol   = std['release_angle_tolerance']
            if abs(ra - ideal) > tol:
                direction = 'too flat — push higher' if ra < ideal else 'too steep — push more outward'
                errors.append({
                    'type': 'release_angle_off',
                    'severity': 'medium',
                    'description': f'Release angle is {direction}',
                    'your_value': f"{ra:.1f}°",
                    'ideal_value': f"{ideal - tol}°–{ideal + tol}°",
                    'fix': f'Your release is {direction}. Adjust wrist and elbow position at release.',
                    'drills': ['Standing release drills', 'High-release medicine ball throws']
                })

        sway = metrics.get('lateral_sway')
        if sway is not None and sway > 0.25:
            errors.append({
                'type': 'excessive_lateral_sway',
                'severity': 'low',
                'description': 'Too much lateral (side-to-side) movement',
                'your_value': f"{sway:.2f} normalized",
                'ideal_value': '< 0.15',
                'fix': 'Keep your base of support solid. Drive through the block leg without swaying.',
                'drills': ['Balance board throws', 'Single-leg stability drills']
            })

        return errors

    def _discus_errors(self, metrics):
        errors = []
        std = self.pro_standards['discus']

        sep = metrics.get('hip_shoulder_separation')
        if sep is not None and sep < std['min_hip_shoulder_separation']:
            errors.append({
                'type': 'poor_separation',
                'severity': 'high',
                'description': 'Not enough hip-shoulder separation in the spin',
                'your_value': f"{sep:.1f}°",
                'ideal_value': f"{std['min_hip_shoulder_separation']}°+",
                'fix': 'Wind shoulders back further at entry. Let hips lead the rotation.',
                'drills': ['Standing throws (focus on wind-up)', 'Pivot drills', 'Shadow throwing']
            })

        ra = metrics.get('release_angle')
        if ra is not None:
            ideal = std['ideal_release_angle']
            tol   = std['release_angle_tolerance']
            if abs(ra - ideal) > tol:
                errors.append({
                    'type': 'release_angle_off',
                    'severity': 'medium',
                    'description': 'Release angle not in optimal range',
                    'your_value': f"{ra:.1f}°",
                    'ideal_value': f"{ideal-tol}°–{ideal+tol}°",
                    'fix': 'Adjust release point. Keep discus at shoulder height at release.',
                    'drills': ['Standing release practice', 'Slow-motion spin drills']
                })

        ext = metrics.get('release_arm_extension')
        if ext is not None and ext < 0.5:
            errors.append({
                'type': 'arm_not_extended_at_release',
                'severity': 'medium',
                'description': 'Arm is bent at release — losing distance',
                'your_value': f"{ext:.2f} (bent)",
                'ideal_value': '> 0.7 (straight)',
                'fix': 'Fully extend your throwing arm at release. Think "long arm" through the throw.',
                'drills': ['Arm extension drills', 'Standing throws against wall target']
            })

        return errors

    def _javelin_errors(self, metrics):
        errors = []
        std = self.pro_standards['javelin']

        ra = metrics.get('release_angle')
        if ra is not None:
            ideal = std['ideal_release_angle']
            tol   = std['release_angle_tolerance']
            if abs(ra - ideal) > tol:
                direction = 'too low — the javelin will nose-dive' if ra < ideal else 'too high — losing distance'
                errors.append({
                    'type': 'release_angle_off',
                    'severity': 'high',
                    'description': f'Javelin release angle is {direction}',
                    'your_value': f"{ra:.1f}°",
                    'ideal_value': f"{ideal-tol}°–{ideal+tol}°",
                    'fix': f'Your release is {direction}. Focus on keeping the javelin tip up through pull-through.',
                    'drills': ['Standing throws focusing on angle', 'Pull-through drills', 'Approach-only throws']
                })

        sep = metrics.get('hip_shoulder_separation')
        if sep is not None and sep < 30:
            errors.append({
                'type': 'poor_separation',
                'severity': 'medium',
                'description': 'Not enough bow position at cross-step',
                'your_value': f"{sep:.1f}°",
                'ideal_value': '40°+',
                'fix': 'At your cross-step, shoulders should be pulled way back like drawing a bow. More stretch = more power.',
                'drills': ['Cross-step drills', 'Standing throws (exaggerate bow)', 'Rubber band resistance throws']
            })

        ext = metrics.get('release_arm_extension')
        if ext is not None and ext < 0.5:
            errors.append({
                'type': 'elbow_dropping',
                'severity': 'high',
                'description': 'Elbow dropping below shoulder at release',
                'your_value': f"{ext:.2f} (low extension)",
                'ideal_value': '> 0.7',
                'fix': 'Keep elbow high and drive it forward. Elbow leads, then wrist snaps over.',
                'drills': ['High elbow medicine ball throws', 'Wall throw with elbow check', 'Towel pull-through']
            })

        sway = metrics.get('lateral_sway')
        if sway is not None and sway > 0.30:
            errors.append({
                'type': 'approach_drift',
                'severity': 'low',
                'description': 'Drifting sideways during approach run',
                'your_value': f"{sway:.2f}",
                'ideal_value': '< 0.20',
                'fix': 'Run in a straight line during approach. Use a runway line as a guide.',
                'drills': ['Straight-line approach drills', 'Cone-guided approach runs']
            })

        return errors

    # ─── SCORING ─────────────────────────────────────────────────────────────

    def _calculate_score(self, errors, metrics):
        """
        Score starts at 75 (not 100) so there's real room to move.
        Good metrics add points. Errors remove points.
        """
        score = 75

        # Add points for things done well
        if self.event_type == 'sprint':
            angle = metrics.get('block_torso_angle')
            if angle is not None and angle >= 45:
                score += 10
            elif angle is not None and angle >= 38:
                score += 5

            drive = metrics.get('drive_phase_duration', 0)
            if drive >= 20:
                score += 8
            elif drive >= 10:
                score += 4

            knee = metrics.get('avg_knee_lift')
            if knee is not None and knee > 0.05:
                score += 7

        elif self.event_type in ['shot_put', 'discus', 'javelin']:
            sep = metrics.get('hip_shoulder_separation')
            std = self.pro_standards.get(self.event_type, {})
            if sep is not None and sep >= std.get('min_hip_shoulder_separation', 40):
                score += 10

            ra = metrics.get('release_angle')
            ideal = std.get('ideal_release_angle', 38)
            tol   = std.get('release_angle_tolerance', 6)
            if ra is not None and abs(ra - ideal) <= tol:
                score += 10

            ext = metrics.get('release_arm_extension')
            if ext is not None and ext > 0.7:
                score += 5

        # Deduct for errors
        deductions = {'high': 18, 'medium': 10, 'low': 4}
        for error in errors:
            score -= deductions.get(error['severity'], 5)

        return max(40, min(100, score))

    # ─── OUTPUT HELPERS ───────────────────────────────────────────────────────

    def _suggest_drills(self, errors):
        all_drills = []
        for e in errors:
            all_drills.extend(e.get('drills', []))
        return list(dict.fromkeys(all_drills))  # deduplicate, preserve order

    def _generate_summary(self, errors, score):
        if score >= 85:
            return "Strong technique overall! A few small refinements will take you to the next level."
        elif score >= 70:
            return "Solid foundation with clear areas to improve. Focus on the high-severity issues first."
        elif score >= 55:
            return "Several technique issues found. Work through the drills consistently — big gains available."
        else:
            return "Significant technique faults detected. Start with the fundamental drills before adding intensity."

    def _empty_result(self, reason):
        return {
            'event': self.event_type,
            'overall_score': 0,
            'phases_detected': [],
            'metrics': {},
            'errors_found': 0,
            'errors': [],
            'recommended_drills': [],
            'summary': reason
        }


if __name__ == "__main__":
    judge = TechniqueJudge('sprint')
    print("TechniqueJudge loaded for:", judge.event_type)