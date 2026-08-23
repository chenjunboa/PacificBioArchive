# Four-person relay plan and handoff contract

This is the team's binding division of work. The project is delivered as a relay: each member
starts from the previous accepted Git tag, works on a personal branch, opens a pull request,
and hands over a runnable version with evidence. The named owner is accountable for the code,
tests, documentation and evidence in that stage.

## Shared rules

- Private repository: `chenjunboa/PacificBioArchive`; integration branch: `main`.
- Branches: `member-1/prototype`, `member-2/cloud-deployment`,
  `member-3/core-hardening`, `member-4/ui-e2e`.
- After the first handoff, nobody develops directly on `main`. Every stage is a reviewed PR.
  Member 3 reviews Member 2, Member 4 reviews Member 3, and Member 1 reviews Member 4.
- Use personal GitHub accounts. Never share accounts, passwords, MFA codes or credentials.
- Never commit `.env`, Terraform state, AWS credentials, GCP keys, media or model binaries.
- A push is not a handoff. The stage is complete only when every acceptance item passes and
  evidence links are recorded in the PR.
- A cloud-permission block must record service, attempted action, exact error, UTC time and a
  redacted screenshot in an issue labelled `handoff-blocker`.
- Each person adds dated entries to `docs/ai-usage.md`, stating the tool, purpose, files they
  reviewed/changed and their verification method.

## Schedule and ownership

| Date | Owner | Stage | Accepted tag |
|---|---|---|---|
| 23 Aug 2026 | Member 1 | Local end-to-end prototype and system contract | `handoff-1-local` |
| 24 Aug 2026 | Member 2 | Real AWS/GCP foundation, deployment and authentication | `handoff-2-cloud` |
| 25 Aug 2026 | Member 3 | Cloud persistence, processing and query correctness | `handoff-3-core-complete` |
| 26 Aug 2026 | Member 4 | UI integration, E2E tests and demo release candidate | `release-candidate-1` |
| 27–29 Aug 2026 | Everyone | Fixes, report, evidence and two demo rehearsals | `submission-candidate` |
| 30 Aug 2026 | Everyone | Final verification and submission | `v1.0.0` |

If a date slips, incomplete work does not silently become the next person's responsibility.
The current owner opens a `handoff-blocker` issue and ownership changes only when recorded.

## Member 1 — local prototype and architecture baseline

### Sole responsibility

- Repository structure, local developer workflow and target architecture.
- FastAPI contract and validation models for every assignment route.
- Local-only JWT, SQLite/filesystem adapters and deterministic inference mode.
- React prototype covering upload, queries, tags, deletion and subscriptions.
- Initial inference service, one-frame-per-second sampler and real-model validation path.
- Initial Terraform resource map, GitHub Actions and the handoff documents.

### Required deliverables

1. Clean private repository with no secret, Terraform state or model weight in Git.
2. README plus local, API, architecture, deployment, handoff and verification documents.
3. Passing tests, style checks, web production build and Terraform validation.
4. Local demo: login, upload, `READY`, tag/species/file/thumbnail queries, tag update,
   subscription and delete.
5. Annotated tag `handoff-1-local` on the exact accepted commit.

### Boundaries to state honestly

- SQLite and local files are development adapters, not the AWS production data path.
- Terraform is a target baseline until it has been applied under actual course permissions.
- Stub inference proves integration, not model accuracy. Real-model local verification is
  separate; private Cloud Run inference remains Member 2/3 work.

### Acceptance gate

- `uv run pytest -q` passes.
- `uv run ruff check services/api services/inference` has no findings.
- `npm ci` and `npm run build` in `web` pass.
- `terraform fmt -check`, `terraform init -backend=false`, `terraform validate` pass in `infra`.
- GitHub Actions starts successfully after push.
- `git status --short` is empty; `git ls-files "*.pt" "*.onnx" ".env"` returns nothing.

## Member 2 — live cloud foundation, deployment and authentication

Start from `handoff-1-local` and read `docs/cloud-deployment-runbook.md` before editing.

### Sole responsibility

- Confirm Learner Lab and an already-billed GCP project; never bind a card without approval.
- Make Terraform work with actual course permissions. Prefer minimum privilege; when role
  creation is denied, set `lab_role_arn` to `LabRole` and document the restriction.
- Publish API/worker images to ECR and inference/web images to Artifact Registry by digest.
- Deploy private inference Cloud Run and public web Cloud Run.
- Configure AWS-to-GCP Workload Identity Federation; no service-account JSON key is allowed.
- Configure Cognito email registration/login/logout, API Gateway JWT and exact CORS/callbacks.
- Add Amplify/Cognito login when cloud configuration exists while preserving local mode.
- Establish cloud adapters and separate API/worker entry points so the deployed system does
  not rely on Lambda-local SQLite or filesystem data.

### Required outcomes

- Cloud `/auth/dev-token` is unavailable; missing token gives 401; valid Cognito JWT works.
- Registration collects required fields and verifies email.
- Anonymous inference is denied; the federated AWS worker can invoke it.
- No long-lived GCP key exists in Git, Lambda environment or GitHub secrets.
- Authenticated upload reaches S3 and produces one SQS message. Until processing is complete,
  status stays truthfully `UPLOADED`/`PROCESSING`, never fake `READY`.

### Evidence and acceptance

- PR from `member-2/cloud-deployment`, Terraform plan summary and repeatable instructions.
- Record regions, GCP project ID, redacted AWS account, service URLs, user pool ID and image
  digests; never record tokens or presigned URL query strings.
- Screenshots: verified user, 401 and 200 calls, S3/SQS, private inference denial, federated
  inference success and public web page.
- Cost note: min instances, lifecycle rules, resources and named post-marking cleanup owner.
- Tag `handoff-2-cloud` only after Member 3 repeats login and one upload independently.

Do not change API shapes, normalisation, one-frame-per-second logic, owner permissions or
global checksum semantics without a written team decision.

## Member 3 — cloud data, processing and query correctness

Start from `handoff-2-cloud`. Turn the deployed foundation into the complete cloud backend.

### Sole responsibility

- DynamoDB production repository with the documented single-table layout.
- S3 constrained presigned uploads and atomic global checksum reservation.
- SQS worker, retries, DLQ and terminal `FAILED` state.
- Proportional thumbnails, strict video sampling and private Cloud Run inference.
- Manifest generation polling, SHA-256, label order and output dimension 46 validation.
- All query modes, ephemeral query cleanup and tag-index consistency.
- SNS subscription storage/publication where coupled to DynamoDB writes.

### Exact DynamoDB contract

- `MEDIA#{mediaId}` / `META`: owner, stable S3 URIs, checksum, type, size, tags, status,
  model version, error and timestamps.
- `CHECKSUM#{sha256}` / `LOCK`: media ID and reservation state.
- `TAG#{normalisedTag}` / `COUNT#{zeroPaddedCount}#MEDIA#{mediaId}`: count-query index.
- `THUMB#{urlHash}` / `MAP`: thumbnail-to-original mapping.
- `USER#{sub}` / `SUB#{normalisedTag}`: tag subscription.
- Owner GSI: `GSI1PK=OWNER#{sub}`, `GSI1SK={createdAt}#MEDIA#{mediaId}`.

Use DynamoDB transactions for related metadata/index changes where supported. Delete must
remove originals, thumbnail, tag rows, thumbnail map, checksum lock and metadata; repeats are
harmless.

### Acceptance gate

- Renamed duplicate returns 409 and existing media ID; four concurrent reservations create
  exactly one record and object.
- Landscape, portrait and transparent thumbnails preserve ratio and are compressed JPEG.
- A 2.4 s video samples `t=0,1,2`; invalid video becomes `FAILED`; a video's species count is
  the maximum simultaneous count across frames, never a cross-frame sum.
- `{"a":2,"b":1}` returns only media satisfying both bounds.
- File query creates no media record and deletes temporary S3 data on success and failure.
- GCP timeout/inference errors retry, reach DLQ and expose a safe error.
- Tag update/delete leaves no stale index row, proven by direct DynamoDB query evidence.

### Deliverables

- PR from `member-3/core-hardening` with unit and live integration tests.
- Redacted CloudWatch request logs, DynamoDB before/after evidence, one image and one video
  result, model version and label-dimension proof.
- Tag `handoff-3-core-complete` after Member 4 repeats the API smoke tests.

## Member 4 — UI, E2E validation and release candidate

Start from `handoff-3-core-complete`. Own the user-visible integrated system, not only report
writing.

### Sole responsibility

- Complete Amplify registration, verification, login, refresh and logout.
- Upload UI with hash progress, type/size limits, duplicate and processing/failure states.
- Media results with thumbnails/video, tags, model version and permitted owner actions.
- UI for AND/count tags, species, thumbnail reverse and query-by-file.
- Bulk tag add/remove, confirmed delete, subscriptions and clear 401/403 messages.
- Responsive loading/error/empty states and an uninterrupted demo workflow.
- Playwright critical-path tests locally and smoke tests against the deployed environment.
- Release defect triage, `docs/demo-script.md` and final evidence matrix.

### Acceptance gate

- New user registers, verifies, signs in, refreshes and signs out without DB edits.
- Unsupported/oversized/duplicate files, processing failure, 401 and 403 show specific messages.
- All four query forms work; temporary links open; reverse lookup returns the right original.
- Other users lack mutation controls, and crafted mutation still gets API 403.
- Bulk tags/deletion refresh without stale results.
- Playwright critical path passes twice consecutively; rehearsed demo has no console error.

### Deliverables

- PR from `member-4/ui-e2e`, test report and critical-path screenshots/video.
- Exact demo steps, expected outputs and fallback media in `docs/demo-script.md`.
- Updated `docs/verification-matrix.md` with evidence links.
- Tag `release-candidate-1`; Member 1 reviews and files concrete blockers or approves.

## Final shared work, 27–30 August

- Member 1 writes architecture, local-prototype rationale, API contract and coordination.
- Member 2 writes deployment, IAM/Cognito/WIF, cost and security limitations.
- Member 3 writes data model, consistency, media/ML, queries and failure handling.
- Member 4 writes UI, E2E strategy, verification evidence and demo procedure.

Each member writes and approves their own section. Final release requires: four merged stage
PRs; green CI; no `release-blocker`; clean secret/model/state scan; every verification row
executed in cloud; two demo rehearsals by different presenters; consistent report URLs; and
contribution figures backed by commits, issues, reviews and written sections. Tag the accepted
commit `v1.0.0` and record the cloud cleanup owner.

## Mandatory 20-minute handoff meeting

The outgoing member must:

1. Show exact commit/tag and clean working tree.
2. Run acceptance commands live.
3. Demonstrate the new behaviour and one failure case.
4. Review PR evidence, known limitations and blocker issues.
5. State required accounts/projects without transmitting secrets.
6. Watch the incoming member fetch the tag and reproduce the primary smoke test.
7. Record: `Accepted by <name>, <UTC time>, commit <sha>` in the PR.

If step 6 fails, the handoff remains open and ownership stays with the outgoing member.
