"""Capture real intermediate outputs without changing the inspection pipeline."""
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cv2
import numpy as np

from spanwitness.examples import pole_annotations
from spanwitness.policy import plan_review
from spanwitness.vision import analyze, decode_image


def main():
    source = ROOT / "spanwitness/static/samples/field-house.jpg"
    output = ROOT / "remotion-demo/public/opencv-evidence"
    output.mkdir(parents=True, exist_ok=True)
    image = decode_image(source.read_bytes())
    marks = pole_annotations("field-house")
    calls = {"Canny": [], "HoughLinesP": [], "fitLine": []}
    originals = {name: getattr(cv2, name) for name in calls}

    def capture(name):
        def run(*args, **kwargs):
            result = originals[name](*args, **kwargs)
            calls[name].append({"input": args[0].copy(),
                                "result": None if result is None else result.copy()})
            return result
        return run

    with patch.object(cv2, "Canny", side_effect=capture("Canny")), \
         patch.object(cv2, "HoughLinesP", side_effect=capture("HoughLinesP")), \
         patch.object(cv2, "fitLine", side_effect=capture("fitLine")):
        report, _, _ = analyze(image, None, marks["pole"], marks["vertical_reference"])

    assert all(len(items) == 2 for items in calls.values())
    assert report["pole_alignment"]["usable"]
    assert plan_review(report)["priority"] == "major"
    cv2.imwrite(str(output / "original.png"), image)
    cv2.imwrite(str(output / "canny-edges.png"), calls["Canny"][0]["result"])
    hough = np.zeros_like(image)
    fitted = image.copy()
    colors = [(80, 210, 242), (217, 177, 129)]
    fit_trace = []
    for index, color in enumerate(colors):
        entry = calls["HoughLinesP"][index]
        cv2.imwrite(str(output / f"supported-edges-{index}.png"), entry["input"])
        for segment in entry["result"].reshape(-1, 4):
            cv2.line(hough, tuple(segment[:2]), tuple(segment[2:]), color, 1)
        fit = calls["fitLine"][index]
        vx, vy, cx, cy = fit["result"].ravel().tolist()
        points = fit["input"]
        distances = (points - [cx, cy]) @ [vx, vy]
        endpoints = np.array([cx, cy]) + np.array([vx, vy]) * np.percentile(distances, [1, 99])[:, None]
        cv2.line(fitted, tuple(np.rint(endpoints[0]).astype(int)),
                 tuple(np.rint(endpoints[1]).astype(int)), color, 3, cv2.LINE_AA)
        fit_trace.append({"region": "pole" if index == 0 else "reference",
                          "hough_segments": len(entry["result"]), "fit_points": len(points),
                          "fit_vector": [vx, vy], "fit_center": [cx, cy]})
    cv2.imwrite(str(output / "hough-candidates.png"), hough)
    cv2.imwrite(str(output / "fitted-axes.png"), fitted)

    height, width = image.shape[:2]
    marked = np.array(marks["pole"] + marks["vertical_reference"]) * [width - 1, height - 1]
    x0, y0 = np.maximum(np.floor(marked.min(axis=0) - [55, 55]), [0, 0]).astype(int)
    x1, y1 = np.minimum(np.ceil(marked.max(axis=0) + [55, 55]), [width, height]).astype(int)
    for name in ["original", "canny-edges", "hough-candidates", "fitted-axes"]:
        full = cv2.imread(str(output / f"{name}.png"))
        cv2.imwrite(str(output / f"{name}-crop.png"), full[y0:y1, x0:x1])

    credits = json.loads((ROOT / "spanwitness/static/samples/ATTRIBUTION.json").read_text())
    receipt = {"opencv": cv2.__version__, "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
               "method": "Actual analyze() execution; wrappers record inputs and outputs of cv2 functions without modifying them.",
               "source": "spanwitness/pole.py:fit_axis and pole_alignment; spanwitness/vision.py:analyze",
               "operator_marks": marks, "image": {"width": width, "height": height}, "display_crop": {"x": int(x0), "y": int(y0), "width": int(x1-x0), "height": int(y1-y0)},
               "calls": {name: len(items) for name, items in calls.items()}, "fits": fit_trace,
               "relative_image_angle_deg": report["pole_alignment"]["relative_angle_deg"],
               "scope": "Diagnostic display from one selected photo. Crops share the same bounds. No physical lean or field accuracy is inferred.",
               "attribution": next(c for c in credits if c["id"] == "field-house")}
    (output / "trace.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"opencv": receipt["opencv"], "calls": receipt["calls"],
                      "angle": receipt["relative_image_angle_deg"], "display_crop": receipt["display_crop"]}))


if __name__ == "__main__":
    main()
