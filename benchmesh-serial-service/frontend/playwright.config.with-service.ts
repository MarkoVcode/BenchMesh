import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for BenchMesh E2E tests WITH real backend service
 * Use this when you want to test against the actual running service
 *
 * Prerequisites:
 * 1. Start the backend service: `cd benchmesh-serial-service && PYTHONPATH=src uvicorn benchmesh_service.api:app --host 0.0.0.0 --port 57666`
 * 2. Run tests: `npx playwright test --config=playwright.config.with-service.ts`
 */
export default defineConfig({
  testDir: './e2e',

  /* Run tests in files in parallel */
  fullyParallel: false, // Run sequentially when testing against real service

  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Opt out of parallel tests on CI */
  workers: 1, // Single worker when testing real service

  /* Reporter to use */
  reporter: process.env.CI ? 'dot' : 'html',

  /* Shared settings for all the projects below */
  use: {
    /* Base URL pointing to real service */
    baseURL: 'http://localhost:57666',

    /* Collect trace when retrying the failed test */
    trace: 'on-first-retry',

    /* Screenshot on failure */
    screenshot: 'only-on-failure',

    /* Video on failure */
    video: 'retain-on-failure',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* DO NOT start webServer - expect service to be running already */
  // Service should be started manually before running tests
});
