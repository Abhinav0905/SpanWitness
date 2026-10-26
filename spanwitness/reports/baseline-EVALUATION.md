# Evaluation

Generated: 2026-10-26T01:50:11.374216+00:00

OpenCV 5.0.0; Python 3.14.7; arm64.

- Synthetic screening checks: 123/144.
- Synthetic second-view checks: 24/36.
- Local screening time: median 13.5 ms; maximum 21.7 ms.

## Limits

- Procedural image variations share scene geometry; these are regression and stress checks, not independent field data.
- Seeds, resize and compression change texture and image quality. They do not model real electrical faults or physical parallax.
- Two licensed field photographs have no validated condition labels. No field precision or recall is reported.
- Latency measures local OpenCV screening, excluding upload, comparison, weather, storage and AWS cold starts.

## Failures

- `{"case": "cover", "seed": 71, "scale": 0.7, "jpeg_quality": 65, "expected_priority": "moderate", "actual_priority": "major", "passed": false, "processing_ms": 7.0}`
- `{"case": "cover", "seed": 71, "scale": 1.2, "jpeg_quality": 65, "expected_priority": "moderate", "actual_priority": "major", "passed": false, "processing_ms": 19.9}`
- `{"case": "cover", "seed": 208, "scale": 0.7, "jpeg_quality": 65, "expected_priority": "moderate", "actual_priority": "major", "passed": false, "processing_ms": 6.7}`
- `{"case": "cover", "seed": 208, "scale": 1.2, "jpeg_quality": 65, "expected_priority": "moderate", "actual_priority": "major", "passed": false, "processing_ms": 19.5}`
- `{"case": "cover", "seed": 309, "scale": 0.7, "jpeg_quality": 65, "expected_priority": "moderate", "actual_priority": "major", "passed": false, "processing_ms": 6.7}`
- `{"case": "cover", "seed": 309, "scale": 1.2, "jpeg_quality": 65, "expected_priority": "moderate", "actual_priority": "major", "passed": false, "processing_ms": 19.3}`
- `{"case": "clear", "seed": 71, "scale": 0.7, "jpeg_quality": 65, "expected_priority": "routine", "actual_priority": "major", "passed": false, "processing_ms": 6.6}`
- `{"case": "clear", "seed": 71, "scale": 1.2, "jpeg_quality": 65, "expected_priority": "routine", "actual_priority": "major", "passed": false, "processing_ms": 20.1}`
- `{"case": "clear", "seed": 208, "scale": 0.7, "jpeg_quality": 65, "expected_priority": "routine", "actual_priority": "major", "passed": false, "processing_ms": 6.6}`
- `{"case": "clear", "seed": 208, "scale": 1.2, "jpeg_quality": 65, "expected_priority": "routine", "actual_priority": "major", "passed": false, "processing_ms": 18.5}`
- `{"case": "clear", "seed": 309, "scale": 0.7, "jpeg_quality": 65, "expected_priority": "routine", "actual_priority": "major", "passed": false, "processing_ms": 6.4}`
- `{"case": "clear", "seed": 309, "scale": 1.2, "jpeg_quality": 65, "expected_priority": "routine", "actual_priority": "major", "passed": false, "processing_ms": 18.3}`
- `{"case": "pole-lean", "seed": 71, "scale": 1.2, "jpeg_quality": 88, "expected_priority": "major", "actual_priority": "unassessed", "passed": false, "processing_ms": 19.4}`
- `{"case": "pole-lean", "seed": 208, "scale": 1.2, "jpeg_quality": 88, "expected_priority": "major", "actual_priority": "unassessed", "passed": false, "processing_ms": 19.2}`
- `{"case": "pole-lean", "seed": 309, "scale": 1.2, "jpeg_quality": 88, "expected_priority": "major", "actual_priority": "unassessed", "passed": false, "processing_ms": 19.3}`
- `{"case": "camera-roll", "seed": 71, "scale": 1.2, "jpeg_quality": 65, "expected_priority": "routine", "actual_priority": "unassessed", "passed": false, "processing_ms": 19.7}`
- `{"case": "camera-roll", "seed": 71, "scale": 1.2, "jpeg_quality": 88, "expected_priority": "routine", "actual_priority": "unassessed", "passed": false, "processing_ms": 19.2}`
- `{"case": "camera-roll", "seed": 208, "scale": 1.2, "jpeg_quality": 65, "expected_priority": "routine", "actual_priority": "unassessed", "passed": false, "processing_ms": 19.4}`
- `{"case": "camera-roll", "seed": 208, "scale": 1.2, "jpeg_quality": 88, "expected_priority": "routine", "actual_priority": "unassessed", "passed": false, "processing_ms": 19.6}`
- `{"case": "camera-roll", "seed": 309, "scale": 1.2, "jpeg_quality": 65, "expected_priority": "routine", "actual_priority": "unassessed", "passed": false, "processing_ms": 20.0}`
- `{"case": "camera-roll", "seed": 309, "scale": 1.2, "jpeg_quality": 88, "expected_priority": "routine", "actual_priority": "unassessed", "passed": false, "processing_ms": 19.0}`
- `{"case": "perspective", "seed": 71, "scale": 1.2, "jpeg_quality": 65, "status": "followup_unusable", "passed": false, "inliers": 344}`
- `{"case": "perspective", "seed": 71, "scale": 1.2, "jpeg_quality": 88, "status": "followup_unusable", "passed": false, "inliers": 457}`
- `{"case": "perspective", "seed": 208, "scale": 1.2, "jpeg_quality": 65, "status": "followup_unusable", "passed": false, "inliers": 361}`
- `{"case": "perspective", "seed": 208, "scale": 1.2, "jpeg_quality": 88, "status": "followup_unusable", "passed": false, "inliers": 444}`
- `{"case": "perspective", "seed": 309, "scale": 1.2, "jpeg_quality": 65, "status": "followup_unusable", "passed": false, "inliers": 362}`
- `{"case": "perspective", "seed": 309, "scale": 1.2, "jpeg_quality": 88, "status": "followup_unusable", "passed": false, "inliers": 443}`
- `{"case": "persistent", "seed": 71, "scale": 1.2, "jpeg_quality": 65, "status": "followup_unusable", "passed": false, "inliers": 414}`
- `{"case": "persistent", "seed": 71, "scale": 1.2, "jpeg_quality": 88, "status": "followup_unusable", "passed": false, "inliers": 552}`
- `{"case": "persistent", "seed": 208, "scale": 1.2, "jpeg_quality": 65, "status": "followup_unusable", "passed": false, "inliers": 432}`
- `{"case": "persistent", "seed": 208, "scale": 1.2, "jpeg_quality": 88, "status": "followup_unusable", "passed": false, "inliers": 540}`
- `{"case": "persistent", "seed": 309, "scale": 1.2, "jpeg_quality": 65, "status": "followup_unusable", "passed": false, "inliers": 436}`
- `{"case": "persistent", "seed": 309, "scale": 1.2, "jpeg_quality": 88, "status": "followup_unusable", "passed": false, "inliers": 539}`

## Field smoke checks

- field-crossing: routine; no trigger. No correctness score.
- field-span: routine; no trigger. No correctness score.

The full per-case results are in [evaluation.json](evaluation.json).
