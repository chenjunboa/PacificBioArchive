# Member 4 image cloud smoke evidence

Date: 2026-08-29

Purpose: verify that the deployed multi-cloud application can accept real image uploads, process
them through the main AWS Lambda worker and GCP inference path, return SpeciesNet tags, support
tag/count and thumbnail reverse queries, delete the uploaded media, and clean up metadata/index
records.

## Deployment state before evidence runs

```text
API Lambda image digest: sha256:725287c1f9bb6198a625646eaaf023a0d5ac6fffb0291878d4017a42e1f98c57
Worker Lambda image digest: sha256:295ed696f139bbfcb265173fbd0624a72050ce9dfde8d5c16f83576485a466ec
member3-worker SQS event source mapping 4b479c2d-0b63-4d2b-9bee-ecf00684cd68: Disabled
```

## Cloud smoke results

```text
npm run test:e2e:cloud -- --timeout=600000
cloud-smoke-media-id=6e10a04c-9bb6-4128-bf83-6b4cec8daa38
1 passed
elapsed: 26.0s

npm run test:e2e:cloud -- --timeout=600000
cloud-smoke-media-id=6f32f21a-d6e0-41af-b398-d9070430eed5
1 passed
elapsed: 24.2s
```

The Playwright cloud smoke signed in through the deployed frontend, uploaded an assignment-provided
image, waited for the deployed API to return `READY` with tag `alectura_lathami`, verified tag/count
query and thumbnail reverse query through the protected API using the same Cognito token, deleted the
uploaded media by URL, verified the media endpoint returned 404, and signed out.

## AWS evidence summary

```text
DynamoDB cleanup check for both successful image media IDs:
Count: 0

SQS media DLQ after the runs:
ApproximateNumberOfMessages: 0
ApproximateNumberOfMessagesDelayed: 0
ApproximateNumberOfMessagesNotVisible: 0
```

Earlier debugging proved the latest main worker writes the expected DynamoDB index rows before
delete: `TAG#alectura_lathami`, `THUMB#...`, `CHECKSUM#...`, and `MEDIA#...`. The final smoke runs
then verified API-level query and delete behavior and left no records for the uploaded media IDs.

Secrets, temporary Cognito credentials, JWTs, presigned URL query strings, and full cloud account
identifiers were not recorded in this evidence file.
