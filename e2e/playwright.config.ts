import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testIgnore: ['**/setup/**', '**/global-*.ts'],
  timeout: 30000,
  expect: { timeout: 5000 },
  fullyParallel: false,
  retries: 0,
  reporter: 'list',
  // globalSetup/globalTeardown intentionally omitted — test.sh handles
  // test data lifecycle (python3 backend/test_setup.py create/destroy)
  // before launching the UI. Re-add them only for headless CI runs.
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    headless: true,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // Do NOT auto-start dev server — run manually: cd frontend && npm run dev
});
