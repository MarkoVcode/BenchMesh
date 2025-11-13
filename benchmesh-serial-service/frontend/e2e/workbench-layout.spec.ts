import { test, expect } from './fixtures/base';
import { waitForInstruments, waitForWebSocket } from './utils/api-mock';

test.describe('Workbench Layout', () => {
  test('should display workbench container', async ({ mockPage }) => {
    // Check if workbench container exists
    const workbench = mockPage.locator('.workbench');
    await expect(workbench).toBeVisible();
  });

  test('should display topbar with brand and buttons', async ({ mockPage }) => {
    // Check topbar exists
    const topbar = mockPage.locator('.topbar');
    await expect(topbar).toBeVisible();

    // Check brand
    await expect(mockPage.locator('.brand')).toHaveText('BenchMesh');

    // Check for navigation buttons
    await expect(mockPage.locator('button:has-text("⚙️ Configuration")')).toBeVisible();
    await expect(mockPage.locator('button:has-text("📊 Recording")')).toBeVisible();
    await expect(mockPage.locator('button:has-text("📚 Documentation")')).toBeVisible();
    await expect(mockPage.locator('button:has-text("📈 Metrics")')).toBeVisible();
  });

  test('should display topbar status indicators', async ({ mockPage }) => {
    await waitForWebSocket(mockPage);

    // Check for WebSocket status pill
    const wsStatus = mockPage.locator('.statuspill').filter({ hasText: 'receiving' });
    await expect(wsStatus).toBeVisible();

    // Check for API status pill
    const apiStatus = mockPage.locator('.statuspill').filter({ hasText: 'API ok' });
    await expect(apiStatus).toBeVisible();
  });

  test('should display ActivityBar', async ({ mockPage }) => {
    await waitForInstruments(mockPage);

    // Check ActivityBar exists
    const activityBar = mockPage.locator('[data-testid="activity-bar"]');
    await expect(activityBar).toBeVisible();

    // Check for view icons at bottom
    const settingsIcon = mockPage.locator('[data-testid="view-icon-settings"]');
    await expect(settingsIcon).toBeVisible();
  });

  test('should display Sidebar with instrument list', async ({ mockPage }) => {
    await waitForInstruments(mockPage);

    // Check Sidebar exists
    const sidebar = mockPage.locator('[data-testid="sidebar"]');
    await expect(sidebar).toBeVisible();

    // Check sidebar title
    await expect(sidebar.locator('.sidebar__title')).toHaveText('Instruments');

    // Check for instrument list
    const instrumentList = sidebar.locator('.instrument-list');
    await expect(instrumentList).toBeVisible();
  });

  test('should display instrument items in sidebar', async ({ mockPage }) => {
    await waitForInstruments(mockPage);

    // Wait for instruments to load
    await mockPage.waitForTimeout(1000);

    // Check for instrument list items
    const instrumentItems = mockPage.locator('.instrument-list__item');
    const count = await instrumentItems.count();

    // Should have at least some instruments (mock data provides multiple)
    expect(count).toBeGreaterThan(0);

    if (count > 0) {
      // Check first instrument item structure
      const firstItem = instrumentItems.first();
      await expect(firstItem).toBeVisible();

      // Check for status indicator
      const status = firstItem.locator('.instrument-list__item-status');
      await expect(status).toBeVisible();
    }
  });

  test('should display EditorArea', async ({ mockPage }) => {
    await waitForInstruments(mockPage);

    // Check EditorArea exists (initially showing empty state)
    const editor = mockPage.locator('[data-testid="editor-area"]');
    await expect(editor).toBeVisible();
  });

  test('should display empty state when no instruments active', async ({ mockPage }) => {
    await waitForInstruments(mockPage);

    // Check for empty state message
    const emptyState = mockPage.locator('.editor__empty-content');
    await expect(emptyState).toBeVisible();

    // Check for empty state message
    await expect(emptyState.locator('.editor__empty-title')).toContainText('No Instruments Open');
  });

  test('should display StatusBar at bottom', async ({ mockPage }) => {
    await waitForInstruments(mockPage);

    // Check StatusBar exists
    const statusBar = mockPage.locator('[data-testid="status-bar"]');
    await expect(statusBar).toBeVisible();

    // Check for WebSocket status
    const wsStatus = statusBar.locator('.status-bar__item').filter({ hasText: /Connected|Disconnected/ });
    await expect(wsStatus).toBeVisible();

    // Check for device count
    const deviceCount = statusBar.locator('.status-bar__item').filter({ hasText: /Devices/ });
    await expect(deviceCount).toBeVisible();
  });

  test('should toggle sidebar when clicking view icons', async ({ mockPage }) => {
    await waitForInstruments(mockPage);

    // Get sidebar
    const sidebar = mockPage.locator('[data-testid="sidebar"]');
    await expect(sidebar).toBeVisible();

    // Close sidebar
    await mockPage.click('.sidebar__close');
    await mockPage.waitForTimeout(300);

    // Sidebar should be hidden
    await expect(sidebar).not.toBeVisible();

    // Click settings icon to reopen
    await mockPage.click('[data-testid="view-icon-settings"]');
    await mockPage.waitForTimeout(300);

    // Sidebar should be visible again with Settings title
    await expect(sidebar).toBeVisible();
    await expect(sidebar.locator('.sidebar__title')).toHaveText('Settings');
  });

  test('should switch sidebar views', async ({ mockPage }) => {
    await waitForInstruments(mockPage);

    const sidebar = mockPage.locator('[data-testid="sidebar"]');

    // Initially showing Instruments view
    await expect(sidebar.locator('.sidebar__title')).toHaveText('Instruments');

    // Click Recording view icon
    await mockPage.click('[data-testid="view-icon-recording"]');
    await mockPage.waitForTimeout(300);

    // Should show Recording title
    await expect(sidebar.locator('.sidebar__title')).toHaveText('Recording');

    // Click Metrics view icon
    await mockPage.click('[data-testid="view-icon-metrics"]');
    await mockPage.waitForTimeout(300);

    // Should show Metrics title
    await expect(sidebar.locator('.sidebar__title')).toHaveText('Metrics');

    // Click back to Instruments
    await mockPage.click('[data-testid="view-icon-instruments"]');
    await mockPage.waitForTimeout(300);

    // Should show Instruments again
    await expect(sidebar.locator('.sidebar__title')).toHaveText('Instruments');
  });

  test('should display LED badges on instrument icons', async ({ mockPage }) => {
    await waitForInstruments(mockPage);
    await waitForWebSocket(mockPage);

    // Wait for registry data to populate
    await mockPage.waitForTimeout(1000);

    // Check for activity bar items with LED badges
    const activityItems = mockPage.locator('.activity-bar__item');
    const count = await activityItems.count();

    if (count > 0) {
      // Check first instrument has LED badge
      const firstItem = activityItems.first();
      const ledBadge = firstItem.locator('.led-badge');
      await expect(ledBadge).toBeVisible();
    }
  });

  test('should display BottomPanel when toggled', async ({ mockPage }) => {
    await waitForInstruments(mockPage);

    // Bottom panel should be visible by default
    const bottomPanel = mockPage.locator('[data-testid="bottom-panel"]');
    await expect(bottomPanel).toBeVisible();

    // Check for tabs
    await expect(bottomPanel.locator('[data-testid="bottom-panel-tab-graphs"]')).toBeVisible();
    await expect(bottomPanel.locator('[data-testid="bottom-panel-tab-records"]')).toBeVisible();
    await expect(bottomPanel.locator('[data-testid="bottom-panel-tab-logs"]')).toBeVisible();
    await expect(bottomPanel.locator('[data-testid="bottom-panel-tab-nodered"]')).toBeVisible();
  });

  test('should switch BottomPanel tabs', async ({ mockPage }) => {
    await waitForInstruments(mockPage);

    const bottomPanel = mockPage.locator('[data-testid="bottom-panel"]');

    // Click Records tab
    await mockPage.click('[data-testid="bottom-panel-tab-records"]');
    await mockPage.waitForTimeout(300);

    // Check active state
    const recordsTab = mockPage.locator('[data-testid="bottom-panel-tab-records"]');
    await expect(recordsTab).toHaveClass(/bottom-panel__tab--active/);

    // Click Logs tab
    await mockPage.click('[data-testid="bottom-panel-tab-logs"]');
    await mockPage.waitForTimeout(300);

    // Check active state switched
    const logsTab = mockPage.locator('[data-testid="bottom-panel-tab-logs"]');
    await expect(logsTab).toHaveClass(/bottom-panel__tab--active/);
  });

  test('should close BottomPanel', async ({ mockPage }) => {
    await waitForInstruments(mockPage);

    const bottomPanel = mockPage.locator('[data-testid="bottom-panel"]');
    await expect(bottomPanel).toBeVisible();

    // Click close button
    await mockPage.click('.bottom-panel__close');
    await mockPage.waitForTimeout(300);

    // Panel should be hidden
    await expect(bottomPanel).not.toBeVisible();
  });

  test('should activate instrument in editor when clicked', async ({ mockPage }) => {
    await waitForInstruments(mockPage);
    await waitForWebSocket(mockPage);

    // Wait for data
    await mockPage.waitForTimeout(1000);

    // Get first instrument in activity bar
    const firstInstrument = mockPage.locator('.activity-bar__item--instrument').first();
    await expect(firstInstrument).toBeVisible();

    // Click to activate
    await firstInstrument.click();
    await mockPage.waitForTimeout(500);

    // Editor should no longer show empty state
    const emptyState = mockPage.locator('.editor__empty-content');
    await expect(emptyState).not.toBeVisible();

    // Should show mosaic or instrument content
    // (exact content depends on InstrumentPod integration)
  });
});

test.describe('Workbench Modals Integration', () => {
  test('should open configuration modal from topbar', async ({ mockPage }) => {
    // Click configuration button in topbar
    await mockPage.click('button:has-text("⚙️ Configuration")');

    // Wait for modal
    await mockPage.waitForSelector('.modal-overlay', { timeout: 5000 });
    await expect(mockPage.locator('.modal-overlay')).toBeVisible();

    // Close modal
    await mockPage.click('.modal-close');
    await mockPage.waitForTimeout(500);
    await expect(mockPage.locator('.modal-overlay')).not.toBeVisible();
  });

  test('should open recording modal from topbar', async ({ mockPage }) => {
    // Click recording button in topbar
    await mockPage.click('button:has-text("📊 Recording")');

    // Wait for modal heading
    await mockPage.waitForSelector('h2:has-text("📊 Data Recording")', { timeout: 5000 });
    await expect(mockPage.locator('h2:has-text("📊 Data Recording")')).toBeVisible();

    // Close modal
    await mockPage.click('button:has-text("×")');
    await mockPage.waitForTimeout(500);
    await expect(mockPage.locator('h2:has-text("📊 Data Recording")')).not.toBeVisible();
  });

  test('should open documentation modal from topbar', async ({ mockPage }) => {
    // Click documentation button in topbar
    await mockPage.click('button:has-text("📚 Documentation")');

    // Wait for modal
    await mockPage.waitForSelector('.modal-overlay', { timeout: 5000 });
    const modal = mockPage.locator('.modal-overlay');
    await expect(modal).toBeVisible();

    // Check for docs content
    await expect(mockPage.locator('.docs-modal-content h1')).toContainText('BenchMesh Documentation');

    // Close modal
    await mockPage.click('.modal-close');
    await mockPage.waitForTimeout(500);
    await expect(modal).not.toBeVisible();
  });

  test('should open metrics modal from topbar', async ({ mockPage }) => {
    // Click metrics button in topbar
    await mockPage.click('button:has-text("📈 Metrics")');

    // Wait for modal heading
    await mockPage.waitForSelector('h2:has-text("Serial Port Utilization Metrics")', { timeout: 5000 });
    await expect(mockPage.locator('h2:has-text("Serial Port Utilization Metrics")')).toBeVisible();

    // Close modal
    await mockPage.click('.modal-close');
    await mockPage.waitForTimeout(500);
    await expect(mockPage.locator('.modal-overlay')).not.toBeVisible();
  });
});
