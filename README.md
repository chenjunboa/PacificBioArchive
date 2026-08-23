# Pacific BioArchive

FIT5225 Assignment 2 multi-cloud wildlife archive. This is the accepted **local end-to-end
prototype** plus AWS/GCP infrastructure baseline. Cloud deployment is the next team stage;
SQLite/local files must not be presented as the production AWS implementation.

## Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- Node.js 22 and npm
- Terraform 1.5+ for infrastructure checks
- Docker Desktop only for the optional Compose path

The supplied `.pt` models are intentionally excluded from Git because of their size.

## Start locally

Terminal 1, repository root:

```powershell
uv sync --extra dev
uv run uvicorn app.main:app --app-dir services/api --reload
```

Terminal 2:

```powershell
Set-Location web
npm ci
npm run dev
```

Open `http://localhost:5173` and enter a syntactically valid email. Local login receives a
development-only JWT. API documentation is at `http://localhost:8000/docs`.

Default inference derives a tag from the test filename, allowing fast upload/query/tag/delete
testing without loading roughly 493 MB of models. Real MegaDetector/SpeciesNet inference is
isolated under `services/inference`.

## Verify

```powershell
uv run pytest -q
uv run ruff check services/api services/inference
Push-Location web
npm ci
npm run build
Pop-Location
Push-Location infra
terraform fmt -check
terraform init -backend=false
terraform validate
Pop-Location
```

## Documentation

- `docs/local-development.md`: native and Docker workflows.
- `docs/api.md`: fixed HTTP contract.
- `docs/architecture.md`: target cross-cloud design.
- `docs/handoff.md`: exact four-person ownership, dates and acceptance gates.
- `docs/cloud-deployment-runbook.md`: Member 2's account/deployment procedure.
- `docs/verification-matrix.md`: requirement-by-requirement evidence ledger.
- `docs/ai-usage.md`: mandatory AI-use record.

Never commit credentials, `.env`, Terraform state, uploaded media, presigned URLs or models.
