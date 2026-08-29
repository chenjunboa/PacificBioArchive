# Member 4 evidence checklist

This directory is reserved for redacted Member 4 evidence captured during local E2E, cloud smoke,
demo rehearsal, and final report preparation.

## Current status

Live-cloud smoke evidence was produced on 2026-08-29 after the API and Worker Lambda images were
updated from `main` and the fallback `member3-worker` SQS trigger was disabled.

```text
npm run test:e2e:cloud evidence run 1: passed in 26.0s, mediaId 6e10a04c-9bb6-4128-bf83-6b4cec8daa38
npm run test:e2e:cloud evidence run 2: passed in 24.2s, mediaId 6f32f21a-d6e0-41af-b398-d9070430eed5
DynamoDB cleanup check after both successful runs: Count 0
Worker Lambda recent invocations completed successfully; media DLQ message count remained 0.
Short MP4 cloud smoke: passed in 1.7m, mediaId b4c56c61-e229-4aa3-8539-8ff6e1e8f372, contentType video/mp4
Short MP4 cleanup check: Count 0; media DLQ message count remained 0.
```

The sanitized validation summaries are committed as `13-video-cloud-smoke-redacted.md` and
`14-image-cloud-smoke-redacted.md`. Before final submission, also export any Playwright report,
screenshots, and CloudWatch/DynamoDB snippets that the group report will cite.

## Suggested files

Use stable numbered names so the group report can cite each artifact clearly:

| File | Purpose |
|---|---|
| `01-local-e2e-report-redacted.png` or `01-local-e2e-report.zip` | Local Playwright report showing the archive workflow passed. |
| `02-cloud-run-1-ready-redacted.png` | First deployed smoke run showing uploaded media reaches `READY`. |
| `03-cloud-run-2-ready-redacted.png` | Second deployed smoke run showing the critical path is repeatable. |
| `04-tag-query-redacted.png` | Tag/count AND query result. |
| `05-species-query-redacted.png` | Species query result loaded from `/species`. |
| `06-thumbnail-query-redacted.png` | Thumbnail reverse query result. |
| `07-file-query-redacted.png` | Temporary file query result. |
| `08-duplicate-409-redacted.png` | Duplicate upload rejection evidence. |
| `09-non-owner-403-redacted.png` | Non-owner mutation blocked by the API. |
| `10-signed-out-401-redacted.png` | Signed-out API request rejected. |
| `11-sns-confirmation-redacted.png` | SNS email subscription confirmation evidence. |
| `12-delete-cleanup-redacted.png` | Delete workflow and cleanup evidence. |
| `13-video-cloud-smoke-redacted.md` | Short MP4 upload, inference, tag query, delete, and cleanup evidence. |
| `14-image-cloud-smoke-redacted.md` | Two repeatable image cloud smoke runs with tag/thumbnail queries and cleanup evidence. |

## Redaction rules

Before committing screenshots, traces, or logs, remove passwords, email verification codes, MFA
codes, JWTs, refresh tokens, access keys, secret keys, presigned URL query strings, private user
emails, and any cloud account identifiers the team does not want in the report.

## Commands

Run the local E2E workflow from `web/`:

```text
npm run test:e2e
```

Run the deployed cloud smoke workflow from `web/` after the account holder provides the deployed
frontend URL, verified Cognito user, password, and safe image path:

```text
npm run test:e2e:cloud
npm run test:e2e:cloud
```

Keep the two cloud runs separate so the report can show repeatability instead of a single lucky
pass.
