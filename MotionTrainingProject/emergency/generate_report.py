import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def plot_drill_radar(eval_result: dict, output_path: str):
    labels = ["Action", "Process", "Network", "Synergy"]
    values = [
        eval_result["action_score"],
        eval_result["process_score"],
        eval_result["network_score"],
        eval_result["synergy_score"],
    ]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    values_plot = values + [values[0]]
    angles_plot = angles + [angles[0]]

    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
    ax.fill(angles_plot, values_plot, color="#e74c3c", alpha=0.25)
    ax.plot(angles_plot, values_plot, "o-", color="#e74c3c", linewidth=2)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=12)
    ax.set_ylim(0, 100)
    ax.set_title(f"Total: {eval_result['total_score']}", fontsize=14, fontweight="bold", pad=20)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_action_bar(actions: list, output_path: str):
    names = [a["name"][:12] for a in actions]
    confidences = [a["confidence"] * 100 for a in actions]
    colors = {"completed": "#27ae60", "detected": "#f39c12", "uncertain": "#e74c3c"}
    bar_colors = [colors.get(a["status"], "#95a5a6") for a in actions]

    fig, ax = plt.subplots(figsize=(8, 4))
    y_pos = np.arange(len(names))
    ax.barh(y_pos, confidences, color=bar_colors, height=0.6)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel("Confidence (%)")
    ax.set_title("Action Recognition Results")
    ax.set_xlim(0, 100)
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_drill_report(eval_result: dict, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)

    radar_path = os.path.join(output_dir, "drill_radar.png")
    plot_drill_radar(eval_result, radar_path)

    actions = eval_result.get("actions", [])
    bar_path = os.path.join(output_dir, "drill_actions.png")
    if actions:
        plot_action_bar(actions, bar_path)

    pdf_path = os.path.join(output_dir, "drill_report.pdf")
    c = canvas.Canvas(pdf_path, pagesize=A4)
    w, h = A4
    y = h - 30 * mm

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(30 * mm, y, "Emergency Drill Evaluation Report")
    y -= 10 * mm

    c.setFont("Helvetica", 11)
    c.drawString(30 * mm, y, f"Scenario: {eval_result.get('scenario_name', 'N/A')}")
    y -= 7 * mm
    c.drawString(30 * mm, y, f"Date: {time.strftime('%Y-%m-%d %H:%M')}")
    y -= 12 * mm

    # Scores
    c.setFont("Helvetica-Bold", 14)
    c.drawString(30 * mm, y, f"Total Score: {eval_result['total_score']}")
    y -= 10 * mm

    c.setFont("Helvetica", 11)
    for label, key in [
        ("Action Quality", "action_score"),
        ("Process Compliance", "process_score"),
        ("Network Recovery", "network_score"),
        ("Synergy Efficiency", "synergy_score"),
    ]:
        c.drawString(30 * mm, y, f"  {label}: {eval_result[key]}")
        y -= 7 * mm

    # Radar chart page
    y -= 5 * mm
    if os.path.exists(radar_path):
        c.showPage()
        c.drawImage(radar_path, 50 * mm, h - 150 * mm, width=110 * mm, height=110 * mm)

    # Actions page
    c.showPage()
    y = h - 30 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(30 * mm, y, "Action Recognition Results")
    y -= 10 * mm

    c.setFont("Helvetica", 10)
    status_symbols = {"completed": "[OK]", "detected": "[??]", "uncertain": "[XX]"}
    for a in actions:
        sym = status_symbols.get(a["status"], "[--]")
        conf = a["confidence"]
        c.drawString(30 * mm, y, f"  {sym} {a['name']}  (confidence: {conf:.0%})")
        y -= 6 * mm
        if y < 40 * mm:
            c.showPage()
            y = h - 30 * mm

    if actions and os.path.exists(bar_path):
        c.showPage()
        c.drawImage(bar_path, 15 * mm, h - 120 * mm, width=180 * mm, height=90 * mm)

    # Core network status
    c.showPage()
    y = h - 30 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(30 * mm, y, "Core Network Recovery Status")
    y -= 10 * mm

    c.setFont("Helvetica", 11)
    for cs in eval_result.get("core_network_status", []):
        status = cs["status"]
        sym = "ONLINE" if status == "connected" else "OFFLINE"
        c.drawString(30 * mm, y, f"  {cs['step']}: {sym}")
        y -= 7 * mm

    # Issues
    issues = eval_result.get("issues", [])
    if issues:
        y -= 5 * mm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(30 * mm, y, "Issues Found:")
        y -= 8 * mm
        c.setFont("Helvetica", 10)
        for issue in issues:
            c.drawString(35 * mm, y, f"  - {issue}")
            y -= 6 * mm
            if y < 40 * mm:
                c.showPage()
                y = h - 30 * mm

    # Suggestions
    suggestions = eval_result.get("suggestions", [])
    if suggestions:
        y -= 5 * mm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(30 * mm, y, "Suggestions:")
        y -= 8 * mm
        c.setFont("Helvetica", 10)
        for s in suggestions:
            c.drawString(35 * mm, y, f"  - {s}")
            y -= 6 * mm

    c.save()
    return pdf_path
