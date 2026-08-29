import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { resolve } from 'node:path'

const repositoryRoot = resolve(import.meta.dirname, '..', '..')
const pythonCandidates = process.platform === 'win32'
  ? [resolve(repositoryRoot, '.venv', 'Scripts', 'python.exe')]
  : [resolve(repositoryRoot, '.venv', 'bin', 'python'), 'python3']
const python = pythonCandidates.find(candidate => candidate === 'python3' || existsSync(candidate))

if (!python) {
  throw new Error('Python virtual environment not found. Run `uv sync --extra dev` first.')
}

const child = spawn(
  python,
  [
    '-m',
    'uvicorn',
    'app.main:app',
    '--app-dir',
    resolve(repositoryRoot, 'services', 'api'),
    '--host',
    '127.0.0.1',
    '--port',
    '8000',
  ],
  {
    cwd: repositoryRoot,
    env: {
      ...process.env,
      APP_ENV: 'local',
      LOCAL_DATA_DIR: process.env.PBA_E2E_DATA_DIR
        ?? resolve(repositoryRoot, `.local-e2e-data-${Date.now()}`),
      LABELS_PATH: resolve(repositoryRoot, 'labels.txt'),
    },
    stdio: 'inherit',
  },
)

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => child.kill(signal))
}

child.on('exit', code => process.exit(code ?? 0))
