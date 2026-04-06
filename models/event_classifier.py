"""
Event Classifier - Detects sprint, shot_put, discus, or javelin
Fixed version: better sprint vs javelin separation
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
 
        # --- Hip position / movement ---
        hip_x = [p['points']['left_hip']['x'] for p in poses]
        hip_y = [p['points']['left_hip']['y'] for p in poses]
        f['distance_moved']   = max(hip_x) - min(hip_x)
        f['vertical_range']   = max(hip_y) - min(hip_y)
        f['start_hip_height'] = hip_y[0]          # y: 0=top, 1=bottom of frame
        f['end_hip_height']   = hip_y[-1]
        f['min_hip_height']   = max(hip_y)         # highest value = lowest position
 
        # --- Speed of movement ---
        f['avg_hip_speed'] = f['distance_moved'] / max(len(poses), 1)
 
        # --- Shoulder rotation ---
        shoulder_angles = []
        for p in poses:
            l = p['points']['left_shoulder']
            r = p['points']['right_shoulder']
            angle = np.arctan2(r['y'] - l['y'], r['x'] - l['x'])
            shoulder_angles.append(angle)
        f['shoulder_rotation'] = max(shoulder_angles) - min(shoulder_angles)
 
        # --- Torso angle at START (key for sprint vs javelin) ---
        f['start_torso_angle'] = self._torso_angle(poses[0])
        f['end_torso_angle']   = self._torso_angle(poses[-1])
 
        # --- Arm extension at start and end ---
        f['start_arm_ext'] = max(
            self._arm_ext(poses[0], 'left'),
            self._arm_ext(poses[0], 'right')
        )
        f['end_arm_ext'] = max(
            self._arm_ext(poses[-1], 'left'),
            self._arm_ext(poses[-1], 'right')
        )
 
        # --- Bounce / rhythm (sprints have alternating leg rhythm) ---
        hip_vel = np.diff(hip_y)
        f['bounciness'] = float(np.std(hip_vel))
 
        # --- How upright are they throughout? (avg torso angle) ---
        torso_angles = [self._torso_angle(p) for p in poses]
        f['avg_torso_angle'] = float(np.mean(torso_angles))
 
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
        ux, uy = e['x']-s['x'], e['y']-s['y']
        lx, ly = w['x']-e['x'], w['y']-e['y']
        mag = (np.sqrt(ux**2+uy**2) * np.sqrt(lx**2+ly**2)) + 1e-6
        return float((ux*lx + uy*ly) / mag)
 
    # ─── EVENT SCORERS ───────────────────────────────────────────────────────
 
    def _score_sprint(self, f):
        """
        Sprint — real observed values:
          bounciness=0.037, torso_change=+71, avg_hip_speed=0.016,
          distance_moved=0.55, start_arm_ext=0.52
        """
        score = 0.0
        torso_change = f['end_torso_angle'] - f['start_torso_angle']
 
        # #1 signal: very high bounciness (0.037 vs next highest 0.018)
        if f['bounciness'] > 0.025:
            score += 0.40
        elif f['bounciness'] > 0.014:
            score += 0.20
        else:
            score -= 0.15
 
        # #2 signal: large POSITIVE torso change (crouch to upright)
        if torso_change > 50:
            score += 0.30
        elif torso_change > 30:
            score += 0.15
        elif torso_change < 0:
            score -= 0.20
 
        # #3 signal: fastest hip speed by far
        if f['avg_hip_speed'] > 0.010:
            score += 0.20
        elif f['avg_hip_speed'] > 0.005:
            score += 0.08
 
        # #4: farthest horizontal movement
        if f['distance_moved'] > 0.50:
            score += 0.10
 
        return max(0.0, min(1.0, score))
 
    def _score_javelin(self, f):
        """
        Javelin — real observed values:
          start_arm_ext=0.99, bounciness=0.018, torso_change=+36,
          distance_moved=0.35, avg_hip_speed=0.003
        """
        score = 0.0
        torso_change = f['end_torso_angle'] - f['start_torso_angle']
 
        # #1 signal: arm nearly fully extended at start (holding javelin)
        if f['start_arm_ext'] > 0.90:
            score += 0.45
        elif f['start_arm_ext'] > 0.70:
            score += 0.25
        elif f['start_arm_ext'] < 0.55:
            score -= 0.20
 
        # #2 signal: mid-range bounciness (between sprint and throws)
        if 0.010 < f['bounciness'] < 0.028:
            score += 0.25
        elif f['bounciness'] > 0.028:
            score -= 0.15
 
        # #3: positive torso change but less than sprint
        if 20 < torso_change < 55:
            score += 0.20
        elif torso_change > 55:
            score -= 0.10
 
        # #4: moderate distance (run-up but shorter than sprint)
        if 0.25 < f['distance_moved'] < 0.50:
            score += 0.10
 
        return max(0.0, min(1.0, score))
 
    def _score_shot_put(self, f):
        """
        Shot put — real observed values:
          end_hip_height=0.72 (hips rise!), torso_change=-33 (negative!),
          bounciness=0.005, avg_hip_speed=0.001, start_arm_ext=0.75
        """
        score = 0.0
        torso_change = f['end_torso_angle'] - f['start_torso_angle']
 
        # #1 signal: hips end HIGHER than they started (end_hip_height highest of all)
        # y increases downward, so higher end_hip_height = lower body position at end
        if f['end_hip_height'] > 0.65:
            score += 0.40
        elif f['end_hip_height'] > 0.55:
            score += 0.20
 
        # #2 signal: NEGATIVE torso change (leans back/rotates opposite to sprint)
        if torso_change < -20:
            score += 0.30
        elif torso_change < 0:
            score += 0.15
 
        # #3: very slow hip speed (slowest of all events)
        if f['avg_hip_speed'] < 0.002:
            score += 0.20
        elif f['avg_hip_speed'] < 0.005:
            score += 0.10
 
        # #4: moderate arm extension throughout
        if 0.60 < f['start_arm_ext'] < 0.90:
            score += 0.10
 
        # Penalty: very bouncy = sprint not shot
        if f['bounciness'] > 0.020:
            score -= 0.25
 
        return max(0.0, min(1.0, score))
 
    def _score_discus(self, f):
        """
        Discus — real observed values:
          bounciness=0.004 (lowest!), torso_change=+7 (tiny),
          avg_hip_speed=0.002, start_arm_ext=0.49, end_arm_ext=0.98
        """
        score = 0.0
        torso_change = f['end_torso_angle'] - f['start_torso_angle']
 
        # #1 signal: lowest bounciness of all (0.004)
        if f['bounciness'] < 0.006:
            score += 0.35
        elif f['bounciness'] < 0.010:
            score += 0.15
        else:
            score -= 0.10
 
        # #2 signal: tiny torso change (spinning = consistent lean)
        if abs(torso_change) < 15:
            score += 0.30
        elif abs(torso_change) < 25:
            score += 0.15
 
        # #3: arm goes from mid to very extended (the swing/release)
        if f['start_arm_ext'] < 0.60 and f['end_arm_ext'] > 0.90:
            score += 0.25
        elif f['end_arm_ext'] > 0.90:
            score += 0.10
 
        # #4: slow hip speed (not moving linearly)
        if f['avg_hip_speed'] < 0.003:
            score += 0.10
 
        # Penalty: bouncy or fast = sprint
        if f['bounciness'] > 0.020:
            score -= 0.30
 
        return max(0.0, min(1.0, score))
 
 
if __name__ == "__main__":
    print("EventClassifier loaded!")
    print("Detects: sprint, shot_put, discus, javelin")