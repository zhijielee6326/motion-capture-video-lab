"""Export motion evaluation score as UE5-compatible JSON."""
import sys, os, argparse, json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from python_ai.convert_motive_csv import convert_motive_csv
from python_ai.read_csv import read_csv
from python_ai.preprocess import preprocess
from python_ai.angle import compute_all_angles
from python_ai.score import full_scoring


JOINT_TO_MOTIVE_BONE = {
    "RightElbow": "RFArm",
    "LeftElbow": "LFArm",
    "RightShoulder": "RShoulder",
    "LeftShoulder": "LShoulder",
    "RightKnee": "RShin",
    "LeftKnee": "LShin",
    "RightHip": "RThigh",
    "LeftHip": "LThigh",
}


def _detect_and_convert(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        first = f.readline()
    if "Format Version" in first:
        converted = path.replace(".csv", "_converted.csv")
        convert_motive_csv(path, converted)
        return converted
    return path


def _color_for_score(score: float) -> str:
    if score >= 80:
        return "green"
    elif score >= 50:
        return "yellow"
    return "red"


def export_ue5_json(student_csv: str, std_csv: str = None,
                    split: float = 0.5, output: str = None,
                    student_id: str = "S001",
                    action_type: str = "unknown") -> dict:
    if std_csv is None:
        std_csv = student_csv
        use_split = True
    else:
        use_split = False

    std_path = _detect_and_convert(std_csv)
    stu_path = _detect_and_convert(student_csv)

    std_df = read_csv(std_path)
    stu_df = read_csv(stu_path)

    if use_split:
        mid = int(len(std_df) * split)
        std_df = std_df.iloc[:mid].reset_index(drop=True)
        stu_df = stu_df.iloc[mid:].reset_index(drop=True)

    std_clean = std_path.replace(".csv", "_ue5clean.csv")
    stu_clean = stu_path.replace(".csv", "_ue5clean.csv")
    preprocess(std_path, std_clean)
    preprocess(stu_path, stu_clean)

    std_df = read_csv(std_clean)
    stu_df = read_csv(stu_clean)

    if use_split:
        mid = int(len(std_df) * split)
        std_df = std_df.iloc[:mid].reset_index(drop=True)
        stu_df = stu_df.iloc[mid:].reset_index(drop=True)

    std_angles = compute_all_angles(std_df)
    stu_angles = compute_all_angles(stu_df)
    result = full_scoring(std_angles, stu_angles, student_id, action_type)

    fps = None
    if "time" in std_df.columns and len(std_df) > 1:
        dt = std_df["time"].diff().dropna()
        fps = round(1.0 / dt.mean(), 1)

    ue5_data = {
        "final_score": result["total_score"],
        "grade": result["grade"]["grade"],
        "student_info": {
            "name": student_id,
            "action_type": action_type,
            "fps": fps,
            "frame_count_std": len(std_df),
            "frame_count_stu": len(stu_df),
        },
        "dimensions": [
            {"name": "ROM 动作幅度", "score": result["rom_score"], "max_score": 100,
             "color": _color_for_score(result["rom_score"])},
            {"name": "DTW 节奏一致性", "score": result["dtw_score"], "max_score": 100,
             "color": _color_for_score(result["dtw_score"])},
            {"name": "左右对称性", "score": result["symmetry_score"], "max_score": 100,
             "color": _color_for_score(result["symmetry_score"])},
            {"name": "RMSE 关节精度", "score": result["rmse_score"], "max_score": 100,
             "color": _color_for_score(result["rmse_score"])},
        ],
        "joint_colors": [],
        "deductions": result.get("deductions", []),
        "suggestions": result.get("suggestions", []),
        "error_joints": result.get("error_joints", []),
        "weights": result.get("weights", {}),
    }

    for joint_name, details in result.get("joint_details", {}).items():
        if joint_name.endswith("_symmetry"):
            continue
        avg_score = np.mean([details["rom_score"], details["dtw_score"],
                             details["rmse_score"]])
        bone = JOINT_TO_MOTIVE_BONE.get(joint_name, joint_name)
        ue5_data["joint_colors"].append({
            "bone": bone,
            "joint": joint_name,
            "label": result.get("grade", {}),
            "score": round(avg_score, 1),
            "color": _color_for_score(avg_score),
            "rom_score": details["rom_score"],
            "dtw_score": details["dtw_score"],
            "rmse_score": details["rmse_score"],
            "max_error_degree": details["max_error_degree"],
            "max_error_frame": details["max_error_frame"],
        })

    if output:
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            json.dump(ue5_data, f, ensure_ascii=False, indent=2)
        print(f"Exported to {output}")

    return ue5_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export motion score as UE5 JSON")
    parser.add_argument("student_csv", help="Student motion CSV (or single CSV if using --split)")
    parser.add_argument("--std-csv", help="Standard motion CSV (if separate from student)")
    parser.add_argument("--split", type=float, default=0.5, help="Split ratio for single CSV (default 0.5)")
    parser.add_argument("--output", "-o", help="Output JSON path")
    parser.add_argument("--student-id", default="S001")
    parser.add_argument("--action-type", default="unknown",
                        choices=["aerobics", "basketball_dribble", "basketball_shot", "gymnastics", "dance", "rehab", "unknown"])
    args = parser.parse_args()

    out = args.output or args.student_csv.replace(".csv", "_ue5_score.json")
    data = export_ue5_json(
        args.student_csv,
        std_csv=args.std_csv,
        split=args.split,
        output=out,
        student_id=args.student_id,
        action_type=args.action_type,
    )
    print(f"Score: {data['final_score']}  Grade: {data['grade']}")
    print(f"Joints: {len(data['joint_colors'])}  Colors: "
          + ", ".join(f"{j['bone']}={j['color']}" for j in data['joint_colors']))
