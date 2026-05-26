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
    "basketball_dribble": "篮球运球",
    "gymnastics": "体操", "dance": "舞蹈", "rehab": "康复训练",
}

JOINT_CN = {
    "RightElbow": "右肘", "LeftElbow": "左肘",
    "RightShoulder": "右肩", "LeftShoulder": "左肩",
    "RightKnee": "右膝", "LeftKnee": "左膝",
    "RightHip": "右髋", "LeftHip": "左髋",
}

LEVEL_CN = {"red": "严重", "yellow": "注意", "green": "正常"}
LEVEL_COLOR = {"red": "#e74c3c", "yellow": "#f39c12", "green": "#27ae60"}


def plot_radar_chart(scores: dict, output_path: str):
    labels = ["ROM\n动作幅度", "DTW\n节奏", "对称性", "RMSE\n精度"]
    values = [scores["rom_score"], scores["dtw_score"],
              scores["symmetry_score"], scores["rmse_score"]]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    values_plot = values + [values[0]]
    angles_plot = angles + [angles[0]]

    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(1.8, 1.8), subplot_kw=dict(polar=True))
    ax.fill(angles_plot, values_plot, color="#4472C4", alpha=0.25)
    ax.plot(angles_plot, values_plot, "o-", color="#4472C4", linewidth=1.2, markersize=3)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=5.5)
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["", "50", "", "100"], fontsize=5, color="#aaa")
    grade = scores.get("grade", {})
    grade_label = grade.get("grade", "") if isinstance(grade, dict) else ""
    ax.set_title(f"{scores['total_score']}分 {grade_label}", fontsize=8, fontweight="bold", pad=8)
    fig.tight_layout(pad=0.3)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_angle_comparison(std_angles: dict, stu_angles: dict, joint: str, output_path: str):
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(2.6, 1.3))
    jn = JOINT_CN.get(joint, joint)
    if joint in std_angles and joint in stu_angles:
        ax.plot(std_angles[joint], label="标准", color="#4472C4", linewidth=1)
        ax.plot(stu_angles[joint], label="学生", color="#ED7D31", linewidth=1, alpha=0.8)
    ax.set_xlabel("帧", fontsize=5)
    ax.set_ylabel("角度(°)", fontsize=5)
    ax.set_title(f"{jn}({joint})", fontsize=7, pad=3)
    ax.legend(fontsize=5, loc="upper right")
    ax.grid(True, alpha=0.2)
    ax.tick_params(labelsize=5)
    fig.tight_layout(pad=0.3)
    fig.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def _draw_score_bar(c, x, y, width, score):
    bar_h = 3
    c.setFillColor("#e0e0e0")
    c.rect(x, y, width, bar_h, stroke=0, fill=1)
    color = "#27ae60" if score >= 80 else "#f39c12" if score >= 60 else "#e74c3c"
    fill_w = width * min(score / 100, 1.0)
    c.setFillColor(color)
    c.rect(x, y, fill_w, bar_h, stroke=0, fill=1)


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
    LM = 15 * mm
    RM = 15 * mm
    content_w = w - LM - RM

    # ── Header bar ──
    c.setFillColor("#1b2838")
    c.rect(0, h - 12 * mm, w, 12 * mm, stroke=0, fill=1)
    c.setFillColor("#7ec8e3")
    c.setFont(font_bold, 12)
    c.drawString(LM, h - 9 * mm, "运动质量评估报告")
    c.setFillColor("#8899aa")
    c.setFont(font, 6.5)
    c.drawRightString(w - RM, h - 9 * mm, "AI Motion Quality Assessment")
    y = h - 16 * mm

    # ── Student info ──
    action_cn = ACTION_CN.get(result.get("action_type", ""), result.get("action_type", ""))
    grade_info = result.get("grade", {})
    grade_label = grade_info.get("grade", "") if isinstance(grade_info, dict) else str(grade_info)
    grade_color = grade_info.get("color", "#4472C4") if isinstance(grade_info, dict) else "#4472C4"

    c.setFont(font, 8)
    c.setFillColor("#333")
    c.drawString(LM, y, f"学生: {result['student_id']}    动作: {action_cn}")
    # Grade badge
    c.setFillColor(grade_color)
    c.roundRect(w - RM - 22 * mm, y - 2, 22 * mm, 7, 3, stroke=0, fill=1)
    c.setFillColor("#fff")
    c.setFont(font_bold, 7.5)
    c.drawCentredString(w - RM - 11 * mm, y, grade_label)
    c.setFillColor("#333")
    y -= 8 * mm

    # ── Left: Score + Dimension bars ──
    LEFT_W = 95 * mm
    c.setFont(font_bold, 24)
    c.setFillColor("#1b2838")
    c.drawString(LM, y - 3 * mm, f"{result['total_score']}")
    c.setFont(font, 7)
    c.setFillColor("#888")
    c.drawString(LM + 40 * mm, y, "分 / 100")
    y -= 8 * mm

    weights = result.get("weights", {"rom": 0.25, "dtw": 0.25, "symmetry": 0.20, "rmse": 0.30})
    dim_info = [
        ("ROM 动作幅度", "rom_score", "rom"),
        ("DTW 节奏一致性", "dtw_score", "dtw"),
        ("左右对称性", "symmetry_score", "symmetry"),
        ("RMSE 关节精度", "rmse_score", "rmse"),
    ]
    bar_w = 40 * mm
    for label, key, wk in dim_info:
        wt = weights.get(wk, 0)
        score = result[key]
        c.setFont(font, 7)
        c.setFillColor("#333")
        c.drawString(LM, y, f"{label}")
        c.drawRightString(LM + 30 * mm, y, f"{score}")
        _draw_score_bar(c, LM + 32 * mm, y + 0.5, bar_w, score)
        c.setFont(font, 5.5)
        c.setFillColor("#888")
        c.drawString(LM + 32 * mm + bar_w + 1.5 * mm, y, f"{int(wt*100)}%")
        y -= 5.5 * mm

    # ── Right: Radar chart ──
    radar_x = LM + LEFT_W + 5 * mm
    radar_sz = 45 * mm
    radar_y = h - 16 * mm - 8 * mm - 24 * mm - 8 * mm - 4 * 5.5 * mm
    if os.path.exists(radar_path):
        c.drawImage(radar_path, radar_x, radar_y, width=radar_sz, height=radar_sz)

    # ── Divider ──
    y -= 3 * mm
    c.setStrokeColor("#ccc")
    c.setLineWidth(0.4)
    c.line(LM, y, w - RM, y)
    y -= 4 * mm

    # ── Error joints (inline, compact) ──
    error_joints = result.get("error_joints", [])
    if error_joints:
        c.setFont(font_bold, 7.5)
        c.setFillColor("#1b2838")
        c.drawString(LM, y, "偏差关节: ")
        ex = LM + 18 * mm
        c.setFont(font, 6.5)
        for ej in error_joints:
            jn = JOINT_CN.get(ej["joint"], ej["joint"])
            level = ej.get("level", "")
            level_cn = LEVEL_CN.get(level, level)
            level_color = LEVEL_COLOR.get(level, "#888")
            c.setFillColor("#333")
            c.drawString(ex, y, f"{jn}")
            ex += 10 * mm
            c.setFillColor(level_color)
            c.drawString(ex, y, f"{ej['error_degree']}°[{level_cn}]")
            ex += 16 * mm
            c.setFillColor("#333")
        y -= 5 * mm

    # ── Deductions (compact, one line each) ──
    deductions = result.get("deductions", [])
    if deductions:
        c.setFont(font_bold, 7.5)
        c.setFillColor("#1b2838")
        c.drawString(LM, y, "扣分明细:")
        y -= 4 * mm
        c.setFont(font, 6.5)
        for d in deductions:
            c.setFillColor("#e74c3c")
            c.drawString(LM + 2*mm, y, f"■ {d['dimension']}(-{d['points_lost']}分)")
            c.setFillColor("#555")
            suggestion = d.get("suggestion", "")
            if len(suggestion) > 45:
                suggestion = suggestion[:42] + "..."
            c.drawString(LM + 55 * mm, y, f"建议: {suggestion}")
            y -= 4 * mm

    # ── Suggestions (compact) ──
    suggestions = result.get("suggestions", [])
    if suggestions:
        y -= 1 * mm
        c.setFont(font_bold, 7.5)
        c.setFillColor("#1b2838")
        c.drawString(LM, y, "改进建议:")
        y -= 4 * mm
        c.setFont(font, 6.5)
        c.setFillColor("#333")
        # Combine into fewer lines
        text = "  ".join(f"{i}.{s}" for i, s in enumerate(suggestions, 1))
        if len(text) > 110:
            text = text[:107] + "..."
        c.drawString(LM + 2*mm, y, text)
        y -= 5 * mm

    # ── Divider ──
    y -= 2 * mm
    c.setStrokeColor("#ccc")
    c.line(LM, y, w - RM, y)
    y -= 3 * mm

    # ── Angle charts 2x2 grid ──
    c.setFont(font_bold, 7.5)
    c.setFillColor("#1b2838")
    c.drawString(LM, y, "关节角度对比分析")
    y -= 2 * mm

    chart_w = (content_w - 4 * mm) / 2
    chart_h = 35 * mm

    positions = [
        (LM, y - chart_h),
        (LM + chart_w + 4 * mm, y - chart_h),
        (LM, y - chart_h * 2 - 2 * mm),
        (LM + chart_w + 4 * mm, y - chart_h * 2 - 2 * mm),
    ]

    for i, ap in enumerate(angle_paths):
        if i >= 4 or not os.path.exists(ap):
            continue
        cx, cy = positions[i]
        c.drawImage(ap, cx, cy, width=chart_w, height=chart_h)

    c.showPage()
    c.save()
    return pdf_path
