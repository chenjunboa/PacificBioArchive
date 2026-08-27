# Member 4 backend stabilization blockers

Branch created for this work: `member-4/backend-stabilize-then-ui`

Base reviewed: `origin/member-3/aws-worker` at `fcb458743d590e7d0f536b88b786cbfa7819fc23`

This file records the handoff risks found before starting Member 4 UI and E2E work. It does not change
Member 3's branch or tags.

## Current handoff status

- `handoff-3-core-complete` does not exist locally after fetching tags.
- Current working branch is based on `origin/member-3/aws-worker`, not on a completed handoff tag.
- Member 3 documentation claims several cloud data paths are complete, but the code still has stage-two
  placeholders and explicit cloud 501 responses.

## Release blockers to fix before UI/E2E

1. Cloud file-query endpoints are not implemented.
   - `POST /api/v1/queries/file/init` returns 501 in cloud mode.
   - `POST /api/v1/queries/file/{queryId}/execute` returns 501 in cloud mode.
   - Required fix: create temporary S3 query reservations, presigned upload, inference execution, AND tag query,
     and guaranteed temporary object cleanup.

2. DynamoDB tag queries still scan media records.
   - `DynamoDBRepository.list_media()` uses `table.scan()`.
   - `find_by_tags()` filters scanned READY media in application code.
   - Required fix: maintain `TAG#{normalizedTag}` / `COUNT#{paddedCount}#MEDIA#{mediaId}` rows and query tag
     partitions, then intersect media IDs for AND/count semantics.

3. Thumbnail reverse query does not use a stable thumbnail mapping.
   - API resolves the media ID by parsing the URL path.
   - Cloud presigned thumbnail URLs may not contain a stable `/media/{id}` path.
   - Required fix: store and query `THUMB#{urlHash}` / `MAP` items that resolve to the media ID and stable
     original S3 URI.

4. Delete does not clean all DynamoDB secondary records.
   - `delete_media()` deletes only `MEDIA#{mediaId}` and `CHECKSUM#{sha256}`.
   - It does not remove TAG index rows, THUMB mappings, subscriptions impacted by media updates, or other
     related metadata.
   - Required fix: delete original/thumbnail S3 objects and all related table rows consistently.

5. Subscription and notification logic is incomplete.
   - `upsert_subscription()` writes `PENDING_CONFIRMATION`, but the API returns `CONFIRMED_LOCAL`.
   - `subscribers_for()` always returns an empty list.
   - Worker publishes to one topic without checking confirmed tag subscriptions.
   - Required fix: align subscription state with SNS email confirmation expectations, and trigger notifications
     only for watched tags.

6. Alternate zip worker path is a placeholder and must not be used for final deployment.
   - `services/worker/member3_lambda.py` writes `pending_ml` and `awaiting-cloud-run-ml` instead of model tags.
   - `infra/aws.tf` can deploy this path when `deploy_zip_worker=true`.
   - Required fix: remove or disable this deployment path for final release, or replace it with the real
     inference-backed worker behavior.

7. Worker updates media metadata but does not maintain query indexes.
   - The real container worker calls private inference and writes `tags`, `modelVersion`, and thumbnail URI.
   - It does not write TAG rows or THUMB mappings after inference.
   - Required fix: worker success path should update media metadata, TAG index rows, THUMB mapping rows, and
     notifications together enough to avoid stale query results.

8. Automated tests do not prove the cloud blockers.
   - Current tests cover local API behavior, a DynamoDB serialization boundary, S3 URI splitting, and worker
     thumbnail generation.
   - Missing tests: cloud file query, TAG/THUMB index writes, indexed AND/count query, full delete cleanup,
     confirmed subscription filtering, and worker index updates.

## Suggested fix order

1. Add small repository helpers for TAG row keys, THUMB row keys, media batch reads, and synchronized tag index
   updates.
2. Make worker success path write TAG/THUMB rows whenever it marks media READY.
3. Replace DynamoDB `find_by_tags()` scan with indexed tag-partition queries and AND intersection.
4. Implement cloud temporary query upload/execution/cleanup.
5. Fix delete cleanup for S3 objects, checksum lock, TAG rows, THUMB row, and media metadata.
6. Align subscriptions/notifications with SNS confirmation limits.
7. Disable or remove the placeholder zip worker path from final deployment.
8. Add focused unit tests for each cloud data contract before starting UI/E2E work.

## Progress on this branch

- Added DynamoDB helpers for TAG rows, THUMB rows, subscription rows, and temporary query reservations.
- Replaced cloud tag/species query behavior with TAG partition lookup and AND/count intersection.
- Added cloud thumbnail reverse lookup through THUMB mapping.
- Added cloud temporary query upload, execution, inference, AND query, and cleanup paths.
- Extended delete cleanup to remove media metadata, checksum lock, TAG rows, and THUMB rows.
- Changed cloud subscription response to `PENDING_CONFIRMATION`.
- Made the placeholder ZIP worker opt-in instead of default.
- Extended the real container worker to write TAG and THUMB indexes after inference succeeds.
- Added API-side optional AWS-to-GCP WIF ID-token support for cloud file-query inference calls.
- Added focused fake-client tests for cloud repository index behavior and worker index writes.

Remaining validation:

- Full `pytest` and `ruff` still need a Python 3.12 environment with project dependencies installed.
- `terraform validate` still needs `terraform init` because AWS/Google provider plugins are not cached.
- Real AWS/GCP verification is still required before claiming cloud acceptance in the report.
