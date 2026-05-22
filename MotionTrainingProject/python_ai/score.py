import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import json
import numpy as np
from python_ai.metrics import compute_all_metrics


WEIGHTS = {"rom": 0.25, "dtw": 0.25, "symmetry": 0.20, "rmse": 0.30}


def aggregate_scores(joint_results: dict) -> dict:
    rom_scores, dtw_scores, rmse_scores, sym_scores = [], [], [], []
    error_joints = []

    for key, val in joint_results.items():
        if key.endswith("_symmetry"):
            sym_scores.append(val["symmetry_score"])
            continue
        rom_scores.append(val["rom_score"])
        dtw_scores.append(val["dtw_score"])
        rmse_scores.append(val["rmse_score"])
        if val["max_error_degree"] > 10:
            error_joints.append({
                "joint": key,
                "error_degree": val["max_error_degree"],
                "frame": val["max_error_frame"],
            })

    avg = lambda lst: round(float(np.mean(lst)), 2) if lst else 0.0
    rom_avg = avg(rom_scores)
    dtw_avg = avg(dtw_scores)
    rmse_avg = avg(rmse_scores)
    sym_avg = avg(sym_scores)

    rmse_avg_val = rmse_avg
    total = round(
        WEIGHTS["rom"] * rom_avg +
        WEIGHTS["dtw"] * dtw_avg +
        WEIGHTS["symmetry"] * sym_avg +
        WEIGHTS["rmse"] * rmse_avg_val,
        2
    )

    error_joints.sort(key=lambda x: x["error_degree"], reverse=True)
    for ej in error_joints[:5]:
        deg = ej["error_degree"]
        ej["level"] = "red" if deg > 15 else "yellow" if deg > 10 else "green"

    return {
        "total_score": total,
        "rom_score": rom_avg,
        "dtw_score": dtw_avg,
        "symmetry_score": sym_avg,
        "rmse_score": rmse_avg,
        "error_joints": error_joints[:5],
    }


def full_scoring(std_angles: dict, stu_angles: dict, student_id: str = "S001",
                 action_type: str = "unknown") -> dict:
    joint_results = compute_all_metrics(std_angles, stu_angles)
    summary = aggregate_scores(joint_results)
    summary["student_id"] = student_id
    summary["action_type"] = action_type
    summary["joint_details"] = joint_results
    return summary


def save_result(result: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
