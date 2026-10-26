# Evaluation

Generated: 2026-10-26T06:51:06.495682+00:00

OpenCV 5.0.0; Python 3.14.7; arm64.

- Synthetic screening checks: 144/144.
- Synthetic second-view checks: 36/36.
- Local screening time: median 15.1 ms; maximum 37.1 ms.

## Limits

- Procedural image variations share scene geometry; these are regression and stress checks, not independent field data.
- Seeds, resize and compression change texture and image quality. They do not model real electrical faults or physical parallax.
- Two licensed field photographs have no validated condition labels. No field precision or recall is reported.
- Latency measures local OpenCV screening, excluding upload, comparison, weather, storage and AWS cold starts.

## Failures

No failures in this declared synthetic matrix.

## Field smoke checks

- field-crossing: routine; no trigger. No correctness score.
- field-span: routine; no trigger. No correctness score.

The full per-case results are in [evaluation.json](evaluation.json).
