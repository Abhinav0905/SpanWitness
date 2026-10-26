# Build validation

Verified locally on October 25, 2026, Pacific Time.

| Check | Result | Boundary |
| --- | --- | --- |
| Regression and API suite | 60 passed | Includes four AWS SDK contract checks with stubbed responses, chronology/provenance checks and history evidence/review persistence. |
| Synthetic screening matrix | 144 / 144 | Procedural variants, revised after baseline failures. Not field accuracy. |
| Synthetic second-view matrix | 36 / 36 | Image correspondence and decision branches. Not physical clearance. |
| History development matrix | 108 / 108 | Known drawn change, camera rotation, changed perspective and blur across seeds, sizes and JPEG settings. Not field accuracy. |
| Two licensed field photographs | Both processed | No condition labels or correctness score. |
| JavaScript syntax | Passed | `node --check`. |
| AWS SAM template lint | Passed | Both the source template and generated local-image template. Live deployment is checked separately. |
| Linux Lambda image smoke | Passed locally and in AWS CloudShell | Real OpenCV computation, multipart request, binary image and JSON export. SQLite inside the container; not a deployed Lambda/S3/DynamoDB stack. |
| Live Lambda/S3/DynamoDB API smoke | Passed | Actual OpenCV 5 workload, credential gate, persisted images/records, export and second-view decision. |
| Hosted browser flow | Passed | Chrome sign-in, second-view comparison, labeled demo review and reload persistence. |
| Browser inspection | Passed | First observation, changed-view comparison, pole alignment, camera-roll example, saved review, archive filters and queue. |
| Phone-width layout | Checked | No horizontal document overflow at the tested narrow viewport. Physical camera permissions and hardware capture were not exercised. |
| NWS live alert context | Available | Public San Francisco city coordinates returned an available response with no active fire-weather alert. This does not establish low fire danger. |

The first stress run had 123 / 144 expected screening results and 24 / 36 expected comparison results. JPEG color islands and resolution-dependent sharpness explained the failures. Those results are preserved in `baseline-evaluation.json`. The revised method suppresses small green-color components and normalizes the sharpness measurement to a reference width.

The Lambda container smoke test also exposed Python 3.14's change to default event-loop creation. The adapter now establishes a loop for synchronous Lambda requests. The corrected image passed the smoke test.

The SAM legacy Docker build failed on this machine with a content-digest export error. Docker BuildKit builds the image successfully; `scripts/prepare_deploy.py` creates a SAM deployment template for that local image. The separate CloudShell build and live stack verification subsequently passed.

## Not established

- Field detection precision or recall, physical lean or clearance accuracy, calibrated severity, wildfire probability or utility adoption.
- A controlled AWS cold-start or sustained-load study.
- Physical camera capture or independently recorded phone footage.
- A final video, public repository, Devpost registration or submitted project.

## AWS connection and cloud build

The owner-supplied console session was checked against STS in CloudShell. Docker and SAM are available. The uploaded source archive passed a SHA-256 check, Docker built the image in CloudShell and its OpenCV smoke test passed. No local work profile or exported access key was used. The approved private stack reached CREATE_COMPLETE. Live OpenCV processing, S3/DynamoDB readback and browser review persistence passed. Account details and original connection receipts are excluded from the source archive. See [live AWS verification](AWS_LIVE.md).

## Learned-model boundary

Two pole-appearance experiments did not meet the declared acceptance boundary. Their results are in [MODEL_DEVELOPMENT.md](MODEL_DEVELOPMENT.md). Neither is loaded by the app, and the publisher test split remains untouched.

## Asset-history extension

The two additions are a dated asset timeline with baseline selection, and a constrained pole-alignment comparison. Local browser checks covered the change case, camera-rotation control, perspective refusal, saved comparison after reload, review confirmation and a review export that retains both observations. Phone-width history layout had no horizontal document overflow at the tested 312 CSS-pixel viewport. A repeated fixture run initially selected an older baseline and hid its newly saved result; selection now restores the latest saved comparison pair.

The original screening/comparison checks were rerun after the directional-edge fitting change and still passed 144/144 and 36/36. History checks passed 108/108 with zero change alerts in the controls. Accepted apparent-angle error against the drawing geometry was median 0.05 degrees, maximum 0.59 degrees. The scene design is shared and was used during development. These numbers are not physical pole accuracy.

The history extension reached UPDATE_COMPLETE. Its live API and browser checks passed, including comparison persistence and the historical-review export. The earlier conductor review remained intact. See [HISTORY_RELEASE.md](HISTORY_RELEASE.md). No demo recording has begun.
