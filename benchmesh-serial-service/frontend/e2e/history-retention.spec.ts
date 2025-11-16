/**
 * E2E tests for history retention and persistence
 *
 * Tests:
 * - Request logs persist across page reload
 * - Logs older than retention period are removed
 * - Logs within retention period are kept
 * - Changing retention setting triggers cleanup
 * - 1000-entry hard limit is enforced
 */

import { test, expect } from '@playwright/test';
import { mockAPIResponses } from './utils/api-mock';

test.describe('History Retention and Persistence', () => {
  test.beforeEach(async ({ page }) => {
    // Clear localStorage before each test
    await page.goto('http://localhost:57666/ui');
    await page.evaluate(() => localStorage.clear());

    // Mock API responses
    await mockAPIResponses(page);

    await page.goto('http://localhost:57666/ui');
    await page.waitForSelector('[data-testid="workbench"]', { timeout: 10000 });
  });

  test('request logs persist across page reload', async ({ page }) => {
    // Add some test logs manually via localStorage (simulating logged requests)
    await page.evaluate(() => {
      const testLogs = [
        {
          id: 'test-1',
          timestamp: new Date().toISOString(),
          method: 'GET',
          url: '/instruments/PSU/test-1/1/voltage',
          status: 200,
          duration: 45,
        },
        {
          id: 'test-2',
          timestamp: new Date().toISOString(),
          method: 'POST',
          url: '/instruments/PSU/test-1/1/current/2.5',
          status: 200,
          duration: 52,
        },
      ];
      localStorage.setItem('benchmesh:requestLogs', JSON.stringify(testLogs));
    });

    // Reload page
    await page.reload();
    await page.waitForSelector('[data-testid="workbench"]');

    // Open bottom panel History tab
    const bottomPanelToggle = page.locator('[title="Show Bottom Panel"]');
    if (await bottomPanelToggle.isVisible()) {
      await bottomPanelToggle.click();
    }

    const historyTab = page.locator('[data-testid="bottom-panel-tab-history"]');
    await historyTab.click();

    // Verify logs are loaded and displayed
    await expect(page.getByText('GET')).toBeVisible();
    await expect(page.getByText('/instruments/PSU/test-1/1/voltage')).toBeVisible();
    await expect(page.getByText('POST')).toBeVisible();
  });

  test('logs older than retention period are removed on load', async ({ page }) => {
    // Set retention to 1 day
    await page.evaluate(() => {
      localStorage.setItem('benchmesh:historyRetentionDays', '1');
    });

    // Add test logs: one recent, one old (3 days ago)
    await page.evaluate(() => {
      const now = Date.now();
      const threeDaysAgo = now - (3 * 24 * 60 * 60 * 1000);

      const testLogs = [
        {
          id: 'recent-1',
          timestamp: new Date(now).toISOString(),
          method: 'GET',
          url: '/instruments/PSU/test-1/1/voltage',
          status: 200,
        },
        {
          id: 'old-1',
          timestamp: new Date(threeDaysAgo).toISOString(),
          method: 'POST',
          url: '/instruments/PSU/test-1/1/current/2.5',
          status: 200,
        },
      ];
      localStorage.setItem('benchmesh:requestLogs', JSON.stringify(testLogs));
    });

    // Reload page to trigger cleanup on load
    await page.reload();
    await page.waitForSelector('[data-testid="workbench"]');

    // Check localStorage - old log should be removed
    const storedLogs = await page.evaluate(() => {
      const logs = localStorage.getItem('benchmesh:requestLogs');
      return logs ? JSON.parse(logs) : [];
    });

    // Only recent log should remain
    expect(storedLogs.length).toBe(1);
    expect(storedLogs[0].id).toBe('recent-1');
  });

  test('logs within retention period are kept', async ({ page }) => {
    // Set retention to 7 days
    await page.evaluate(() => {
      localStorage.setItem('benchmesh:historyRetentionDays', '7');
    });

    // Add logs from 5 days ago (within 7 day retention)
    await page.evaluate(() => {
      const fiveDaysAgo = Date.now() - (5 * 24 * 60 * 60 * 1000);

      const testLogs = [
        {
          id: 'kept-1',
          timestamp: new Date(fiveDaysAgo).toISOString(),
          method: 'GET',
          url: '/instruments/PSU/test-1/1/voltage',
          status: 200,
        },
      ];
      localStorage.setItem('benchmesh:requestLogs', JSON.stringify(testLogs));
    });

    // Reload page
    await page.reload();
    await page.waitForSelector('[data-testid="workbench"]');

    // Check localStorage - log should still be there
    const storedLogs = await page.evaluate(() => {
      const logs = localStorage.getItem('benchmesh:requestLogs');
      return logs ? JSON.parse(logs) : [];
    });

    expect(storedLogs.length).toBe(1);
    expect(storedLogs[0].id).toBe('kept-1');
  });

  test('changing retention from 7 days to 1 day removes old logs', async ({ page }) => {
    // Set initial retention to 7 days
    await page.evaluate(() => {
      localStorage.setItem('benchmesh:historyRetentionDays', '7');
    });

    // Add logs: one recent (12 hours), one old (3 days ago)
    await page.evaluate(() => {
      const now = Date.now();
      const twelveHoursAgo = now - (12 * 60 * 60 * 1000);
      const threeDaysAgo = now - (3 * 24 * 60 * 60 * 1000);

      const testLogs = [
        {
          id: 'recent-1',
          timestamp: new Date(twelveHoursAgo).toISOString(),
          method: 'GET',
          url: '/instruments/PSU/test-1/1/voltage',
          status: 200,
        },
        {
          id: 'old-1',
          timestamp: new Date(threeDaysAgo).toISOString(),
          method: 'POST',
          url: '/instruments/PSU/test-1/1/current/2.5',
          status: 200,
        },
      ];
      localStorage.setItem('benchmesh:requestLogs', JSON.stringify(testLogs));
    });

    // Reload page
    await page.reload();
    await page.waitForSelector('[data-testid="workbench"]');

    // Both logs should be loaded (within 7 days)
    let storedLogs = await page.evaluate(() => {
      const logs = localStorage.getItem('benchmesh:requestLogs');
      return logs ? JSON.parse(logs) : [];
    });
    expect(storedLogs.length).toBe(2);

    // Open settings and change retention to 1 day
    await page.locator('[data-testid="activity-bar-view-settings"]').click();
    const dropdown = page.locator('[data-testid="history-retention-dropdown"]');
    await dropdown.selectOption('1');

    // Wait a moment for cleanup event to process
    await page.waitForTimeout(500);

    // Check localStorage - old log (3 days) should be removed
    storedLogs = await page.evaluate(() => {
      const logs = localStorage.getItem('benchmesh:requestLogs');
      return logs ? JSON.parse(logs) : [];
    });

    expect(storedLogs.length).toBe(1);
    expect(storedLogs[0].id).toBe('recent-1');
  });

  test('enforces 1000-entry hard limit', async ({ page }) => {
    // Add 1005 test logs
    await page.evaluate(() => {
      const now = Date.now();
      const testLogs = Array.from({ length: 1005 }, (_, i) => ({
        id: `log-${i}`,
        timestamp: new Date(now - i * 1000).toISOString(), // 1 second apart
        method: 'GET',
        url: `/test/${i}`,
        status: 200,
      }));
      localStorage.setItem('benchmesh:requestLogs', JSON.stringify(testLogs));
    });

    // Reload page to trigger load with hard limit
    await page.reload();
    await page.waitForSelector('[data-testid="workbench"]');

    // Check localStorage - should be capped at 1000
    const storedLogs = await page.evaluate(() => {
      const logs = localStorage.getItem('benchmesh:requestLogs');
      return logs ? JSON.parse(logs) : [];
    });

    expect(storedLogs.length).toBeLessThanOrEqual(1000);
  });

  test('persists new logs to localStorage automatically', async ({ page }) => {
    // Clear any existing logs
    await page.evaluate(() => {
      localStorage.removeItem('benchmesh:requestLogs');
    });

    // The page will have empty logs initially
    // In a real scenario, making API requests would add logs
    // For this test, we'll verify the storage mechanism is set up

    const logsExist = await page.evaluate(() => {
      // Check if logs key exists (may be empty array)
      const logs = localStorage.getItem('benchmesh:requestLogs');
      return logs !== null;
    });

    // After page load, logs storage should be initialized (even if empty)
    expect(logsExist).toBe(true);
  });

  test('clear logs button removes all logs from localStorage', async ({ page }) => {
    // Add some test logs
    await page.evaluate(() => {
      const testLogs = [
        {
          id: 'test-1',
          timestamp: new Date().toISOString(),
          method: 'GET',
          url: '/test',
          status: 200,
        },
      ];
      localStorage.setItem('benchmesh:requestLogs', JSON.stringify(testLogs));
    });

    // Reload and open history panel
    await page.reload();
    await page.waitForSelector('[data-testid="workbench"]');

    const bottomPanelToggle = page.locator('[title="Show Bottom Panel"]');
    if (await bottomPanelToggle.isVisible()) {
      await bottomPanelToggle.click();
    }

    const historyTab = page.locator('[data-testid="bottom-panel-tab-history"]');
    await historyTab.click();

    // Click clear logs button
    const clearButton = page.locator('button:has-text("Clear All")');
    await clearButton.click();

    // Wait a moment for state update and localStorage save
    await page.waitForTimeout(300);

    // Verify localStorage is cleared
    const storedLogs = await page.evaluate(() => {
      const logs = localStorage.getItem('benchmesh:requestLogs');
      return logs ? JSON.parse(logs) : [];
    });

    expect(storedLogs.length).toBe(0);
  });
});
