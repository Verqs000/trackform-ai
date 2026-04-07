"""
Event Classifier - Detects sprint, shot_put, discus, or javelin
Tuned on 10 real videos:
  Sprint (3): bounciness 0.034/0.026/0.012, avg_torso 40/43/45, hip_speed 0.021/0.009/0.003
  Javelin (3): bounciness 0.008/0.042/0.006, avg_torso 30/15/13, hip_speed 0.006/0.003/0.004
  Discus (2):  bounciness 0.004/0.009, avg_torso 10/14, hip_speed 0.0007/0.0025
  Shot (2):    bounciness 0.016/0.008, avg_torso 15/32, hip_speed 0.003/0.005

Block start note:
  avg_hip_speed is unreliable for block starts — athlete barely moves horizontally
  in a short clip. Use vertical_range + hip_rise + torso_angle instead.
  Block start features: vertical_range ~0.41, avg_torso ~43, bounciness ~0.014,
  start_hip_height LOW (crouched ~0.44), end_hip_height HIGH (~0.76).
"""

import numpy as np


class EventClassifier:

    def classify(self, pose_data):
        poses = pose_data['poses']

        if len(poses) < 5:
            return {'event': 'unknown', 'confidence': 0, 'all_scores': {}, 'features': {}}

        features = self._extract_features(poses)

        scores = {
            'sprint':   self._score_sprint(features),
            'shot_put': self._score_shot_put(features),
            'discus':   self._score_discus(features),
            'javelin':  self._score_javelin(features),
        }

        best_event = max(scores, key=scores.get)

        return {
            'event': best_event,
            'confidence': scores[best_event],
            'all_scores': scores,
            'features': features
        }

    # ─── FEATURE EXTRACTION ──────────────────────────────────────────────────

    def _extract_features(self, poses):
        f = {}

        hip_x = [p['points']['left_hip']['x'] for p in poses]
        hip_y = [p['points']['left_hip']['y'] for p in poses]

        f['distance_moved']   = max(hip_x) - min(hip_x)
        f['vertical_range']   = max(hip_y) - min(hip_y)
        f['start_hip_height'] = hip_y[0]
        f['end_hip_height']   = hip_y[-1]
        f['min_hip_height']   = max(hip_y)

        # hip_rise: how much the hip went UP from start to end
        # positive = athlete rose (block start driving out, shot put release)
        # block start: ~+0.31. shot put: ~+0.20. throws mostly smaller.
        f['hip_rise'] = hip_y[-1] - hip_y[0]

        # avg_hip_speed: horizontal movement only — NOT reliable for block starts
        # kept for running sprints and throws
        f['avg_hip_speed'] = f['distance_moved'] / max(len(poses), 1)

        shoulder_angles = []
        for p in poses:
            l = p['points']['left_shoulder']
            r = p['points']['right_shoulder']
            angle = np.arctan2(r['y'] - l['y'], r['x'] - l['x'])
            shoulder_angles.append(angle)
        f['shoulder_rotation'] = max(shoulder_angles) - min(shoulder_angles)

        torso_angles = [self._torso_angle(p) for p in poses]
        f['start_torso_angle'] = torso_angles[0]
        f['end_torso_angle']   = torso_angles[-1]
        f['avg_torso_angle']   = float(np.mean(torso_angles))

        n = max(len(poses), 1)
        first_slice = poses[:max(1, n // 5)]
        last_slice  = poses[-(max(1, n // 5)):]

        start_exts = [max(self._arm_ext(p, 'left'), self._arm_ext(p, 'right')) for p in first_slice]
        end_exts   = [max(self._arm_ext(p, 'left'), self._arm_ext(p, 'right')) for p in last_slice]
        f['start_arm_ext'] = float(np.median(start_exts))
        f['end_arm_ext']   = float(np.median(end_exts))

        hip_vel = np.diff(hip_y)
        f['bounciness'] = float(np.std(hip_vel))

        return f

    def _torso_angle(self, pose):
        s = pose['points']['left_shoulder']
        h = pose['points']['left_hip']
        dx = s['x'] - h['x']
        dy = s['y'] - h['y']
        return float(np.degrees(np.arctan2(abs(dx), abs(dy))))

    def _arm_ext(self, pose, side):
        s = pose['points'][f'{side}_shoulder']
        e = pose['points'][f'{side}_elbow']
        w = pose['points'][f'{side}_wrist']
        ux, uy = e['x'] - s['x'], e['y'] - s['y']
        lx, ly = w['x'] - e['x'], w['y'] - e['y']
        mag = (np.sqrt(ux**2 + uy**2) * np.sqrt(lx**2 + ly**2)) + 1e-6
        return float((ux * lx + uy * ly) / mag)

    # ─── EVENT SCORERS ───────────────────────────────────────────────────────
    #
    # BLOCK START vs SHOT PUT — the hard separation case:
    #
    #                    block_start   shot_put
    # avg_torso_angle:   40-45         15-32      ← sprint wins clearly (+0.45 vs -0.35)
    # vertical_range:    0.35-0.45     0.05-0.20  ← sprint wins clearly (+0.35 vs -0.30)
    # hip_rise:          ~+0.31        ~+0.20     ← sprint slight edge
    # bounciness:        0.012-0.034   0.008-0.016 ← overlaps, minor signal
    # avg_hip_speed:     ~0.004        ~0.003-0.005 ← useless, ignore for this case
    #
    # With your block start metrics (torso=43.6, vertical_range=0.41, hip_rise=0.31):
    #   sprint score  ≈ 0.45 + 0.35 + 0.15 + 0.08 = ~0.85 ✓
    #   shot score    ≈ -0.35 - 0.30 + 0.20 + 0.15 = ~-0.30 → clamped 0.0 ✓
    # ─────────────────────────────────────────────────────────────────────────

    def _score_sprint(self, f):
        """
        Sprint / block start signature:
        - HIGH avg_torso_angle (40-45) — forward lean throughout
        - HIGH vertical_range (0.35+) — hips travel a lot vertically
        - large hip_rise — crouched start rising into drive
        - bounciness 0.012+ for running, lower ok for block start
        - avg_hip_speed bonus only — NOT used as a gate (breaks block starts)
        """
        score = 0.0

        # #1: avg_torso_angle — best single separator, sprint always >38
        if f['avg_torso_angle'] > 38:
            score += 0.45
        elif f['avg_torso_angle'] > 30:
            score += 0.20
        elif f['avg_torso_angle'] > 22:
            score += 0.05
        else:
            score -= 0.30  # very upright = throw

        # #2: vertical_range — block start's killer feature vs all throws
        # Block start: 0.35-0.45. Throws: typically < 0.20.
        if f['vertical_range'] > 0.30:
            score += 0.35
        elif f['vertical_range'] > 0.20:
            score += 0.15
        elif f['vertical_range'] > 0.10:
            score += 0.05
        else:
            score -= 0.20

        # #3: hip_rise — athlete rises out of blocks
        if f['hip_rise'] > 0.25:
            score += 0.15
        elif f['hip_rise'] > 0.15:
            score += 0.08

        # #4: bounciness
        if f['bounciness'] > 0.025:
            score += 0.15
        elif f['bounciness'] > 0.010:
            score += 0.08

        # #5: hip speed — bonus for running sprints, not a gate
        if f['avg_hip_speed'] > 0.015:
            score += 0.15
        elif f['avg_hip_speed'] > 0.008:
            score += 0.08

        return max(0.0, min(1.0, score))

    def _score_shot_put(self, f):
        """
        Shot put signature:
        - UPRIGHT torso (15-32)
        - LOW vertical_range (0.05-0.20) — mostly rotational
        - end_hip_height elevated on release
        - slow hip speed
        """
        score = 0.0
        torso_change = f['end_torso_angle'] - f['start_torso_angle']

        # #1: upright torso
        if f['avg_torso_angle'] < 35:
            score += 0.30
        elif f['avg_torso_angle'] > 38:
            score -= 0.35  # sprint territory

        # #2: LOW vertical_range — key separator from block start
        # Block start: ~0.41. Shot put: < 0.20.
        if f['vertical_range'] < 0.15:
            score += 0.30
        elif f['vertical_range'] < 0.25:
            score += 0.15
        elif f['vertical_range'] > 0.30:
            score -= 0.30  # block start territory

        # #3: end hip height elevated
        if f['end_hip_height'] > 0.50:
            score += 0.20
        elif f['end_hip_height'] > 0.40:
            score += 0.10

        # #4: slow hip speed
        if f['avg_hip_speed'] < 0.006:
            score += 0.15
        elif f['avg_hip_speed'] > 0.012:
            score -= 0.10

        # #5: large torso wind-up
        if f['start_torso_angle'] > 40 or abs(torso_change) > 25:
            score += 0.10

        # #6: bounciness
        if f['bounciness'] < 0.020:
            score += 0.05
        else:
            score -= 0.10

        return max(0.0, min(1.0, score))

    def _score_javelin(self, f):
        """
        Javelin signature:
        - UPRIGHT avg_torso (13-30)
        - LOW vertical_range (linear run-up)
        - arms extended (carrying javelin)
        - moderate bounciness
        """
        score = 0.0

        # #1: upright torso
        if 10 < f['avg_torso_angle'] < 35:
            score += 0.30
        elif f['avg_torso_angle'] < 10:
            score += 0.10
        elif f['avg_torso_angle'] > 38:
            score -= 0.35

        # #2: LOW vertical_range
        if f['vertical_range'] < 0.20:
            score += 0.20
        elif f['vertical_range'] > 0.30:
            score -= 0.25

        # #3: arms extended
        if f['start_arm_ext'] > 0.80 and f['end_arm_ext'] > 0.80:
            score += 0.25
        elif f['start_arm_ext'] > 0.70 or f['end_arm_ext'] > 0.70:
            score += 0.12

        # #4: moderate hip speed
        if 0.003 < f['avg_hip_speed'] < 0.008:
            score += 0.15
        elif f['avg_hip_speed'] > 0.012:
            score -= 0.10

        # #5: moderate bounciness
        if 0.005 < f['bounciness'] < 0.020:
            score += 0.10
        elif f['bounciness'] < 0.005:
            score -= 0.10

        return max(0.0, min(1.0, score))

    def _score_discus(self, f):
        """
        Discus signature:
        - VERY UPRIGHT torso (10-14)
        - LOWEST bounciness (0.004-0.009)
        - very slow hip speed (0.0007-0.003)
        - LOW vertical_range (spinning in place)
        - small torso change
        """
        score = 0.0
        torso_change = f['end_torso_angle'] - f['start_torso_angle']

        # #1: very upright
        if f['avg_torso_angle'] < 16:
            score += 0.35
        elif f['avg_torso_angle'] < 25:
            score += 0.15
        elif f['avg_torso_angle'] > 35:
            score -= 0.30

        # #2: very low vertical_range
        if f['vertical_range'] < 0.12:
            score += 0.25
        elif f['vertical_range'] < 0.20:
            score += 0.10
        elif f['vertical_range'] > 0.30:
            score -= 0.25

        # #3: lowest bounciness
        if f['bounciness'] < 0.006:
            score += 0.25
        elif f['bounciness'] < 0.012:
            score += 0.10
        else:
            score -= 0.15

        # #4: very slow hip speed
        if f['avg_hip_speed'] < 0.003:
            score += 0.15
        elif f['avg_hip_speed'] < 0.006:
            score += 0.08
        elif f['avg_hip_speed'] > 0.010:
            score -= 0.15

        # #5: small torso change
        if abs(torso_change) < 8:
            score += 0.10
        elif abs(torso_change) > 25:
            score -= 0.10

        return max(0.0, min(1.0, score))


if __name__ == "__main__":
    print("EventClassifier loaded!")
    print("Detects: sprint, shot_put, discus, javelin")
    print("Tuned on 10 real videos + block start fix")