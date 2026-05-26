import os
import cv2
import numpy as np
from .pose_estimator import KeyPoint

FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "simsun.ttc")

SKELETON_CONNECTIONS = [
    (15, 13, (0, 165, 255)), (13, 11, (0, 230, 0)),
    (16, 14, (255, 130, 0)), (14, 12, (255, 80, 0)),
    (11, 12, (200, 180, 255)),
    (5, 11, (180, 0, 180)), (6, 12, (240, 160, 80)),
    (5, 6, (180, 255, 180)),
    (5, 7, (180, 50, 100)), (6, 8, (80, 130, 255)),
    (7, 9, (80, 255, 50)), (8, 10, (80, 255, 255)),
    (1, 2, (255, 130, 130)), (0, 5, (255, 255, 130)),
    (0, 6, (255, 130, 230)),
]

KPT_COLORS = {
    0: (0, 0, 255), 1: (255, 180, 0), 2: (255, 180, 0),
    5: (220, 200, 255), 6: (220, 200, 255),
    7: (50, 180, 255), 8: (50, 180, 255),
    9: (50, 255, 255), 10: (50, 255, 255),
    11: (200, 80, 255), 12: (200, 80, 255),
    13: (80, 200, 255), 14: (80, 200, 255),
    15: (0, 140, 255), 16: (0, 140, 255),
}

KPT_RADIUS = 6
KPT_OUTLINE = 2
BONE_THICKNESS = 3

_font_cache: dict = {}


def _get_font(font_size: int):
    if font_size in _font_cache:
        return _font_cache[font_size]
    from PIL import ImageFont
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except OSError:
        font = ImageFont.load_default()
    _font_cache[font_size] = font
    return font


def _put_text(img, text, position, font_size=30, text_color=(255, 255, 255),
              bg_color=(0, 0, 0), padding=6):
    from PIL import Image, ImageDraw
    x, y = position
    font = _get_font(font_size)
    tmp_img = Image.new("RGB", (1, 1))
    tmp_draw = ImageDraw.Draw(tmp_img)
    bbox = tmp_draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    rx1, ry1 = max(0, x - padding), max(0, y - padding)
    rx2, ry2 = min(img.shape[1], x + text_w + padding), min(img.shape[0], y + text_h + padding)
    if bg_color is not None:
        roi = img[ry1:ry2, rx1:rx2]
        if roi.size > 0:
            bg_overlay = np.full_like(roi, bg_color, dtype=np.uint8)
            cv2.addWeighted(bg_overlay, 0.6, roi, 0.4, 0, roi)
    pil_x = x - rx1
    pil_y = y - ry1
    roi = img[ry1:ry2, rx1:rx2]
    if roi.size == 0:
        return img
    roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
    pil_roi = Image.fromarray(roi_rgb)
    draw = ImageDraw.Draw(pil_roi)
    draw.text((pil_x, pil_y), text, text_color[:3], font=font)
    roi[:] = cv2.cvtColor(np.asarray(pil_roi), cv2.COLOR_RGB2BGR)
    return img


def draw_skeleton(frame, keypoints):
    coords = [(kp.x, kp.y) for kp in keypoints]
    for src_id, dst_id, color in SKELETON_CONNECTIONS:
        if src_id < len(coords) and dst_id < len(coords):
            pt1 = (round(coords[src_id][0]), round(coords[src_id][1]))
            pt2 = (round(coords[dst_id][0]), round(coords[dst_id][1]))
            cv2.line(frame, pt1, pt2, color, BONE_THICKNESS)
    for kid, color in KPT_COLORS.items():
        if kid < len(coords):
            cx, cy = round(coords[kid][0]), round(coords[kid][1])
            cv2.circle(frame, (cx, cy), KPT_RADIUS + KPT_OUTLINE, (255, 255, 255), -1)
            cv2.circle(frame, (cx, cy), KPT_RADIUS, color, -1)
    return frame


def draw_angle_arc(frame, point_a, point_b, point_c, angle, is_good):
    color = (0, 220, 0) if is_good else (0, 0, 240)
    bx, by = int(point_b[0]), int(point_b[1])
    cv2.line(frame, (int(point_a[0]), int(point_a[1])), (bx, by), color, 3)
    cv2.line(frame, (int(point_c[0]), int(point_c[1])), (bx, by), color, 3)
    text_color = (80, 255, 80) if is_good else (80, 80, 255)
    frame = _put_text(frame, f"{angle:.0f}", (bx + 12, by - 14), font_size=22, text_color=text_color)
    return frame


def draw_info_bar(frame, score, max_score=100.0):
    h, w = frame.shape[:2]
    bar_h = 48
    overlay = frame[:bar_h, :].copy()
    cv2.rectangle(frame, (0, 0), (w, bar_h), (0, 0, 0), -1)
    cv2.addWeighted(frame[:bar_h, :], 0.3, overlay, 0.7, 0, frame[:bar_h, :])
    frame = _put_text(frame, f"Score: {score:.0f}/{max_score:.0f}", (12, 8),
                      font_size=30, text_color=(80, 255, 80), bg_color=None)
    return frame


def draw_dimension_panel(frame, dimension_scores):
    if not dimension_scores:
        return frame
    h, w = frame.shape[:2]
    panel_w = 170
    line_h = 22
    title_h = 28
    padding = 10
    panel_h = title_h + len(dimension_scores) * line_h + padding * 2
    x0 = w - panel_w
    y0 = 60
    roi = frame[y0:y0 + panel_h, x0:x0 + panel_w]
    if roi.size == 0:
        return frame
    overlay = roi.copy()
    cv2.rectangle(overlay, (0, 0), (panel_w, panel_h), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.7, roi, 0.3, 0, roi)
    cv2.rectangle(frame, (x0, y0), (x0 + panel_w, y0 + panel_h), (100, 100, 100), 1)
    frame = _put_text(frame, "评分维度", (x0 + padding, y0 + 4),
                      font_size=22, text_color=(255, 255, 255), bg_color=None)
    bar_max_w = 50
    for i, dim in enumerate(dimension_scores):
        yi = y0 + title_h + i * line_h + 2
        name = dim["name"][:4]
        ratio = dim["score"] / dim["max_score"] if dim["max_score"] > 0 else 0
        if ratio >= 0.8:
            bar_color, txt_color = (80, 200, 80), (80, 255, 80)
        elif ratio >= 0.5:
            bar_color, txt_color = (80, 180, 255), (80, 200, 255)
        else:
            bar_color, txt_color = (80, 80, 255), (80, 80, 255)
        frame = _put_text(frame, name, (x0 + padding, yi),
                          font_size=18, text_color=(200, 200, 200), bg_color=None)
        bar_x = x0 + padding + 55
        bar_y = yi + 6
        bar_w = int(bar_max_w * ratio)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_max_w, bar_y + 10), (60, 60, 60), -1)
        if bar_w > 0:
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 10), bar_color, -1)
        frame = _put_text(frame, f"{dim['score']:.0f}", (bar_x + bar_max_w + 4, yi),
                          font_size=18, text_color=txt_color, bg_color=None)
    return frame
