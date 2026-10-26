# AWS deployment

Status: the private preview is deployed in the owner's personal account in `us-west-2`. CloudFormation completed and the live OpenCV, S3 and DynamoDB checks passed on October 25, 2026, Pacific Time. The current runtime is 0.2.1. It includes the asset-history extension and a problem-first opening page. See [live verification](reports/AWS_LIVE.md) and [the history release receipt](reports/HISTORY_RELEASE.md).

Preview: https://ec1f3mu6m7.execute-api.us-west-2.amazonaws.com

Username: `judge`. The access code is stored as an encrypted SSM parameter at `/spanwitness/spanwitness-demo/preview-access`. Retrieve it in the owner's console, then keep it out of chat, screenshots, URLs and source archives.

## Services

API Gateway forwards the interface and image API to a container-based Lambda function. Lambda runs the actual OpenCV analysis. S3 retains JPEG evidence; DynamoDB retains observations, comparison links and human-review requests.

The stack uses a private encrypted bucket, an on-demand table, API request throttling and a browser access code. The browser username is `judge`. This access code is for a private hackathon preview, not a production identity system.

## Build and validate

Use a personal AWS profile chosen by the account owner. Do not use an existing work profile by inference. Docker Desktop must be running.

From the workspace root:

```sh
python3.14 -m venv .tools-venv
.tools-venv/bin/python -m pip install aws-sam-cli==1.170.0
SAM_CLI_TELEMETRY=0 .tools-venv/bin/sam validate --lint --template-file spanwitness/template.yaml --region us-west-2
docker build --platform linux/amd64 --provenance=false -f spanwitness/Dockerfile -t spanwitness:local .
docker run --rm --platform linux/amd64 --entrypoint /var/lang/bin/python -e SPANWITNESS_DATA=/tmp/spanwitness -e AWS_EC2_METADATA_DISABLED=true spanwitness:local -m spanwitness.scripts.container_smoke
.tools-venv/bin/python spanwitness/scripts/prepare_deploy.py
```

BuildKit is used explicitly. The local SAM legacy Docker build failed with a content-digest export error on this machine. The helper produces a SAM template that references the already-built local image. SAM can upload that image during deployment.

## Deploy after choosing the personal profile

```sh
SAM_CLI_TELEMETRY=0 .tools-venv/bin/sam deploy --guided --template-file spanwitness/artifacts/deployment-template.json --stack-name spanwitness-demo --region us-west-2 --profile PERSONAL_PROFILE --resolve-image-repos
```

Replace `PERSONAL_PROFILE` with the confirmed profile name. Enter a preview access code of at least 16 characters at the hidden prompt. Do not save secret parameter overrides in `samconfig.toml`, command arguments or source control. Review the change set before execution.

This creates an ECR image repository, Lambda, API Gateway, IAM execution permissions, S3, DynamoDB and CloudWatch logs. The stack output provides the preview URL. Deployment can incur AWS charges. API throttles bound the request rate; they are not a spending cap.

The evidence bucket and table are retained if the stack is deleted. Images expire after 30 days; DynamoDB records currently have no automatic expiry. Review costs and retained resources after the competition. The preview contains demo data only and has no external crew-delivery integration.

## Verify the live stack

- Sign in to the preview using `judge` and the preview access code.
- Check `/api/health`: OpenCV must report version 5 and storage must be `aws_s3_dynamodb`.
- Analyze an example, open its stored JPEG and export its evidence JSON.
- Request a second view and verify the reference ID and changed action.
- Stage a labeled demo review, refresh the application and confirm persistence.
- Record the deployed URL, stack outputs and a live smoke-test receipt. Keep access codes out of screenshots and the public report.

The archive's DynamoDB index is eventually consistent, so a new observation can take a short time to appear. Browser uploads are resized to at most 1400 pixels; the API accepts files below 4 MB to fit the Lambda request path. The initial AWS cold start has not been measured.

## References

- [Lambda container images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
- [SAM function resource](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-resource-function.html)
- [SAM upload of local images](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/deploy-upload-local-files.html)
- [Mangum adapter](https://mangum.fastapiexpert.com/adapter/)

## Existing console session / CloudShell

A personal CLI profile is optional when CloudShell is used. The current browser session has been checked against `sts:GetCallerIdentity`, and Docker plus SAM are available in CloudShell. Account identifiers and the connection receipt stay in the ignored local data directory. No local work profile was used.

The source archive was uploaded through CloudShell's Actions menu, checked by SHA-256 and built with Docker. `scripts/cloud_deploy.py` prepared a change set, reused the encrypted preview code and executed the approved deployment. `scripts/cloud_verify.py` checked the actual API and stored evidence. This route used the existing AWS session without creating or exporting access keys. Original receipts are retained under the ignored local `data/aws/` directory. A sanitized receipt is included in the report.

For another deployment, extract a newly versioned source archive into a separate CloudShell folder, then run `cloud_deploy.py prepare --expected-account ACCOUNT_ID --approved-budget 5`. Inspect the change set before running its `execute` action. Never pass the access code as a command argument.

The owner approved at most $5 of usage through judging. This is an operating limit, not a hard billing cap. No always-on VM, NAT gateway, paid model endpoint or GPU instance is used. Check billing and retained resources after judging; the evidence table, bucket, ECR images and SSM parameter need separate cleanup if the stack is removed.

The personal account preflight reported a regional Lambda concurrency quota of 10. The template therefore does not reserve function concurrency. It uses API Gateway throttling instead, including a one-request-per-second rate and a burst of two for image analysis.
