# Final submission readiness

Last updated: 2026-08-29

## Completed by repository and cloud validation

- Latest `main` is pushed to GitHub.
- API Lambda and main Worker Lambda were updated from the latest `main` container images.
- The fallback `member3-worker` SQS event source mapping is disabled, so it no longer consumes media
  processing jobs.
- Two live image cloud smoke runs passed through Cognito sign-in, frontend upload, AWS API, S3,
  SQS, main Worker Lambda, GCP inference, tag query, thumbnail reverse query, delete, 404 after
  deletion, and sign-out.
- One live 3 second MP4 cloud smoke run passed through Cognito sign-in, frontend upload, AWS API,
  S3, SQS, main Worker Lambda, GCP inference, tag query, delete, 404 after deletion, and sign-out.
- DynamoDB cleanup checks for the successful smoke media IDs returned `Count: 0`.
- The media DLQ remained empty.
- `web npm run build` passed.
- `web npm run test:e2e:cloud` correctly skips when cloud credentials/environment variables are not
  provided.
- Member 4 evidence summaries are available under `docs/evidence/member-4/`.
- Team and Member 4 individual report drafts are available under `docs/`.

## Still externally blocked

These items require a human account holder or team approval and should not be marked complete until
that happens.

| Item | Status | Required owner action |
|---|---|---|
| SNS email confirmation | Pending | `bpan0043@student.monash.edu` has a pending AWS SNS confirmation email. Open the email and click `Confirm subscription`, then re-run the SNS status check. |
| SNS screenshot | Pending | After confirmation, capture a redacted screenshot showing the confirmed subscription or confirmation email. Hide token-like links and private details. |
| Official architecture diagram | Draft-ready | Build the final diagram using official AWS and Google Cloud architecture icons, then insert it into the team report PDF. |
| Team member names and student IDs | Pending | Replace every `TODO` in `docs/final-team-report-draft.md` and `docs/final-individual-report-member4-draft.md`. |
| Member 1 review | Pending | Member 1 should review the final `main` commit and evidence before release tagging. |
| `release-candidate-1` tag | Waiting on review | Create only after Member 1 accepts the release candidate. |
| `v1.0.0` tag | Waiting on team acceptance | Create only after all members accept the final state. |
| Final PDFs | Waiting on missing details | Export the team report and individual report to PDF after TODO values and diagram are inserted. |

## Commands for the final human checks

```bash
git status --short --branch
git log --oneline -5
aws sns list-subscriptions-by-topic \
  --profile fit5225 \
  --region us-east-1 \
  --topic-arn arn:aws:sns:us-east-1:220664822460:pacific-bioarchive-prototype-tag-notifications \
  --query 'Subscriptions[].{Endpoint:Endpoint,Protocol:Protocol,SubscriptionArn:SubscriptionArn}' \
  --output table
```

Do not commit screenshots or logs that contain passwords, email confirmation codes, JWTs, AWS/GCP
access tokens, presigned URL query strings, Terraform state, or model weights.
