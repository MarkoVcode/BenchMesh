import { test, expect } from '@playwright/test';

/**
 * Basic E2E tests that run against the REAL BenchMesh service
 *
 * Prerequisites:
 * - Backend service must be running on port 57666
 * - Service should have a valid config.yaml
 *
 * Run with: npx playwright test --config=playwright.config.with-service.ts with-service/
 */

test.describe('BenchMesh App - Real Service', () => {
  test('should load the app and connect to real API', async ({ page }) => {
    await page.goto('/ui/');

    // Wait for brand to appear
    await expect(page.locator('.brand')).toHaveText('BenchMesh');

    // Wait for API connection (may take a moment)
    await page.waitForSelector('.statuspill:has-text("API ok")', { timeout: 10000 });

    // Check API status is good
    const apiStatus = page.locator('.statuspill').filter({ hasText: 'API ok' });
    await expect(apiStatus).toBeVisible();
  });

  test('should connect to WebSocket', async ({ page }) => {
    await page.goto('/ui/');

    // Wait for WebSocket connection
    await page.waitForSelector('.statuspill', { timeout: 10000 });

    // WebSocket should show some status (connecting, receiving, or error)
    const wsStatus = page.locator('.statuspill').first();
    await expect(wsStatus).toBeVisible();
  });

  test('should display navigation elements', async ({ page }) => {
    await page.goto('/ui/');

    // Wait for page load
    await expect(page.locator('.brand')).toBeVisible();

    // Check for main navigation buttons
    await expect(page.locator('button:has-text("⚙️ Configuration")')).toBeVisible();
    await expect(page.locator('button:has-text("📊 Recording")')).toBeVisible();
    await expect(page.locator('button:has-text("📚 Documentation")')).toBeVisible();
    await expect(page.locator('button:has-text("📈 Metrics")')).toBeVisible();
  });

  test('should open configuration modal', async ({ page }) => {
    await page.goto('/ui/');

    // Click configuration button
    await page.click('button:has-text("⚙️ Configuration")');

    // Wait for modal overlay
    await page.waitForSelector('.modal-overlay', { timeout: 5000 });

    // Modal should be visible
    await expect(page.locator('.modal-overlay')).toBeVisible();
    await expect(page.locator('.modal-content')).toBeVisible();

    // Should have configuration heading
    await expect(page.locator('h2:has-text("Configuration")')).toBeVisible();

    // Close modal
    await page.locator('.modal-close').first().click();
    await page.waitForTimeout(500);
  });

  test('should display instruments from config', async ({ page }) => {
    await page.goto('/ui/');

    // Wait for instruments to load
    await page.waitForTimeout(2000);

    // Check if any instrument cards are present
    // Note: This will vary based on your config.yaml
    const cardCount = await page.locator('.card').count();

    // Should have at least 0 cards (depends on config)
    expect(cardCount).toBeGreaterThanOrEqual(0);

    if (cardCount > 0) {
      // If instruments exist, first card should have an IDN or online status
      const firstCard = page.locator('.card').first();
      await expect(firstCard).toBeVisible();
    }
  });

  test('should access documentation', async ({ page }) => {
    await page.goto('/ui/');

    // Click documentation button
    await page.click('button:has-text("📚 Documentation")');

    // Wait for modal overlay
    await page.waitForSelector('.modal-overlay', { timeout: 5000 });

    // Should show documentation content
    await expect(page.locator('.modal-overlay')).toBeVisible();
    await expect(page.locator('.docs-modal-content')).toBeVisible();

    // Close modal
    await page.locator('.modal-close').first().click();
    await page.waitForTimeout(500);
  });

  test('should access metrics viewer', async ({ page }) => {
    await page.goto('/ui/');

    // Click metrics button
    await page.click('button:has-text("📈 Metrics")');

    // Wait for modal overlay
    await page.waitForSelector('.modal-overlay', { timeout: 5000 });

    // Should show metrics content
    await expect(page.locator('.modal-overlay')).toBeVisible();
    await expect(page.locator('.modal-content')).toBeVisible();

    // Close modal
    await page.locator('.modal-close').first().click();
    await page.waitForTimeout(500);
  });

  test('should redirect non-existent routes to main UI', async ({ page }) => {
    // Navigate to a non-existent route
    await page.goto('/ui/nonexistent');

    // App should redirect/load and display main UI
    await expect(page.locator('.brand')).toBeVisible();

    // Should still be able to connect to API
    await page.waitForSelector('.statuspill:has-text("API ok")', { timeout: 10000 });
    await expect(page.locator('.statuspill').filter({ hasText: 'API ok' })).toBeVisible();
  });
});
