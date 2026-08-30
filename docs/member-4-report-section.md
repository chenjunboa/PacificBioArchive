# Member 4 report section draft

## Role and contribution

Member 4 completed the final user-facing integration, local end-to-end validation, demonstration
planning, and release acceptance documentation for Pacific BioArchive. The work was implemented on
the `member-4/backend-stabilize-then-ui` branch and merged progressively into `main` after local
verification.

## Frontend integration

The React frontend was extended from a basic prototype into a complete archive workflow. The
authentication page supports cloud-mode Cognito registration with given name, family name, email,
password, email confirmation, sign-in, session restoration, token refresh, and sign-out. In local
development mode, the frontend still uses the API-issued development JWT so the team can run tests
without cloud credentials. The cloud build does not expose the local development shortcut because it
is controlled by Vite Cognito environment variables.

The upload workflow now enforces the accepted media types, communicates the 20 MB image and 100 MB /
60 second video limits, shows checksum calculation and upload progress states, polls the backend
until `READY` or `FAILED`, and displays processing errors with retry guidance. Completed media cards
show content type, status, tag counts, model version, creation time, media ID, checksum prefix,
original file link, and thumbnail link.

All four required query modes were implemented in the UI. Tag/count search supports multiple
conditions and sends an AND query to the API. Species search loads the supported species list from
`/species` instead of maintaining a separate frontend list. Thumbnail reverse search accepts a
thumbnail URL and resolves it back to the original media record. Temporary file query uploads a
short-lived query file, runs inference through the backend, displays normal media cards for matches,
and does not add the query file to the archive.

Media management and notification workflows were also completed. Owner-only controls allow bulk tag
add/remove operations and confirmed deletion, while non-owner mutation was validated through a 403
API response. The notification page supports subscribe and unsubscribe operations and explains that
cloud SNS email subscriptions require mailbox confirmation.

## Backend stabilization before UI completion

During handoff review, several cloud-mode API paths required stabilization before the frontend could
truthfully demonstrate the assignment workflow. Member 4 added DynamoDB helpers for tag index rows,
thumbnail reverse mappings, subscription rows, and temporary query reservations. Cloud tag/species
queries now use indexed AND/count lookup; thumbnail reverse query uses a stable thumbnail mapping;
temporary query files are uploaded, executed, and cleaned up; delete removes related metadata and S3
objects; and the worker writes tag and thumbnail index records after inference.

The API-side inference client was also prepared for AWS-to-GCP Workload Identity Federation so cloud
file-query inference calls can authenticate to the private Cloud Run inference service when the
required WIF settings are deployed.

## Testing and verification

Local verification covered both unit-level and browser-level workflows:

```text
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check services/api services/inference services/worker
npm run build
npm run test:e2e
terraform -chdir=infra validate
```

The Playwright local E2E test covers login, image upload to `READY`, duplicate 409 handling, tag
query, species query, thumbnail reverse query, temporary file query, tag add/remove, non-owner 403,
delete, and signed-out 401 behaviour. A separate cloud smoke runner was implemented as
`npm run test:e2e:cloud`; it runs only when deployed cloud URL, verified Cognito test user, password,
and media path are supplied through local environment variables.

On 29 August 2026, after the latest `main` API and Worker Lambda images were deployed and the
fallback `member3-worker` trigger was disabled, the cloud smoke runner passed twice with real image
uploads. The two runs exercised Cognito sign-in, deployed frontend upload, the protected AWS API,
S3/SQS/Lambda processing, GCP inference through the main worker path, tag/count query, thumbnail
reverse query, delete, signed-out UI return, and DynamoDB cleanup checks. A separate short MP4 cloud
smoke also passed; it verified `video/mp4` upload, worker video processing, SpeciesNet tag output,
tag query, delete, and zero remaining DynamoDB records for the video media ID.

## Release and demonstration preparation

Member 4 added `docs/demo-script.md`, which gives the team a minute-by-minute demonstration flow,
including test image checksums, duplicate upload, four query modes, notification, non-owner
permission evidence, deletion, cold-start fallback, and cleanup. `docs/cloud-smoke-evidence.md`
documents how to run the deployed smoke test twice, and `docs/evidence/member-4/README.md` defines
the evidence filenames and redaction rules for screenshots, logs, and Playwright reports.
`docs/member-4-acceptance.md` records the boundary between completed repository/cloud verification
and remaining final-submission evidence tasks.

## Remaining evidence boundary

The repository now contains the implemented UI, local E2E test, cloud smoke runner, release
documentation, two successful live image smoke runs, one successful live short MP4 smoke run, and
confirmed SNS email subscription evidence for the Member 4 mailbox. The team still needs all members
to accept the final state before creating the final `v1.0.0` tag.

## Commits to cite

- `8ce93fa` `fix(member4): stabilize cloud backend handoff`
- `f1efc0a` `chore(member4): verify backend stabilization`
- `c9f6e37` `feat(member4): complete UI workflows and demo script`
- `a9db514` `test(member4): add local E2E release workflow`
- `78e4b23` `docs(member4): record acceptance status and AI usage`
- `16da32e` `test(member4): prepare cloud smoke evidence workflow`
- `b0cfb6d` `docs(member4): draft report contribution section`
- `85abda1` `test(member4): record live cloud smoke validation`
