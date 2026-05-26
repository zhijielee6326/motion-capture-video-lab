from dataclasses import dataclass

import cv2

from .pose_estimator import YOLOPoseEstimator, KeyPoint


@dataclass
class FrameData:
    frame_id: int
    keypoints: list[KeyPoint] | None = None


class VideoProcessor:
    def __init__(self):
        self.estimator = YOLOPoseEstimator()

    def process_video(self, video_path: str) -> tuple[list[FrameData], float, tuple[int, int]]:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        frames_data: list[FrameData] = []
        frame_id = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            keypoints = self.estimator.estimate(frame)
            frames_data.append(FrameData(frame_id=frame_id, keypoints=keypoints))
            frame_id += 1

        cap.release()
        return frames_data, fps, (width, height)
