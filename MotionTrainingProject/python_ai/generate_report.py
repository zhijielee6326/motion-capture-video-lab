import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm


def plot_radar_chart(scores: dict, output_path: str):
    labels = ["ROM", "DTW", "Symmetry", "RMSE"]
    values = [scores["rom_score"], scores["dtw_score"],
              scores["symmetry_score"], scores["rmse_score"]]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    values_plot = values + [values[0]]
    angles_plot = angles + [angles[0]]

    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
    ax.fill(angles_plot, values_plot, color="#4472C4", alpha=0.25)
    ax.plot(angles_plot, values_plot, "o-", color="#4472C4", linewidth=2)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=12)
    ax.set_ylim(0, 100)
    ax.set_title(f"Score: {scores['total_score']}", fontsize=14, fontweight="bold", pad=20)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_angle_comparison(std_angles: dict, stu_angles: dict, joint: str, output_path: str):
    fig, ax = plt.subplots(figsize=(8, 4))
    if joint in std_angles and joint in stu_angles:
        ax.plot(std_angles[joint], label="Standard", color="#4472C4", linewidth=1.5)
        ax.plot(stu_angles[joint], label="Student", color="#ED7D31", linewidth=1.5, alpha=0.8)
    ax.set_xlabel("Frame")
    ax.set_ylabel("Angle (deg)")
    ax.set_title(f"{joint} Angle Comparison")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


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

    pdf_path = os.path.join(output_dir, f"{result['student_id']}_report.pdf")
    c = canvas.Canvas(pdf_path, pagesize=A4)
    w, h = A4
    y = h - 30 * mm

    c.setFont("Helvetica-Bold", 18)
    c.drawString(30 * mm, y, "Motion Quality Assessment Report")
    y -= 12 * mm

    c.setFont("Helvetica", 11)
    c.drawString(30 * mm, y, f"Student: {result['student_id']}    Action: {result['action_type']}")
    y -= 10 * mm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(30 * mm, y, f"Total Score: {result['total_score']}")
    y -= 8 * mm

    c.setFont("Helvetica", 11)
    for label, key in [("ROM", "rom_score"), ("DTW", "dtw_score"),
                        ("Symmetry", "symmetry_score"), ("RMSE", "rmse_score")]:
        c.drawString(30 * mm, y, f"  {label}: {result[key]}")
        y -= 7 * mm

    y -= 5 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30 * mm, y, "Error Joints:")
    y -= 8 * mm
    c.setFont("Helvetica", 10)
    for ej in result.get("error_joints", []):
        c.drawString(35 * mm, y, f"  {ej['joint']}: {ej['error_degree']} deg (frame {ej['frame']})")
        y -= 6 * mm
        if y < 50 * mm:
            c.showPage()
            y = h - 30 * mm

    c.showPage()

    if os.path.exists(radar_path):
        c.drawImage(radar_path, 30 * mm, h - 160 * mm, width=120 * mm, height=120 * mm)
        c.showPage()

    for ap in angle_paths:
        if os.path.exists(ap):
            c.drawImage(ap, 15 * mm, h - 120 * mm, width=180 * mm, height=90 * mm)
            c.showPage()

    c.save()
    return pdf_path
