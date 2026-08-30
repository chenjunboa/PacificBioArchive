# Pacific BioArchive

Pacific BioArchive is a multi-cloud, serverless wildlife media platform developed for FIT5225 Assignment 2. Authenticated users can upload images and videos, automatically identify wildlife species, search the shared archive, manage tags, delete their own media, and subscribe to tag-based email notifications.

The production solution combines AWS and Google Cloud. AWS provides authentication, API, storage, event processing, metadata, and notifications; Google Cloud hosts the private ML inference service and the public React web application.

> This is a private academic repository. Do not redistribute the source code, reports, credentials, model files, or deployment details.

## Live Application

- Web application: <https://pacific-bioarchive-prototype-web-k5t5pat3lq-uc.a.run.app/>
- Region: AWS `us-east-1` and Google Cloud `us-central1`
- Access: a verified Cognito account is required for all application features

The Cloud Run frontend is publicly reachable, while the inference service remains private. AWS Lambda invokes inference through Workload Identity Federation, so no long-lived Google Cloud service-account key is stored in the application.

## Architecture

![Pacific BioArchive multi-cloud architecture](docs/assets/architecture/pacific-bioarchive-architecture.png)

The editable SVG and official icon sources are available in [`docs/assets/architecture/`](docs/assets/architecture/).

### Processing flow

1. The browser calculates a SHA-256 checksum and requests an upload reservation.
2. The API performs a conditional DynamoDB write to prevent duplicate uploads.
3. The browser uploads the media directly to S3 using a short-lived presigned request.
4. An S3 event is delivered through SQS to the worker Lambda.
5. Images receive aspect-ratio-preserving JPEG thumbnails; videos are sampled at exactly one frame per second.
6. The worker calls the private Cloud Run inference service for animal detection and species classification.
7. Metadata, tag counts, ownership, thumbnail mappings, and processing status are stored in DynamoDB.
8. Matching SNS subscriptions are notified when watched tags are added or updated.

Failed queue messages are retried and can be moved to a dead-letter queue. Temporary query uploads are deleted after execution and are never added to the media archive.

## Features

- Cognito sign-up, email verification, sign-in, sign-out, and JWT-protected APIs
- Checksum-based global upload deduplication, including concurrent upload protection
- JPG, JPEG, PNG, MP4, and MOV handling
- Image thumbnail generation and one-frame-per-second video sampling
- Versioned ML model loading through an external manifest
- Multi-tag AND queries with minimum species counts
- Species-only search
- Thumbnail-to-original reverse lookup
- Query-by-file without permanent storage
- Bulk tag addition and removal
- Idempotent media deletion with ownership enforcement
- Tag-based SNS email subscriptions
- Responsive React UI for upload, search, media management, and notifications

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Vite, AWS Amplify Auth |
| AWS | Cognito, API Gateway, Lambda, S3, SQS/DLQ, DynamoDB, SNS, ECR |
| Google Cloud | Cloud Run, Cloud Storage, Artifact Registry, Workload Identity Federation |
| Backend | Python 3.12, FastAPI, Pydantic, Boto3 |
| ML | MegaDetector and SpeciesNet-compatible inference pipeline |
| Infrastructure | Terraform |
| Local development | Docker Compose and a local-only JWT issuer |
| Quality | Pytest, Ruff, Playwright, GitHub Actions |

## Repository Layout

```text
.
├── services/
│   ├── api/          # FastAPI application and Lambda entry point
│   ├── worker/       # SQS media-processing worker
│   └── inference/    # Cloud Run inference service
├── web/              # React and TypeScript frontend
├── infra/            # AWS and Google Cloud Terraform
├── scripts/          # Model bundle preparation utilities
├── docs/             # Handoffs, evidence, demo guide, and report sources
├── output/final/     # Submission-ready PDF and DOCX reports
├── docker-compose.yml
├── labels.txt        # Authoritative 46-species label order
└── model-manifest.json
```

## Local Quick Start

### Prerequisites

- Docker Desktop with Docker Compose
- Alternatively: Python `3.12`, Node.js `22`, and `uv`

### Run the complete local stack

```bash
docker compose up --build
```

Then open:

- Web UI: <http://localhost:5173>
- API documentation: <http://localhost:8000/docs>
- API health check: <http://localhost:8000/health>

Local mode accepts a valid email format and issues a development JWT. This issuer is available only when `APP_ENV=local`; the cloud deployment uses Cognito and does not expose the development token endpoint.

The default Compose configuration uses deterministic stub inference so the complete workflow can be tested without downloading large model weights or using cloud resources.

### Stop the stack

```bash
docker compose down
```

Use `docker compose down -v` only when local development data may be permanently removed.

## Development and Testing

### Backend

```bash
uv sync --extra dev
uv run ruff check services/api services/inference services/worker
uv run pytest -q
```

### Frontend

```bash
cd web
npm ci
npm run build
npm run test:e2e
```

GitHub Actions runs backend linting and tests, the frontend production build, Playwright end-to-end tests, and container builds on pushes and pull requests. The latest `main` workflow completed successfully.

## API Summary

All routes below use the `/api/v1` prefix. Except for the health check and the local-only development token route, cloud business endpoints require a valid Cognito JWT.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/uploads/init` | Reserve a deduplicated upload and return a presigned request |
| `GET` | `/media/{mediaId}` | Return processing status, tags, and temporary media URLs |
| `POST` | `/queries/tags` | Query multiple tags using AND and minimum counts |
| `POST` | `/queries/species` | Query a species with a minimum count of one |
| `POST` | `/queries/thumbnail` | Resolve a thumbnail to its original image |
| `POST` | `/queries/file/init` | Reserve a temporary query upload |
| `POST` | `/queries/file/{queryId}/execute` | Detect query-file tags and find matching archive items |
| `POST` | `/tags/bulk` | Add or remove tags from multiple owned media items |
| `DELETE` | `/media` | Delete owned originals, thumbnails, indexes, and records |
| `POST` | `/subscriptions` | Subscribe an email address to a normalized tag |
| `DELETE` | `/subscriptions/{tag}` | Remove a tag subscription |
| `GET` | `/species` | Return the supported species list |

Tags are normalized using Unicode NFC, lowercasing, trimming, and replacement of whitespace or hyphens with underscores. Empty tags and tags longer than 64 characters are rejected. Authenticated users may query the shared archive, but only an uploader may change tags or delete that uploader's media.

## Deployment

Terraform definitions for AWS and Google Cloud are stored in [`infra/`](infra/). The detailed deployment and handoff instructions are intentionally kept in the private documentation:

- [`docs/member-2-deployment-runbook.md`](docs/member-2-deployment-runbook.md)
- [`docs/member-2-delivery.md`](docs/member-2-delivery.md)
- [`docs/final-submission-readiness.md`](docs/final-submission-readiness.md)

Do not apply Terraform without confirming the active AWS account, Google Cloud project, billing status, regions, resource names, and cleanup responsibility. Never commit `.env` files, Terraform state, passwords, MFA codes, JWTs, cloud tokens, presigned URLs, or unredacted subscription links.

## Validation Status

The final cloud validation includes:

- two live image workflows from Cognito sign-in through upload, S3, SQS, Lambda, private GCP inference, search, reverse thumbnail lookup, deletion, and sign-out;
- one live three-second MP4 workflow through upload, processing, inference, search, deletion, and sign-out;
- DynamoDB cleanup checks with no remaining records for deleted smoke-test media;
- an empty media dead-letter queue after the successful runs;
- a confirmed SNS email subscription; and
- successful backend, web, E2E, and container CI jobs.

Detailed, redacted evidence is indexed in [`docs/cloud-smoke-evidence.md`](docs/cloud-smoke-evidence.md) and [`docs/evidence/member-4/`](docs/evidence/member-4/).

## Team Contributions

| Member | Student ID | Primary responsibility |
|---|---:|---|
| Junbo Chen | 36970271 | Local prototype, API baseline, React UI, inference scaffold, Terraform skeleton, repository structure, and initial validation |
| Bingyi Wang | 36668397 | AWS/GCP deployment, Cognito, API Gateway, Lambda images, S3, SQS/DLQ, DynamoDB, SNS, Cloud Run, model bundle, and WIF |
| Duo Chen | 36668222 | S3-to-SQS worker integration, Lambda fallback, media processing, and backend data/query/delete planning |
| Bo Pang | 36969842 | Final UI and cloud integration, tag/thumbnail index stabilization, E2E and cloud smoke testing, notifications, evidence, and reports |

All four members contributed through their own repository identities. The formal contribution percentages and assessed project elements are recorded in the final team report.

## Reports and Demonstration

- [Final team report](output/final/Pacific-BioArchive-Team-Report.pdf)
- [Member 1 individual report](output/final/Junbo-Chen-Individual-Report.pdf)
- [Member 4 individual report](output/final/Bo-Pang-Individual-Report.pdf)
- [Demonstration script](docs/demo-script.md)

The system demonstration is a mandatory assessment component. Every team member must attend and be able to explain the architecture, implementation decisions, individual contribution, and relevant failure handling.

## Academic Integrity and AI Disclosure

Generative AI was used selectively for planning, implementation assistance, testing support, documentation, and review. All generated suggestions were inspected, adapted, and validated by team members. The detailed usage record is maintained in [`docs/ai-usage-zh.md`](docs/ai-usage-zh.md), and the required disclosure is included in the final reports.

## Release State

- `handoff-1-local`: reviewed local prototype handoff
- `handoff-2-cloud`: cloud deployment handoff
- `release-candidate-1`: reviewed release candidate with successful CI
- `v1.0.0`: reserved for final approval by all team members
