# Member 2 cloud deployment runbook

Begin only after `handoff-1-local` is accepted. Account checks, foundation provisioning,
container publication and compute deployment are separate gates so that a permission problem
cannot be mistaken for a successful deployment.

## Inputs received from Member 1

- Repository access, accepted commit and tag.
- Fixed regions: AWS `us-east-1`, GCP `us-central1`.
- Baseline test results and known limitations in the handoff PR.
- Model filenames and SHA-256 values; weights are transferred outside Git.

Member 1 never transmits GitHub tokens, AWS keys, GCP tokens, passwords or MFA codes.

## Account gate

### AWS Academy

1. Enter FIT5225 Learner Lab from the course site, choose **Start Lab**, wait for green status,
   and open **AWS Console**.
2. Select **N. Virginia (`us-east-1`)**.
3. Record AWS account ID suffix, remaining lab time and whether `LabRole` exists.
4. Load session credentials only into the current terminal. Never paste them into Git, issues,
   chat or screenshots.
5. Confirm create permission, not just page access, for S3, DynamoDB, SQS, SNS, Lambda, API
   Gateway, Cognito and ECR.

### GCP

1. Select an existing approved project and record its name and immutable project ID.
2. Open **Billing** and confirm billing is active for that project.
3. Confirm permission to enable APIs and create Cloud Run, Storage, Artifact Registry, service
   accounts and Workload Identity Pools.
4. If there is no already-billed project, stop. Do not start a trial, bind a card or create a
   paid Billing Account without explicit owner approval.

Record `PASS`, `BLOCKED` or `NOT AVAILABLE` for each check in the PR, never a credential.

## Reproduce the baseline

```powershell
git fetch --tags origin
git switch -c member-2/cloud-deployment handoff-1-local
uv sync --extra dev
uv run pytest -q
uv run ruff check services/api services/inference
Push-Location web
npm ci
npm run build
Pop-Location
Push-Location infra
terraform init -backend=false
terraform validate
Pop-Location
```

If baseline fails, open an issue with command/error and ask Member 1 to reproduce it. Do not
silently mix prototype repair into deployment work.

## Configure without committing secrets

Copy `infra/terraform.tfvars.example` to the ignored `infra/terraform.tfvars` and set:

- `gcp_project_id`: immutable project ID;
- `aws_account_id`: current Learner Lab account ID;
- `lab_role_arn`: course `LabRole` ARN only if dedicated IAM role creation is denied;
- `deploy_compute = false` for the foundation plan;
- `notification_email` only when its owner can confirm the SNS subscription.

AWS Academy sessions expire. Refresh temporary credentials before plan/apply and verify the
account ID to avoid deploying to a personal account.

## Provision and publish in this order

1. Initialise Terraform normally, save/review a plan, and keep plan/state out of Git.
2. Apply with `deploy_compute=false` to create storage, queues, DynamoDB, Cognito, registries
   and identity foundation.
3. Read ECR and Artifact Registry destinations from Terraform outputs.
4. Build API, worker, inference and web containers from the accepted commit.
5. Tag every image with the full commit SHA, push it, and record its immutable digest.
6. Upload `labels.txt`, models and manifest to private GCS. Verify SHA-256 before and after
   upload; manifest supplies model version, label URI and hashes.
7. Set digest-pinned image URIs, change `deploy_compute=true`, review a second plan and apply.

The inference baseline expects a local manifest path. Implement a GCS download/mount/startup
path consistently; a developer-machine path is not a cloud deployment.

## Production adapter gap to close

The baseline API intentionally uses SQLite/local files. Do not deploy it unchanged. Add
configuration-selected boundaries:

- local: SQLite + local filesystem + local JWT;
- cloud API: DynamoDB + S3 presigned URL + Cognito JWT;
- worker: SQS event -> S3 object -> inference -> DynamoDB/SNS;
- separate API and worker Lambda handlers/images.

Member 2 owns deployability and these boundaries. Member 3 owns full consistency, indexes,
retries and edge cases. Any temporary incomplete cloud operation must expose an honest state
and be listed in the Member 2 PR.

## Authentication and network checks

1. Configure Cognito `given_name`, `family_name`, email, auto-verification, app client and exact
   Cloud Run callback/logout URLs.
2. Configure Amplify with environment values; do not hard-code personal users.
3. Restrict API Gateway CORS to local origins and the exact Cloud Run web origin.
4. JWT-protect every business route. Only health and approved authentication callback routes
   may be public.
5. Keep inference private and grant `roles/run.invoker` only to the federated caller identity.
6. Test WIF and an identity-token-authenticated call from the worker. Never use a downloaded
   service-account JSON key as a shortcut.

## Required handoff smoke test

With a new verified Cognito user:

1. Public web loads; registration and email verification work.
2. Missing token returns 401; valid token makes `/species` return 46 entries.
3. Upload initialisation returns a constrained presigned target.
4. Object appears under `originals/{mediaId}/...` and emits exactly one SQS message.
5. Anonymous inference is denied; the worker obtains short-lived Google identity.
6. Media moves through truthful states and reaches `READY` or a documented `FAILED`.
7. Sign-out invalidates the browser session.

Member 3 must reproduce this before accepting `handoff-2-cloud`.

## Rollback and cleanup ownership

- Keep the media bucket `force_destroy=false`.
- Inventory Terraform state and both consoles after a partial failure; list manual resources.
- Preserve redacted evidence before cleanup and target only dedicated assignment resources.
- After marking, the named cloud owner exports evidence, empties dedicated buckets, performs a
  reviewed destroy where permitted, and confirms Cloud Run/registries/subscriptions are gone.
