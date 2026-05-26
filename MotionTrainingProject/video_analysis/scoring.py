import numpy as np
from .math_utils import get_abc_degree, get_2d_dist
from .processor import FrameData

# YOLOv8 keypoint indices
R_SHOULDER, L_SHOULDER = 5, 6
R_ELBOW, L_ELBOW = 7, 8
R_WRIST, L_WRIST = 9, 10
R_HIP, L_HIP = 11, 12
R_KNEE, L_KNEE = 13, 14
R_ANKLE, L_ANKLE = 15, 16


def score_motion(frames_data: list[FrameData], fps: float) -> dict:
    valid = [f for f in frames_data if f.keypoints]
    if len(valid) < 5:
        return {
            "total_score": 0,
            "dimensions": [],
            "suggestions": ["未检测到足够的人体关键点，请确保视频中人物清晰可见"],
        }

    kpts_list = [[(kp.x, kp.y) for kp in f.keypoints] for f in valid]

    # 1. Joint Angle Reasonableness (0-100)
    angle_score = _score_joint_angles(kpts_list)

    # 2. Body Stability (0-100)
    stability_score = _score_stability(kpts_list)

    # 3. Range of Motion (0-100)
    rom_score = _score_rom(kpts_list)

    # 4. Left-Right Symmetry (0-100)
    symmetry_score = _score_symmetry(kpts_list)

    total = round(angle_score * 0.25 + stability_score * 0.25 +
                  rom_score * 0.25 + symmetry_score * 0.25, 1)

    suggestions = []
    if angle_score < 60:
        suggestions.append("部分关节角度超出正常范围，注意动作规范性")
    if stability_score < 60:
        suggestions.append("身体晃动较大，建议加强核心稳定性训练")
    if rom_score < 60:
        suggestions.append("动作幅度偏小，建议增大关节活动范围")
    if symmetry_score < 60:
        suggestions.append("左右两侧动作不对称，注意均衡发力")

    return {
        "total_score": min(100, max(0, total)),
        "dimensions": [
            {"name": "关节角度", "score": round(angle_score, 1), "max_score": 100},
            {"name": "身体稳定", "score": round(stability_score, 1), "max_score": 100},
            {"name": "动作幅度", "score": round(rom_score, 1), "max_score": 100},
            {"name": "左右对称", "score": round(symmetry_score, 1), "max_score": 100},
        ],
        "suggestions": suggestions,
    }


def _score_joint_angles(kpts_list):
    sample = kpts_list[::5]
    angles = {"r_elbow": [], "l_elbow": [], "r_knee": [], "l_knee": []}
    for kpts in sample:
        if R_SHOULDER < len(kpts) and R_ELBOW < len(kpts) and R_WRIST < len(kpts):
            a = get_abc_degree(kpts[R_SHOULDER], kpts[R_ELBOW], kpts[R_WRIST])
            if 10 < a < 200:
                angles["r_elbow"].append(a)
        if L_SHOULDER < len(kpts) and L_ELBOW < len(kpts) and L_WRIST < len(kpts):
            a = get_abc_degree(kpts[L_SHOULDER], kpts[L_ELBOW], kpts[L_WRIST])
            if 10 < a < 200:
                angles["l_elbow"].append(a)
        if R_HIP < len(kpts) and R_KNEE < len(kpts) and R_ANKLE < len(kpts):
            a = get_abc_degree(kpts[R_HIP], kpts[R_KNEE], kpts[R_ANKLE])
            if 10 < a < 200:
                angles["r_knee"].append(a)
        if L_HIP < len(kpts) and L_KNEE < len(kpts) and L_ANKLE < len(kpts):
            a = get_abc_degree(kpts[L_HIP], kpts[L_KNEE], kpts[L_ANKLE])
            if 10 < a < 200:
                angles["l_knee"].append(a)

    all_angles = []
    for v in angles.values():
        all_angles.extend(v)
    if not all_angles:
        return 50

    in_range = sum(1 for a in all_angles if 40 <= a <= 180)
    return round(in_range / len(all_angles) * 100, 1)


def _score_stability(kpts_list):
    if len(kpts_list) < 3:
        return 50
    joints = [R_SHOULDER, L_SHOULDER, R_HIP, L_HIP]
    total_movement = 0
    count = 0
    for jid in joints:
        for i in range(1, len(kpts_list)):
            if jid < len(kpts_list[i]) and jid < len(kpts_list[i - 1]):
                total_movement += get_2d_dist(kpts_list[i][jid], kpts_list[i - 1][jid])
                count += 1
    if count == 0:
        return 50
    avg = total_movement / count
    if avg < 3:
        return 95
    elif avg < 8:
        return 80
    elif avg < 15:
        return 60
    elif avg < 25:
        return 40
    else:
        return 20


def _score_rom(kpts_list):
    if len(kpts_list) < 5:
        return 50
    joint_pairs = [
        (R_SHOULDER, R_WRIST),
        (L_SHOULDER, L_WRIST),
        (R_HIP, R_ANKLE),
        (L_HIP, L_ANKLE),
    ]
    total_range = 0
    count = 0
    for start_jid, end_jid in joint_pairs:
        positions = []
        for kpts in kpts_list[::3]:
            if start_jid < len(kpts) and end_jid < len(kpts):
                positions.append(kpts[end_jid])
        if len(positions) > 2:
            xs = [p[0] for p in positions]
            ys = [p[1] for p in positions]
            range_x = max(xs) - min(xs)
            range_y = max(ys) - min(ys)
            total_range += (range_x + range_y) / 2
            count += 1
    if count == 0:
        return 50
    avg_range = total_range / count
    if avg_range > 150:
        return 95
    elif avg_range > 100:
        return 80
    elif avg_range > 60:
        return 65
    elif avg_range > 30:
        return 45
    else:
        return 25


def _score_symmetry(kpts_list):
    if len(kpts_list) < 5:
        return 50
    sym_pairs = [
        (R_SHOULDER, L_SHOULDER), (R_ELBOW, L_ELBOW),
        (R_WRIST, L_WRIST), (R_HIP, L_HIP),
        (R_KNEE, L_KNEE), (R_ANKLE, L_ANKLE),
    ]
    angle_diffs = []
    for kpts in kpts_list[::5]:
        for l_jid, r_jid in sym_pairs:
            if l_jid < len(kpts) and r_jid < len(kpts):
                diff = abs(kpts[l_jid][0] - kpts[r_jid][0])
                angle_diffs.append(diff)
    if not angle_diffs:
        return 50
    avg_diff = np.mean(angle_diffs)
    if avg_diff < 20:
        return 95
    elif avg_diff < 40:
        return 80
    elif avg_diff < 70:
        return 60
    elif avg_diff < 100:
        return 40
    else:
        return 20
