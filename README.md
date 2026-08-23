# Pacific BioArchive

Multi-cloud serverless wildlife media archive prototype for FIT5225 Assignment 2.

## Local quick start

```powershell
uv sync --extra dev
uv run uvicorn app.main:app --app-dir services/api --reload
```

Open `http://localhost:8000/docs`. In local mode, create a development token with
`POST /api/v1/auth/dev-token`, then use it as `Bearer <token>`.

The default local inference mode is deterministic and derives a species tag from the
test filename. It lets the entire upload/query/tag/delete workflow run without loading
the 493 MB model pair. The real model is isolated in `services/inference` and can be
enabled independently.

See `docs/local-development.md` and `docs/api.md` for the complete workflow.
