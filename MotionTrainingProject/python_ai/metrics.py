import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean


def _clean(angles):
    a = np.array(angles, dtype=float)
    mask = ~np.isnan(a)
    return a[mask] if mask.any() else a

def rom_score(std_angles, stu_angles):
    std_angles, stu_angles = _clean(std_angles), _clean(stu_angles)
    if len(std_angles) == 0 or len(stu_angles) == 0:
        return 50.0, 0.0, 0.0
    std_rom = float(np.max(std_angles) - np.min(std_angles))
    stu_rom = float(np.max(stu_angles) - np.min(stu_angles))
    diff = abs(std_rom - stu_rom)
    score = max(0.0, 100.0 - diff * 2)
    return score, std_rom, stu_rom


def dtw_score(std_seq, stu_seq):
    std_seq, stu_seq = _clean(std_seq), _clean(stu_seq)
    if len(std_seq) == 0 or len(stu_seq) == 0:
        return 50.0, 0.0
    std_arr = np.array(std_seq).reshape(-1, 1)
    stu_arr = np.array(stu_seq).reshape(-1, 1)
    distance, path = fastdtw(std_arr, stu_arr, dist=euclidean)
    avg_dist = distance / len(path) if len(path) > 0 else distance
    score = max(0.0, 100.0 - avg_dist * 2)
    return score, float(distance)


def symmetry_score(left_angles, right_angles):
    left_angles, right_angles = _clean(left_angles), _clean(right_angles)
    if len(left_angles) == 0 or len(right_angles) == 0:
        return 50.0, 0.0
    left = np.array(left_angles)
    right = np.array(right_angles)
    n = min(len(left), len(right))
    left, right = left[:n], right[:n]
    diff = np.mean(np.abs(left - right))
    score = max(0.0, 100.0 - diff * 2)
    return score, float(diff)


def rmse_score(std_angles, stu_angles):
    std_angles, stu_angles = _clean(std_angles), _clean(stu_angles)
    if len(std_angles) == 0 or len(stu_angles) == 0:
        return 50.0, 0.0
    std = np.array(std_angles)
    stu = np.array(stu_angles)
    n = min(len(std), len(stu))
    std, stu = std[:n], stu[:n]
    rmse = float(np.sqrt(np.mean((std - stu) ** 2)))
    score = max(0.0, 100.0 - rmse * 2)
    return score, rmse


def compute_all_metrics(std_angles: dict, stu_angles: dict) -> dict:
    results = {}
    for joint in std_angles:
        if joint not in stu_angles:
            continue
        std_a = std_angles[joint]
        stu_a = stu_angles[joint]

        rom_s, std_rom, stu_rom = rom_score(std_a, stu_a)
        dtw_s, dtw_dist = dtw_score(std_a, stu_a)
        rmse_s, rmse_val = rmse_score(std_a, stu_a)

        results[joint] = {
            "rom_score": round(rom_s, 2),
            "dtw_score": round(dtw_s, 2),
            "rmse_score": round(rmse_s, 2),
            "rmse_value": round(rmse_val, 2),
            "std_rom": round(std_rom, 2),
            "stu_rom": round(stu_rom, 2),
            "dtw_distance": round(dtw_dist, 2),
            "max_error_frame": int(np.argmax(np.abs(std_a[:len(stu_a)] - stu_a[:len(std_a)]))),
            "max_error_degree": round(float(np.max(np.abs(std_a[:len(stu_a)] - stu_a[:len(std_a)]))), 2),
        }

    symmetry_pairs = [
        ("LeftKnee", "RightKnee", "Knee"),
        ("LeftElbow", "RightElbow", "Elbow"),
        ("LeftShoulder", "RightShoulder", "Shoulder"),
        ("LeftHip", "RightHip", "Hip"),
    ]
    for left_name, right_name, label in symmetry_pairs:
        if left_name in std_angles and right_name in std_angles:
            sym_s, sym_diff = symmetry_score(std_angles[left_name], std_angles[right_name])
            results[f"{label}_symmetry"] = {
                "symmetry_score": round(sym_s, 2),
                "symmetry_diff": round(sym_diff, 2),
            }

    return results
