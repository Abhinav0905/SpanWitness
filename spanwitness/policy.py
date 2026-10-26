"""A declared prototype review policy, separate from visual measurement."""
from __future__ import annotations

POLICY_VERSION = "prototype-review-v1"


def plan_review(report: dict, weather: dict | None = None, comparison: dict | None = None, prior_plan: dict | None = None) -> dict:
    weather = weather or {"status": "unknown", "fire_weather_alert": False}
    codes = {finding["code"] for finding in report["findings"]}
    trace = [
        {"tool": "assess_observation", "result": "usable" if report["quality"]["usable"] else "retake_required"},
        {"tool": "screen_pole_alignment" if report.get("inspection_mode") == "pole_alignment" else "screen_selected_span", "result": sorted(codes)},
    ]
    priority, label, team, action = "routine", "Routine review", "Asset inspection", "Review the marked span"
    reason = "No configured screening trigger in this observation. This is not an asset clearance."
    if report.get("inspection_mode") == "pole_alignment":
        action = "Review the pole and its selected reference"
    if "ground_cover_candidate" in codes:
        priority, label, team = "moderate", "Moderate review", "Vegetation management"
        action = "Confirm the ground-cover condition"
        reason = "A ground-color screening trigger needs vegetation review."
    if "vegetation_near_span" in codes:
        priority, label, team = "major", "Major review", "Joint asset / vegetation review"
        action = "Request a second view"
        reason = "Vegetation projects close to the selected conductor; physical contact is unknown."
        trace.append({"tool": "request_second_view", "result": "Move to another normal viewing position and keep the same span in view."})
    if "pole_alignment_candidate" in codes:
        priority, label, team = "major", "Major review", "Asset engineering"
        action = "Request a structural alignment inspection"
        reason = "The pole axis differs from the selected reference. Perspective and true physical lean require a qualified assessment."
        trace.append({"tool": "request_structural_review", "result": "Attach the pole and reference-axis measurements."})
    if comparison:
        trace.append({"tool": "compare_views", "result": comparison["status"]})
        if comparison["status"] == "projection_sensitive" and "conductor_gap_candidate" not in codes:
            priority, label = "moderate", "Moderate review"
            action = "Retain the evidence for clearance review"
            reason = "The overlap changes with viewpoint. It cannot establish physical contact or a safe clearance."
        elif comparison["status"] == "overlap_persists":
            priority, label = "major", "Major review"
            action = "Request a qualified clearance inspection"
            reason = "Projected overlap persists in both observations."
    if weather.get("fire_weather_alert") and codes & {"vegetation_near_span", "ground_cover_candidate"}:
        priority, label = "major", "Major review"
        action = "Prioritize the vegetation review with fire-weather context"
        reason += " A fire-weather alert is supplied as context; no fire-spread probability was calculated."
        trace.append({"tool": "attach_weather_context", "result": weather.get("source_kind", "unknown")})
    if "conductor_gap_candidate" in codes:
        priority, label, team = "critical_review", "Critical review", "Asset engineering"
        action = "Request urgent engineering review"
        reason = "A possible discontinuity needs prompt specialist review. A broken or energized conductor has not been diagnosed."
        trace.append({"tool": "request_engineering_review", "result": "Possible gap or occlusion; include a detailed crop and operator confirmation."})
    if codes & {"span_unverified", "alignment_unverified"} or not report["quality"]["usable"]:
        priority, label, action = "unassessed", "More evidence needed", "Capture a clearer view or mark the conductor again"
        if report.get("inspection_mode") == "pole_alignment":
            team = "Asset inspection"
            action = "Capture a clearer pole view and mark continuous pole and reference edges"
        reason = "The observation is insufficient. An absence of detections cannot lower the review priority."
        trace.append({"tool": "request_observation", "result": "Do not issue a low-priority asset conclusion from this frame."})
    if prior_plan and prior_plan["priority"] == "critical_review":
        priority, label, team = "critical_review", "Critical review", "Asset engineering"
        action = "Retain urgent engineering review"
        reason = "A prior conductor-gap candidate remains unresolved. A later image does not close that review without a qualified assessment."
        trace.append({"tool": "retain_unresolved_finding", "result": "The earlier critical-review request is retained for a human reviewer."})
    elif prior_plan and comparison and comparison["status"] in {
        "duplicate_view", "different_span", "insufficient_correspondence", "followup_unusable", "independent_followup"
    }:
        ranks = {"routine": 0, "moderate": 1, "major": 2, "critical_review": 3}
        prior_rank = ranks.get(prior_plan["priority"], -1)
        current_rank = ranks.get(priority, -1)
        if prior_rank > current_rank:
            priority, label, team = prior_plan["priority"], prior_plan["label"], prior_plan["team"]
            action = "Capture a usable view of the same asset"
            reason = "The follow-up did not resolve the earlier finding. Its review priority is retained."
            trace.append({"tool": "retain_unresolved_finding", "result": "Unusable comparison cannot close an earlier review."})
        else:
            trace.append({"tool": "retain_current_finding", "result": "A failed comparison cannot lower a new concern."})
    trace.append({"tool": "stage_review", "result": {"priority": priority, "team": team, "action": action}})
    return {"policy_version": POLICY_VERSION, "priority": priority, "label": label,
            "team": team, "action": action, "reason": reason, "trace": trace,
            "meaning": "Provisional crew-review priority, not certified asset severity or a dispatch order.",
            "human_confirmation_required": True}
