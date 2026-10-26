"""Reproducible synthetic stress checks plus two unlabeled field smoke checks."""
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import statistics

import cv2

from spanwitness.examples import normalized_span, pole_annotations, render_scene
from spanwitness.policy import plan_review
from spanwitness.vision import analyze, compare_views, decode_image, encode_image

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"perspective": "major", "persistent": "major", "gap": "critical_review", "cover": "moderate",
            "clear": "routine", "blur": "unassessed", "pole-lean": "major", "camera-roll": "routine"}


def measure(case, view=1, seed=71, scale=1, jpeg=88):
    image, path = render_scene(case, view, seed)
    if scale != 1:
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
    image = decode_image(encode_image(image, jpeg))
    axes = pole_annotations(case)
    report, _, _ = analyze(image, path or None, axes["pole"] if axes else None, axes["vertical_reference"] if axes else None)
    return image, report


def main():
    rows, comparisons, field = [], [], []
    for case, expected in EXPECTED.items():
        for seed in [71, 208, 309]:
            for scale in [.7, 1, 1.2]:
                for jpeg in [65, 88]:
                    image, report = measure(case, seed=seed, scale=scale, jpeg=jpeg)
                    plan = plan_review(report)
                    rows.append({"case": case, "seed": seed, "scale": scale, "jpeg_quality": jpeg,
                                 "expected_priority": expected, "actual_priority": plan["priority"],
                                 "passed": plan["priority"] == expected, "processing_ms": report["processing_ms"]})
                    if case in {"perspective", "persistent"}:
                        follow, other = measure(case, 2, seed, scale, jpeg)
                        comparison = compare_views(image, follow, report, other)
                        expected_status = "projection_sensitive" if case == "perspective" else "overlap_persists"
                        comparisons.append({"case": case, "seed": seed, "scale": scale, "jpeg_quality": jpeg,
                                            "status": comparison["status"], "passed": comparison["status"] == expected_status,
                                            "inliers": comparison["inliers"]})
    for case in ["field-crossing", "field-span"]:
        image = decode_image((ROOT / "static" / "samples" / f"{case}.jpg").read_bytes())
        report, _, _ = analyze(image, normalized_span(case))
        field.append({"case": case, "priority": plan_review(report)["priority"], "findings": [f["code"] for f in report["findings"]],
                      "condition_ground_truth": None, "meaning": "Functional run only; neither correctness nor field accuracy is scored."})
    latencies = [row["processing_ms"] for row in rows]
    output = {"generated_at": datetime.now(timezone.utc).isoformat(), "opencv": cv2.__version__, "python": platform.python_version(),
              "machine": platform.machine(), "policy": "prototype-review-v1", "synthetic_screens": {"passed": sum(r["passed"] for r in rows), "total": len(rows)},
              "synthetic_comparisons": {"passed": sum(r["passed"] for r in comparisons), "total": len(comparisons)},
              "screening_latency_ms": {"median": round(statistics.median(latencies), 1), "max": max(latencies)},
              "limits": ["Procedural image variations share scene geometry; these are regression and stress checks, not independent field data.",
                         "Seeds, resize and compression change texture and image quality. They do not model real electrical faults or physical parallax.",
                         "Two licensed field photographs have no validated condition labels. No field precision or recall is reported.",
                         "Latency measures local OpenCV screening, excluding upload, comparison, weather, storage and AWS cold starts."],
              "screens": rows, "comparisons": comparisons, "unlabeled_field_runs": field}
    destination = ROOT / "reports"
    destination.mkdir(exist_ok=True)
    (destination / "evaluation.json").write_text(json.dumps(output, indent=2) + "\n")
    summary = ["# Evaluation", "", f"Generated: {output['generated_at']}", "",
               f"OpenCV {output['opencv']}; Python {output['python']}; {output['machine']}.", "",
               f"- Synthetic screening checks: {output['synthetic_screens']['passed']}/{len(rows)}.",
               f"- Synthetic second-view checks: {output['synthetic_comparisons']['passed']}/{len(comparisons)}.",
               f"- Local screening time: median {output['screening_latency_ms']['median']} ms; maximum {max(latencies)} ms.", "",
               "## Limits", "", *[f"- {item}" for item in output["limits"]], "", "## Failures", ""]
    failed = [r for r in rows if not r["passed"]] + [r for r in comparisons if not r["passed"]]
    summary.extend([f"- `{json.dumps(row)}`" for row in failed] if failed else ["No failures in this declared synthetic matrix."])
    summary.extend(["", "## Field smoke checks", "", *[f"- {r['case']}: {r['priority']}; {', '.join(r['findings']) or 'no trigger'}. No correctness score." for r in field],
                    "", "The full per-case results are in [evaluation.json](evaluation.json).", ""])
    (destination / "EVALUATION.md").write_text("\n".join(summary))
    print(json.dumps({key: output[key] for key in ["synthetic_screens", "synthetic_comparisons", "screening_latency_ms", "unlabeled_field_runs"]}))


if __name__ == "__main__":
    main()
