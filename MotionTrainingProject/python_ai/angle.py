import numpy as np
from python_ai.read_csv import get_joint_coords

ANGLE_DEFINITIONS = {
    "RightElbow": ("RightArm", "RightForeArm", "RightHand"),
    "LeftElbow": ("LeftArm", "LeftForeArm", "LeftHand"),
    "RightShoulder": ("Spine1", "RightShoulder", "RightArm"),
    "LeftShoulder": ("Spine1", "LeftShoulder", "LeftArm"),
    "RightKnee": ("RightUpLeg", "RightLeg", "RightFoot"),
    "LeftKnee": ("LeftUpLeg", "LeftLeg", "LeftFoot"),
    "RightHip": ("Spine", "RightUpLeg", "RightLeg"),
    "LeftHip": ("Spine", "LeftUpLeg", "LeftLeg"),
}


def calculate_angle(a, b, c):
    a, b, c = np.array(a, dtype=float), np.array(b, dtype=float), np.array(c, dtype=float)
    if np.any(np.isnan(a)) or np.any(np.isnan(b)) or np.any(np.isnan(c)):
        return np.nan
    ba = a - b
    bc = c - b
    cos_val = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
    cos_val = np.clip(cos_val, -1.0, 1.0)
    return np.degrees(np.arccos(cos_val))


def compute_joint_angle(df, angle_name: str) -> np.ndarray:
    if angle_name not in ANGLE_DEFINITIONS:
        raise ValueError(f"Unknown angle: {angle_name}. Available: {list(ANGLE_DEFINITIONS.keys())}")
    joint_a, joint_b, joint_c = ANGLE_DEFINITIONS[angle_name]
    a = get_joint_coords(df, joint_a)
    b = get_joint_coords(df, joint_b)
    c = get_joint_coords(df, joint_c)
    n = min(len(a), len(b), len(c))
    angles = np.array([calculate_angle(a[i], b[i], c[i]) for i in range(n)])
    return angles


def compute_all_angles(df) -> dict:
    result = {}
    for name in ANGLE_DEFINITIONS:
        try:
            result[name] = compute_joint_angle(df, name)
        except KeyError:
            continue
    return result
