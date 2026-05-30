"""Batch analysis: convert + analyze all 4 conditions, generate comparison charts."""
from __future__ import annotations

import csv
import re
import json
from collections import Counter
from pathlib import Path

import kineticstoolkit as ktk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
import numpy as np
import pandas as pd


# ── Input: 4 Motive CSVs in lab3 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "数据" / "lab3"
CONDITIONS = {
    "正常(最佳标定)": DATA_DIR / "案例3-正常best.csv",
    "标定结果差":     DATA_DIR / "案例3-标定结果差.csv",
    "少两个标记点":   DATA_DIR / "案例3-少俩个标记点.csv",
    "遮挡摄像头":     DATA_DIR / "案例3-遮挡视像头.csv",
}

# ── Output ──
OUT_BASE = Path(__file__).resolve().parent / "data" / "conditions"
SERVER_STATIC = PROJECT_ROOT / "MotionTrainingProject" / "server" / "static"
CASE1_ANALYSIS = PROJECT_ROOT / "MotionTrainingProject" / "data" / "case1_analysis"

MAJOR_KEY_JOINTS = [
    "Skeleton_002", "Ab", "Chest", "Neck", "Head",
    "LShoulder", "LElbow", "LWrist", "LHand",
    "RShoulder", "RElbow", "RWrist", "RHand",
    "LHip", "LKnee", "LAnkle", "LFoot", "LToe",
    "RHip", "RKnee", "RAnkle", "RFoot", "RToe",
]

DERIVED_JOINTS = {
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


# ── Motive CSV reader (from convert_dance_csv_to_timeseries.py) ──

def _safe_name(name: str) -> str:
    name = name.split(":")[-1].strip()
    name = re.sub(r"[^0-9A-Za-z_]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "Unnamed"


def _make_unique(names: list[str]) -> list[str]:
    counts: Counter[str] = Counter()
    unique_names = []
    for name in names:
        counts[name] += 1
        if counts[name] == 1:
            unique_names.append(name)
        else:
            unique_names.append(f"{name}_{counts[name]}")
    return unique_names


def _to_float(value: str) -> float:
    value = value.strip()
    return float(value) if value else np.nan


def read_mocap_csv(path: Path) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Read Motive CSV → flat DataFrame + frame + time arrays."""
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        rows = list(csv.reader(f))

    name_row = rows[3]
    quantity_row = rows[6]
    axis_row = rows[7]
    data_rows = rows[8:]

    frame = np.array([int(row[0]) for row in data_rows], dtype=int)
    time = np.array([float(row[1]) for row in data_rows], dtype=float)

    channels = []
    column_groups = []
    base_names = []

    for col in range(2, len(axis_row), 3):
        axes = axis_row[col:col + 3]
        if axes != ["X", "Y", "Z"]:
            continue
        if quantity_row[col].strip() != "Position":
            continue
        base_name = _safe_name(name_row[col])
        base_names.append(base_name)
        column_groups.append((col, col + 1, col + 2))

    unique_names = _make_unique(base_names)
    columns = {"Frame": frame, "Time": time}
    for unique_name, cols in zip(unique_names, column_groups):
        xyz_mm = np.array(
            [[_to_float(row[c]) for c in cols] for row in data_rows], dtype=float
        )
        xyz_m = xyz_mm / 1000.0
        columns[f"{unique_name}_X"] = xyz_m[:, 0]
        columns[f"{unique_name}_Y"] = xyz_m[:, 1]
        columns[f"{unique_name}_Z"] = xyz_m[:, 2]
        channels.append(unique_name)

    return pd.DataFrame(columns), frame, time, channels


def load_xyz(df: pd.DataFrame, key: str) -> np.ndarray:
    cols = [f"{key}_X", f"{key}_Y", f"{key}_Z"]
    if not all(c in df.columns for c in cols):
        return np.full((len(df), 3), np.nan)
    return df[cols].to_numpy(dtype=float)


def nanmean_stack(arrays: list[np.ndarray]) -> np.ndarray:
    stack = np.stack(arrays)
    valid = np.isfinite(stack)
    count = valid.sum(axis=0)
    total = np.nansum(stack, axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = total / count
    out[count == 0] = np.nan
    return out


def moving_average_ignore_nan(values: np.ndarray, window: int = 13) -> np.ndarray:
    pad = window // 2
    kernel = np.ones(window, dtype=float)
    smoothed = np.empty_like(values, dtype=float)
    for axis in range(values.shape[1]):
        signal = values[:, axis]
        valid = np.isfinite(signal).astype(float)
        filled = np.nan_to_num(signal, nan=0.0)
        numerator = np.convolve(filled, kernel, mode="same")
        denominator = np.convolve(valid, kernel, mode="same")
        with np.errstate(invalid="ignore", divide="ignore"):
            smoothed[:, axis] = numerator / denominator
        smoothed[denominator == 0] = np.nan
        smoothed[:pad, axis] = np.nan
        smoothed[-pad:, axis] = np.nan
    return smoothed


def classify_quality(rms_m: float, jump_m: float, missing_pct: float) -> str:
    if missing_pct > 10 or jump_m > 0.50 or rms_m > 0.050:
        return "poor"
    if missing_pct > 2 or jump_m > 0.20 or rms_m > 0.020:
        return "warning"
    return "ok"


def compute_joint_metrics(xyz: np.ndarray, frame: np.ndarray, time: np.ndarray) -> dict:
    valid = np.all(np.isfinite(xyz), axis=1)
    missing_pct = 100.0 * (~valid).sum() / len(xyz)

    step = np.diff(xyz, axis=0)
    step_valid = np.all(np.isfinite(step), axis=1)
    if step_valid.any():
        norms = np.linalg.norm(step[step_valid], axis=1)
        idx = int(np.argmax(norms))
        max_jump_m = float(norms[idx])
        max_jump_frame = int(frame[np.flatnonzero(step_valid)[idx] + 1])
    else:
        max_jump_m = np.nan
        max_jump_frame = -1

    ref = moving_average_ignore_nan(xyz)
    residual = xyz - ref
    res_valid = np.all(np.isfinite(residual), axis=1)
    rms_m = float(np.sqrt(np.mean(np.sum(residual[res_valid] ** 2, axis=1)))) if res_valid.any() else np.nan

    return {
        "rms_jitter_mm": rms_m * 1000,
        "max_jump_mm": max_jump_m * 1000,
        "missing_percent": missing_pct,
        "max_jump_frame": max_jump_frame,
        "quality": classify_quality(rms_m, max_jump_m, missing_pct),
    }


# ── Main pipeline ──

def main():
    OUT_BASE.mkdir(parents=True, exist_ok=True)

    all_condition_data = {}   # label → (df, frame, time, channels, all_xyz)
    all_condition_metrics = {}

    for label, csv_path in CONDITIONS.items():
        if not csv_path.exists():
            print(f"SKIP {label}: {csv_path} not found")
            continue
        print(f"Processing: {label} ...")
        df, frame, time, channels = read_mocap_csv(csv_path)

        # Build all_xyz including derived joints
        all_xyz = {}
        for ch in channels:
            all_xyz[ch] = load_xyz(df, ch)
        for derived_key, source_keys in DERIVED_JOINTS.items():
            available = [all_xyz[s] for s in source_keys if s in all_xyz]
            if available:
                all_xyz[derived_key] = nanmean_stack(available)

        all_condition_data[label] = (df, frame, time, channels, all_xyz)

        # Per-joint metrics for major key joints
        joint_metrics = {}
        for j in MAJOR_KEY_JOINTS:
            if j in all_xyz:
                joint_metrics[j] = compute_joint_metrics(all_xyz[j], frame, time)

        ok = sum(1 for m in joint_metrics.values() if m["quality"] == "ok")
        warn = sum(1 for m in joint_metrics.values() if m["quality"] == "warning")
        poor = sum(1 for m in joint_metrics.values() if m["quality"] == "poor")
        worst_rms = max(joint_metrics.values(), key=lambda m: m.get("rms_jitter_mm", 0)) if joint_metrics else {}
        worst_jump = max(joint_metrics.values(), key=lambda m: m.get("max_jump_mm", 0)) if joint_metrics else {}

        all_condition_metrics[label] = {
            "summary": {
                "label": label,
                "sample_rate": 120.0,
                "joints_analyzed": len(joint_metrics),
                "ok": ok, "warning": warn, "poor": poor,
                "worst_rms_mm": worst_rms.get("rms_jitter_mm", 0),
                "worst_jump_mm": worst_jump.get("max_jump_mm", 0),
            },
            "joints": joint_metrics,
        }

    if not all_condition_data:
        print("No data processed!")
        return

    # ── 1. Trajectory comparison: RWrist X across all conditions ──
    colors = {"正常(最佳标定)": "#27ae60", "标定结果差": "#e67e22", "少两个标记点": "#e74c3c", "遮挡摄像头": "#9b59b6"}
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    ax = axes[0]
    for label, (df, frame, time, channels, all_xyz) in all_condition_data.items():
        if "RWrist" in all_xyz:
            ax.plot(time, all_xyz["RWrist"][:, 0], label=label, linewidth=0.8, color=colors.get(label, None), alpha=0.85)
    ax.set_ylabel("RWrist X (m)")
    ax.set_title("右腕 X 轨迹对比 — 四种采集条件")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)

    # Smoothed overlay
    ax = axes[1]
    for label, (df, frame, time, channels, all_xyz) in all_condition_data.items():
        if "RWrist" in all_xyz:
            smoothed = moving_average_ignore_nan(all_xyz["RWrist"])
            ax.plot(time, smoothed[:, 0], label=label, linewidth=1.2, color=colors.get(label, None))
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("RWrist X smoothed (m)")
    ax.set_title("右腕 X 平滑轨迹对比")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    traj_path = OUT_BASE / "trajectory_comparison_all_conditions.png"
    fig.savefig(traj_path, dpi=160)
    plt.close(fig)
    print(f"Saved: {traj_path}")

    # ── 2. Per-condition trajectory (4 separate subplots) ──
    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
    for i, (label, (df, frame, time, channels, all_xyz)) in enumerate(all_condition_data.items()):
        ax = axes[i]
        if "RWrist" in all_xyz:
            raw = all_xyz["RWrist"][:, 0]
            smoothed = moving_average_ignore_nan(all_xyz["RWrist"])[:, 0]
            ax.plot(time, raw, linewidth=0.6, alpha=0.6, color=colors.get(label, None), label="原始轨迹")
            ax.plot(time, smoothed, linewidth=1.5, color=colors.get(label, None), label="平滑参考")
        ax.set_ylabel(f"{label}\nX (m)", fontsize=9)
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, alpha=0.3)
    axes[-1].set_xlabel("Time (s)")
    axes[0].set_title("各条件下右腕 X 轨迹")
    fig.tight_layout()
    per_cond_path = OUT_BASE / "per_condition_trajectory.png"
    fig.savefig(per_cond_path, dpi=160)
    plt.close(fig)
    print(f"Saved: {per_cond_path}")

    # ── 3. Quality bar chart comparison ──
    labels = list(all_condition_metrics.keys())
    ok_vals = [all_condition_metrics[l]["summary"]["ok"] for l in labels]
    warn_vals = [all_condition_metrics[l]["summary"]["warning"] for l in labels]
    poor_vals = [all_condition_metrics[l]["summary"]["poor"] for l in labels]

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(labels))
    w = 0.25
    ax.bar(x - w, ok_vals, w, label="OK", color="#27ae60")
    ax.bar(x, warn_vals, w, label="Warning", color="#f39c12")
    ax.bar(x + w, poor_vals, w, label="Poor", color="#e74c3c")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("关节数")
    ax.set_title("各条件下关节质量分布")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    bar_path = OUT_BASE / "quality_comparison_bar.png"
    fig.savefig(bar_path, dpi=160)
    plt.close(fig)
    print(f"Saved: {bar_path}")

    # ── 4. RMS jitter comparison bar chart ──
    compare_joints = ["RWrist", "LWrist", "RElbow", "LElbow", "RShoulder", "LShoulder", "RHip", "LHip", "RKnee", "LKnee"]
    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(compare_joints))
    w = 0.2
    for i, label in enumerate(labels):
        rms_vals = []
        for j in compare_joints:
            jm = all_condition_metrics[label]["joints"].get(j, {})
            rms_vals.append(jm.get("rms_jitter_mm", 0))
        ax.bar(x + i * w, rms_vals, w, label=label, color=colors.get(label, None))
    ax.set_xticks(x + w * 1.5)
    ax.set_xticklabels(compare_joints, fontsize=9, rotation=30, ha="right")
    ax.set_ylabel("RMS 抖动 (mm)")
    ax.set_title("各条件关键关节 RMS 抖动对比")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    rms_path = OUT_BASE / "rms_jitter_comparison.png"
    fig.savefig(rms_path, dpi=160)
    plt.close(fig)
    print(f"Saved: {rms_path}")

    # ── 5. Save comparison JSON ──
    comp_json = OUT_BASE / "comparison_metrics.json"
    with open(comp_json, "w", encoding="utf-8") as f:
        json.dump(all_condition_metrics, f, ensure_ascii=False, indent=2)
    print(f"Saved: {comp_json}")

    # ── 6. Copy to server static ──
    import shutil
    for src, dst_name in [
        (traj_path, "case1_trajectory_comparison.png"),
        (bar_path, "case1_quality_comparison.png"),
        (per_cond_path, "case1_per_condition_trajectory.png"),
        (rms_path, "case1_rms_jitter_comparison.png"),
    ]:
        dst = SERVER_STATIC / dst_name
        shutil.copy2(src, dst)
        print(f"Copied → {dst}")

    # Also update the case1_analysis comparison JSON
    comp_dst = CASE1_ANALYSIS / "comparison_metrics.json"
    shutil.copy2(comp_json, comp_dst)
    print(f"Updated → {comp_dst}")

    print("\nDone! All conditions analyzed and charts generated.")


if __name__ == "__main__":
    main()
