import pandas as pd
import numpy as np


JOINT_NAMES = [
    "Head", "Neck", "Spine", "Spine1", "Spine2", "Spine3", "Hips",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "LeftHandThumb", "LeftHandIndex", "LeftHandMiddle", "LeftHandRing", "LeftHandPinky",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "RightHandThumb", "RightHandIndex", "RightHandMiddle", "RightHandRing", "RightHandPinky",
    "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
    "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
]


def read_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


def check_csv(df: pd.DataFrame) -> dict:
    total_values = df.size
    missing = df.isnull().sum().sum()
    missing_ratio = missing / total_values if total_values > 0 else 0

    coords = [c for c in df.columns if c.endswith(("_x", "_y", "_z"))]
    joints_found = list(set(c.rsplit("_", 1)[0] for c in coords))

    time_col = "time" if "time" in df.columns else None
    if time_col is not None and len(df) > 1:
        dt = df[time_col].diff().dropna()
        fps = round(1.0 / dt.mean(), 1)
    else:
        fps = None

    return {
        "total_frames": len(df),
        "total_columns": len(df.columns),
        "joints_found": sorted(joints_found),
        "joints_count": len(joints_found),
        "total_values": total_values,
        "missing_values": int(missing),
        "missing_ratio": round(missing_ratio, 4),
        "estimated_fps": fps,
        "columns": list(df.columns),
    }


def get_joint_coords(df: pd.DataFrame, joint: str) -> np.ndarray:
    cols = [f"{joint}_x", f"{joint}_y", f"{joint}_z"]
    for c in cols:
        if c not in df.columns:
            raise KeyError(f"Column {c} not found. Available: {list(df.columns)}")
    return df[cols].values


def get_joint_by_side(df: pd.DataFrame, joint_prefix: str):
    left = get_joint_coords(df, f"Left{joint_prefix}")
    right = get_joint_coords(df, f"Right{joint_prefix}")
    return left, right


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path:
        df = read_csv(path)
        info = check_csv(df)
        for k, v in info.items():
            print(f"{k}: {v}")
    else:
        print("Usage: python read_csv.py <csv_path>")
