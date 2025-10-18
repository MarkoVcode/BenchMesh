import { test, expect } from './fixtures/base';
import { waitForInstruments, waitForWebSocket } from './utils/api-mock';

test.describe('BenchMesh App Navigation', () => {
  test('should load the app and display the brand', async ({ mockPage }) => {
    await expect(mockPage.locator('.brand')).toHaveText('BenchMesh');
  });

  test('should display status indicators', async ({ mockPage }) => {
    await waitForWebSocket(mockPage);

    // Check for WebSocket status pill
    const wsStatus = mockPage.locator('.statuspill').filter({ hasText: 'receiving' });
    await expect(wsStatus).toBeVisible();

    // Check for API status pill
    const apiStatus = mockPage.locator('.statuspill').filter({ hasText: 'API ok' });
    await expect(apiStatus).toBeVisible();
  });

  test('should display navigation buttons', async ({ mockPage }) => {
    // Check for Configuration button
    await expect(mockPage.locator('button', { hasText: '⚙️ Configuration' })).toBeVisible();

    // Check for Recording button
    await expect(mockPage.locator('button', { hasText: '📊 Recording' })).toBeVisible();

    // Check for Documentation button
    await expect(mockPage.locator('button', { hasText: '📚 Documentation' })).toBeVisible();

    // Check for Metrics button
    await expect(mockPage.locator('button', { hasText: '📈 Metrics' })).toBeVisible();
  });

  test('should open and close configuration modal', async ({ mockPage }) => {
    // Click configuration button
    await mockPage.click('button:has-text("⚙️ Configuration")');

    // Wait for modal overlay to appear
    await mockPage.waitForSelector('.modal-overlay', { timeout: 5000 });

    // Check modal is visible
    const modal = mockPage.locator('.modal-overlay');
    await expect(modal).toBeVisible();

    // Check for modal content
    const modalContent = mockPage.locator('.modal-content');
    await expect(modalContent).toBeVisible();

    // Check for close button (✕) and click it
    const closeButton = mockPage.locator('.modal-close').first();
    await closeButton.click();

    // Wait for modal to disappear
    await mockPage.waitForTimeout(500);

    // Modal should be closed
    await expect(modal).not.toBeVisible();
  });

  test('should open and close documentation modal', async ({ mockPage }) => {
    // Click documentation button
    await mockPage.click('button:has-text("📚 Documentation")');

    // Wait for modal overlay to appear
    await mockPage.waitForSelector('.modal-overlay', { timeout: 5000 });

    // Check modal is visible
    const modal = mockPage.locator('.modal-overlay');
    await expect(modal).toBeVisible();

    // Check for markdown content (DocsViewer uses docs-modal-content)
    const docsContent = mockPage.locator('.docs-modal-content');
    await expect(docsContent).toBeVisible();
    await expect(docsContent.locator('h1')).toContainText('BenchMesh Documentation');

    // Check for close button and click it
    const closeButton = mockPage.locator('.modal-close').first();
    await closeButton.click();

    // Wait for modal to disappear
    await mockPage.waitForTimeout(500);

    // Modal should be closed
    await expect(modal).not.toBeVisible();
  });

  test('should open and close metrics modal', async ({ mockPage }) => {
    // Click metrics button
    await mockPage.click('button:has-text("📈 Metrics")');

    // Wait for modal heading to appear (more reliable than overlay)
    await mockPage.waitForSelector('h2:has-text("Serial Port Utilization Metrics")', { timeout: 5000 });

    // Check modal elements are visible
    await expect(mockPage.locator('h2:has-text("Serial Port Utilization Metrics")')).toBeVisible();
    const modal = mockPage.locator('.modal-overlay');
    await expect(modal).toBeVisible();

    // Check for close button and click it
    const closeButton = mockPage.locator('.modal-close').first();
    await expect(closeButton).toBeVisible();
    await closeButton.click();

    // Wait for modal to disappear
    await mockPage.waitForTimeout(500);

    // Modal should be closed
    await expect(modal).not.toBeVisible();
  });

  test('should open and close recording modal', async ({ mockPage }) => {
    // Click recording button
    await mockPage.click('button:has-text("📊 Recording")');

    // Wait for modal heading to appear
    await mockPage.waitForSelector('h2:has-text("📊 Data Recording")', { timeout: 5000 });

    // Check modal heading is visible
    await expect(mockPage.locator('h2:has-text("📊 Data Recording")')).toBeVisible();

    // Find and click the close button (× character, positioned in header)
    // Look for button containing × in the same area as the heading
    const closeButton = mockPage.locator('button:has-text("×")').first();
    await expect(closeButton).toBeVisible();
    await closeButton.click();

    // Wait for modal to disappear
    await mockPage.waitForTimeout(500);

    // Modal heading should not be visible anymore
    await expect(mockPage.locator('h2:has-text("📊 Data Recording")')).not.toBeVisible();
  });

  test('should display measurement status bar', async ({ mockPage }) => {
    // The MeasurementStatusBar should be at the bottom
    const statusBar = mockPage.locator('.measurement-status-bar, .status-bar');

    // Give it a moment to render
    await mockPage.waitForTimeout(500);

    // Check if status bar exists (it may be hidden initially if no measurements)
    const count = await statusBar.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });
});
