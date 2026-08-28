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
| Cloud smoke runner | Prepared | `npm run test:e2e:cloud` runs against a deployed URL when the required `PBA_CLOUD_*` environment variables are provided. |
| Demo script | Complete | `docs/demo-script.md` contains the minute-by-minute rehearsal script, demo image checksums, evidence checklist, cold-start fallback, and cleanup checklist. |

## Latest local validation

Run on 2026-08-28 after merging Member 4 E2E work into `main`:

```text
npm run test:e2e: 1 passed
npm run build: passed
.venv/bin/python -m pytest -q: 17 passed, 2 warnings
.venv/bin/python -m ruff check services/api services/inference services/worker: passed
terraform -chdir=infra validate: passed
```

## Still required before final submission

These items need the live AWS/GCP deployment, real Cognito users, or team review. Do not mark them
as complete in the report until the evidence exists.

| Remaining item | Owner | Blocking reason |
|---|---|---|
| Cloud smoke run 1 | Member 4 plus AWS/GCP account holder | Requires deployed frontend/API/worker/inference and a verified Cognito test user. |
| Cloud smoke run 2 | Member 4 plus AWS/GCP account holder | Assignment handoff asks for the critical cloud path to run twice successfully. |
| Real short video evidence | Member 3 or Member 4 | A known-good MP4/MOV sample and deployed worker logs are needed. |
| SNS confirmation screenshot | Member 4 | Requires a real email subscription and mailbox confirmation flow. |
| Redacted screenshots/logs | All members | Each report claim needs matching evidence without tokens, passwords, OTPs, presigned URL query strings, or account secrets. |
| First-member review of release candidate | Member 1 | Required before creating the final release tag. |
| `release-candidate-1` tag | Team representative after review | Should point to the accepted commit only after cloud smoke evidence and review. |
| Final `v1.0.0` tag | Team representative after all checks | Should not be created before every member accepts the final state. |
| Group report PDF | Team representative | Must include names, student IDs, private repository link, AI use statement, screenshots, and contribution evidence. |
| Individual reports | Every member | Submitted separately through the individual link. |
| Cloud cleanup owner | Team representative | Must be named in the final report for after marking. |

## Recommended next order

1. Run `npm run test:e2e` once more from clean `main` immediately before cloud rehearsal.
2. Ask the AWS/GCP account holder to confirm the deployed URLs and Cognito test users.
3. Run `docs/cloud-smoke-evidence.md` twice, then execute `docs/demo-script.md`, saving redacted screenshots or Playwright videos.
4. Fill the group report with only verified claims.
5. Ask Member 1 to review the release candidate.
6. Create `release-candidate-1`, then final `v1.0.0` only after all members confirm.
