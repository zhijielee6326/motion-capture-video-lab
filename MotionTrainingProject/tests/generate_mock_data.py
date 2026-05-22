import os
import sys
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw_csv")
os.makedirs(RAW_DIR, exist_ok=True)

JOINTS = [
    "Head", "Neck", "Spine", "Spine1", "Spine2", "Spine3", "Hips",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "LeftHandThumb", "LeftHandIndex", "LeftHandMiddle", "LeftHandRing", "LeftHandPinky",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "RightHandThumb", "RightHandIndex", "RightHandMiddle", "RightHandRing", "RightHandPinky",
    "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
    "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
]

BASE_POS = {
    "Head": (0, 1700, 0), "Neck": (0, 1550, 0),
    "Spine": (0, 1300, 0), "Spine1": (0, 1400, 0), "Spine2": (0, 1200, 0), "Spine3": (0, 1100, 0),
    "Hips": (0, 1000, 0),
    "LeftShoulder": (-200, 1500, 0), "LeftArm": (-350, 1400, 0), "LeftForeArm": (-450, 1200, 0),
    "LeftHand": (-500, 1050, 0),
    "RightShoulder": (200, 1500, 0), "RightArm": (350, 1400, 0), "RightForeArm": (450, 1200, 0),
    "RightHand": (500, 1050, 0),
    "LeftUpLeg": (-150, 900, 0), "LeftLeg": (-150, 550, 0), "LeftFoot": (-150, 100, 0),
    "RightUpLeg": (150, 900, 0), "RightLeg": (150, 550, 0), "RightFoot": (150, 100, 0),
}


def generate_motion(n_frames=300, noise=5.0, deform_scale=1.0) -> pd.DataFrame:
    frames = np.arange(n_frames)
    t = frames / 100.0
    cols = ["frame", "time"]
    data = {"frame": frames, "time": t}

    for joint in JOINTS:
        bx, by, bz = BASE_POS.get(joint, (0, 800, 0))
        amp = noise * deform_scale

        if "Hand" in joint and "Pinky" not in joint and "Ring" not in joint and "Middle" not in joint and "Index" not in joint:
            x = bx + amp * np.sin(2 * np.pi * t * 1.5 + np.random.uniform(0, 6.28))
            y = by + amp * 2 * np.sin(2 * np.pi * t * 0.8 + np.random.uniform(0, 6.28))
            z = bz + amp * np.sin(2 * np.pi * t * 1.2 + np.random.uniform(0, 6.28))
        elif "Arm" in joint or "ForeArm" in joint:
            x = bx + amp * 1.5 * np.sin(2 * np.pi * t * 1.0 + np.random.uniform(0, 6.28))
            y = by + amp * 2 * np.sin(2 * np.pi * t * 0.7 + np.random.uniform(0, 6.28))
            z = bz + amp * np.sin(2 * np.pi * t * 0.9 + np.random.uniform(0, 6.28))
        elif "Leg" in joint or "Foot" in joint:
            phase = 0 if "Left" in joint else np.pi
            x = bx + amp * 0.5 * np.sin(2 * np.pi * t * 1.0 + phase)
            y = by + amp * 3 * np.sin(2 * np.pi * t * 0.5 + phase)
            z = bz + amp * np.sin(2 * np.pi * t * 0.8 + phase)
        elif "Shoulder" in joint:
            x = bx + amp * np.sin(2 * np.pi * t * 0.6 + np.random.uniform(0, 6.28))
            y = by + amp * np.sin(2 * np.pi * t * 0.5)
            z = bz + amp * 0.5 * np.sin(2 * np.pi * t * 0.4)
        else:
            x = bx + amp * 0.3 * np.sin(2 * np.pi * t * 0.3)
            y = by + amp * 0.3 * np.sin(2 * np.pi * t * 0.2)
            z = bz + amp * 0.3 * np.sin(2 * np.pi * t * 0.25)

        noise_arr = np.random.normal(0, noise * 0.3, n_frames)
        data[f"{joint}_x"] = x + noise_arr
        data[f"{joint}_y"] = y + noise_arr
        data[f"{joint}_z"] = z + noise_arr

    return pd.DataFrame(data)


def inject_missing(df, ratio=0.02):
    df = df.copy()
    coord_cols = [c for c in df.columns if c.endswith(("_x", "_y", "_z"))]
    n_missing = int(len(df) * len(coord_cols) * ratio)
    for _ in range(n_missing):
        r = np.random.randint(0, len(df))
        c = coord_cols[np.random.randint(0, len(coord_cols))]
        df.iloc[r, df.columns.get_loc(c)] = np.nan
    return df


def main():
    print("Generating mock data...")
    np.random.seed(42)

    std_df = generate_motion(n_frames=300, noise=3.0, deform_scale=1.0)
    std_path = os.path.join(RAW_DIR, "STD-aerobics-001.csv")
    std_df.to_csv(std_path, index=False)
    print(f"  Standard: {std_path} ({len(std_df)} frames)")

    for i, (noise, deform) in enumerate([(5.0, 1.2), (8.0, 1.5), (12.0, 1.8)], 1):
        stu_df = generate_motion(n_frames=300, noise=noise, deform_scale=deform)
        stu_df = inject_missing(stu_df, ratio=0.01 * i)
        stu_path = os.path.join(RAW_DIR, f"S001-aerobics-00{i}.csv")
        stu_df.to_csv(stu_path, index=False)
        print(f"  Student {i}: {stu_path} ({len(stu_df)} frames, noise={noise})")

    emergency_df = generate_motion(n_frames=800, noise=4.0, deform_scale=1.0)
    emg_path = os.path.join(RAW_DIR, "emergency_drill_001.csv")
    emergency_df.to_csv(emg_path, index=False)
    print(f"  Emergency: {emg_path} ({len(emergency_df)} frames)")

    print("\nDone! Run the server to test:")
    print(f"  cd {BASE_DIR}")
    print("  python -m server.main")
    print("  Open http://127.0.0.1:8000/case2/dashboard")
    print("  Open http://127.0.0.1:8000/case4/dashboard")


if __name__ == "__main__":
    main()
