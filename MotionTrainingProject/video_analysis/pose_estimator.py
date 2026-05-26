import os
import numpy as np
import cv2


class KeyPoint:
    def __init__(self, name: str, x: int, y: int, confidence: float = 1.0):
        self.name = name
        self.x = x
        self.y = y
        self.confidence = confidence


KEYPOINT_NAMES = [
    "nose", "right_eye", "left_eye", "right_ear", "left_ear",
    "right_shoulder", "left_shoulder", "right_elbow", "left_elbow",
    "right_wrist", "left_wrist", "right_hip", "left_hip",
    "right_knee", "left_knee", "right_ankle", "left_ankle",
]

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "weights", "yolov8n-pose.onnx")


class YOLOPoseEstimator:
    def __init__(self, conf_threshold=0.15):
        model_path = MODEL_PATH
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")
        self.net = cv2.dnn.readNetFromONNX(model_path)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        self.input_size = (640, 640)
        self.conf_threshold = conf_threshold

    def _letterbox(self, frame):
        h, w = frame.shape[:2]
        iw, ih = self.input_size
        scale = min(iw / w, ih / h)
        new_w, new_h = int(w * scale), int(h * scale)

        resized = cv2.resize(frame, (new_w, new_h))
        pad_top = (ih - new_h) // 2
        pad_left = (iw - new_w) // 2

        canvas = np.zeros((ih, iw, 3), dtype=np.uint8)
        canvas[pad_top:pad_top + new_h, pad_left:pad_left + new_w] = resized

        return canvas, scale, pad_left, pad_top

    def estimate(self, frame: np.ndarray) -> list[KeyPoint] | None:
        h, w = frame.shape[:2]
        canvas, scale, pad_x, pad_y = self._letterbox(frame)

        blob = cv2.dnn.blobFromImage(canvas, 1.0 / 255.0, self.input_size, swapRB=True)
        self.net.setInput(blob)
        output = self.net.forward()

        if output.shape[0] != 1 or output.shape[1] != 56:
            return None

        data = output[0]
        scores = data[4, :]

        best_idx = np.argmax(scores)
        best_score = scores[best_idx]

        if best_score < self.conf_threshold:
            return None

        kpts = data[5:, best_idx]
        keypoints = []
        for i in range(17):
            kx = (kpts[i * 3] - pad_x) / scale
            ky = (kpts[i * 3 + 1] - pad_y) / scale
            kc = kpts[i * 3 + 2]
            keypoints.append(KeyPoint(
                name=KEYPOINT_NAMES[i],
                x=int(kx),
                y=int(ky),
                confidence=float(kc),
            ))

        return keypoints
