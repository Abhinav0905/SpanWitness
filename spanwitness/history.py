"""Conservative comparison of operator-marked pole observations over time."""
from __future__ import annotations

from datetime import datetime, timezone
from math import atan2, degrees, hypot

import cv2
import numpy as np

CHANGE_THRESHOLD_DEG = 3.0
METHOD_VERSION = "pole-history-v1"


def observation_time(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError
        stamp = stamp.astimezone(timezone.utc)
        if stamp.timestamp() > datetime.now(timezone.utc).timestamp() + 300:
            raise ValueError
    except (ValueError, OverflowError):
        raise ValueError("Use a valid observation date with a time zone, no later than now.") from None
    return stamp.isoformat()


def angle_difference(first: float, second: float) -> float:
    return float((second - first + 90) % 180 - 90)


def pixel_points(axis: dict, image: np.ndarray) -> np.ndarray:
    return np.asarray(axis["points"], np.float32) * [image.shape[1] - 1, image.shape[0] - 1]


def background_mask(image: np.ndarray, alignment: dict) -> np.ndarray:
    mask = np.full(image.shape[:2], 255, np.uint8)
    points = np.rint(pixel_points(alignment["pole"], image)).astype(np.int32)
    cv2.line(mask, tuple(points[0]), tuple(points[1]), 0, max(40, round(image.shape[1] * .09)))
    # Do not use the moving pole or its immediate surroundings for registration.
    return mask


def compare_pole_history(first: np.ndarray, second: np.ndarray, first_report: dict,
                         second_report: dict, *, repeatable_capture: bool = False,
                         same_file: bool = False) -> dict:
    result = {"method_version": METHOD_VERSION, "status": "not_comparable",
              "reason_code": "capture_not_confirmed", "inliers": 0, "matches": 0,
              "baseline_angle_deg": None, "current_angle_deg": None, "change_deg": None,
              "change_threshold_deg": CHANGE_THRESHOLD_DEG,
              "capture_setup": "operator_confirmed_repeatable_view" if repeatable_capture else "unconfirmed",
              "meaning": "Apparent 2D pole alignment relative to a selected reference. No physical lean, structural strength, fall date or fire probability is measured."}

    def reject(code, reason):
        result.update(reason_code=code, reason=reason)
        return result

    if not repeatable_capture:
        return reject("capture_not_confirmed", "Confirm the same pole, fixed reference and repeatable camera position before comparing.")
    if same_file:
        return reject("reused_image", "The same input file was used twice. It cannot establish an independent inspection over time.")
    if not all(report.get("quality", {}).get("usable") for report in [first_report, second_report]):
        return reject("image_quality", "One observation does not support a reliable image measurement. Capture a clearer view.")
    a, b = [report.get("pole_alignment", {}) for report in [first_report, second_report]]
    if not a.get("usable") or not b.get("usable"):
        return reject("missing_axes", "Both observations need supported pole and fixed-reference axes. Mark them in each image first.")
    aspect_a, aspect_b = first.shape[1] / first.shape[0], second.shape[1] / second.shape[0]
    if abs(aspect_b / aspect_a - 1) > .04:
        return reject("frame_shape", "The framing proportions differ too much for this constrained comparison. Repeat the original capture setup.")
    orb = cv2.ORB_create(nfeatures=2500, fastThreshold=12)
    key_a, desc_a = orb.detectAndCompute(cv2.cvtColor(first, cv2.COLOR_BGR2GRAY), background_mask(first, a))
    key_b, desc_b = orb.detectAndCompute(cv2.cvtColor(second, cv2.COLOR_BGR2GRAY), background_mask(second, b))
    if desc_a is None or desc_b is None:
        return reject("background_features", "There are too few stable background landmarks to compare these views.")
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    pairs = matcher.knnMatch(desc_a, desc_b, k=2)
    reverse_pairs = matcher.knnMatch(desc_b, desc_a, k=2)
    reverse = {pair[0].queryIdx: pair[0].trainIdx for pair in reverse_pairs
               if len(pair) == 2 and pair[0].distance < .7 * pair[1].distance}
    good = [pair[0] for pair in pairs if len(pair) == 2 and pair[0].distance < .7 * pair[1].distance
            and reverse.get(pair[0].trainIdx) == pair[0].queryIdx]
    result["matches"] = len(good)
    if len(good) < 24:
        return reject("background_features", "Too few background matches. Repeat the capture or use a clearer, more detailed view.")
    source = np.float32([key_a[match.queryIdx].pt for match in good])
    target = np.float32([key_b[match.trainIdx].pt for match in good])
    diagonal = hypot(*second.shape[:2])
    matrix, inlier_mask = cv2.estimateAffinePartial2D(source, target, method=cv2.RANSAC,
        ransacReprojThreshold=max(2.5, diagonal * .003), maxIters=3000, confidence=.995, refineIters=20)
    if matrix is None or inlier_mask is None:
        return reject("registration", "Stable image registration failed. Retain the earlier inspection for review.")
    keep = inlier_mask.ravel().astype(bool)
    result.update(inliers=int(keep.sum()), inlier_fraction=round(float(keep.mean()), 3))
    if keep.sum() < 20 or keep.mean() < .45:
        return reject("registration", "The views do not share enough consistent background matches.")
    extent = float(cv2.contourArea(cv2.convexHull(source[keep]))) / (first.shape[0] * first.shape[1])
    result["background_coverage_fraction"] = round(extent, 3)
    if extent < .08:
        return reject("background_extent", "Matches cover too little of the scene to support a repeatable-view comparison.")
    fitted = cv2.transform(source[keep][None], matrix)[0]
    result["median_registration_error_px"] = round(float(np.median(np.linalg.norm(fitted - target[keep], axis=1))), 2)
    result["estimated_camera_rotation_deg"] = round(degrees(atan2(matrix[1, 0], matrix[0, 0])), 2)

    # A similarity transform handles shared roll, translation and uniform scale.
    # A competing projective fit that disagrees across the scene makes us abstain.
    homography, homography_mask = cv2.findHomography(source, target, cv2.RANSAC, max(2.5, diagonal * .003))
    if homography is not None and homography_mask is not None and homography_mask.sum() >= 20:
        grid = np.float32([[x * first.shape[1], y * first.shape[0]] for x in [.15, .5, .85] for y in [.15, .5, .85]])
        affine_grid = cv2.transform(grid[None], matrix)[0]
        projective_grid = cv2.perspectiveTransform(grid[None], homography)[0]
        disagreement = float(np.max(np.linalg.norm(affine_grid - projective_grid, axis=1))) / diagonal
        result["projective_disagreement_fraction"] = round(disagreement, 4)
        if not np.isfinite(disagreement) or disagreement > .012:
            return reject("perspective_change", "The scene geometry changes beyond the supported capture setup. A viewpoint change could imitate pole movement.")

    ref_a = cv2.transform(pixel_points(a["reference"], first)[None].astype(np.float32), matrix)[0]
    ref_b = pixel_points(b["reference"], second)
    direction = ref_b[1] - ref_b[0]
    length = float(np.linalg.norm(direction))
    offsets = ref_a - ref_b[0]
    distances = np.abs(offsets[:, 0] * direction[1] - offsets[:, 1] * direction[0]) / max(length, 1)
    reference_error = float(np.mean(distances))
    result["reference_alignment_error_px"] = round(reference_error, 2)
    reference_rotation = degrees(atan2(*(ref_a[1] - ref_a[0])))
    current_reference_rotation = degrees(atan2(*direction))
    if reference_error > diagonal * .012 or abs(angle_difference(reference_rotation, current_reference_rotation)) > 1.5:
        return reject("reference_mismatch", "The selected fixed reference does not correspond between observations. Check the marked edge and camera position.")
    pole_a = cv2.transform(pixel_points(a["pole"], first)[None].astype(np.float32), matrix)[0]
    pole_b = pixel_points(b["pole"], second)
    base_a, base_b = pole_a[np.argmax(pole_a[:, 1])], pole_b[np.argmax(pole_b[:, 1])]
    if np.linalg.norm(base_a - base_b) > diagonal * .04:
        return reject("pole_position", "The marked pole bases do not correspond well enough. Check the asset and repeat the framing.")
    first_angle, second_angle = a["relative_angle_deg"], b["relative_angle_deg"]
    change = angle_difference(first_angle, second_angle)
    changed = abs(change) >= CHANGE_THRESHOLD_DEG
    result.update(status="change_detected" if changed else "no_material_change", reason_code=None,
        baseline_angle_deg=first_angle, current_angle_deg=second_angle, change_deg=round(change, 2),
        reason="Apparent alignment change exceeds the declared 3-degree review threshold. Request a repeat capture and structural review." if changed else "No apparent alignment change above the declared 3-degree threshold. Existing findings remain open.")
    return result


def history_plan(comparison: dict, baseline_plan: dict, current_plan: dict) -> dict:
    ranks = {"unassessed": -1, "routine": 0, "moderate": 1, "major": 2, "critical_review": 3}
    existing = max([baseline_plan, current_plan], key=lambda plan: ranks.get(plan["priority"], -1))
    plan = dict(existing)
    plan["trace"] = list(existing.get("trace", [])) + [{"tool": "compare_pole_history", "result": comparison["status"]}]
    if comparison["status"] == "change_detected" and ranks.get(existing["priority"], -1) < 2:
        plan.update(priority="major", label="Major review", team="Asset engineering",
                    action="Repeat the capture and request a structural review", reason=comparison["reason"])
    elif comparison["status"] == "not_comparable":
        plan.update(action="Capture a comparable observation", reason=comparison["reason"] + " Earlier review requests remain open.")
        if ranks.get(existing["priority"], -1) < 1:
            plan.update(priority="unassessed", label="More evidence needed")
    elif comparison["status"] == "no_material_change" and ranks.get(existing["priority"], -1) < 1:
        plan.update(priority="routine", label="Routine review", action="Keep monitoring the asset", reason=comparison["reason"])
    if existing["priority"] == "critical_review":
        plan.update(action="Retain urgent engineering review", reason="An earlier urgent finding remains unresolved. The history comparison does not close it.")
    plan.update(policy_version="history-review-v1", human_confirmation_required=True,
                meaning="Provisional human-review priority. No structural failure or fire forecast.")
    return plan
