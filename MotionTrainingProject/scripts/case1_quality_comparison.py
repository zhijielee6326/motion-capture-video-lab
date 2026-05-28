"""案例1/3 动捕数据质量对比分析 — 4组健美操CSV（正常+3种异常）"""

import json
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial"]
plt.rcParams["axes.unicode_minus"] = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = r"E:\Desktop\动捕视频采集与传输实验\data\数据"
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "case1_analysis")
STATIC_DIR = os.path.join(BASE_DIR, "server", "static")

FILES = {
    "正常(最佳标定)": "案例3-正常best.csv",
    "标定结果差": "案例3-标定结果差.csv",
    "少两个标记点": "案例3-少俩个标记点.csv",
    "遮挡摄像头": "案例3-遮挡视像头.csv",
}

# Key joints to analyze (from Kinetics Toolkit analysis)
KEY_JOINTS = [
    "LWrist", "RWrist", "LElbow", "RElbow",
    "LShoulder", "RShoulder", "LHip", "RHip",
    "LKnee", "RKnee", "LAnkle", "RAnkle",
    "Head", "Neck", "Chest",
]

DERIVED = {
    "LWrist": ["LWristOut", "LWristIn"],
    "RWrist": ["RWristOut", "RWristIn"],
    "LElbow": ["LElbowOut", "LFArm_2"],
    "RElbow": ["RElbowOut", "RFArm_2"],
    "LHip": ["WaistLFront", "WaistLBack", "LThigh"],
    "RHip": ["WaistRFront", "WaistRBack", "RThigh"],
    "LKnee": ["LKneeOut", "LShin_2"],
    "RKnee": ["RKneeOut", "RShin_2"],
    "LAnkle": ["LAnkleOut", "LHeel"],
    "RAnkle": ["RAnkleOut", "RHeel"],
}


def parse_fzmotion_csv(path):
    """Parse FZMotion/Motive CSV (8-row header, Bone channels with X/Y/Z)."""
    # Read all 8 header lines
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        header_lines = [f.readline().strip() for _ in range(8)]

    # Parse sample rate from line 1
    first_parts = header_lines[0].split(",")
    sample_rate = 120.0
    for i in range(0, len(first_parts) - 1, 2):
        if "Capture Frame Rate" in first_parts[i]:
            try:
                sample_rate = float(first_parts[i + 1])
            except (ValueError, IndexError):
                pass
            break

    # Line 4 (index 3): Name row — "Skeleton 001:Skeleton 001", "Skeleton 001:Ab", ...
    # Line 7 (index 6): Quantity row — "Rotation", "Rotation", "Rotation", "Position", "Position", "Position", ...
    # Line 8 (index 7): Axis row — "X", "Y", "Z", "X", "Y", "Z", ...
    name_parts = header_lines[3].split(",")
    qty_parts = header_lines[6].split(",")
    axis_parts = header_lines[7].split(",")

    # Build column -> joint mapping (only Position columns)
    col_to_joint = {}
    for i in range(len(axis_parts)):
        if i < len(qty_parts) and "Position" in qty_parts[i]:
            if i < len(name_parts) and i < len(axis_parts):
                raw_name = name_parts[i]
                joint = raw_name.split(":")[-1] if ":" in raw_name else raw_name
                axis = axis_parts[i]
                if axis in ("X", "Y", "Z") and joint:
                    col_to_joint[i] = (joint, axis)

    # Read data (line 9 onwards)
    data_df = pd.read_csv(path, skiprows=8, low_memory=False, header=None, on_bad_lines="skip")

    # Build xyz_data (convert mm to m)
    xyz_data = {}
    n_rows = len(data_df)
    for col_idx, (joint, axis) in col_to_joint.items():
        if col_idx < data_df.shape[1]:
            if joint not in xyz_data:
                xyz_data[joint] = {}
            xyz_data[joint][axis] = pd.to_numeric(data_df[col_idx], errors="coerce").values / 1000.0

    time = np.arange(n_rows) / sample_rate
    return xyz_data, time, sample_rate


def get_joint_xyz(xyz_data, joint_name):
    """Get XYZ array for a joint (derived or direct)."""
    if joint_name in DERIVED:
        sources = DERIVED[joint_name]
        arrays = []
        for src in sources:
            if src in xyz_data and "X" in xyz_data[src]:
                arr = np.column_stack([xyz_data[src]["X"], xyz_data[src]["Y"], xyz_data[src]["Z"]])
                arrays.append(arr)
        if not arrays:
            return None
        # Mean of sources (ignoring NaN)
        stack = np.stack(arrays)
        with np.errstate(invalid="ignore"):
            result = np.nanmean(stack, axis=0)
        return result

    if joint_name in xyz_data and "X" in xyz_data[joint_name]:
        return np.column_stack([xyz_data[joint_name]["X"], xyz_data[joint_name]["Y"], xyz_data[joint_name]["Z"]])
    return None


def compute_quality_metrics(xyz):
    """Compute quality metrics for a single joint's XYZ trajectory."""
    n = len(xyz)
    valid = np.isfinite(xyz).all(axis=1)
    missing_percent = (1 - valid.sum() / n) * 100

    diffs = np.diff(xyz[valid], axis=0)
    jump_dists = np.sqrt(np.sum(diffs ** 2, axis=1)) if len(diffs) > 0 else np.array([0])
    max_jump_m = float(np.max(jump_dists))
    max_jump_frame = int(np.argmax(jump_dists)) if len(jump_dists) > 0 else 0

    # Moving average for jitter
    window = 13
    pad = window // 2
    smoothed = np.copy(xyz)
    for ax in range(3):
        signal = xyz[:, ax]
        valid_mask = np.isfinite(signal)
        filled = np.nan_to_num(signal, nan=0.0)
        kernel = np.ones(window)
        num = np.convolve(filled, kernel, mode="same")
        den = np.convolve(valid_mask.astype(float), kernel, mode="same")
        with np.errstate(invalid="ignore", divide="ignore"):
            smoothed[:, ax] = num / np.maximum(den, 1)
        smoothed[~valid_mask, ax] = np.nan
        smoothed[:pad, ax] = np.nan
        smoothed[-pad:, ax] = np.nan

    residuals = xyz - smoothed
    valid_res = np.isfinite(residuals).all(axis=1)
    if valid_res.sum() > 0:
        rms_jitter = float(np.sqrt(np.nanmean(residuals[valid_res] ** 2)))
    else:
        rms_jitter = 0.0

    # Quality flag
    if missing_percent > 10 or max_jump_m > 0.50 or rms_jitter > 0.050:
        quality = "poor"
    elif missing_percent > 2 or max_jump_m > 0.20 or rms_jitter > 0.020:
        quality = "warning"
    else:
        quality = "ok"

    return {
        "rms_jitter_mm": round(rms_jitter * 1000, 1),
        "max_jump_mm": round(max_jump_m * 1000, 1),
        "missing_percent": round(missing_percent, 1),
        "max_jump_frame": max_jump_frame,
        "quality": quality,
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_results = {}
    for label, filename in FILES.items():
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            print(f"WARNING: {path} not found, skipping")
            continue

        print(f"Processing: {label} ({filename})...")
        xyz_data, time, rate = parse_fzmotion_csv(path)

        joint_metrics = {}
        for joint in KEY_JOINTS:
            xyz = get_joint_xyz(xyz_data, joint)
            if xyz is not None:
                metrics = compute_quality_metrics(xyz)
                joint_metrics[joint] = metrics

        # Summary
        qualities = [m["quality"] for m in joint_metrics.values()]
        summary = {
            "label": label,
            "sample_rate": round(rate, 1),
            "joints_analyzed": len(joint_metrics),
            "ok": qualities.count("ok"),
            "warning": qualities.count("warning"),
            "poor": qualities.count("poor"),
            "worst_rms_joint": max(joint_metrics, key=lambda j: joint_metrics[j]["rms_jitter_mm"]) if joint_metrics else "",
            "worst_rms_mm": max((m["rms_jitter_mm"] for m in joint_metrics.values()), default=0),
            "worst_jump_joint": max(joint_metrics, key=lambda j: joint_metrics[j]["max_jump_mm"]) if joint_metrics else "",
            "worst_jump_mm": max((m["max_jump_mm"] for m in joint_metrics.values()), default=0),
        }

        all_results[label] = {"summary": summary, "joints": joint_metrics}
        print(f"  OK:{summary['ok']} Warn:{summary['warning']} Poor:{summary['poor']}")

    # Save JSON
    json_path = os.path.join(OUTPUT_DIR, "comparison_metrics.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\nSaved: {json_path}")

    # Generate comparison bar charts
    labels = list(all_results.keys())
    colors = {"ok": "#27ae60", "warning": "#f39c12", "poor": "#e74c3c"}
    bar_colors = ["#27ae60", "#e74c12", "#f39c12", "#e74c3c"]

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle("动捕数据质量对比 — 4组健美操采集数据", fontsize=14, fontweight="bold")

    # Chart 1: Quality distribution
    ax = axes[0]
    x = np.arange(len(labels))
    ok_vals = [all_results[l]["summary"]["ok"] for l in labels]
    warn_vals = [all_results[l]["summary"]["warning"] for l in labels]
    poor_vals = [all_results[l]["summary"]["poor"] for l in labels]
    ax.bar(x, ok_vals, color="#27ae60", label="OK")
    ax.bar(x, warn_vals, bottom=ok_vals, color="#f39c12", label="Warning")
    ax.bar(x, poor_vals, bottom=[o+w for o, w in zip(ok_vals, warn_vals)], color="#e74c3c", label="Poor")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("关节数")
    ax.set_title("关节质量分布")
    ax.legend(fontsize=9)

    # Chart 2: RMS jitter comparison
    ax = axes[1]
    # Pick a few representative joints
    rep_joints = ["RWrist", "RElbow", "RShoulder", "RAnkle", "RKnee"]
    x = np.arange(len(rep_joints))
    width = 0.2
    for i, label in enumerate(labels):
        vals = [all_results[label]["joints"].get(j, {}).get("rms_jitter_mm", 0) for j in rep_joints]
        ax.bar(x + i * width, vals, width, label=label, color=bar_colors[i])
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(rep_joints, fontsize=9)
    ax.set_ylabel("RMS抖动 (mm)")
    ax.set_title("关键关节 RMS 抖动对比")
    ax.legend(fontsize=8)
    ax.axhline(y=20, color="#f39c12", linestyle="--", alpha=0.5, label="Warning阈值")

    # Chart 3: Max jump comparison
    ax = axes[2]
    for i, label in enumerate(labels):
        vals = [all_results[label]["joints"].get(j, {}).get("max_jump_mm", 0) for j in rep_joints]
        ax.bar(x + i * width, vals, width, label=label, color=bar_colors[i])
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(rep_joints, fontsize=9)
    ax.set_ylabel("最大跳跃 (mm)")
    ax.set_title("关键关节最大跳跃对比")
    ax.legend(fontsize=8)
    ax.axhline(y=200, color="#f39c12", linestyle="--", alpha=0.5)
    ax.axhline(y=500, color="#e74c3c", linestyle="--", alpha=0.5)

    plt.tight_layout()
    chart_path = os.path.join(STATIC_DIR, "case1_quality_comparison.png")
    fig.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {chart_path}")

    # Generate trajectory comparison (right wrist X)
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    fig.suptitle("右腕 X 轨迹对比 — 正常 vs 异常", fontsize=14, fontweight="bold")

    for idx, (label, filename) in enumerate(FILES.items()):
        ax = axes[idx // 2][idx % 2]
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            continue
        xyz_data, time, rate = parse_fzmotion_csv(path)
        wrist_xyz = get_joint_xyz(xyz_data, "RWrist")
        if wrist_xyz is not None:
            ax.plot(time, wrist_xyz[:, 0], linewidth=0.5, alpha=0.8)
        ax.set_title(label, fontsize=11)
        ax.set_xlabel("时间 (s)")
        ax.set_ylabel("X 位置 (mm)")
        ax.set_ylim([-1500, 500])

    plt.tight_layout()
    traj_path = os.path.join(STATIC_DIR, "case1_trajectory_comparison.png")
    fig.savefig(traj_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {traj_path}")

    print("\nDone! All comparison data and charts generated.")


if __name__ == "__main__":
    main()
