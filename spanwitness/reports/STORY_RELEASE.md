# Presentation release 0.2.1

The opening page now explains the inspection problem, gives the pole-beside-a-school example and describes the approach before its technical details. The two history features and the original conductor/vegetation workflow are unchanged.

The deployed source archive is `SpanWitness-story-0aed7a31.zip`, SHA-256 `0aed7a31919d97e0354f9d74156e6841d57751b9911b414e66502f2e639c822f`. CloudFormation reached UPDATE_COMPLETE. Live checks passed at 2026-10-26T05:24:19Z. The runtime reported app 0.2.1, OpenCV 5.0.0 and S3/DynamoDB storage. Actual Lambda measurements were 4.95 degrees for the drawn-change case and 0.0 for the camera-rotation control.

See [the sanitized live receipt](aws-story-live-receipt.json). It also verifies that the frontend files match the frozen source, private access rejects unauthenticated calls and saved images/comparisons can be read back. These are synthetic workflow checks, not field accuracy.

The submission repository includes later documentation and media preparation. Its source manifest describes that repository, while the frozen archive identifies the deployed runtime.
