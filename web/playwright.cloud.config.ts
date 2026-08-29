import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  testMatch: /cloud-smoke\.spec\.ts/,
  timeout: 180_000,
  expect: { timeout: 30_000 },
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL: process.env.PBA_CLOUD_WEB_URL ?? 'http://127.0.0.1:5173',
    trace: 'on',
    video: 'on',
  },
  projects: [
    {
      name: 'cloud-chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
