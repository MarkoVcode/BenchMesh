import { test, expect } from './fixtures/base';
import { waitForInstruments, waitForWebSocket } from './utils/api-mock';

test.describe('Instrument Display', () => {
  test('should display instrument cards', async ({ mockPage }) => {
    await waitForInstruments(mockPage, 2);

    // Should have 2 instrument cards
    const cards = mockPage.locator('.card');
    await expect(cards).toHaveCount(2);
  });

  test('should display instrument IDs', async ({ mockPage }) => {
    await waitForInstruments(mockPage, 2);

    // Check for PSU card
    const psuCard = mockPage.locator('.card').filter({ hasText: 'test-psu-1' });
    await expect(psuCard).toBeVisible();

    // Check for DMM card
    const dmmCard = mockPage.locator('.card').filter({ hasText: 'test-dmm-1' });
    await expect(dmmCard).toBeVisible();
  });

  test('should display instrument IDN information', async ({ mockPage }) => {
    await waitForInstruments(mockPage, 2);
    await waitForWebSocket(mockPage);

    // Check PSU IDN
    const psuCard = mockPage.locator('.card').filter({ hasText: 'test-psu-1' });
    await expect(psuCard.locator('.card-idn')).toContainText('TENMA,72-2540');

    // Check DMM IDN
    const dmmCard = mockPage.locator('.card').filter({ hasText: 'test-dmm-1' });
    await expect(dmmCard.locator('.card-idn')).toContainText('OWON,XDM1041');
  });

  test('should show online status for connected devices', async ({ mockPage }) => {
    await waitForInstruments(mockPage, 2);
    await waitForWebSocket(mockPage);

    // Check for online status indicators
    const onlineIndicators = mockPage.locator('.wsdiag').filter({ hasText: 'online' });
    await expect(onlineIndicators).toHaveCount(2);
  });

  test('should display PSU with channels', async ({ mockPage }) => {
    await waitForInstruments(mockPage, 2);

    // Find PSU card
    const psuCard = mockPage.locator('.card').filter({ hasText: 'test-psu-1' });

    // Check that it has class information
    await expect(psuCard.locator('.card-classes')).toBeVisible();
  });

  test('should display DMM with measurement capability', async ({ mockPage }) => {
    await waitForInstruments(mockPage, 2);

    // Find DMM card
    const dmmCard = mockPage.locator('.card').filter({ hasText: 'test-dmm-1' });

    // Check that it has class information
    await expect(dmmCard.locator('.card-classes')).toBeVisible();
  });

  test('should handle empty instrument list gracefully', async ({ mockPage, page }) => {
    // Override the mock to return empty instruments
    await page.route('**/instruments', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
        headers: {
          'ETag': '"empty-etag"'
        }
      });
    });

    // Reload page
    await page.goto('/ui/');

    // Wait a bit for the app to load
    await page.waitForTimeout(1000);

    // Should not have any instrument cards
    const cards = page.locator('.card');
    await expect(cards).toHaveCount(0);

    // Should still show status indicators
    await expect(page.locator('.statuspill').filter({ hasText: 'API ok' })).toBeVisible();
  });
});
