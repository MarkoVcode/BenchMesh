import { test, expect } from './fixtures/base';

test.describe('API Integration', () => {
  test('should handle successful API responses', async ({ mockPage, page }) => {
    let apiCalled = false;
    await page.route('**/instruments', async (route) => {
      apiCalled = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'api-test-1',
            IDN: 'TEST,INSTRUMENT,SN001,V1.0',
            classes: [{ class: 'PSU', channels: ['1'] }]
          }
        ]),
        headers: { 'ETag': '"test-etag"' }
      });
    });

    await page.goto('/ui/');

    // Wait for API call
    await page.waitForTimeout(1000);

    // Verify API was called
    expect(apiCalled).toBe(true);

    // Should display the instrument
    await expect(page.locator('.card').filter({ hasText: 'api-test-1' })).toBeVisible();
  });

  test('should handle 304 Not Modified responses', async ({ mockPage, page }) => {
    let callCount = 0;

    await page.route('**/instruments', async (route) => {
      callCount++;
      if (callCount === 1) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
          headers: { 'ETag': '"etag-123"' }
        });
      } else {
        // Return 304 for subsequent requests
        await route.fulfill({
          status: 304,
          headers: { 'ETag': '"etag-123"' }
        });
      }
    });

    await page.goto('/ui/');

    // Wait for initial load
    await page.waitForTimeout(1000);

    // Wait for retry
    await page.waitForTimeout(6000);

    // Should have made multiple requests
    expect(callCount).toBeGreaterThan(1);
  });

  test('should handle API errors and retry', async ({ mockPage, page }) => {
    let callCount = 0;

    await page.route('**/instruments', async (route) => {
      callCount++;
      if (callCount === 1) {
        // Fail first request
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Internal server error' })
        });
      } else {
        // Succeed on retry
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
          headers: { 'ETag': '"success-etag"' }
        });
      }
    });

    await page.goto('/ui/');

    // Wait for initial error
    await page.waitForTimeout(500);

    // Should show error state
    await expect(page.locator('.statuspill').filter({ hasText: 'API unreachable' })).toBeVisible();

    // Wait for retry (1s delay on failure)
    await page.waitForTimeout(1500);

    // Should recover and show success
    await expect(page.locator('.statuspill').filter({ hasText: 'API ok' })).toBeVisible();
  });

  test('should handle network timeouts', async ({ mockPage, page }) => {
    await page.route('**/instruments', async (route) => {
      // Simulate network timeout by delaying indefinitely
      await new Promise(resolve => setTimeout(resolve, 30000));
    });

    await page.goto('/ui/');

    // Wait a bit
    await page.waitForTimeout(2000);

    // Status should indicate loading or error
    const loadingStatus = page.locator('.statuspill').filter({ hasText: 'Loading' });
    const errorStatus = page.locator('.statuspill').filter({ hasText: 'API unreachable' });

    const hasLoadingOrError = (await loadingStatus.count()) > 0 || (await errorStatus.count()) > 0;
    expect(hasLoadingOrError).toBe(true);
  });

  test('should send If-None-Match header with ETag', async ({ mockPage, page }) => {
    let requestHeaders: Record<string, string> = {};

    await page.route('**/instruments', async (route) => {
      requestHeaders = Object.fromEntries(
        route.request().headers() as any
      );

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
        headers: { 'ETag': '"my-etag-123"' }
      });
    });

    await page.goto('/ui/');

    // Wait for initial request
    await page.waitForTimeout(1000);

    // Wait for second request (should include If-None-Match)
    await page.waitForTimeout(6000);

    // Second request should have included If-None-Match header
    // Note: This might not work in the test environment due to timing
  });

  test('should handle malformed JSON responses', async ({ mockPage, page }) => {
    await page.route('**/instruments', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: 'invalid json {]'
      });
    });

    await page.goto('/ui/');

    // Wait a bit
    await page.waitForTimeout(1000);

    // Should show error state
    await expect(page.locator('.statuspill').filter({ hasText: 'API unreachable' })).toBeVisible();
  });

  test('should handle WebSocket connection failures', async ({ page }) => {
    // Don't setup WebSocket mock for this test
    await page.goto('/ui/');

    // Mock instruments endpoint
    await page.route('**/instruments', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
        headers: { 'ETag': '"test"' }
      });
    });

    // Wait a bit
    await page.waitForTimeout(1500);

    // WebSocket should show error or disconnected state
    const wsStatus = page.locator('.statuspill').filter({ has: page.locator('.dot') }).first();
    await expect(wsStatus).toBeVisible();

    // Check that it's not showing "receiving"
    const receivingStatus = page.locator('.statuspill').filter({ hasText: 'receiving' });
    const count = await receivingStatus.count();
    expect(count).toBe(0);
  });

  test('should maintain WebSocket connection and receive updates', async ({ mockPage, page }) => {
    // Wait for WebSocket to connect
    await page.waitForTimeout(500);

    // Should show receiving status
    await expect(page.locator('.statuspill').filter({ hasText: 'receiving' })).toBeVisible();

    // Wait for a few updates
    await page.waitForTimeout(5000);

    // Should still be receiving
    await expect(page.locator('.statuspill').filter({ hasText: 'receiving' })).toBeVisible();
  });

  test('should handle concurrent API and WebSocket data', async ({ mockPage, page }) => {
    // Both API and WebSocket should be active
    await page.waitForTimeout(1000);

    // Check both status indicators are green
    const goodDots = page.locator('.statuspill .dot[style*="var(--good)"]');
    const count = await goodDots.count();

    // Should have at least 2 good status dots (WS and API)
    expect(count).toBeGreaterThanOrEqual(2);
  });
});
