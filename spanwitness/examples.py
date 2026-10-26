"""Original synthetic fixtures. Their labels are never inputs to perception."""
from __future__ import annotations

from functools import lru_cache
import cv2
import numpy as np

EXAMPLES = [
    {"id": "field-house", "name": "Field photograph: pole beside a house", "description": "PD-Defect authors / CC BY 4.0. Real field photograph with two example operator marks. No physical lean or failure diagnosis.", "second_view": False, "kind": "public_image"},
    {"id": "field-warehouse", "name": "Field photograph: limited pole-edge support", "description": "PD-Defect authors / CC BY 4.0. Real field photograph with example operator marks; the selected pole edge is insufficient for an alignment result.", "second_view": False, "kind": "public_image"},
    {"id": "perspective", "name": "A suspicious overlap", "description": "Compare a second viewpoint before escalating an apparent contact.", "second_view": True, "kind": "synthetic"},
    {"id": "persistent", "name": "Overlap in both views", "description": "A second observation keeps the clearance question open.", "second_view": True, "kind": "synthetic"},
    {"id": "gap", "name": "A conductor gap candidate", "description": "A deliberately missing segment tests the engineering-review branch.", "second_view": False, "kind": "synthetic"},
    {"id": "cover", "name": "Ground-cover review", "description": "Tan vegetation-colored strokes test a maintenance-review trigger.", "second_view": False, "kind": "synthetic"},
    {"id": "clear", "name": "No configured trigger", "description": "A comparison case, not a certified safe asset.", "second_view": False, "kind": "synthetic"},
    {"id": "blur", "name": "An unusable observation", "description": "Poor evidence requests another view instead of assigning low priority.", "second_view": False, "kind": "synthetic"},
    {"id": "pole-lean", "name": "Pole alignment candidate", "description": "A pole axis differs from a marked reference; not a physical lean measurement.", "second_view": False, "kind": "synthetic"},
    {"id": "camera-roll", "name": "Camera roll, upright pole", "description": "A shared image rotation should not become a pole-lean claim.", "second_view": False, "kind": "synthetic"},
    {"id": "field-crossing", "name": "Field photograph: crossed wires", "description": "Paul Harrop / CC BY-SA 2.0. A real photo without a validated condition label.", "second_view": False, "kind": "public_image"},
    {"id": "field-span", "name": "Field photograph: rural poles", "description": "Andy Beecroft / CC BY-SA 2.0. A real photo without a validated condition label.", "second_view": False, "kind": "public_image"},
]


def normalized_span(example: str, view: int = 1) -> list[list[float]] | None:
    if example in {"pole-lean", "camera-roll", "field-house", "field-warehouse"}:
        return None
    if example == "field-crossing":
        return [[.47, .405], [.73, .43], [.98, .455]]
    if example == "field-span":
        return [[.647, .115], [.63, .21], [.61, .27], [.56, .298]]
    _, span = render_scene(example, view)
    return span


def pole_annotations(example: str) -> dict | None:
    if example == "field-house":
        return {"pole": [[372/738, 680/1599], [476/738, 1020/1599]],
                "vertical_reference": [[411/738, 350/1599], [410/738, 650/1599]]}
    if example == "field-warehouse":
        return {"pole": [[295/589, 500/1279], [279/589, 1000/1279]],
                "vertical_reference": [[405/589, 240/1279], [395/589, 670/1279]]}
    if example not in {"pole-lean", "camera-roll"}:
        return None
    pole = np.array([[390, 115], [510, 555]] if example == "pole-lean" else [[450, 115], [450, 555]], np.float32)
    reference = np.array([[760, 100], [760, 565]], np.float32)
    if example == "camera-roll":
        matrix = cv2.getRotationMatrix2D((500, 320), 12, 1)
        pole = cv2.transform(pole[None], matrix)[0]
        reference = cv2.transform(reference[None], matrix)[0]
    return {"pole": (pole / [999, 639]).round(6).tolist(),
            "vertical_reference": (reference / [999, 639]).round(6).tolist()}


@lru_cache(maxsize=64)
def render_scene(example: str, view: int = 1, seed: int = 23) -> tuple[np.ndarray, list[list[float]]]:
    if example not in {item["id"] for item in EXAMPLES if item["kind"] == "synthetic"}:
        raise ValueError("Unknown synthetic example.")
    width, height = 1000, 640
    rng = np.random.default_rng(seed)
    image = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        if y < 460:
            image[y] = (226 - y // 20, 210 - y // 25, 181 - y // 30)
        else:
            image[y] = (127, 152, 148)
    if example in {"pole-lean", "camera-roll"}:
        pole = np.array([[390, 115], [510, 555]] if example == "pole-lean" else [[450, 115], [450, 555]])
        cv2.rectangle(image, (760, 90), (910, 575), (190, 197, 198), -1)
        cv2.line(image, (760, 100), (760, 565), (69, 81, 84), 4)
        cv2.line(image, tuple(pole[0]), tuple(pole[1]), (62, 80, 101), 23, cv2.LINE_AA)
        cv2.line(image, tuple(pole[0] + [-65, 20]), tuple(pole[0] + [65, 20]), (61, 74, 91), 10)
        for y in range(160, 550, 35):
            cv2.line(image, (780, y), (880, y), (130, 145, 147), 2)
        cv2.putText(image, "REFERENCE", (780, 135), cv2.FONT_HERSHEY_SIMPLEX, .4, (55, 70, 76), 1, cv2.LINE_AA)
        if example == "camera-roll":
            matrix = cv2.getRotationMatrix2D((500, 320), 12, 1)
            image = cv2.warpAffine(image, matrix, (width, height), borderMode=cv2.BORDER_REFLECT)
        return image, []
    # Landmarks add stable visual texture for an actual ORB/RANSAC comparison.
    for x in [120, 865]:
        cv2.rectangle(image, (x - 10, 115), (x + 10, 580), (65, 83, 101), -1)
        cv2.rectangle(image, (x - 48, 143), (x + 48, 152), (69, 77, 89), -1)
        for index in range(12):
            px = x - 8 + int(rng.integers(0, 15))
            py = 175 + index * 30
            cv2.line(image, (px, py), (px + int(rng.integers(-5, 6)), py + 13), (40, 52, 66), 2)
        for offset in [-35, 35]:
            cv2.rectangle(image, (x + offset - 5, 126), (x + offset + 5, 143), (100, 97, 91), -1)
            for y in [129, 134, 139]:
                cv2.line(image, (x + offset - 7, y), (x + offset + 7, y), (71, 70, 65), 2)
        cv2.putText(image, "SW-27" if x < 500 else "SW-28", (x - 29, 425), cv2.FONT_HERSHEY_SIMPLEX, .35, (225, 225, 222), 1, cv2.LINE_AA)
    points = np.array([[120, 141], [310, 167], [500, 178], [690, 166], [865, 141]], np.int32)
    if example == "gap":
        path = []
        for a, b in zip(points[:-1], points[1:]):
            path.extend(np.linspace(a, b, int(np.linalg.norm(b - a)), endpoint=False))
        path = np.asarray(path, np.int32)
        cv2.polylines(image, [path[:300]], False, (41, 45, 49), 3, cv2.LINE_AA)
        cv2.polylines(image, [path[375:]], False, (41, 45, 49), 3, cv2.LINE_AA)
    else:
        cv2.polylines(image, [points], False, (41, 45, 49), 3, cv2.LINE_AA)

    # These are controlled image variations, not a simulator of electrical contact.
    if example in {"perspective", "persistent"}:
        center = (535, 236) if view == 1 or example == "persistent" else (615, 333)
        cv2.line(image, (center[0] + 15, 515), center, (72, 91, 109), 12)
        for offset_x, offset_y, radius in [(-40, -18, 42), (2, -24, 45), (43, -8, 36), (-18, 23, 48)]:
            cv2.circle(image, (center[0] + offset_x, center[1] + offset_y), radius, (68, 125, 74), -1, cv2.LINE_AA)
            cv2.circle(image, (center[0] + offset_x - 10, center[1] + offset_y - 7), radius // 2, (73, 139, 82), -1, cv2.LINE_AA)
    else:
        cv2.circle(image, (930, 365), 62, (66, 127, 73), -1, cv2.LINE_AA)

    if example == "cover":
        for _ in range(2100):
            x, y = int(rng.integers(0, width)), int(rng.integers(455, height))
            shade = int(rng.integers(-16, 16))
            color = (max(0, 75 + shade), max(0, 143 + shade), max(0, 188 + shade))
            cv2.line(image, (x, y), (x + int(rng.integers(-8, 9)), y - int(rng.integers(10, 38))), color, 3)
    else:
        cv2.rectangle(image, (0, 535), (999, 639), (126, 147, 146), -1)
        for _ in range(160):
            x, y = int(rng.integers(0, width)), int(rng.integers(545, height))
            cv2.line(image, (x, y), (x + 4, y - 8), (109, 128, 126), 1)
    for x, y in [(280, 370), (720, 390)]:
        cv2.rectangle(image, (x - 15, y - 10), (x + 15, y + 10), (168, 171, 169), -1)
        cv2.putText(image, "27", (x - 10, y + 5), cv2.FONT_HERSHEY_SIMPLEX, .35, (70, 74, 75), 1, cv2.LINE_AA)

    if view == 2:
        matrix = cv2.getRotationMatrix2D((500, 320), 1.2, 1)
        matrix[:, 2] += [9, -3]
        image = cv2.warpAffine(image, matrix, (width, height), borderMode=cv2.BORDER_REFLECT)
        points = cv2.transform(points.astype(np.float32)[None, :, :], matrix)[0]
    if example == "blur":
        image = cv2.GaussianBlur(image, (45, 45), 12)
    span = (points / [width - 1, height - 1]).round(6).tolist()
    return image, span
