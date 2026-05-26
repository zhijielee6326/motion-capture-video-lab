import shutil
import subprocess
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np

from .pose_estimator import KeyPoint
from .annotator import draw_skeleton, draw_info_bar, draw_dimension_panel
from .processor import FrameData


class AnnotatedVideoWriter:
    def __init__(self, video_path: str, fps: float, detect_size=(640, 480)):
        self.video_path = video_path
        self.fps = fps
        self.detect_size = detect_size

    def write(self, frames_data: list[FrameData], score_result: dict, output_path: str) -> str:
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            return ""

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        original_fps = cap.get(cv2.CAP_PROP_FPS)

        fourcc = cv2.VideoWriter.fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_path, fourcc, original_fps, (width, height))

        dw, dh = self.detect_size
        scale_x = width / dw
        scale_y = height / dh

        frame_step = max(1, int(original_fps / self.fps)) if self.fps > 0 else 1

        frame_id = 0
        data_idx = 0
        total_data = len(frames_data)

        overlay_cache = np.zeros((height, width, 3), dtype=np.uint8)
        has_overlay = False

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_id % frame_step == 0 and data_idx < total_data:
                fd = frames_data[data_idx]
                if fd.keypoints:
                    overlay_cache = np.zeros_like(frame)
                    scaled_kpts = [
                        KeyPoint(kp.name, int(kp.x * scale_x), int(kp.y * scale_y), kp.confidence)
                        for kp in fd.keypoints
                    ]
                    draw_skeleton(overlay_cache, scaled_kpts)
                    has_overlay = True

                if has_overlay:
                    mask = overlay_cache.any(axis=2)
                    frame[mask] = overlay_cache[mask]

                data_idx += 1
            else:
                if has_overlay:
                    mask = overlay_cache.any(axis=2)
                    frame[mask] = overlay_cache[mask]

            # Draw info bar and dimension panel on sampled frames
            if frame_id % frame_step == 0 and score_result.get("total_score", 0) > 0:
                draw_info_bar(frame, score_result["total_score"])
                draw_dimension_panel(frame, score_result.get("dimensions", []))

            writer.write(frame)
            frame_id += 1

        cap.release()
        writer.release()

        self._transcode_to_h264(output_path)
        return output_path

    def _transcode_to_h264(self, input_path: str):
        h264_path = input_path.replace(".mp4", "_h264.mp4")
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        try:
            subprocess.run(
                [ffmpeg_exe, "-i", input_path,
                 "-c:v", "libx264", "-preset", "fast", "-crf", "28",
                 "-movflags", "+faststart", "-y", h264_path],
                check=True, capture_output=True,
            )
            Path(input_path).unlink()
            shutil.move(h264_path, input_path)
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            if Path(h264_path).exists():
                Path(h264_path).unlink(missing_ok=True)
