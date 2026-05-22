import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import json
import numpy as np
from python_ai.metrics import compute_all_metrics


WEIGHTS = {"rom": 0.25, "dtw": 0.25, "symmetry": 0.20, "rmse": 0.30}

ACTION_WEIGHTS = {
    "aerobics":        {"rom": 0.30, "dtw": 0.25, "symmetry": 0.15, "rmse": 0.30},
    "basketball_dribble": {"rom": 0.20, "dtw": 0.20, "symmetry": 0.15, "rmse": 0.45},
    "basketball_shot":   {"rom": 0.20, "dtw": 0.20, "symmetry": 0.15, "rmse": 0.45},
    "gymnastics":      {"rom": 0.35, "dtw": 0.25, "symmetry": 0.20, "rmse": 0.20},
    "dance":           {"rom": 0.30, "dtw": 0.30, "symmetry": 0.20, "rmse": 0.20},
    "rehab":           {"rom": 0.20, "dtw": 0.25, "symmetry": 0.30, "rmse": 0.25},
}

JOINT_CN = {
    "RightElbow": "右肘", "LeftElbow": "左肘",
    "RightShoulder": "右肩", "LeftShoulder": "左肩",
    "RightKnee": "右膝", "LeftKnee": "左膝",
    "RightHip": "右髋", "LeftHip": "左髋",
}

GRADE_THRESHOLDS = [
    (90, "优秀", "#27ae60"),
    (80, "良好", "#4472C4"),
    (70, "中等", "#f39c12"),
    (60, "及格", "#e67e22"),
    (0,  "需要加强", "#e74c3c"),
]


def _get_weights(action_type: str) -> dict:
    return ACTION_WEIGHTS.get(action_type, WEIGHTS)


def _grade(total_score: float) -> dict:
    for threshold, label, color in GRADE_THRESHOLDS:
        if total_score >= threshold:
            return {"grade": label, "color": color}
    return {"grade": "需要加强", "color": "#e74c3c"}


def _generate_deductions(scores: dict, joint_results: dict) -> list:
    deductions = []

    if scores["rom_score"] < 80:
        deductions.append({
            "dimension": "ROM 动作幅度",
            "points_lost": round(100 - scores["rom_score"], 1),
            "reason": f"动作幅度得分{scores['rom_score']}分，低于优秀阈值80分",
            "suggestion": "注意加大关节活动范围，确保动作充分伸展，对照标准动作模板调整幅度。",
        })

    if scores["dtw_score"] < 80:
        deductions.append({
            "dimension": "DTW 节奏一致性",
            "points_lost": round(100 - scores["dtw_score"], 1),
            "reason": f"节奏一致性得分{scores['dtw_score']}分，动作节奏与标准模板偏差较大",
            "suggestion": "练习时注意动作节奏，可先慢速跟练标准动作，逐步提速至标准节奏。",
        })

    if scores["symmetry_score"] < 80:
        deductions.append({
            "dimension": "左右对称性",
            "points_lost": round(100 - scores["symmetry_score"], 1),
            "reason": f"左右对称性得分{scores['symmetry_score']}分，左右侧肢体动作存在明显差异",
            "suggestion": "关注左右侧关节角度的一致性，针对性加强较弱一侧的训练。",
        })

    if scores["rmse_score"] < 80:
        deductions.append({
            "dimension": "RMSE 关节精度",
            "points_lost": round(100 - scores["rmse_score"], 1),
            "reason": f"关节角度误差得分{scores['rmse_score']}分，部分关节与标准动作偏差较大",
            "suggestion": "重点关注偏差较大的关节，对照标准动作的关键帧逐一调整姿势。",
        })

    return deductions


def _generate_suggestions(deductions: list, error_joints: list) -> list:
    suggestions = []

    if not deductions:
        suggestions.append("动作质量优秀，继续保持！可以尝试提高动作难度或速度。")
        return suggestions

    dim_names = [d["dimension"] for d in deductions]
    if "ROM 动作幅度" in dim_names:
        suggestions.append("建议进行关节活动度训练，每次练习前做充分的热身拉伸。")
    if "DTW 节奏一致性" in dim_names:
        suggestions.append("建议使用节拍器辅助练习，先以70%速度跟练，再逐步提速。")
    if "左右对称性" in dim_names:
        suggestions.append("建议进行单侧强化训练，提升较弱一侧的控制力。")
    if "RMSE 关节精度" in dim_names:
        suggestions.append("建议放慢动作速度，逐帧对照标准姿势进行精确修正。")

    for ej in error_joints[:3]:
        jn = JOINT_CN.get(ej["joint"], ej["joint"])
        if ej["level"] == "red":
            suggestions.append(f"{jn}偏差严重（{ej['error_degree']}°），需重点纠正，建议单独反复练习该关节动作。")

    return suggestions


def aggregate_scores(joint_results: dict, action_type: str = "unknown") -> dict:
    weights = _get_weights(action_type)
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
                "joint_cn": JOINT_CN.get(key, key),
                "error_degree": val["max_error_degree"],
                "frame": val["max_error_frame"],
            })

    avg = lambda lst: round(float(np.mean(lst)), 2) if lst else 0.0
    rom_avg = avg(rom_scores)
    dtw_avg = avg(dtw_scores)
    rmse_avg = avg(rmse_scores)
    sym_avg = avg(sym_scores)

    total = round(
        weights["rom"] * rom_avg +
        weights["dtw"] * dtw_avg +
        weights["symmetry"] * sym_avg +
        weights["rmse"] * rmse_avg,
        2
    )

    error_joints.sort(key=lambda x: x["error_degree"], reverse=True)
    for ej in error_joints[:5]:
        deg = ej["error_degree"]
        ej["level"] = "red" if deg > 15 else "yellow" if deg > 10 else "green"

    scores = {
        "total_score": total,
        "rom_score": rom_avg,
        "dtw_score": dtw_avg,
        "symmetry_score": sym_avg,
        "rmse_score": rmse_avg,
        "weights": weights,
        "error_joints": error_joints[:5],
    }

    scores["grade"] = _grade(total)
    scores["deductions"] = _generate_deductions(scores, joint_results)
    scores["suggestions"] = _generate_suggestions(scores["deductions"], scores["error_joints"])

    return scores


def full_scoring(std_angles: dict, stu_angles: dict, student_id: str = "S001",
                 action_type: str = "unknown") -> dict:
    joint_results = compute_all_metrics(std_angles, stu_angles)
    summary = aggregate_scores(joint_results, action_type)
    summary["student_id"] = student_id
    summary["action_type"] = action_type
    summary["joint_details"] = joint_results
    return summary


def save_result(result: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
