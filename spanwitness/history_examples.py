"""Original controlled image pairs for the history workflow, not field evidence."""
from functools import lru_cache

import cv2
import numpy as np

HISTORY_EXAMPLES = [
    {"id": "alignment-change", "name": "A changed pole alignment", "description": "A controlled 5-degree change in a model pole. Compare its dated observations."},
    {"id": "camera-roll", "name": "Only the camera rotates", "description": "The pole stays upright while the whole image rotates. It should not become a deterioration alert."},
    {"id": "perspective", "name": "The viewpoint changes", "description": "The capture angle changes. The comparison should request a repeatable view."},
    {"id": "blurred", "name": "The new view is blurred", "description": "Poor evidence should request another capture, not clear an earlier concern."},
]


@lru_cache(maxsize=64)
def render_history_scene(case: str, view: str = "baseline", seed: int = 417):
    if case not in {item["id"] for item in HISTORY_EXAMPLES} or view not in {"baseline", "current"}:
        raise ValueError("Unknown history example.")
    width, height = 1000, 640
    image = np.full((height, width, 3), (210, 207, 199), np.uint8)
    image[:75] = (227, 216, 196)
    image[565:] = (160, 162, 155)
    rng = np.random.default_rng(seed)
    # Fixed landmarks spread over the scene and remain outside the moving pole.
    for x in range(45, 970, 75):
        for y in range(90, 550, 65):
            if 350 < x < 500:
                continue
            color = tuple(int(c) for c in rng.integers(65, 150, size=3))
            cv2.rectangle(image, (x, y), (x + 30, y + 22), color, 2)
            cv2.line(image, (x, y + 22), (x + 30, y), color, 2)
            cv2.circle(image, (x + int(rng.integers(5, 25)), y + 10), 4, color, -1)
    cv2.rectangle(image, (800, 75), (930, 560), (184, 190, 187), -1)
    cv2.line(image, (800, 80), (800, 558), (54, 68, 72), 4)
    cv2.putText(image, "FIXED EDGE", (813, 113), cv2.FONT_HERSHEY_SIMPLEX, .38, (53, 66, 70), 1, cv2.LINE_AA)
    angle = 5 if case == "alignment-change" and view == "current" else 0
    pole = np.float32([[420 - np.tan(np.radians(angle)) * 440, 110], [420, 550]])
    reference = np.float32([[800, 85], [800, 550]])
    cv2.line(image, tuple(np.rint(pole[0]).astype(int)), tuple(pole[1].astype(int)), (57, 75, 93), 23, cv2.LINE_AA)
    cv2.line(image, tuple(np.rint(pole[0] + [-60, 25]).astype(int)), tuple(np.rint(pole[0] + [60, 25]).astype(int)), (49, 64, 75), 9, cv2.LINE_AA)
    cv2.putText(image, "MODEL POLE 27", (315, 602), cv2.FONT_HERSHEY_SIMPLEX, .42, (53, 67, 69), 1, cv2.LINE_AA)
    if view == "current" and case == "camera-roll":
        matrix = cv2.getRotationMatrix2D((500, 320), 8, 1)
        image = cv2.warpAffine(image, matrix, (width, height), borderMode=cv2.BORDER_REFLECT)
        pole = cv2.transform(pole[None], matrix)[0]
        reference = cv2.transform(reference[None], matrix)[0]
    elif view == "current" and case == "perspective":
        matrix = cv2.getPerspectiveTransform(np.float32([[0, 0], [999, 0], [999, 639], [0, 639]]),
            np.float32([[75, 0], [930, 75], [999, 639], [0, 610]]))
        image = cv2.warpPerspective(image, matrix, (width, height), borderMode=cv2.BORDER_REFLECT)
        pole = cv2.perspectiveTransform(pole[None], matrix)[0]
        reference = cv2.perspectiveTransform(reference[None], matrix)[0]
    elif view == "current" and case == "blurred":
        image = cv2.GaussianBlur(image, (51, 51), 15)
    return image, {"pole": (pole / [999, 639]).round(6).tolist(),
                   "vertical_reference": (reference / [999, 639]).round(6).tolist()}
