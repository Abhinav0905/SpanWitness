"""Compare two image axes without claiming a gravity or 3D measurement."""
from math import atan2, degrees

import cv2
import numpy as np


def fit_axis(image: np.ndarray, points: list[list[float]]) -> dict:
    height, width = image.shape[:2]
    marked = np.asarray(points, dtype=np.float32)
    if marked.shape != (2, 2) or not np.isfinite(marked).all() or ((marked < 0) | (marked > 1)).any():
        raise ValueError("Mark exactly two finite points between 0 and 1 for each axis.")
    marked *= [width - 1, height - 1]
    length = float(np.linalg.norm(marked[1] - marked[0]))
    if length < min(width, height) * .2:
        raise ValueError("Mark a longer section of the pole or reference edge.")
    mask = np.zeros((height, width), np.uint8)
    radius = max(10, round(width * .018))
    cv2.line(mask, tuple(marked[0].astype(int)), tuple(marked[1].astype(int)), 255, radius * 2)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    smooth = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(smooth, 45, 120)
    # Crossarms and wall texture share the corridor but do not follow its axis.
    gradient_x = cv2.Sobel(smooth, cv2.CV_32F, 1, 0, ksize=3)
    gradient_y = cv2.Sobel(smooth, cv2.CV_32F, 0, 1, ksize=3)
    marked_axis = (marked[1] - marked[0]) / length
    tangent_agreement = np.abs(-gradient_y * marked_axis[0] + gradient_x * marked_axis[1]) / np.maximum(cv2.magnitude(gradient_x, gradient_y), 1)
    supported_edges = ((mask > 0) & (edges > 0) & (tangent_agreement > .975)).astype(np.uint8) * 255
    lines = cv2.HoughLinesP(supported_edges, 1, np.pi / 720, max(25, round(length * .10)),
                           minLineLength=length * .4, maxLineGap=length * .04)
    if lines is None:
        return {"usable": False, "reason": "No long edge supports the marked axis. Capture a clearer view or mark the full visible edge."}
    candidates = []
    midpoint = marked.mean(axis=0)
    for coordinates in np.asarray(lines).reshape(-1, 4):
        start, end = coordinates[:2].astype(float), coordinates[2:].astype(float)
        direction = end - start
        extent = float(np.linalg.norm(direction))
        direction /= max(extent, 1)
        if abs(float(direction @ marked_axis)) < .975:
            continue
        offset = midpoint - start
        distance = abs(float(offset[0] * direction[1] - offset[1] * direction[0]))
        candidates.append((extent / (1 + distance / radius), start, direction))
    if not candidates:
        return {"usable": False, "reason": "The visible edges do not follow the marked axis."}
    _, edge_start, edge_direction = max(candidates, key=lambda item: item[0])
    y, x = np.nonzero(supported_edges)
    offsets = np.column_stack([x, y]) - edge_start
    near = np.abs(offsets[:, 0] * edge_direction[1] - offsets[:, 1] * edge_direction[0]) < 3
    x, y = x[near], y[near]
    if len(x) < 30:
        return {"usable": False, "reason": "Too little visible edge support for this marked axis."}
    samples = np.column_stack([x, y]).astype(np.float32)
    vx, vy, cx, cy = cv2.fitLine(samples, cv2.DIST_HUBER, 0, .01, .01).ravel().tolist()
    if vy < 0:
        vx, vy = -vx, -vy
    axis = np.array([vx, vy])
    extents = (samples - [cx, cy]) @ axis
    observed_extent = float(np.percentile(extents, 95) - np.percentile(extents, 5)) / length
    agreement = abs(float(marked_axis @ axis))
    usable = observed_extent >= .65 and agreement >= .95
    return {"usable": usable, "angle_from_image_vertical_deg": round(degrees(atan2(vx, vy)), 2),
            "edge_points": len(x), "observed_extent_fraction": round(min(observed_extent, 1), 3),
            "points": (marked / [width - 1, height - 1]).round(5).tolist(),
            "reason": "OpenCV directional-edge selection and Huber fit within the marked image corridor." if usable else "The visible edges do not support the marked axis well enough."}


def pole_alignment(image: np.ndarray, pole_points: list, reference_points: list | None) -> dict:
    pole = fit_axis(image, pole_points)
    reference = fit_axis(image, reference_points) if reference_points is not None else None
    result = {"pole": pole, "reference": reference, "relative_angle_deg": None,
              "usable": bool(pole["usable"] and reference and reference["usable"]),
              "meaning": "Two-dimensional alignment relative to an operator-selected vertical reference. Not a gravity-calibrated or 3D pole-lean measurement."}
    if result["usable"]:
        angle = pole["angle_from_image_vertical_deg"] - reference["angle_from_image_vertical_deg"]
        result["relative_angle_deg"] = round((angle + 90) % 180 - 90, 2)
    return result
