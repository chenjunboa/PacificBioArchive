# Member 4 acceptance status

This file records what Member 4 has actually completed and what still requires live cloud
verification before the assignment report can claim final acceptance.

## Completed in the repository

| Area | Status | Evidence |
|---|---|---|
| Backend handoff stabilization | Complete locally | Cloud repository and worker fake-client tests cover tag indexes, thumbnail maps, temporary query files, delete cleanup, and worker index writes. |
| React authentication flow | Complete locally | Local mode uses `/auth/dev-token`; cloud mode uses Cognito sign-up, confirmation, sign-in, session restore, token refresh, and sign-out from Vite environment variables. |
| Upload UI | Complete locally | File type restrictions, image/video size messaging, video duration check, checksum status, upload status, backend polling, READY/FAILED display, duplicate 409 messaging, and thumbnail display are implemented. |
| Four query modes | Complete locally | Tag/count AND query, `/species` dropdown with 46 API-loaded species, thumbnail reverse query, and temporary file query are implemented. |
| Media management | Complete locally | Owner-only controls, bulk tag add/remove, delete confirmation, and delete result messaging are implemented. |
| Notifications UI | Complete locally | Subscribe and unsubscribe actions show success/failure messages and explain SNS email confirmation. |
| Local E2E | Complete | `npm run test:e2e` covers login, image upload to READY, duplicate 409, tag query, species query, thumbnail query, file query, tag add/remove, non-owner 403, delete, and signed-out 401. |
| Cloud smoke runner | Complete in live cloud | `npm run test:e2e:cloud` runs against the deployed Cloud Run frontend and protected AWS API when the required `PBA_CLOUD_*` environment variables are provided. |
| Demo script | Complete | `docs/demo-script.md` contains the minute-by-minute rehearsal script, demo image checksums, evidence checklist, cold-start fallback, and cleanup checklist. |

## Latest local validation

Run on 2026-08-29 on `member-4/backend-stabilize-then-ui` after adding the cloud smoke runner:

```text
npm run test:e2e: 1 passed
npm run test:e2e:cloud without PBA_CLOUD_* environment variables: 1 skipped
npm run build: passed
.venv/bin/python -m pytest -q: 17 passed, 2 warnings
.venv/bin/python -m ruff check services/api services/inference services/worker: passed
terraform -chdir=infra validate: passed
```

## Latest live cloud validation

Run on 2026-08-29 after `main` was deployed to the AWS Lambda API and worker images:

```text
API Lambda image digest: sha256:725287c1f9bb6198a625646eaaf023a0d5ac6fffb0291878d4017a42e1f98c57
Worker Lambda image digest: sha256:295ed696f139bbfcb265173fbd0624a72050ce9dfde8d5c16f83576485a466ec
member3-worker SQS event source mapping 4b479c2d-0b63-4d2b-9bee-ecf00684cd68: Disabled
SQS DLQ ApproximateNumberOfMessages: 0
web npm run build: passed
npm run test:e2e:cloud evidence run 1: passed in 26.0s, mediaId 6e10a04c-9bb6-4128-bf83-6b4cec8daa38
npm run test:e2e:cloud evidence run 2: passed in 24.2s, mediaId 6f32f21a-d6e0-41af-b398-d9070430eed5
DynamoDB cleanup check after both successful runs: 0 records remaining for those media IDs
```

The live smoke runner signs in through the deployed frontend, uploads a real image, waits for the
deployed API to return `READY` with the expected SpeciesNet tag, verifies tag/count and thumbnail
reverse queries through the protected API using the same Cognito token, deletes the uploaded media,
checks the media endpoint returns 404, and signs out.

## Still required before final submission

These items need the live AWS/GCP deployment, real Cognito users, or team review. Do not mark them
as complete in the report until the evidence exists.

| Remaining item | Owner | Blocking reason |
|---|---|---|
| Real short video evidence | Member 3 or Member 4 | A known-good MP4/MOV sample and deployed worker logs are needed. |
| SNS confirmation screenshot | Member 4 | Requires a real email subscription and mailbox confirmation flow. |
| Redacted screenshots/logs | All members | Use `docs/evidence/member-4/README.md` for Member 4 naming and redaction rules. Each report claim needs matching evidence without tokens, passwords, OTPs, presigned URL query strings, or account secrets. |
| First-member review of release candidate | Member 1 | Required before creating the final release tag. |
| `release-candidate-1` tag | Team representative after review | Should point to the accepted commit only after cloud smoke evidence and review. |
| Final `v1.0.0` tag | Team representative after all checks | Should not be created before every member accepts the final state. |
| Group report PDF | Team representative | Must include names, student IDs, private repository link, AI use statement, screenshots, and contribution evidence. |
| Individual reports | Every member | Submitted separately through the individual link. |
| Cloud cleanup owner | Team representative | Must be named in the final report for after marking. |

## Recommended next order

1. Capture or export redacted evidence artifacts from the two successful cloud smoke runs.
2. Add the remaining video evidence if the team wants to claim MP4/MOV processing in the report.
3. Capture SNS subscription confirmation evidence if the team wants to claim the email notification workflow.
4. Fill the group report with only verified claims.
5. Ask Member 1 to review the release candidate.
6. Create `release-candidate-1`, then final `v1.0.0` only after all members confirm.
