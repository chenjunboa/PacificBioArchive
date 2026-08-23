# Local development

## Native fast path

1. Install dependencies: `uv sync --extra dev`.
2. Start the API: `uv run uvicorn app.main:app --app-dir services/api --reload`.
3. In `web`, run `npm ci` then `npm run dev`.
4. Open `http://localhost:5173` and use any syntactically valid email address.

The native path uses SQLite, local filesystem storage and deterministic filename-based
inference. No cloud account, email or credential is used.

## Docker path

Start Docker Desktop and run `docker compose up --build`. This starts:

- React UI at `http://localhost:5173`;
- API at `http://localhost:8000`;
- inference service at `http://localhost:8081`;
- LocalStack at `http://localhost:4566`.

The inference container validates video files and samples exactly one frame per second.
Set `MODEL_MODE=real` and mount a valid model manifest at `/models/manifest.json` to use
the supplied models.

The supplied classifier references `onnx2torch`. Its declared ONNX 1.12 dependency has no
Python 3.12 wheel, so the container deliberately installs current ONNX first and installs
`onnx2torch` without dependency re-resolution. This combination was verified against the
provided model and `Alectura_lathami_1.JPG`.

## Validation

Run `uv run pytest -q`, `uv run ruff check services/api`, and `npm run build` from `web`.
Local runtime state is stored under `.local-data` and is excluded from Git.
