"""Shared OpenCV preprocessing for training and deployed ONNX inference."""
import cv2
import numpy as np

SIDE = 224
MEAN = np.array([.485, .456, .406], np.float32)
STD = np.array([.229, .224, .225], np.float32)


def letterbox_rgb(image: np.ndarray, side: int = SIDE) -> np.ndarray:
    height, width = image.shape[:2]
    scale = side / max(height, width)
    resized = cv2.resize(image, (max(1, round(width * scale)), max(1, round(height * scale))),
                         interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
    canvas = np.full((side, side, 3), 127, np.uint8)
    y, x = (side - resized.shape[0]) // 2, (side - resized.shape[1]) // 2
    canvas[y:y + resized.shape[0], x:x + resized.shape[1]] = resized
    return cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)


def input_tensor(image: np.ndarray, side: int = SIDE) -> np.ndarray:
    rgb = letterbox_rgb(image, side).astype(np.float32) / 255
    return np.ascontiguousarray(((rgb - MEAN) / STD).transpose(2, 0, 1)[None])
