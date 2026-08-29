# Cloud smoke evidence guide

Use this guide after the AWS/GCP deployment is live. The cloud smoke test is intentionally not part
of default CI because it needs a real deployed URL, a verified Cognito user, and a local demo image.

## Required local environment variables

Set these in the current terminal only. Do not commit them to Git, screenshots, or the report.

```bash
export PBA_CLOUD_WEB_URL="https://your-cloud-run-web-url"
export PBA_CLOUD_EMAIL="verified-test-user@example.com"
export PBA_CLOUD_PASSWORD="test-user-password"
export PBA_CLOUD_IMAGE_PATH="/absolute/path/to/Alectura_lathami_1.JPG"
export PBA_CLOUD_EXPECTED_TAG="alectura_lathami"
export PBA_CLOUD_READY_TIMEOUT_MS="300000"
```

`PBA_CLOUD_EXPECTED_TAG` is optional and defaults to `alectura_lathami`. `PBA_CLOUD_READY_TIMEOUT_MS`
is optional and defaults to five minutes, which leaves room for Lambda cold starts and the GCP
inference call.

## Command

Run the cloud smoke test twice from the `web` directory:

```bash
npm run test:e2e:cloud
npm run test:e2e:cloud
```

Each run signs in through the deployed frontend, uploads one image, waits for `READY`, checks tag and
thumbnail queries through the protected deployed API, deletes the uploaded media, checks the media
endpoint returns 404, and signs out. The runner prints `cloud-smoke-media-id=...` for the uploaded
record so the report can tie Playwright output to CloudWatch, DynamoDB, and S3 evidence without
recording secrets.

## Evidence to save

- Playwright HTML report for run 1.
- Playwright HTML report for run 2.
- Console output showing `cloud-smoke-media-id=...` and `1 passed` for each run.
- Video or screenshots showing READY status, model version, tag query, thumbnail query, delete, and
  sign-out.
- Redacted CloudWatch worker logs for the uploaded media ID.
- Redacted DynamoDB before/after evidence for media row, tag index rows, thumbnail mapping, checksum
  reservation, and deletion cleanup.
- SNS confirmation screenshot if the notification demo is also run.

## Redaction rules

Hide passwords, MFA/OTP/email confirmation codes, JWTs, AWS/GCP access tokens, full presigned URL
query strings, account IDs if required by the team, and any private email addresses not needed for
marking.

## Manual registration note

Cognito email registration and confirmation require a real mailbox and code. Perform that step once
before this automated smoke test, then use the verified test user through `PBA_CLOUD_EMAIL` and
`PBA_CLOUD_PASSWORD`.
