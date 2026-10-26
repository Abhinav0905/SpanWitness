# Asset-history release 0.2.0

Released October 25, 2026, Pacific Time. Exactly two product additions: an asset history with dated baseline selection, and a constrained apparent pole-alignment change comparison. The original conductor/vegetation workflow remains available.

## Verification

- 60 regression/API tests passed, including four stubbed AWS SDK contract cases.
- Original procedural screening: 144/144. Original second-view comparisons: 36/36.
- History development matrix: 108/108, with zero change alerts in the controls. Accepted apparent-angle error against drawing geometry: median 0.05 degrees, maximum 0.59 degrees.
- Private AWS stack reached UPDATE_COMPLETE. Actual OpenCV 5.0.0 executed through Lambda with S3/DynamoDB storage. The live change case measured 4.95 degrees; the camera-rotation control measured 0.0 degrees.
- HTML, both JavaScript files and CSS matched the frozen deployed source.
- Comparison JSON exports and DynamoDB history readback passed. The browser ran a new controlled pair, staged a human-confirmed DEMO ONLY change review and restored it after reload. The earlier conductor review remained intact.
- Phone-width layout was checked at 312 CSS pixels with no horizontal document overflow.

See [the live receipt](aws-history-live-receipt.json), [history development results](HISTORY_EVALUATION.md) and [the technical report](../TECHNICAL_REPORT.md).

## Deployed source

Frozen archive: `SpanWitness-history-1db4d465.zip`.

SHA-256: `1db4d465b59aeb13769fee97bf0d1c27f7a3064cc29ab608bf41911ce8dbb4e0`.

Source manifest SHA-256: `ef05d8becfc08bbfa98bb01bb8c38ea161204564532989aef7698a5d8d561b88`.

Original deployment/API receipts stay under the ignored local data directory. This release note and sanitized receipt were written after deployment; the frozen archive remains unchanged. The prior source and deployment are preserved for rollback.

## Measurement boundary

The history is bounded to the newest 100 observations and 100 comparisons. Asset identity, dates, axes, fixed reference and repeatable capture are supplied by the operator. The method uses supporting background correspondence and declines unsuitable evidence. Its 3-degree review threshold is a prototype setting. An accepted match does not prove a common 3D camera pose.

The supplied dates in the demo are illustrative. These controlled checks do not establish field accuracy or a physical pole-lean change. Crack detection, structural strength, fall-time prediction and fire probability are not implemented. No external crew notification is sent.
