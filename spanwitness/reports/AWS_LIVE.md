# Private AWS preview: live verification

Verified October 25, 2026, Pacific Time (October 26 UTC).

Preview: https://ec1f3mu6m7.execute-api.us-west-2.amazonaws.com

The private `spanwitness-demo` stack reached `CREATE_COMPLETE` in `us-west-2`. Deployment used the owner's existing console and CloudShell session. No local work profile, exported access key or employer data was used. The owner approved a maximum of $5 of usage through judging. This approval is not a hard AWS billing cap or a claim about the current bill.

## Recorded checks

| Check | Result |
| --- | --- |
| Request without preview credentials | HTTP 401 |
| Authenticated runtime | OpenCV 5.0.0, `aws_s3_dynamodb` storage |
| Uploaded gap fixture | Actual Lambda processing returned critical review |
| Original and annotated image readback | S3 bytes matched the recorded hashes |
| Observation and evidence export | DynamoDB-backed record readback passed |
| Two-view fixture | Major review changed to moderate review after registered projected overlap decreased |
| Interface assets | Interface HTML served; JavaScript and CSS matched the tested source |
| Chrome sign-in and browser workflow | Passed |
| Human confirmation and persistence | A clearly labeled demo review remained after reload |

The browser comparison found 375 matching landmark inliers. Image-space overlap changed from 17% to 0%. These figures describe the synthetic views, not physical clearance. The saved review was marked `DEMO ONLY`; no crew was contacted.

The initial three API analysis calls took 1027.1, 211.3 and 991.3 ms end to end. After the wording update, the repeated checks passed at 673.4, 167.2 and 643.0 ms. These include network and storage work. They are neither a latency distribution nor an isolated cold-start study.

## Reproducible evidence

The initial deployed archive was `SpanWitness-03420c0e.zip`, SHA-256 `03420c0ef7f6846d48571266430ebc03bdab12f01f7087c64add1884d728e039`. Its source manifest SHA-256 was `b0cb5dba611b248eca3e44bac79e16a5069fd5431e498bc113b0b7ce46a2f7ac`. Original CloudFormation and API receipts remain in the ignored local `data/aws/` directory. [The sanitized API and browser receipt](aws-live-receipt.json) excludes account identifiers and access codes.

The script `scripts/cloud_verify.py` can repeat the API checks from the owner's CloudShell session. It reads the existing encrypted access parameter in memory. Keep credentials out of terminal output and source archives.

## Limits

The live checks establish execution and persistence. Field detection accuracy, metric clearance, true pole lean, electrical contact, calibrated severity and wildfire probability remain unverified. Physical camera capture and independent phone footage still need testing.

## Current deployed revision

The subsequent wording and report update reached `UPDATE_COMPLETE`. Its frozen archive is `SpanWitness-22d1d393.zip`, SHA-256 `22d1d393f4a8b44a175b9dbc03cd34d5776516fe8843f7074a1d78a16aad7fde`. Source manifest: `4d513318e09b89ec7ab8114184c17d3c3d7c30c38b3ddd1ddd3f1b75a5371a15`. The full live API smoke check passed again, the corrected queue label appeared and the earlier demo review survived the update. The current receipt and this post-deployment addendum were saved after the frozen archive was deployed.

## Asset-history release 0.2.0

The two-feature extension is deployed and verified. The live comparison measured 4.95 degrees for the controlled 5-degree change and 0.0 degrees for camera rotation alone. Original inspection checks, comparison export, DynamoDB history persistence and the browser review/reload path passed. Read [HISTORY_RELEASE.md](HISTORY_RELEASE.md) for the deployed source and exact evidence boundaries.
