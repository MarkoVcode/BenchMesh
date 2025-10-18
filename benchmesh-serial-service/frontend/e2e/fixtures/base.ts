import { test as base, Page } from '@playwright/test';
import { setupApiMocks, setupWebSocketMock } from '../utils/api-mock';

/**
 * Extended test fixture with pre-configured API and WebSocket mocks
 */
export const test = base.extend<{ mockPage: Page }>({
  mockPage: async ({ page }, use) => {
    // Setup API mocks
    await setupApiMocks(page);

    // Setup WebSocket mock
    await setupWebSocketMock(page);

    // Navigate to the app
    await page.goto('/ui/');

    // Use the configured page
    await use(page);
  },
});

export { expect } from '@playwright/test';
