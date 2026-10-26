"""Image-space screening. No metric clearances or fire probabilities are inferred."""
from __future__ import annotations

from io import BytesIO
from math import hypot
import time

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from .pole import pole_alignment

MAX_PIXELS = 20_000_000
MAX_DIMENSION = 1400


def decode_image(data: bytes) -> np.ndarray:
    if not data or len(data) > 8_000_000:
        raise ValueError("Choose a JPEG, PNG or WebP image smaller than 8 MB.")
    try:
        with Image.open(BytesIO(data)) as picture:
            if picture.width * picture.height > MAX_PIXELS:
                raise ValueError("Image resolution exceeds 20 megapixels.")
            if picture.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("Choose a JPEG, PNG or WebP image.")
            picture = ImageOps.exif_transpose(picture).convert("RGB")
            picture.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
            image = cv2.cvtColor(np.asarray(picture), cv2.COLOR_RGB2BGR)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError("The image could not be decoded.") from error
    if min(image.shape[:2]) < 180:
        raise ValueError("The image must be at least 180 pixels on each side.")
    return image


def encode_image(image: np.ndarray, quality: int = 88) -> bytes:
    ok, result = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError("The result image could not be encoded.")
    return result.tobytes()


def parse_span(points: list[list[float]] | None, width: int, height: int) -> np.ndarray | None:
    if points is None:
        return None
    if not 2 <= len(points) <= 8:
        raise ValueError("Mark between two and eight points along one conductor.")
    array = np.asarray(points, dtype=np.float32)
    if array.shape != (len(points), 2) or not np.isfinite(array).all():
        raise ValueError("Span coordinates must be finite pairs.")
    if ((array < 0) | (array > 1)).any():
        raise ValueError("Span coordinates must be between 0 and 1.")
    array *= np.array([width - 1, height - 1], dtype=np.float32)
    if np.linalg.norm(np.diff(array, axis=0), axis=1).sum() < width * .12:
        raise ValueError("Mark a longer section of conductor.")
    return array


def sample_path(points: np.ndarray) -> np.ndarray:
    samples = []
    for first, second in zip(points[:-1], points[1:]):
        count = max(2, int(np.linalg.norm(second - first)))
        samples.append(np.linspace(first, second, count, endpoint=False))
    return np.vstack([*samples, points[-1:]]).astype(np.float32)


def _segments(bits: np.ndarray) -> list[tuple[int, int]]:
    padded = np.pad(bits.astype(np.int8), (1, 1))
    changes = np.diff(padded)
    return list(zip(np.flatnonzero(changes == 1).tolist(), np.flatnonzero(changes == -1).tolist()))


def vegetation_masks(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    green = cv2.inRange(hsv, (30, 45, 24), (96, 255, 250))
    tan = cv2.inRange(hsv, (8, 42, 65), (32, 210, 238))
    kernel = np.ones((3, 3), np.uint8)
    green = cv2.morphologyEx(green, cv2.MORPH_OPEN, kernel)
    green = cv2.morphologyEx(green, cv2.MORPH_CLOSE, kernel)
    # Discard small color islands, including JPEG fringes around dark wires.
    count, components, stats, _ = cv2.connectedComponentsWithStats(green)
    keep = np.zeros(count, dtype=np.uint8)
    if count > 1:
        keep[1:] = (stats[1:, cv2.CC_STAT_AREA] >= max(50, image.shape[0] * image.shape[1] * .0002)) * 255
    green = keep[components]
    tan = cv2.morphologyEx(tan, cv2.MORPH_OPEN, kernel)
    return green, tan


def propose_span(gray: np.ndarray) -> np.ndarray | None:
    height, width = gray.shape
    edges = cv2.Canny(gray, 55, 145)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 720, 45,
                            minLineLength=int(width * .22), maxLineGap=35)
    candidates = []
    if lines is not None:
        for x1, y1, x2, y2 in lines[:, 0]:
            length = hypot(int(x2 - x1), int(y2 - y1))
            if abs(y2 - y1) < abs(x2 - x1) * .55 and max(y1, y2) < height * .78:
                candidates.append((length, [x1, y1], [x2, y2]))
    if not candidates:
        return None
    _, first, second = max(candidates, key=lambda item: item[0])
    return np.asarray(sorted([first, second]), dtype=np.float32)


def analyze(image: np.ndarray, normalized_span: list[list[float]] | None = None,
            pole_points: list | None = None, reference_points: list | None = None) -> tuple[dict, np.ndarray, dict]:
    started = time.perf_counter()
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    quality_gray = cv2.resize(gray, (800, round(height * 800 / width)), interpolation=cv2.INTER_AREA)
    blur_score = float(cv2.Laplacian(quality_gray, cv2.CV_64F).var())
    dark_fraction = float(np.mean(gray < 20))
    bright_fraction = float(np.mean(gray > 247))
    green, tan = vegetation_masks(image)
    ground_start = int(height * .66)
    green_cover = float(np.mean(green[ground_start:] > 0))
    tan_cover = float(np.mean(tan[ground_start:] > 0))
    span = parse_span(normalized_span, width, height)
    span_source = "operator_marked" if span is not None else "automatic_candidate"
    if span is None and pole_points is None:
        span = propose_span(gray)

    quality_ok = blur_score >= 25 and dark_fraction < .65 and bright_fraction < .75
    report = {
        "runtime": {"opencv": cv2.__version__, "method": "image-space-screening-v3"},
        "image": {"width": width, "height": height},
        "quality": {"usable": quality_ok, "sharpness": round(blur_score, 2), "sharpness_reference_width": 800,
                    "dark_fraction": round(dark_fraction, 4), "bright_fraction": round(bright_fraction, 4)},
        "span_source": span_source,
        "span": None,
        "pole_alignment": None,
        "inspection_mode": "pole_alignment" if pole_points is not None else "conductor_span",
        "ground_cover": {"green_fraction": round(green_cover, 4), "tan_fraction": round(tan_cover, 4),
                         "meaning": "Color candidates in the bottom third; not grass identity or fuel moisture."},
        "findings": [],
        "scope": "Image-space screening only. No metric clearance, electrical diagnosis or fire-spread probability.",
    }
    overlay = image.copy()
    tint = np.zeros_like(image)
    tint[green > 0] = (105, 202, 81)
    tinted = cv2.addWeighted(image, .68, tint, .32, 0)
    overlay[green > 0] = tinted[green > 0]
    context = {"green": green, "tan": tan, "gray": gray, "span_points": span}

    if span is not None:
        path = sample_path(span)
        xy = np.rint(path).astype(int)
        xy[:, 0] = np.clip(xy[:, 0], 0, width - 1)
        xy[:, 1] = np.clip(xy[:, 1], 0, height - 1)
        band_px = max(8, round(hypot(width, height) * .013))
        distance = cv2.distanceTransform(cv2.bitwise_not(green), cv2.DIST_L2, 5)
        distances = distance[xy[:, 1], xy[:, 0]]
        has_green = bool(np.any(green))
        near = distances <= band_px if has_green else np.zeros(len(path), dtype=bool)
        touching = distances <= 2 if has_green else np.zeros(len(path), dtype=bool)

        edges = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 45, 120)
        edge_distance = cv2.distanceTransform(cv2.bitwise_not(edges), cv2.DIST_L2, 3)
        supported = edge_distance[xy[:, 1], xy[:, 0]] <= 4
        # Close isolated sampling gaps without concealing long missing sections.
        supported = cv2.morphologyEx(supported.astype(np.uint8)[None, :], cv2.MORPH_CLOSE,
                                     np.ones((1, 7), np.uint8))[0].astype(bool)
        unsupported = ~supported
        # Vegetation can hide a conductor. Such a gap is unresolved, not proof of a break.
        unobscured_missing = unsupported & ~near
        runs = _segments(unobscured_missing)
        substantial = [(a, b) for a, b in runs if b - a >= max(14, len(path) * .025)]
        gaps = []
        for a, b in substantial:
            center = path[(a + b - 1) // 2]
            gaps.append({"fraction": round((b - a) / len(path), 4),
                         "start": (path[a] / [width - 1, height - 1]).round(5).tolist(),
                         "end": (path[b - 1] / [width - 1, height - 1]).round(5).tolist()})
            cv2.circle(overlay, tuple(np.rint(center).astype(int)), max(12, band_px + 3), (68, 82, 242), 2)

        report["span"] = {
            "points": (span / [width - 1, height - 1]).round(5).tolist(),
            "screening_band_px": band_px,
            "minimum_image_gap_px": round(float(distances.min()), 1) if has_green else None,
            "vegetation_near_fraction": round(float(near.mean()), 4),
            "projected_overlap_fraction": round(float(touching.mean()), 4),
            "line_support_fraction": round(float(supported.mean()), 4),
            "unresolved_gap_fraction": round(float(unsupported.mean()), 4),
            "visible_gap_candidates": gaps,
            "measurement_units": "image pixels; not physical clearance",
        }
        if near.mean() > .015:
            report["findings"].append({"code": "vegetation_near_span", "title": "Vegetation projects near the span",
                "observation": f"Green-color candidates enter the {band_px}-pixel screening band along {near.mean():.0%} of the selected path.",
                "uncertainty": "A single view cannot distinguish contact from background vegetation.",
                "next_action": "Capture a second view from a different normal viewing position."})
        if gaps and supported.mean() > .3:
            report["findings"].append({"code": "conductor_gap_candidate", "title": "Possible conductor gap or occlusion",
                "observation": f"{len(gaps)} section(s) lack nearby edge support outside the green-color mask.",
                "uncertainty": "A marked-path error, low contrast or non-green occlusion can produce the same signal.",
                "next_action": "Request engineering review and a clearer view of the marked section."})
        if supported.mean() <= .3:
            report["findings"].append({"code": "span_unverified", "title": "Selected conductor is not sufficiently observed",
                "observation": "Less than 30% of the marked path has nearby edge support.",
                "uncertainty": "The path may be inaccurate or the image may not resolve the conductor.",
                "next_action": "Mark the conductor again or capture a clearer image."})
        cv2.polylines(overlay, [np.rint(span).astype(np.int32)], False, (80, 210, 242), 2, cv2.LINE_AA)
        for point in span:
            cv2.circle(overlay, tuple(np.rint(point).astype(int)), 5, (80, 210, 242), -1)
    elif pole_points is None:
        report["findings"].append({"code": "span_unverified", "title": "Mark a conductor to inspect",
            "observation": "No sufficiently long, near-horizontal candidate was found.",
            "uncertainty": "Automatic line candidates are not asset identification.",
            "next_action": "Mark two or more points along one visible conductor."})

    if pole_points is not None:
        alignment = pole_alignment(image, pole_points, reference_points)
        report["pole_alignment"] = alignment
        for axis, color in [(alignment["pole"], (80, 210, 242)), (alignment["reference"], (217, 177, 129))]:
            if axis and axis.get("points"):
                pixels = np.asarray(axis["points"]) * [width - 1, height - 1]
                cv2.polylines(overlay, [pixels.astype(np.int32)], False, color, 3, cv2.LINE_AA)
        if not alignment["usable"]:
            report["findings"].append({"code": "alignment_unverified", "title": "Pole alignment needs a visible reference",
                "observation": "The pole and a suitable reference edge must both have enough visible line support.",
                "uncertainty": "Image vertical alone cannot separate camera roll from pole inclination.",
                "next_action": "Mark one continuous visible pole edge and a known vertical reference edge in the same image."})
        elif abs(alignment["relative_angle_deg"]) >= 7:
            report["findings"].append({"code": "pole_alignment_candidate", "title": "Pole differs from the selected reference",
                "observation": f"Image-axis difference: {abs(alignment['relative_angle_deg']):.1f} degrees after subtracting the reference orientation.",
                "uncertainty": "Perspective, reference selection and depth affect the result. This is not a physical lean measurement.",
                "next_action": "Request a qualified structural inspection with the reference image."})

    if pole_points is None and (tan_cover > .24 or green_cover > .55):
        report["findings"].append({"code": "ground_cover_candidate", "title": "Ground-cover review candidate",
            "observation": f"Bottom-third color coverage: {green_cover:.0%} green, {tan_cover:.0%} tan/brown.",
            "uncertainty": "Color does not establish grass species, height, dryness or fuel moisture.",
            "next_action": "Review the ground crop and confirm the vegetation condition."})
    if not quality_ok:
        report["findings"].insert(0, {"code": "image_quality", "title": "A clearer observation is needed",
            "observation": f"Sharpness score {blur_score:.1f}; clipped or dark pixels may also limit inspection.",
            "uncertainty": "This frame cannot support a low-priority conclusion.",
            "next_action": "Hold the camera steady and capture another view."})
    cv2.rectangle(overlay, (0, ground_start), (width - 1, height - 1), (154, 188, 211), 1)
    report["processing_ms"] = round((time.perf_counter() - started) * 1000, 1)
    return report, overlay, context


def compare_views(first: np.ndarray, second: np.ndarray, first_report: dict, second_report: dict) -> dict:
    """Report projection sensitivity, never derive meters or certify contact."""
    if first.shape == second.shape and float(cv2.absdiff(first, second).mean()) < 1:
        return {"status": "duplicate_view", "inliers": 0, "matches": 0,
                "meaning": "This repeats the previous image. Capture a genuinely different view."}
    orb = cv2.ORB_create(nfeatures=2000, fastThreshold=12)
    key_a, desc_a = orb.detectAndCompute(cv2.cvtColor(first, cv2.COLOR_BGR2GRAY), None)
    key_b, desc_b = orb.detectAndCompute(cv2.cvtColor(second, cv2.COLOR_BGR2GRAY), None)
    result = {"status": "insufficient_correspondence", "inliers": 0, "matches": 0,
              "meaning": "Views could not be compared reliably. Retain the inspection request."}
    if desc_a is None or desc_b is None:
        return result
    pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(desc_a, desc_b, k=2)
    good = [pair[0] for pair in pairs if len(pair) == 2 and pair[0].distance < .7 * pair[1].distance]
    result["matches"] = len(good)
    if len(good) < 12 or not first_report.get("span") or not second_report.get("span"):
        return result
    source = np.float32([key_a[m.queryIdx].pt for m in good])
    target = np.float32([key_b[m.trainIdx].pt for m in good])
    matrix, inlier_mask = cv2.findHomography(source, target, cv2.RANSAC, 4)
    inliers = int(inlier_mask.sum()) if inlier_mask is not None else 0
    result["inliers"] = inliers
    if matrix is None or inliers < 10 or inliers / len(good) < .35:
        return result
    # Similar backgrounds are not enough: the selected conductor must correspond too.
    first_size = np.array([first.shape[1] - 1, first.shape[0] - 1])
    second_size = np.array([second.shape[1] - 1, second.shape[0] - 1])
    first_span = np.asarray(first_report["span"]["points"], np.float32) * first_size
    second_span = np.asarray(second_report["span"]["points"], np.float32) * second_size
    mapped = cv2.perspectiveTransform(sample_path(first_span)[None, :, :], matrix)[0]
    expected = np.zeros(second.shape[:2], np.uint8)
    cv2.polylines(expected, [np.rint(second_span).astype(np.int32)], False, 255, 1)
    distance = cv2.distanceTransform(cv2.bitwise_not(expected), cv2.DIST_L2, 3)
    coords = np.rint(mapped).astype(int)
    in_frame = ((coords[:, 0] >= 0) & (coords[:, 0] < second.shape[1]) &
                (coords[:, 1] >= 0) & (coords[:, 1] < second.shape[0]))
    if in_frame.mean() < .9:
        result.update(status="different_span", meaning="The selected paths do not share enough visible extent. Mark the same span in both observations.")
        return result
    errors = distance[coords[in_frame, 1], coords[in_frame, 0]]
    result["span_alignment_error_px"] = round(float(np.median(errors)), 2)
    if float(np.median(errors)) > hypot(*second.shape[:2]) * .012:
        result.update(status="different_span", meaning="The marked paths do not correspond after image registration. Mark the same conductor before comparing.")
        return result
    result["inlier_fraction"] = round(inliers / len(good), 3)
    a = first_report["span"]["vegetation_near_fraction"]
    b = second_report["span"]["vegetation_near_fraction"]
    result.update({"first_near_fraction": a, "second_near_fraction": b,
                   "change_percentage_points": round((b - a) * 100, 1)})
    if not first_report["quality"]["usable"] or not second_report["quality"]["usable"]:
        result.update(status="followup_unusable", meaning="The new image is not usable. Request another observation.")
    elif a > .02 and b < a * .45:
        result.update(status="projection_sensitive", meaning="The projected overlap decreases in the new view. Contact and metric clearance remain unverified.")
    elif a > .02 and b > .02:
        result.update(status="overlap_persists", meaning="The projected overlap persists across these views. Request a qualified clearance inspection.")
    else:
        result.update(status="no_persistent_projection", meaning="These samples show no persistent projected overlap. Physical clearance remains unmeasured.")
    return result
