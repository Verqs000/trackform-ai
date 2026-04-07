"""
Event Classifier - Detects sprint, shot_put, discus, or javelin
Tuned on 10 real videos:
  Sprint (3): bounciness 0.034/0.026/0.012, avg_torso 40/43/45, hip_speed 0.021/0.009/0.003
  Javelin (3): bounciness 0.008/0.042/0.006, avg_torso 30/15/13, hip_speed 0.006/0.003/0.004
  Discus (2):  bounciness 0.004/0.009, avg_torso 10/14, hip_speed 0.0007/0.0025
  Shot (2):    bounciness 0.016/0.008, avg_torso 15/32, hip_speed 0.003/0.005
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
        f['avg_hip_speed']    = f['distance_moved'] / max(len(poses), 1)

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

        # Use MEDIAN arm extension over first and last 20% of frames
        # (more robust than single frame)
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
    # Key stats across all 10 videos:
    #
    # avg_torso_angle:  Sprint 40-45 | Javelin 13-30 | Discus 10-14 | Shot 15-32
    # bounciness:       Sprint 0.012-0.034 | Jav 0.006-0.042 | Disc 0.004-0.009 | Shot 0.008-0.016
    # avg_hip_speed:    Sprint 0.003-0.021 | Jav 0.003-0.006 | Disc 0.0007-0.003 | Shot 0.003-0.005
    # end_hip_height:   Sprint 0.29-0.76 | Jav 0.40-0.92 | Disc 0.38-0.47 | Shot 0.54-0.56
    #
    # MOST RELIABLE: avg_torso_angle (sprint clearly highest at 40-45)
    # 2ND: bounciness (sprint + shot overlap 0.012-0.016, but sprint goes higher)
    # 3RD: avg_hip_speed (sprint can go much higher than throws)
    # ─────────────────────────────────────────────────────────────────────────

    def _score_sprint(self, f):
        """
        Sprint signature: HIGH avg_torso_angle (40-45) + bounciness varies
        but avg_hip_speed can be very high (0.021).
        Most reliable: avg_torso_angle > 35 is a very strong sprint signal.
        """
        score = 0.0

        # #1 BEST: avg_torso_angle — sprints lean forward, stays high throughout
        # Sprint: 40-45. All throws: 10-32. Clear separation.
        if f['avg_torso_angle'] > 38:
            score += 0.50
        elif f['avg_torso_angle'] > 30:
            score += 0.30
        elif f['avg_torso_angle'] > 22:
            score += 0.10
        else:
            score -= 0.20  # very upright = throw

        # #2: bounciness — sprint tends higher but overlaps with shot
        if f['bounciness'] > 0.025:
            score += 0.25
        elif f['bounciness'] > 0.015:
            score += 0.15
        elif f['bounciness'] > 0.008:
            score += 0.05

        # #3: hip speed — sprint can be very fast
        if f['avg_hip_speed'] > 0.015:
            score += 0.20
        elif f['avg_hip_speed'] > 0.007:
            score += 0.10
        elif f['avg_hip_speed'] > 0.003:
            score += 0.05

        # #4: end hip should go DOWN (sprint moves from crouch to upright)
        # end_hip_height going very high (>0.70) suggests shot put not sprint
        if f['end_hip_height'] > 0.70:
            score -= 0.15

        return max(0.0, min(1.0, score))

    def _score_javelin(self, f):
        """
        Javelin signature: UPRIGHT avg_torso (13-30) + arms extended
        + moderate bounciness + NOT a slow throw.
        Hard to separate from discus/shot on torso alone — use arm extension.
        """
        score = 0.0

        # #1: upright torso but not as extreme as discus
        if 10 < f['avg_torso_angle'] < 35:
            score += 0.30
        elif f['avg_torso_angle'] < 10:
            score += 0.10  # could be discus
        elif f['avg_torso_angle'] > 38:
            score -= 0.30  # sprint not javelin

        # #2: arms extended throughout (carrying javelin)
        # Use median which is more robust than single frame
        if f['start_arm_ext'] > 0.80 and f['end_arm_ext'] > 0.80:
            score += 0.30
        elif f['start_arm_ext'] > 0.70 or f['end_arm_ext'] > 0.70:
            score += 0.15

        # #3: faster than discus/shot
        if 0.003 < f['avg_hip_speed'] < 0.008:
            score += 0.20
        elif f['avg_hip_speed'] > 0.008:
            score += 0.05  # possible sprint

        # #4: moderate bounciness (not as low as discus)
        if 0.005 < f['bounciness'] < 0.020:
            score += 0.15
        elif f['bounciness'] < 0.005:
            score -= 0.10  # too smooth = discus

        # #5: penalty if end hip very high (shot)
        if f['end_hip_height'] > 0.65:
            score -= 0.20

        return max(0.0, min(1.0, score))

    def _score_shot_put(self, f):
        """
        Shot put signature: UPRIGHT torso (15-32) + high end_hip_height (0.54-0.56)
        + large negative torso change in original video (leaning then releasing).
        Bounciness 0.008-0.016 overlaps with sprint but avg_torso separates them.
        """
        score = 0.0
        torso_change = f['end_torso_angle'] - f['start_torso_angle']

        # #1: upright torso — not as leaned as sprint
        if f['avg_torso_angle'] < 35:
            score += 0.25
        else:
            score -= 0.20  # too leaned = sprint

        # #2: end hip height elevated (squatting then rising for release)
        if f['end_hip_height'] > 0.50:
            score += 0.25
        elif f['end_hip_height'] > 0.40:
            score += 0.10

        # #3: slow hip speed
        if f['avg_hip_speed'] < 0.006:
            score += 0.20
        elif f['avg_hip_speed'] > 0.012:
            score -= 0.15

        # #4: torso change (can be negative OR positive depending on filming angle)
        # Shot put has large start_torso_angle in some videos
        if f['start_torso_angle'] > 40 or abs(torso_change) > 25:
            score += 0.15

        # #5: bounciness — shot overlaps with sprint low end
        if f['bounciness'] < 0.020:
            score += 0.10
        else:
            score -= 0.10

        return max(0.0, min(1.0, score))

    def _score_discus(self, f):
        """
        Discus signature: VERY UPRIGHT torso (10-14) + LOWEST bounciness (0.004-0.009)
        + very slow hip speed (0.0007-0.003) + small torso change.
        Most distinctive: combination of very low bounciness AND very upright torso.
        """
        score = 0.0
        torso_change = f['end_torso_angle'] - f['start_torso_angle']

        # #1: very upright — discus is most upright of all throws
        if f['avg_torso_angle'] < 16:
            score += 0.35
        elif f['avg_torso_angle'] < 25:
            score += 0.15
        elif f['avg_torso_angle'] > 35:
            score -= 0.25  # sprint

        # #2: lowest bounciness
        if f['bounciness'] < 0.006:
            score += 0.30
        elif f['bounciness'] < 0.012:
            score += 0.15
        else:
            score -= 0.15

        # #3: very slow hip speed
        if f['avg_hip_speed'] < 0.003:
            score += 0.20
        elif f['avg_hip_speed'] < 0.006:
            score += 0.10
        elif f['avg_hip_speed'] > 0.010:
            score -= 0.15

        # #4: small torso change (spinning = stays consistent)
        if abs(torso_change) < 8:
            score += 0.15
        elif abs(torso_change) > 25:
            score -= 0.10

        return max(0.0, min(1.0, score))


if __name__ == "__main__":
    print("EventClassifier loaded!")
    print("Detects: sprint, shot_put, discus, javelin")
    print("Tuned on 10 real videos")