# Two real-photo demonstration checks

These selected PD-Defect validation photographs were downloaded from a pinned publisher revision and checked against recorded hashes. They use the publisher-declared CC BY 4.0 license. Complete author credit and source URLs accompany the app images in [ATTRIBUTION.json](../static/samples/ATTRIBUTION.json).

| Photograph | Operator input | Measured result | Next action |
| --- | --- | --- | --- |
| Pole beside a house, 713 | Visible pole edge and building reference edge | 17.93 degree pole edge, -1.40 degree reference, 19.33 degree relative image angle | Structural alignment inspection |
| Pole beside a warehouse, 1005 | Visible pole and reference edge selections | Pole edge lacks sufficient support; no relative angle | Capture clearer pole evidence |

They are different assets. They do not form a before/after pair. The first building is a house, not a school. The initial marks and full reports are in [field-photo-smoke.json](field-photo-smoke.json). Labels do not enter the analysis. Neither example has an instrument-measured physical lean used as ground truth. No field accuracy score is inferred.

The initial center-axis marks failed. Selecting visible edges fixed the first demonstration; the second still abstains. This led to a clearer marking instruction and a pole-specific retake action. No fitting or review thresholds were changed. The app's original conductor and vegetation modes remain separate checks.

The photographs were inspected for identifiable faces and readable vehicle plates; none were found. Original JPEGs contain no EXIF and are copied byte-for-byte. Operator marks are separate annotations; stored evidence overlays are modified images.

## Actual AWS run

The browser run measured 19.32 degrees for photograph 713 after manual operator marking, displayed as 19.3 degrees. Photograph 1005 returned no relative angle. Both rows were read directly from DynamoDB and their stored image hashes were checked against private S3. See [aws-real-photo-receipt.json](aws-real-photo-receipt.json) and the full [cloud regression receipt](aws-field-live-receipt.json). The 0.01 degree difference from the local preset marks is an annotation difference, not evidence of physical accuracy.
