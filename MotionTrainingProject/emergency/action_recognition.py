import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import pandas as pd
from python_ai.read_csv import get_joint_coords
from python_ai.angle import compute_all_angles
from emergency.scenario_configs import get_scenario


def detect_torso_forward(df, threshold_deg=30.0) -> np.ndarray:
    if "Spine_x" not in df.columns or "Hips_x" not in df.columns:
        return np.zeros(len(df))
    spine = get_joint_coords(df, "Spine")
    hips = get_joint_coords(df, "Hips")
    forward = spine[:, 2] - hips[:, 2]
    vertical = spine[:, 1] - hips[:, 1]
    angle = np.degrees(np.arctan2(np.abs(forward), vertical + 1e-8))
    return (angle > threshold_deg).astype(float)


def detect_knee_bend(angles: dict, threshold=100.0) -> dict:
    result = {}
    for side in ("Left", "Right"):
        key = f"{side}Knee"
        if key in angles:
            result[key] = angles[key] > threshold
    return result


def detect_arm_above_shoulder(df) -> np.ndarray:
    if "RightHand_y" not in df.columns:
        return np.zeros(len(df))
    hand_y = df["RightHand_y"].values
    shoulder_y = df["RightShoulder_y"].values
    return (hand_y > shoulder_y).astype(float)


def detect_hands_range(df, threshold_mm=150.0) -> np.ndarray:
    if "RightHand_x" not in df.columns or "LeftHand_x" not in df.columns:
        return np.zeros(len(df))
    rh = get_joint_coords(df, "RightHand")
    lh = get_joint_coords(df, "LeftHand")
    dist = np.linalg.norm(rh - lh, axis=1)
    return (dist < threshold_mm).astype(float)


def detect_gait(angles: dict) -> np.ndarray:
    lk = angles.get("LeftKnee", np.array([]))
    rk = angles.get("RightKnee", np.array([]))
    if len(lk) == 0 or len(rk) == 0:
        return np.array([])
    n = min(len(lk), len(rk))
    variation = np.abs(np.diff(lk[:n])) + np.abs(np.diff(rk[:n]))
    variation = np.append(variation, variation[-1])
    return (variation > 2.0).astype(float)


def recognize_actions(df: pd.DataFrame, angles: dict, scenario_id: str) -> list:
    config = get_scenario(scenario_id)
    n_frames = len(df)
    results = []

    torso_fwd = detect_torso_forward(df)
    knee_bend = detect_knee_bend(angles)
    arm_above = detect_arm_above_shoulder(df)
    hands_range = detect_hands_range(df)
    gait = detect_gait(angles)

    total_frames = n_frames
    frames_per_action = max(total_frames // len(config["actions"]), 1)

    for i, action in enumerate(config["actions"]):
        start = i * frames_per_action
        end = min((i + 1) * frames_per_action, total_frames)
        segment = slice(start, end)

        confidence = 0.5
        det = action["detect"]

        if "torso_forward" in det and len(torso_fwd) > 0:
            confidence += 0.2 * torso_fwd[segment].mean()
        if "gait_cycle" in det and len(gait) > 0:
            s = min(end, len(gait))
            confidence += 0.2 * gait[start:s].mean()
        if "knee_bend" in det:
            for side in ("Left", "Right"):
                kb = knee_bend.get(f"{side}Knee")
                if kb is not None and len(kb) > end:
                    confidence += 0.1 * kb[segment].mean()
        if "arm_above_shoulder" in det and len(arm_above) > 0:
            confidence += 0.2 * arm_above[segment].mean()
        if "hands_small_range" in det and len(hands_range) > 0:
            confidence += 0.2 * hands_range[segment].mean()

        confidence = min(round(confidence, 2), 1.0)
        status = "completed" if confidence > 0.6 else "detected" if confidence > 0.4 else "uncertain"

        results.append({
            "id": action["id"],
            "name": action["name"],
            "status": status,
            "confidence": confidence,
            "frame_range": [start, end],
            "key_joints": action["key_joints"],
        })

    return results
