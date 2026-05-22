import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_FONT_REGISTERED = False

def _register_fonts():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return
    for name, paths in [
        ("SimHei", ["C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/msyh.ttc"]),
        ("SimSun", ["C:/Windows/Fonts/simsun.ttc", "C:/Windows/Fonts/msyh.ttc"]),
    ]:
        for p in paths:
            if os.path.exists(p):
                try:
                    pdfmetrics.registerFont(TTFont(name, p))
                    break
                except Exception:
                    continue
    _FONT_REGISTERED = True


def _cn_font():
    _register_fonts()
    try:
        pdfmetrics.getFont("SimHei")
        return "SimHei"
    except Exception:
        try:
            pdfmetrics.getFont("SimSun")
            return "SimSun"
        except Exception:
            return "Helvetica"


ACTION_CN = {
    "aerobics": "健美操", "basketball_shot": "篮球投篮",
    "gymnastics": "体操", "dance": "舞蹈", "rehab": "康复训练",
}

JOINT_CN = {
    "RightElbow": "右肘", "LeftElbow": "左肘",
    "RightShoulder": "右肩", "LeftShoulder": "左肩",
    "RightKnee": "右膝", "LeftKnee": "左膝",
    "RightHip": "右髋", "LeftHip": "左髋",
}


def plot_radar_chart(scores: dict, output_path: str):
    labels = ["ROM\n动作幅度", "DTW\n节奏一致性", "对称性", "RMSE\n关节精度"]
    values = [scores["rom_score"], scores["dtw_score"],
              scores["symmetry_score"], scores["rmse_score"]]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    values_plot = values + [values[0]]
    angles_plot = angles + [angles[0]]

    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
    ax.fill(angles_plot, values_plot, color="#4472C4", alpha=0.25)
    ax.plot(angles_plot, values_plot, "o-", color="#4472C4", linewidth=2)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 100)
    grade = scores.get("grade", {})
    grade_label = grade.get("grade", "") if isinstance(grade, dict) else ""
    ax.set_title(f"综合评分: {scores['total_score']}  {grade_label}", fontsize=13, fontweight="bold", pad=20)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_angle_comparison(std_angles: dict, stu_angles: dict, joint: str, output_path: str):
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(8, 4))
    jn = JOINT_CN.get(joint, joint)
    if joint in std_angles and joint in stu_angles:
        ax.plot(std_angles[joint], label="标准动作", color="#4472C4", linewidth=1.5)
        ax.plot(stu_angles[joint], label="学生动作", color="#ED7D31", linewidth=1.5, alpha=0.8)
    ax.set_xlabel("帧")
    ax.set_ylabel("角度 (°)")
    ax.set_title(f"{jn}({joint}) 角度对比")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _check_page(c, y, h, margin=50):
    if y < margin * mm:
        c.showPage()
        return h - 30 * mm
    return y


def generate_pdf_report(result: dict, std_angles: dict, stu_angles: dict,
                        output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)

    radar_path = os.path.join(output_dir, "radar_chart.png")
    plot_radar_chart(result, radar_path)

    angle_paths = []
    for joint in list(std_angles.keys())[:4]:
        p = os.path.join(output_dir, f"{joint}_compare.png")
        plot_angle_comparison(std_angles, stu_angles, joint, p)
        angle_paths.append(p)

    font = _cn_font()
    font_bold = font
    pdf_path = os.path.join(output_dir, f"{result['student_id']}_report.pdf")
    c = canvas.Canvas(pdf_path, pagesize=A4)
    w, h = A4
    y = h - 25 * mm

    c.setFont(font_bold, 20)
    c.drawString(30 * mm, y, "运动质量评估报告")
    y -= 8 * mm
    c.setStrokeColor("#4472C4")
    c.setLineWidth(2)
    c.line(30 * mm, y, 180 * mm, y)
    y -= 10 * mm

    c.setFont(font, 12)
    action_cn = ACTION_CN.get(result.get("action_type", ""), result.get("action_type", ""))
    c.drawString(30 * mm, y, f"学生: {result['student_id']}    动作类型: {action_cn}")
    y -= 10 * mm

    grade_info = result.get("grade", {})
    grade_label = grade_info.get("grade", "") if isinstance(grade_info, dict) else str(grade_info)

    c.setFont(font_bold, 16)
    c.drawString(30 * mm, y, f"综合评分: {result['total_score']} 分")
    c.setFont(font_bold, 14)
    c.drawString(140 * mm, y, f"等级: {grade_label}")
    y -= 10 * mm

    weights = result.get("weights", {"rom": 0.25, "dtw": 0.25, "symmetry": 0.20, "rmse": 0.30})
    c.setFont(font, 11)
    dim_info = [
        ("ROM 动作幅度", "rom_score", "rom"),
        ("DTW 节奏一致性", "dtw_score", "dtw"),
        ("左右对称性", "symmetry_score", "symmetry"),
        ("RMSE 关节精度", "rmse_score", "rmse"),
    ]
    for label, key, wk in dim_info:
        wt = weights.get(wk, 0)
        c.drawString(30 * mm, y, f"  {label}: {result[key]} 分 (权重 {int(wt*100)}%)")
        y -= 7 * mm

    y -= 5 * mm
    c.setFont(font_bold, 13)
    c.drawString(30 * mm, y, "偏差关节:")
    y -= 8 * mm
    c.setFont(font, 10)
    for ej in result.get("error_joints", []):
        jn = JOINT_CN.get(ej["joint"], ej["joint"])
        level_cn = {"red": "严重", "yellow": "注意", "green": "正常"}.get(ej["level"], ej["level"])
        c.drawString(35 * mm, y, f"  {jn}({ej['joint']}): {ej['error_degree']}°  帧#{ej['frame']}  [{level_cn}]")
        y -= 6 * mm
        y = _check_page(c, y, h)

    deductions = result.get("deductions", [])
    if deductions:
        y -= 5 * mm
        y = _check_page(c, y, h)
        c.setFont(font_bold, 13)
        c.drawString(30 * mm, y, "扣分明细:")
        y -= 8 * mm
        c.setFont(font, 10)
        for d in deductions:
            c.setFont(font_bold, 11)
            c.drawString(35 * mm, y, f"■ {d['dimension']} (-{d['points_lost']}分)")
            y -= 6 * mm
            y = _check_page(c, y, h)
            c.setFont(font, 10)
            c.drawString(40 * mm, y, f"原因: {d['reason']}")
            y -= 5 * mm
            y = _check_page(c, y, h)
            c.drawString(40 * mm, y, f"建议: {d['suggestion']}")
            y -= 7 * mm
            y = _check_page(c, y, h)

    suggestions = result.get("suggestions", [])
    if suggestions:
        y -= 5 * mm
        y = _check_page(c, y, h)
        c.setFont(font_bold, 13)
        c.drawString(30 * mm, y, "改进建议:")
        y -= 8 * mm
        c.setFont(font, 10)
        for i, s in enumerate(suggestions, 1):
            c.drawString(35 * mm, y, f"{i}. {s}")
            y -= 6 * mm
            y = _check_page(c, y, h)

    c.showPage()

    if os.path.exists(radar_path):
        c.setFont(font_bold, 14)
        c.drawString(30 * mm, h - 25 * mm, "评分雷达图")
        c.drawImage(radar_path, 30 * mm, h - 160 * mm, width=120 * mm, height=120 * mm)
        c.showPage()

    for ap in angle_paths:
        if os.path.exists(ap):
            fname = os.path.basename(ap).replace("_compare.png", "")
            jn = JOINT_CN.get(fname, fname)
            c.setFont(font_bold, 14)
            c.drawString(30 * mm, h - 25 * mm, f"{jn} 角度对比图")
            c.drawImage(ap, 15 * mm, h - 120 * mm, width=180 * mm, height=90 * mm)
            c.showPage()

    c.save()
    return pdf_path
