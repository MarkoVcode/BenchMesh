/**
 * E2E tests for Settings view functionality
 *
 * Tests:
 * - Settings view opens when clicking settings icon
 * - Tab switching between Instruments and Miscellaneous
 * - History retention dropdown functionality
 * - Settings persistence across page reload
 */

import { test, expect } from '@playwright/test';
import { mockAPIResponses } from './utils/api-mock';

test.describe('Settings View', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API responses
    await mockAPIResponses(page);

    // Navigate to workbench UI
    await page.goto('http://localhost:57666/ui');
    await page.waitForSelector('[data-testid="workbench"]', { timeout: 10000 });
  });

  test('opens Settings view when clicking settings icon in ActivityBar', async ({ page }) => {
    // Click settings icon in ActivityBar
    const settingsIcon = page.locator('[data-testid="activity-bar-view-settings"]');
    await expect(settingsIcon).toBeVisible();
    await settingsIcon.click();

    // Verify sidebar opens with Settings view
    await expect(page.locator('[data-testid="sidebar"]')).toBeVisible();
    await expect(page.locator('[data-testid="settings-view"]')).toBeVisible();

    // Verify sidebar title
    const sidebarTitle = page.locator('.sidebar__title');
    await expect(sidebarTitle).toHaveText('Settings');
  });

  test('defaults to Miscellaneous tab on open', async ({ page }) => {
    // Open settings
    await page.locator('[data-testid="activity-bar-view-settings"]').click();
    await expect(page.locator('[data-testid="settings-view"]')).toBeVisible();

    // Verify Miscellaneous tab is active by default
    const miscTab = page.locator('[data-testid="settings-tab-miscellaneous"]');
    await expect(miscTab).toHaveClass(/settings-view__tab--active/);

    // Verify Miscellaneous content is visible
    await expect(page.locator('.settings-view__sections')).toBeVisible();
    await expect(page.getByText('History & Logs')).toBeVisible();
  });

  test('switches between Instruments and Miscellaneous tabs', async ({ page }) => {
    // Open settings
    await page.locator('[data-testid="activity-bar-view-settings"]').click();

    // Click Instruments tab
    const instrumentsTab = page.locator('[data-testid="settings-tab-instruments"]');
    await instrumentsTab.click();

    // Verify Instruments tab is active
    await expect(instrumentsTab).toHaveClass(/settings-view__tab--active/);

    // Verify Instruments placeholder content
    await expect(page.getByText('Instrument configuration - Coming soon')).toBeVisible();

    // Switch back to Miscellaneous
    const miscTab = page.locator('[data-testid="settings-tab-miscellaneous"]');
    await miscTab.click();

    // Verify Miscellaneous tab is active
    await expect(miscTab).toHaveClass(/settings-view__tab--active/);
    await expect(page.getByText('History & Logs')).toBeVisible();
  });

  test('displays history retention dropdown with all options', async ({ page }) => {
    // Open settings
    await page.locator('[data-testid="activity-bar-view-settings"]').click();

    // Verify dropdown exists
    const dropdown = page.locator('[data-testid="history-retention-dropdown"]');
    await expect(dropdown).toBeVisible();

    // Verify all options are available
    const options = await dropdown.locator('option').allTextContents();
    expect(options).toEqual(['1 day', '3 days', '5 days', '7 days']);
  });

  test('defaults to 3 days retention', async ({ page }) => {
    // Clear localStorage to ensure fresh state
    await page.evaluate(() => localStorage.clear());

    // Open settings
    await page.goto('http://localhost:57666/ui');
    await page.waitForSelector('[data-testid="workbench"]');
    await page.locator('[data-testid="activity-bar-view-settings"]').click();

    // Verify default value
    const dropdown = page.locator('[data-testid="history-retention-dropdown"]');
    await expect(dropdown).toHaveValue('3');
  });

  test('changes history retention setting', async ({ page }) => {
    // Open settings
    await page.locator('[data-testid="activity-bar-view-settings"]').click();

    // Change retention to 7 days
    const dropdown = page.locator('[data-testid="history-retention-dropdown"]');
    await dropdown.selectOption('7');

    // Verify selection changed
    await expect(dropdown).toHaveValue('7');

    // Verify description text updates
    await expect(page.getByText(/7 days will be automatically removed/)).toBeVisible();
  });

  test('persists retention setting to localStorage', async ({ page }) => {
    // Open settings
    await page.locator('[data-testid="activity-bar-view-settings"]').click();

    // Change retention to 5 days
    const dropdown = page.locator('[data-testid="history-retention-dropdown"]');
    await dropdown.selectOption('5');

    // Verify localStorage was updated
    const storedValue = await page.evaluate(() =>
      localStorage.getItem('benchmesh:historyRetentionDays')
    );
    expect(storedValue).toBe('5');
  });

  test('loads retention setting from localStorage on mount', async ({ page }) => {
    // Set retention in localStorage before page load
    await page.evaluate(() => {
      localStorage.setItem('benchmesh:historyRetentionDays', '7');
    });

    // Reload page
    await page.goto('http://localhost:57666/ui');
    await page.waitForSelector('[data-testid="workbench"]');
    await page.locator('[data-testid="activity-bar-view-settings"]').click();

    // Verify dropdown shows stored value
    const dropdown = page.locator('[data-testid="history-retention-dropdown"]');
    await expect(dropdown).toHaveValue('7');
  });

  test('closes Settings view when clicking close button', async ({ page }) => {
    // Open settings
    await page.locator('[data-testid="activity-bar-view-settings"]').click();
    await expect(page.locator('[data-testid="settings-view"]')).toBeVisible();

    // Click close button
    const closeButton = page.locator('.sidebar__close');
    await closeButton.click();

    // Verify sidebar is closed
    await expect(page.locator('[data-testid="sidebar"]')).not.toBeVisible();
  });
});
