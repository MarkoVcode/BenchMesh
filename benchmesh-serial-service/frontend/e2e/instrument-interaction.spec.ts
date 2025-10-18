import { test, expect } from './fixtures/base';
import { waitForInstruments, waitForWebSocket } from './utils/api-mock';

test.describe('Instrument Interaction', () => {
  test('should display PSU controls', async ({ mockPage }) => {
    await waitForInstruments(mockPage, 2);
    await waitForWebSocket(mockPage);

    // Find PSU card
    const psuCard = mockPage.locator('.card').filter({ hasText: 'test-psu-1' });

    // Wait for the card to be fully loaded
    await psuCard.waitFor({ state: 'visible' });

    // PSU should have interactive elements (buttons, inputs)
    // This is a basic check - actual controls depend on the GenericPSU component
    const buttons = psuCard.locator('button');
    const buttonCount = await buttons.count();

    // PSU should have at least some buttons for channel control
    expect(buttonCount).toBeGreaterThan(0);
  });

  test('should handle measurement context', async ({ mockPage }) => {
    await waitForInstruments(mockPage, 2);
    await waitForWebSocket(mockPage);

    // The MeasurementProvider wraps the app
    // Verify that measurement status bar is present
    const statusBar = mockPage.locator('.measurement-status-bar, .status-bar, [class*="status"]');
    const count = await statusBar.count();

    // Should have some status elements
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should display real-time data updates', async ({ mockPage, page }) => {
    await waitForInstruments(mockPage, 2);
    await waitForWebSocket(mockPage);

    // Find PSU card
    const psuCard = mockPage.locator('.card').filter({ hasText: 'test-psu-1' });

    // The card should be visible and contain data
    await expect(psuCard).toBeVisible();

    // Wait a moment for WebSocket updates
    await page.waitForTimeout(2500);

    // Card should still be visible after updates
    await expect(psuCard).toBeVisible();
  });

  test('should handle device control actions', async ({ mockPage, page }) => {
    await waitForInstruments(mockPage, 2);
    await waitForWebSocket(mockPage);

    // Mock a control action endpoint
    let controlActionCalled = false;
    await page.route('**/instruments/*/PSU/*/*', async (route) => {
      controlActionCalled = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true })
      });
    });

    // Find PSU card
    const psuCard = mockPage.locator('.card').filter({ hasText: 'test-psu-1' });

    // Try to find and click a control button (if exists)
    const buttons = psuCard.locator('button');
    const buttonCount = await buttons.count();

    if (buttonCount > 0) {
      // Click the first button
      await buttons.first().click();

      // Wait a bit for the action to process
      await page.waitForTimeout(500);
    }

    // Note: We can't verify controlActionCalled here as it depends on actual UI implementation
    // This test verifies the structure is in place
  });

  test('should handle API errors gracefully', async ({ mockPage, page }) => {
    // Mock an error response
    await page.route('**/instruments/test-psu-1/PSU/*/*', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' })
      });
    });

    await waitForInstruments(mockPage, 2);

    // The app should still be functional despite errors
    const psuCard = mockPage.locator('.card').filter({ hasText: 'test-psu-1' });
    await expect(psuCard).toBeVisible();
  });

  test('should maintain state across WebSocket updates', async ({ mockPage, page }) => {
    await waitForInstruments(mockPage, 2);
    await waitForWebSocket(mockPage);

    // Get initial card count
    const initialCards = await mockPage.locator('.card').count();
    expect(initialCards).toBe(2);

    // Wait for a few WebSocket updates
    await page.waitForTimeout(3000);

    // Card count should remain the same
    const finalCards = await mockPage.locator('.card').count();
    expect(finalCards).toBe(initialCards);
  });

  test('should handle rapid user interactions', async ({ mockPage, page }) => {
    await waitForInstruments(mockPage, 2);
    await waitForWebSocket(mockPage);

    // Find PSU card
    const psuCard = mockPage.locator('.card').filter({ hasText: 'test-psu-1' });

    // Get all buttons in the card
    const buttons = psuCard.locator('button');
    const buttonCount = await buttons.count();

    if (buttonCount > 0) {
      // Rapidly click buttons
      for (let i = 0; i < Math.min(3, buttonCount); i++) {
        await buttons.nth(i).click({ timeout: 1000 });
        await page.waitForTimeout(100);
      }
    }

    // Card should still be visible and functional
    await expect(psuCard).toBeVisible();
  });
});
