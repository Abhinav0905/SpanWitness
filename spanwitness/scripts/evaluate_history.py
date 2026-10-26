"""Development stress checks for the constrained history comparison."""
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import cv2
import numpy as np

from spanwitness.history import compare_pole_history
from spanwitness.history_examples import render_history_scene
from spanwitness.vision import analyze, decode_image, encode_image


def main():
    cases = {"alignment-change": "change_detected", "camera-roll": "no_material_change",
             "perspective": "not_comparable", "blurred": "not_comparable"}
    results = []
    for seed in [197, 1139, 9239]:
        for scale in [.7, 1, 1.3]:
            for quality in [70, 88, 95]:
                for case, expected in cases.items():
                    images, reports = [], []
                    start = time.perf_counter()
                    for view in ["baseline", "current"]:
                        image, axes = render_history_scene(case, view, seed)
                        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
                        image = decode_image(encode_image(image, quality))
                        report, _, _ = analyze(image, None, axes["pole"], axes["vertical_reference"])
                        images.append(image)
                        reports.append(report)
                    comparison = compare_pole_history(*images, *reports, repeatable_capture=True)
                    error = abs(comparison["change_deg"] - (5 if case == "alignment-change" else 0)) if comparison["change_deg"] is not None else None
                    results.append({"case": case, "seed": seed, "scale": scale, "jpeg_quality": quality,
                        "expected_status": expected, "passed": comparison["status"] == expected,
                        "apparent_change_error_deg": round(error, 3) if error is not None else None,
                        "elapsed_ms": round((time.perf_counter() - start) * 1000, 1), "comparison": comparison})
    errors = [entry["apparent_change_error_deg"] for entry in results if entry["apparent_change_error_deg"] is not None]
    output = {"generated_at": datetime.now(timezone.utc).isoformat(), "opencv": cv2.__version__,
        "checks": {"passed": sum(entry["passed"] for entry in results), "total": len(results)},
        "accepted_angle_error_deg": {"median": round(float(np.median(errors)), 3), "max": max(errors)},
        "false_change_alerts_in_controls": sum(entry["comparison"]["status"] == "change_detected" for entry in results if entry["case"] != "alignment-change"),
        "limits": ["Procedural fixtures share the same scene design and are not independent field data.",
            "The method was revised after the four initial checks; history-baseline.json preserves those results.",
            "New background seeds, sizes and JPEG settings test implementation sensitivity, not physical lean accuracy.",
            "The 3-degree review threshold is a declared prototype setting, not a utility standard."], "results": results}
    root = Path(__file__).resolve().parents[1]
    (root / "reports/history-evaluation.json").write_text(json.dumps(output, indent=2) + "\n")
    (root / "reports/HISTORY_EVALUATION.md").write_text(f"""# History comparison development checks

Checked with OpenCV {cv2.__version__}. {output['checks']['passed']} / {len(results)} expected decision branches passed.

Three background seeds, three image scales and three JPEG quality settings were applied to four controlled pairs: a drawn 5-degree change, a camera rotation without pole movement, changed perspective and a blurred follow-up.

The accepted apparent-angle measurements had median absolute error {output['accepted_angle_error_deg']['median']} degrees and maximum error {output['accepted_angle_error_deg']['max']} degrees against the drawing geometry. Controls produced {output['false_change_alerts_in_controls']} change alerts. These are image-space fixture results, not physical pole measurements.

The first four checks exposed biased axis fits and excessive abstention on camera rotation. Directional-edge selection with Hough support and mutual background matching were introduced after those checks. Original results remain in [history-baseline.json](history-baseline.json).

All branches, including failed checks, are retained in [history-evaluation.json](history-evaluation.json). These development checks share a procedural scene design. They establish neither field precision/recall nor accuracy on arbitrary camera poses. Asset IDs, dates, selected axes and repeatable capture are operator supplied. Comparison is conditional on that setup. No fall date, structural strength or fire forecast is inferred.
""")
    print(json.dumps({key: output[key] for key in ["checks", "accepted_angle_error_deg", "false_change_alerts_in_controls"]}))


if __name__ == "__main__":
    main()
