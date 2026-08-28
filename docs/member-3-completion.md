# Member 3 implementation handoff

## Implemented code paths

- `APP_ENV=cloud` uses DynamoDB and S3 instead of SQLite and local files.
- Media uses the specified `MEDIA`, `CHECKSUM`, `TAG`, `THUMB`, `USER` single-table keys,
  owner GSI fields, padded tag-count keys, checksum reservation transactions, and temporary-query TTL items.
- The API produces S3 presigned PUT/GET URLs. Browser uploads bind content type and checksum
  metadata; the SQS worker verifies both metadata and the downloaded object's SHA-256.
- `app.worker.handler` consumes S3-to-SQS events idempotently, processes images, invokes the
  private inference endpoint with an identity token, updates media state, maintains tag and thumbnail
  mappings, and re-raises retriable errors so SQS redrive sends them to the DLQ.
- Tag/species queries use DynamoDB tag partitions and intersect media IDs. File-query objects are
  deleted in a `finally` block. Delete removes S3 objects, tag rows, thumbnail maps, checksum lock,
  and metadata.

## Required deployment verification

No cloud account credentials or resources were supplied with this ZIP, so the following must be
performed by the account owner before claiming cloud acceptance:

1. Build API with `services/api/Dockerfile.lambda` and worker with `services/worker/Dockerfile`;
   push immutable digest tags to the two ECR repositories.
2. Configure AWS-to-GCP workload-identity credentials for both Lambda images. Confirm that an
   anonymous request to inference is rejected and that the worker receives a Cloud Run ID token.
3. Add the exact Cloud Run web origin to S3/API CORS; the committed localhost origin is only for
   development.
4. Apply Terraform, then record sanitized evidence for Cognito, S3 upload, SQS processing, DynamoDB
   items/index rows, thumbnail mapping, successful image/video processing, retry/DLQ behaviour, and
   SNS email confirmation.
5. Run the required four-thread duplicate test against the deployed table and perform all four query
   types, owner/stranger mutation checks, and deletion checks through the deployed API.

Do not mark these checks as passed until they have been performed in the real AWS and GCP projects.
