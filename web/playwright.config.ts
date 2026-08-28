import { defineConfig, devices } from '@playwright/test'

const e2eDataDir = process.env.PBA_E2E_DATA_DIR ?? `../.local-e2e-data-${Date.now()}`

export default defineConfig({
  testDir: './e2e',
  testMatch: /archive\.spec\.ts/,
  timeout: 120_000,
  expect: { timeout: 15_000 },
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: `APP_ENV=local LOCAL_DATA_DIR=${e2eDataDir} LABELS_PATH=../labels.txt ../.venv/bin/python -m uvicorn app.main:app --app-dir ../services/api --host 127.0.0.1 --port 8000`,
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5173',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
})
