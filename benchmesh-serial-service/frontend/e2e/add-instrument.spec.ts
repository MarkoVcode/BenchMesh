/**
 * E2E tests for Add Instrument functionality
 *
 * Tests the complete flow of adding a new instrument:
 * 1. Click "+" button in Activity Bar
 * 2. Form auto-expands in Settings sidebar
 * 3. Fill in instrument details
 * 4. Save and verify instrument is added
 */

import { test, expect } from './fixtures/base';

test.describe('Add Instrument Flow', () => {
  test('should open add instrument form when clicking "+" button', async ({ mockPage }) => {
    // In workbench layout, sidebar starts collapsed
    // Click the "+" button in Activity Bar
    const addButton = mockPage.locator('[data-testid="activity-bar-item-add-instrument"]');
    await expect(addButton).toBeVisible();
    await addButton.click();
    await mockPage.waitForTimeout(500);

    // Sidebar should open with Settings view
    const sidebar = mockPage.locator('[data-testid="sidebar"]');
    await expect(sidebar).toBeVisible();
    await expect(sidebar.locator('.sidebar__title')).toHaveText('Settings');

    // Settings view should show Instruments tab as active
    const settingsView = mockPage.locator('[data-testid="settings-view"]');
    await expect(settingsView).toBeVisible();

    const instrumentsTab = settingsView.locator('[data-testid="settings-tab-instruments"]');
    await expect(instrumentsTab).toHaveClass(/settings-view__tab--active/);
  });

  test('should auto-expand new instrument form when "+" clicked', async ({ mockPage }) => {
    // In workbench layout, sidebar starts collapsed
    // Click "+" button
    const addButton = mockPage.locator('[data-testid="activity-bar-item-add-instrument"]');
    await addButton.click();
    await mockPage.waitForTimeout(1000); // Give time for auto-add to trigger

    // Check that a new instrument accordion item appeared
    const accordionItems = mockPage.locator('.accordion__item');
    const count = await accordionItems.count();

    // Should have at least 3 items (2 existing + 1 new)
    expect(count).toBeGreaterThanOrEqual(3);

    // Find the new instrument (look for "New Instrument" text)
    const newInstrumentHeader = mockPage.locator('.accordion__header:has-text("New Instrument")');
    await expect(newInstrumentHeader).toBeVisible();

    // The new instrument accordion should be expanded
    const newInstrumentItem = mockPage.locator('.accordion__item:has-text("New Instrument")');
    await expect(newInstrumentItem).toHaveClass(/accordion__item--expanded/);
  });

  test('should allow filling in instrument details without closing', async ({ mockPage }) => {
    await mockPage.waitForTimeout(300);

    // Click "+" button
    const addButton = mockPage.locator('[data-testid="activity-bar-item-add-instrument"]');
    await addButton.click();
    await mockPage.waitForTimeout(1000);

    // Find the new instrument form
    const newInstrumentItem = mockPage.locator('.accordion__item:has-text("New Instrument")');
    await expect(newInstrumentItem).toBeVisible();

    // Type in the ID field
    const idInput = newInstrumentItem.locator('input[type="text"]').first();
    await idInput.click();
    await idInput.fill('test-device-1');

    // Wait a bit to see if form closes
    await mockPage.waitForTimeout(500);

    // Form should still be expanded
    await expect(newInstrumentItem).toHaveClass(/accordion__item--expanded/);

    // Type in the name field
    const nameInput = newInstrumentItem.locator('input[type="text"]').nth(1);
    await nameInput.click();
    await nameInput.fill('Test Device');
    await mockPage.waitForTimeout(500);

    // Form should still be expanded
    await expect(newInstrumentItem).toHaveClass(/accordion__item--expanded/);

    // Verify values were typed
    await expect(idInput).toHaveValue('test-device-1');
    await expect(nameInput).toHaveValue('Test Device');
  });

  test('should persist form data while selecting driver', async ({ mockPage }) => {
    await mockPage.waitForTimeout(300);

    // Click "+" button
    const addButton = mockPage.locator('[data-testid="activity-bar-item-add-instrument"]');
    await addButton.click();
    await mockPage.waitForTimeout(1000);

    const newInstrumentItem = mockPage.locator('.accordion__item:has-text("New Instrument")');
    await expect(newInstrumentItem).toBeVisible();

    // Fill ID
    const idInput = newInstrumentItem.locator('input[type="text"]').first();
    await idInput.fill('test-psu-1');
    await mockPage.waitForTimeout(300);

    // Select driver from dropdown
    const driverSelect = newInstrumentItem.locator('select').first();
    await driverSelect.selectOption({ index: 1 }); // Select first available driver
    await mockPage.waitForTimeout(500);

    // Form should still be expanded
    await expect(newInstrumentItem).toHaveClass(/accordion__item--expanded/);

    // ID should still be there
    await expect(idInput).toHaveValue('test-psu-1');
  });

  test('should show validation errors for invalid input', async ({ mockPage }) => {
    await mockPage.waitForTimeout(300);

    // Click "+" button
    const addButton = mockPage.locator('[data-testid="activity-bar-item-add-instrument"]');
    await addButton.click();
    await mockPage.waitForTimeout(1000);

    const newInstrumentItem = mockPage.locator('.accordion__item:has-text("New Instrument")');

    // Try to save without filling required fields
    const addInstrumentButton = newInstrumentItem.locator('button:has-text("Add Instrument")');
    await expect(addInstrumentButton).toBeVisible();
    await addInstrumentButton.click();
    await mockPage.waitForTimeout(500);

    // Should show error message
    const errorMessage = newInstrumentItem.locator('.instrument-config__error');
    await expect(errorMessage).toBeVisible();
  });

  test('should successfully add instrument with valid data', async ({ mockPage }) => {
    // Mock the POST /devices endpoint
    await mockPage.route('**/devices', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'ok', message: 'Device added successfully' })
        });
      } else {
        await route.continue();
      }
    });

    // Mock updated instruments list
    await mockPage.route('**/instruments', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'test-psu-1',
            name: 'Test PSU',
            IDN: 'TEST,PSU,SN123,V1.0',
            classes: [{ class: 'PSU', channels: ['1'], ui_component: 'GenericPSU' }]
          }
        ]),
        headers: {
          'ETag': '"new-etag"'
        }
      });
    });

    await mockPage.waitForTimeout(300);

    // Click "+" button
    const addButton = mockPage.locator('[data-testid="activity-bar-item-add-instrument"]');
    await addButton.click();
    await mockPage.waitForTimeout(1000);

    const newInstrumentItem = mockPage.locator('.accordion__item:has-text("New Instrument")');

    // Fill in all required fields
    const idInput = newInstrumentItem.locator('input[type="text"]').first();
    await idInput.fill('test-psu-1');

    const nameInput = newInstrumentItem.locator('input[type="text"]').nth(1);
    await nameInput.fill('Test PSU');

    // Select driver (assuming first option after empty is a valid driver)
    const driverSelect = newInstrumentItem.locator('select').first();
    await driverSelect.selectOption({ index: 1 });
    await mockPage.waitForTimeout(300);

    // Select model if dropdown appears
    const modelSelect = newInstrumentItem.locator('select').nth(1);
    if (await modelSelect.isVisible()) {
      await modelSelect.selectOption({ index: 1 });
    }

    // Fill port
    const portInput = newInstrumentItem.locator('input[type="text"]').nth(2);
    await portInput.fill('/dev/ttyUSB0');

    // Click Add Instrument button
    const addInstrumentButton = newInstrumentItem.locator('button:has-text("Add Instrument")');
    await addInstrumentButton.click();

    // Wait for success
    await mockPage.waitForTimeout(1000);

    // Should show success message
    const successMessage = newInstrumentItem.locator('.instrument-config__success');
    await expect(successMessage).toBeVisible();
  });

  test('should close form when clicking accordion header', async ({ mockPage }) => {
    await mockPage.waitForTimeout(300);

    // Click "+" button
    const addButton = mockPage.locator('[data-testid="activity-bar-item-add-instrument"]');
    await addButton.click();
    await mockPage.waitForTimeout(1000);

    const newInstrumentItem = mockPage.locator('.accordion__item:has-text("New Instrument")');
    await expect(newInstrumentItem).toHaveClass(/accordion__item--expanded/);

    // Click the accordion header to collapse
    const header = newInstrumentItem.locator('.accordion__header');
    await header.click();
    await mockPage.waitForTimeout(300);

    // Should be collapsed now
    await expect(newInstrumentItem).not.toHaveClass(/accordion__item--expanded/);
  });

  test('should allow reopening collapsed form', async ({ mockPage }) => {
    await mockPage.waitForTimeout(300);

    // Click "+" button
    const addButton = mockPage.locator('[data-testid="activity-bar-item-add-instrument"]');
    await addButton.click();
    await mockPage.waitForTimeout(1000);

    const newInstrumentItem = mockPage.locator('.accordion__item:has-text("New Instrument")');

    // Collapse it
    await newInstrumentItem.locator('.accordion__header').click();
    await mockPage.waitForTimeout(300);
    await expect(newInstrumentItem).not.toHaveClass(/accordion__item--expanded/);

    // Reopen it
    await newInstrumentItem.locator('.accordion__header').click();
    await mockPage.waitForTimeout(300);
    await expect(newInstrumentItem).toHaveClass(/accordion__item--expanded/);
  });

  test('should not create multiple new instruments on repeated "+" clicks', async ({ mockPage }) => {
    await mockPage.waitForTimeout(300);

    const addButton = mockPage.locator('[data-testid="activity-bar-item-add-instrument"]');

    // Click "+" multiple times
    await addButton.click();
    await mockPage.waitForTimeout(500);
    await addButton.click();
    await mockPage.waitForTimeout(500);
    await addButton.click();
    await mockPage.waitForTimeout(500);

    // Should only have ONE new instrument
    const newInstrumentHeaders = mockPage.locator('.accordion__header:has-text("New Instrument")');
    const count = await newInstrumentHeaders.count();
    expect(count).toBe(1);
  });

  test('should handle canceling new instrument creation', async ({ mockPage }) => {
    await mockPage.waitForTimeout(300);

    // Click "+" button
    const addButton = mockPage.locator('[data-testid="activity-bar-item-add-instrument"]');
    await addButton.click();
    await mockPage.waitForTimeout(1000);

    const newInstrumentItem = mockPage.locator('.accordion__item:has-text("New Instrument")');
    await expect(newInstrumentItem).toBeVisible();

    // Fill in some data
    const idInput = newInstrumentItem.locator('input[type="text"]').first();
    await idInput.fill('temp-device');

    // Find and click cancel/remove button (✕ button)
    const removeButton = newInstrumentItem.locator('button[title*="Remove"], button:has-text("✕")').first();
    if (await removeButton.isVisible()) {
      await removeButton.click();
      await mockPage.waitForTimeout(500);

      // New instrument should be gone
      await expect(newInstrumentItem).not.toBeVisible();
    }
  });
});

test.describe('Add Instrument Form State Management', () => {
  test('should not reset form when clicking outside accordion', async ({ mockPage }) => {
    await mockPage.waitForTimeout(300);

    // Click "+" button
    const addButton = mockPage.locator('[data-testid="activity-bar-item-add-instrument"]');
    await addButton.click();
    await mockPage.waitForTimeout(1000);

    const newInstrumentItem = mockPage.locator('.accordion__item:has-text("New Instrument")');

    // Fill in ID
    const idInput = newInstrumentItem.locator('input[type="text"]').first();
    await idInput.fill('persistent-test');
    await mockPage.waitForTimeout(300);

    // Click somewhere else in the sidebar (but not on accordion header)
    const settingsView = mockPage.locator('[data-testid="settings-view"]');
    await settingsView.click({ position: { x: 10, y: 10 } });
    await mockPage.waitForTimeout(300);

    // Form should still be expanded with data intact
    await expect(newInstrumentItem).toHaveClass(/accordion__item--expanded/);
    await expect(idInput).toHaveValue('persistent-test');
  });

  test('should preserve form data when switching tabs and back', async ({ mockPage }) => {
    // Click "+" button
    const addButton = mockPage.locator('[data-testid="activity-bar-item-add-instrument"]');
    await addButton.click();
    await mockPage.waitForTimeout(1000);

    const newInstrumentItem = mockPage.locator('.accordion__item:has-text("New Instrument")');

    // Fill in some data
    const idInput = newInstrumentItem.locator('input[type="text"]').first();
    await idInput.fill('tab-test-device');
    await mockPage.waitForTimeout(300);

    // Switch to Miscellaneous tab
    const miscTab = mockPage.locator('[data-testid="settings-tab-miscellaneous"]');
    await miscTab.click();
    await mockPage.waitForTimeout(500);

    // Switch back to Instruments tab
    const instrumentsTab = mockPage.locator('[data-testid="settings-tab-instruments"]');
    await instrumentsTab.click();
    await mockPage.waitForTimeout(500);

    // Data should still be there
    await expect(idInput).toHaveValue('tab-test-device');
  });
});
