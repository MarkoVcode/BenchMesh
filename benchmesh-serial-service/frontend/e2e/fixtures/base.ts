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

    // Wait for activity bar to render (which requires instruments to be loaded)
    await page.waitForSelector('[data-testid="activity-bar"]', { timeout: 10000 });

    // Wait for instrument items to appear in activity bar
    // We have 2 mock instruments, so there should be activity bar items
    await page.waitForSelector('.activity-bar__instruments .activity-bar-item', { timeout: 5000 });

    // Explicitly dismiss any tutorial tooltips or modals that might be open
    try {
      const modalOverlay = page.locator('.modal-overlay');
      const isModalVisible = await modalOverlay.isVisible().catch(() => false);

      if (isModalVisible) {
        // Try to find and click "Got it" button first
        const gotItButton = page.locator('button:has-text("Got it"), button:has-text("OK")');
        const isButtonVisible = await gotItButton.isVisible().catch(() => false);

        if (isButtonVisible) {
          await gotItButton.click({ timeout: 1000 });
        } else {
          // Force close by clicking overlay
          await modalOverlay.click({ force: true, position: { x: 5, y: 5 } });
        }

        // Wait for modal to be completely hidden
        await page.waitForSelector('.modal-overlay', { state: 'hidden', timeout: 3000 }).catch(() => {
          // If it doesn't hide, try removing it with JavaScript as last resort
          page.evaluate(() => {
            const overlay = document.querySelector('.modal-overlay');
            if (overlay) overlay.remove();
          });
        });
      }
    } catch (e) {
      // If anything fails, log but don't fail the test setup
      console.log('Note: Could not dismiss modal overlay:', e);
    }

    // Give time for UI to stabilize
    await page.waitForTimeout(500);

    // Use the configured page
    await use(page);
  },
});

export { expect } from '@playwright/test';
