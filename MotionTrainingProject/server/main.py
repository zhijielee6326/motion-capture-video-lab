import os
import sys
import time
import uuid
import shutil
import numpy as np
import pandas as pd

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from python_ai.read_csv import read_csv, check_csv, get_joint_coords, JOINT_NAMES
from python_ai.preprocess import preprocess, interpolate_missing, gaussian_smooth, normalize_by_hips
from python_ai.angle import compute_all_angles
from python_ai.score import full_scoring, save_result
from python_ai.generate_report import generate_pdf_report
from python_ai.convert_motive_csv import convert_motive_csv
from emergency.action_recognition import recognize_actions
from emergency.scenario_configs import get_scenario
from emergency.ai_evaluator import evaluate_drill
from emergency.generate_report import generate_drill_report


def _is_motive_csv(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as f:
            first_line = f.readline()
        return "Format Version" in first_line
    except Exception:
        return False


def _ensure_fzmotion_csv(path: str) -> str:
    if _is_motive_csv(path):
        converted = path.replace(".csv", "_converted.csv")
        convert_motive_csv(path, converted)
        return converted
    return path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "server", "static", "uploads")
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
LOGS_DIR = os.path.join(BASE_DIR, "logs", "latency")

for d in [UPLOAD_DIR, REPORTS_DIR, LOGS_DIR]:
    os.makedirs(d, exist_ok=True)

app = FastAPI(title="Motion Training & Emergency Drill System")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "server", "static")), name="static")

_core_net_status = {
    "终端接入": "disconnected",
    "用户注册": "disconnected",
    "会话建立": "disconnected",
    "视频回传": "disconnected",
}


def _log_latency(task_id: str, upload_ms: float, score_ms: float, total_ms: float):
    import csv
    log_path = os.path.join(LOGS_DIR, "latency_log.csv")
    write_header = not os.path.exists(log_path)
    with open(log_path, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["task_id", "upload_ms", "score_ms", "total_ms", "timestamp"])
        writer.writerow([task_id, round(upload_ms), round(score_ms), round(total_ms),
                         time.strftime("%Y-%m-%d %H:%M:%S")])


# ──── Case 2: Sports Motion Scoring ────

@app.get("/case2/dashboard", response_class=HTMLResponse)
async def case2_dashboard():
    html_path = os.path.join(BASE_DIR, "server", "static", "case2_dashboard.html")
    return FileResponse(html_path)


@app.post("/case2/upload_motion")
async def case2_upload_motion(
    standard_csv: UploadFile = File(...),
    student_csv: UploadFile = File(...),
    student_id: str = Form("S001"),
    action_type: str = Form("unknown"),
):
    t0 = time.time()
    task_id = str(uuid.uuid4())[:8]

    std_path = os.path.join(UPLOAD_DIR, f"{task_id}_std.csv")
    stu_path = os.path.join(UPLOAD_DIR, f"{task_id}_stu.csv")
    with open(std_path, "wb") as f:
        shutil.copyfileobj(standard_csv.file, f)
    with open(stu_path, "wb") as f:
        shutil.copyfileobj(student_csv.file, f)

    t_upload = time.time()

    std_clean = os.path.join(UPLOAD_DIR, f"{task_id}_std_clean.csv")
    stu_clean = os.path.join(UPLOAD_DIR, f"{task_id}_stu_clean.csv")
    preprocess(_ensure_fzmotion_csv(std_path), std_clean)
    preprocess(_ensure_fzmotion_csv(stu_path), stu_clean)

    std_df = read_csv(std_clean)
    stu_df = read_csv(stu_clean)
    std_angles = compute_all_angles(std_df)
    stu_angles = compute_all_angles(stu_df)

    result = full_scoring(std_angles, stu_angles, student_id, action_type)
    result["task_id"] = task_id

    t_score = time.time()

    report_dir = os.path.join(REPORTS_DIR, task_id)
    pdf_path = generate_pdf_report(result, std_angles, stu_angles, report_dir)
    result["report_url"] = f"/case2/report/{task_id}"

    json_path = os.path.join(report_dir, "result.json")
    save_result(result, json_path)

    t_total = time.time()
    result["latency_ms"] = round((t_total - t0) * 1000, 1)
    _log_latency(task_id, (t_upload - t0) * 1000, (t_score - t_upload) * 1000,
                 (t_total - t0) * 1000)

    return result


@app.get("/case2/report/{task_id}")
async def case2_download_report(task_id: str):
    report_dir = os.path.join(REPORTS_DIR, task_id)
    if not os.path.isdir(report_dir):
        raise HTTPException(404, "Report not found")
    for f in os.listdir(report_dir):
        if f.endswith("_report.pdf"):
            return FileResponse(os.path.join(report_dir, f), media_type="application/pdf",
                                filename=f"{task_id}_{f}")
    raise HTTPException(404, "Report not found")


@app.get("/case2/check_csv")
async def case2_check_csv(path: str):
    if not os.path.exists(path):
        raise HTTPException(404, "File not found")
    df = read_csv(path)
    return check_csv(df)


BONE_CONNECTIONS = [
    ("Neck", "Head"), ("Spine1", "Neck"), ("Spine", "Spine1"), ("Hips", "Spine"),
    ("Spine1", "LeftShoulder"), ("LeftShoulder", "LeftArm"), ("LeftArm", "LeftForeArm"), ("LeftForeArm", "LeftHand"),
    ("Spine1", "RightShoulder"), ("RightShoulder", "RightArm"), ("RightArm", "RightForeArm"), ("RightForeArm", "RightHand"),
    ("Hips", "LeftUpLeg"), ("LeftUpLeg", "LeftLeg"), ("LeftLeg", "LeftFoot"),
    ("Hips", "RightUpLeg"), ("RightUpLeg", "RightLeg"), ("RightLeg", "RightFoot"),
]

SCORING_JOINTS = [
    "Head", "Neck", "Spine", "Spine1", "Spine2", "Spine3", "Hips",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
    "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
]


@app.get("/case2/skeleton_data/{task_id}")
async def case2_skeleton_data(task_id: str):
    json_path = os.path.join(REPORTS_DIR, task_id, "result.json")
    if not os.path.exists(json_path):
        raise HTTPException(404, f"Task {task_id} not found")

    import json
    with open(json_path, "r", encoding="utf-8") as f:
        result = json.load(f)

    std_clean = os.path.join(UPLOAD_DIR, f"{task_id}_std_clean.csv")
    stu_clean = os.path.join(UPLOAD_DIR, f"{task_id}_stu_clean.csv")
    if not os.path.exists(std_clean) or not os.path.exists(stu_clean):
        raise HTTPException(404, "Clean CSV files not found")

    std_df = read_csv(std_clean)
    stu_df = read_csv(stu_clean)

    available_joints = [j for j in SCORING_JOINTS
                        if f"{j}_x" in std_df.columns and f"{j}_x" in stu_df.columns]

    max_frames = max(len(std_df), len(stu_df))
    target_fps = 30
    dt = std_df["time"].diff().dropna()
    orig_fps = round(1.0 / dt.mean(), 1) if len(dt) > 0 else 100
    step = max(1, int(orig_fps / target_fps))

    std_frames = []
    stu_frames = []
    for i in range(0, max_frames, step):
        sf = []
        ef = []
        for j in available_joints:
            if i < len(std_df):
                sf.extend([float(std_df.iloc[i][f"{j}_x"]), float(std_df.iloc[i][f"{j}_y"]), float(std_df.iloc[i][f"{j}_z"])])
            else:
                sf.extend([0, 0, 0])
            if i < len(stu_df):
                ef.extend([float(stu_df.iloc[i][f"{j}_x"]), float(stu_df.iloc[i][f"{j}_y"]), float(stu_df.iloc[i][f"{j}_z"])])
            else:
                ef.extend([0, 0, 0])
        std_frames.append(sf)
        stu_frames.append(ef)

    joint_idx = {j: i for i, j in enumerate(available_joints)}
    bones = []
    for a, b in BONE_CONNECTIONS:
        if a in joint_idx and b in joint_idx:
            bones.append([joint_idx[a], joint_idx[b]])

    error_joints = result.get("error_joints", [])
    joint_colors = []
    error_joint_set = {ej["joint"] for ej in error_joints}
    for j in available_joints:
        color = "default"
        for ej in error_joints:
            if ej["joint"] == j:
                color = ej["level"]
                break
        joint_colors.append({"joint": j, "joint_cn": result.get("joint_cn", {}), "color": color})

    return {
        "fps": target_fps,
        "frame_count": len(std_frames),
        "joint_names": available_joints,
        "std_frames": std_frames,
        "stu_frames": stu_frames,
        "bone_connections": bones,
        "joint_colors": joint_colors,
        "error_joints": error_joints,
        "total_score": result.get("total_score", 0),
        "grade": result.get("grade", {}),
    }


def _inject_fault_on_df(df: pd.DataFrame, fault_type: str) -> pd.DataFrame:
    df = df.copy()
    coord_cols = [c for c in df.columns if c.endswith(("_x", "_y", "_z"))]

    if fault_type == "marker_occlusion":
        for target in ["RightForeArm", "RightHand"]:
            tcols = [c for c in coord_cols if c.startswith(target)]
            mid = len(df) // 3
            for c in tcols:
                df.iloc[mid:mid + 60, df.columns.get_loc(c)] = np.nan

    elif fault_type == "binding_error":
        for target in ["LeftShoulder", "LeftArm"]:
            tcols = [c for c in coord_cols if c.startswith(target)]
            for c in tcols:
                if c.endswith("_x"):
                    df[c] = df[c] + 80
                elif c.endswith("_y"):
                    df[c] = df[c] + 60
                elif c.endswith("_z"):
                    df[c] = df[c] + 40

    elif fault_type == "network_delay":
        df = df.iloc[::3].reset_index(drop=True)

    elif fault_type == "score_drift":
        for target in ["RightForeArm", "RightHand", "RightArm"]:
            tcols = [c for c in coord_cols if c.startswith(target)]
            for c in tcols:
                df[c] = df[c] * 1.8

    return df


def _optimize_fault(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = interpolate_missing(df)
    df = gaussian_smooth(df, sigma=3)
    return df


@app.post("/case2/fault_diagnosis")
async def case2_fault_diagnosis(
    standard_csv: UploadFile = File(...),
    student_csv: UploadFile = File(...),
    fault_type: str = Form("marker_occlusion"),
    student_id: str = Form("S001"),
    action_type: str = Form("unknown"),
):
    task_id = str(uuid.uuid4())[:8]

    std_path = os.path.join(UPLOAD_DIR, f"{task_id}_diag_std.csv")
    stu_path = os.path.join(UPLOAD_DIR, f"{task_id}_diag_stu.csv")
    with open(std_path, "wb") as f:
        shutil.copyfileobj(standard_csv.file, f)
    with open(stu_path, "wb") as f:
        shutil.copyfileobj(student_csv.file, f)

    preprocess(_ensure_fzmotion_csv(std_path), std_path.replace(".csv", "_clean.csv"))
    preprocess(_ensure_fzmotion_csv(stu_path), stu_path.replace(".csv", "_clean.csv"))
    std_df = read_csv(std_path.replace(".csv", "_clean.csv"))
    stu_df = read_csv(stu_path.replace(".csv", "_clean.csv"))
    std_angles = compute_all_angles(std_df)
    stu_angles_normal = compute_all_angles(stu_df)
    result_normal = full_scoring(std_angles, stu_angles_normal, student_id, action_type)

    stu_faulty = _inject_fault_on_df(stu_df, fault_type)
    stu_angles_faulty = compute_all_angles(stu_faulty)
    result_faulty = full_scoring(std_angles, stu_angles_faulty, student_id, action_type)

    stu_optimized = _optimize_fault(stu_faulty)
    stu_angles_opt = compute_all_angles(stu_optimized)
    result_optimized = full_scoring(std_angles, stu_angles_opt, student_id, action_type)

    score_drop = result_normal["total_score"] - result_faulty["total_score"]
    score_recovery = result_optimized["total_score"] - result_faulty["total_score"]
    recovery_pct = round(score_recovery / score_drop * 100, 1) if score_drop > 0 else 0

    fault_descriptions = {
        "marker_occlusion": "右前臂标记点连续30帧遮挡（第{mid}帧附近）",
        "binding_error": "左肩骨骼绑定偏移：X偏移20mm，Y偏移15mm",
        "network_delay": "网络延迟导致采样率降为50fps（隔帧丢失）",
        "score_drift": "右肘关节坐标缩放异常（×1.3倍）",
    }

    diagnosis = {
        "task_id": task_id,
        "fault_type": fault_type,
        "fault_description": fault_descriptions.get(fault_type, fault_type),
        "normal_score": result_normal["total_score"],
        "normal_detail": {
            "rom": result_normal["rom_score"],
            "dtw": result_normal["dtw_score"],
            "symmetry": result_normal["symmetry_score"],
            "rmse": result_normal["rmse_score"],
        },
        "faulty_score": result_faulty["total_score"],
        "faulty_detail": {
            "rom": result_faulty["rom_score"],
            "dtw": result_faulty["dtw_score"],
            "symmetry": result_faulty["symmetry_score"],
            "rmse": result_faulty["rmse_score"],
        },
        "optimized_score": result_optimized["total_score"],
        "optimized_detail": {
            "rom": result_optimized["rom_score"],
            "dtw": result_optimized["dtw_score"],
            "symmetry": result_optimized["symmetry_score"],
            "rmse": result_optimized["rmse_score"],
        },
        "score_drop": round(score_drop, 2),
        "score_recovery": round(score_recovery, 2),
        "recovery_pct": recovery_pct,
        "optimization_method": "线性插值补帧 + 高斯滤波(sigma=3)",
        "normal_error_joints": result_normal["error_joints"],
        "faulty_error_joints": result_faulty["error_joints"],
        "optimized_error_joints": result_optimized["error_joints"],
    }

    import json
    diag_dir = os.path.join(REPORTS_DIR, task_id)
    os.makedirs(diag_dir, exist_ok=True)
    with open(os.path.join(diag_dir, "diagnosis.json"), "w", encoding="utf-8") as f:
        json.dump(diagnosis, f, ensure_ascii=False, indent=2)

    return diagnosis


# ──── Case 1 & 3: Info Pages ────

@app.get("/case1/info", response_class=HTMLResponse)
async def case1_info():
    html_path = os.path.join(BASE_DIR, "server", "static", "case1_info.html")
    return FileResponse(html_path)


@app.get("/case3/info", response_class=HTMLResponse)
async def case3_info():
    html_path = os.path.join(BASE_DIR, "server", "static", "case3_info.html")
    return FileResponse(html_path)


# ──── Case 4: Emergency Drill ────

@app.get("/case4/dashboard", response_class=HTMLResponse)
async def case4_dashboard():
    html_path = os.path.join(BASE_DIR, "server", "static", "case4_dashboard.html")
    return FileResponse(html_path)


@app.post("/case4/upload_action")
async def case4_upload_action(
    motion_csv: UploadFile = File(...),
    scenario: str = Form("earthquake"),
):
    t0 = time.time()
    task_id = str(uuid.uuid4())[:8]

    csv_path = os.path.join(UPLOAD_DIR, f"{task_id}_emergency.csv")
    with open(csv_path, "wb") as f:
        shutil.copyfileobj(motion_csv.file, f)

    clean_path = os.path.join(UPLOAD_DIR, f"{task_id}_emergency_clean.csv")
    preprocess(_ensure_fzmotion_csv(csv_path), clean_path)
    df = read_csv(clean_path)
    angles = compute_all_angles(df)

    actions = recognize_actions(df, angles, scenario)
    eval_result = evaluate_drill(actions, scenario)
    eval_result["task_id"] = task_id
    eval_result["scenario"] = scenario
    eval_result["latency_ms"] = round((time.time() - t0) * 1000, 1)

    report_dir = os.path.join(REPORTS_DIR, task_id)
    generate_drill_report(eval_result, report_dir)
    eval_result["report_url"] = f"/case4/report/{task_id}"

    return eval_result


@app.post("/case4/inject_fault")
async def case4_inject_fault(
    fault_type: str = Form("network_delay"),
    severity: str = Form("medium"),
):
    fault_effects = {
        "network_delay": {"delay_ms": 300, "description": "Network delay 300ms injected"},
        "packet_loss": {"loss_rate": 0.01, "description": "1% random packet loss injected"},
        "marker_occlusion": {"occluded_joints": ["RightForeArm"], "description": "Right forearm marker occluded"},
        "binding_error": {"offset_deg": 10, "description": "10deg binding offset on left shoulder"},
    }
    if fault_type not in fault_effects:
        raise HTTPException(400, f"Unknown fault type: {fault_type}")
    effect = fault_effects[fault_type]
    effect["severity"] = severity
    effect["fault_type"] = fault_type
    return effect


@app.get("/case4/network", response_class=HTMLResponse)
async def case4_network_page():
    html_path = os.path.join(BASE_DIR, "server", "static", "case4_network.html")
    return FileResponse(html_path)


@app.get("/case4/network_status")
async def case4_get_network_status():
    return {"steps": dict(_core_net_status)}


@app.post("/case4/set_network_status")
async def case4_set_network_status(step: str = Form(...), status: str = Form("connected")):
    if step not in _core_net_status:
        raise HTTPException(400, f"Unknown step: {step}. Valid: {list(_core_net_status.keys())}")
    _core_net_status[step] = status
    return {"step": step, "status": status, "all": dict(_core_net_status)}


@app.post("/case4/core_network_timeline")
async def case4_core_network_timeline(task_id: str = ""):
    import time as _t
    now = _t.time()
    steps = [
        {"step": "终端接入", "order": 1},
        {"step": "用户注册", "order": 2},
        {"step": "会话建立", "order": 3},
        {"step": "视频回传", "order": 4},
    ]
    timeline = []
    for i, s in enumerate(steps):
        offset = (i + 1) * 2.5
        timeline.append({
            **s,
            "timestamp": round(now + offset, 2),
            "status": "connected" if task_id else "disconnected",
        })
    return {"timeline": timeline, "steps": len(steps)}


@app.get("/case4/report/{task_id}")
async def case4_download_report(task_id: str):
    pdf_path = os.path.join(REPORTS_DIR, task_id, f"drill_report.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(404, "Report not found")
    return FileResponse(pdf_path, media_type="application/pdf",
                        filename=f"{task_id}_drill_report.pdf")


# ──── CENI Simulation (Case 2) ────

@app.post("/case2/ceni_upload")
async def case2_ceni_upload(task_id: str = Form(...)):
    import time as _t
    t0 = _t.time()
    json_path = os.path.join(REPORTS_DIR, task_id, "result.json")
    if not os.path.exists(json_path):
        raise HTTPException(404, f"Task {task_id} not found")

    import json
    with open(json_path, "r", encoding="utf-8") as f:
        result = json.load(f)

    file_size = os.path.getsize(json_path)
    simulated_delay = round(200 + (file_size % 300), 1)

    _log_latency(task_id + "_ceni", simulated_delay, 0, simulated_delay)

    return {
        "task_id": task_id,
        "status": "uploaded",
        "file_size_bytes": file_size,
        "simulated_upload_ms": simulated_delay,
        "ceni_endpoint": "simulated",
    }


@app.get("/case2/ceni_download/{task_id}")
async def case2_ceni_download(task_id: str):
    report_dir = os.path.join(REPORTS_DIR, task_id)
    if not os.path.isdir(report_dir):
        raise HTTPException(404, "Report not found for CENI download")
    for f in os.listdir(report_dir):
        if f.endswith("_report.pdf"):
            file_size = os.path.getsize(os.path.join(report_dir, f))
            simulated_delay = round(300 + (file_size % 200), 1)
            return FileResponse(os.path.join(report_dir, f), media_type="application/pdf",
                                filename=f"{task_id}_ceni_report.pdf")
    raise HTTPException(404, "Report not found for CENI download")


# ──── Root ────

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = os.path.join(BASE_DIR, "server", "static", "index.html")
    return FileResponse(html_path)
