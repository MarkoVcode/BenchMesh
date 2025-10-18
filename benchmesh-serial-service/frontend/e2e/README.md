# BenchMesh E2E Tests

End-to-end tests for the BenchMesh frontend using Playwright.

## Overview

These tests verify the BenchMesh UI functionality by simulating real user interactions in a browser. The tests use mocked API and WebSocket connections to ensure reliable and fast execution.

## Test Structure

```
e2e/
├── fixtures/
│   └── base.ts           # Base test fixture with mocks
├── utils/
│   └── api-mock.ts       # API and WebSocket mocking utilities
├── app-navigation.spec.ts          # Navigation and modal tests
├── instrument-display.spec.ts      # Instrument card display tests
├── instrument-interaction.spec.ts  # Device interaction tests
└── api-integration.spec.ts         # API/WebSocket integration tests
```

## Running Tests

### Run all tests (headless)
```bash
npm run test:e2e
```

### Run tests with UI mode (interactive)
```bash
npm run test:e2e:ui
```

### Run tests in headed mode (visible browser)
```bash
npm run test:e2e:headed
```

### Run tests in debug mode
```bash
npm run test:e2e:debug
```

### Run specific test file
```bash
npx playwright test app-navigation.spec.ts
```

### Run specific test
```bash
npx playwright test -g "should load the app"
```

## Test Coverage

### App Navigation (`app-navigation.spec.ts`)
- ✅ Brand display
- ✅ Status indicators (WebSocket, API)
- ✅ Navigation buttons
- ✅ Configuration modal
- ✅ Documentation modal
- ✅ Metrics modal
- ✅ Recording modal
- ✅ Measurement status bar

### Instrument Display (`instrument-display.spec.ts`)
- ✅ Instrument card rendering
- ✅ Instrument IDs
- ✅ IDN information
- ✅ Online/offline status
- ✅ PSU channel display
- ✅ DMM measurement display
- ✅ Empty instrument list handling

### Instrument Interaction (`instrument-interaction.spec.ts`)
- ✅ PSU controls
- ✅ Measurement context
- ✅ Real-time data updates
- ✅ Device control actions
- ✅ API error handling
- ✅ State persistence across WebSocket updates
- ✅ Rapid user interaction handling

### API Integration (`api-integration.spec.ts`)
- ✅ Successful API responses
- ✅ 304 Not Modified handling
- ✅ API error recovery and retry
- ✅ Network timeout handling
- ✅ ETag support (If-None-Match)
- ✅ Malformed JSON handling
- ✅ WebSocket connection failures
- ✅ WebSocket update stream
- ✅ Concurrent API and WebSocket data

## Mock Data

The tests use mock data defined in `utils/api-mock.ts`:

- **Mock Instruments**: 2 test devices (PSU and DMM)
- **Mock Registry**: Simulated real-time device data
- **Mock WebSocket**: Simulated WebSocket connection with periodic updates

## Configuration

Tests are configured in `playwright.config.ts`:

- **Base URL**: `http://localhost:57666`
- **Timeout**: 30 seconds per test
- **Retries**: 2 on CI, 0 locally
- **Browser**: Chromium (Desktop Chrome)
- **Screenshots**: On failure only
- **Videos**: On failure only
- **Traces**: On first retry

## CI Integration

These tests run automatically on:
- Pull requests
- Pushes to main branch
- Manual workflow dispatch

See `.github/workflows/e2e-tests.yml` for CI configuration.

## Writing New Tests

### 1. Use the base fixture

```typescript
import { test, expect } from './fixtures/base';

test('my test', async ({ mockPage }) => {
  // mockPage has API and WebSocket mocks pre-configured
  await expect(mockPage.locator('.brand')).toBeVisible();
});
```

### 2. Add custom mocks if needed

```typescript
test('custom mock', async ({ mockPage, page }) => {
  await page.route('**/my-endpoint', async (route) => {
    await route.fulfill({
      status: 200,
      body: JSON.stringify({ data: 'test' })
    });
  });
});
```

### 3. Use helper utilities

```typescript
import { waitForInstruments, waitForWebSocket } from './utils/api-mock';

test('wait for data', async ({ mockPage }) => {
  await waitForInstruments(mockPage, 2);
  await waitForWebSocket(mockPage);
  // Now instruments and WebSocket are ready
});
```

## Best Practices

1. **Use data-testid attributes** for stable selectors (when possible)
2. **Avoid hardcoded timeouts** - use `waitFor` methods instead
3. **Test user behavior** - not implementation details
4. **Keep tests independent** - each test should work in isolation
5. **Use descriptive test names** - clearly state what's being tested
6. **Mock external dependencies** - API, WebSocket, etc.
7. **Clean up after tests** - close modals, reset state

## Troubleshooting

### Tests fail with timeout errors
- Increase timeout in `playwright.config.ts`
- Check if selectors are correct
- Verify mock data is being returned

### WebSocket tests fail
- Check if WebSocket mock is properly initialized
- Verify timing - may need to adjust wait times

### CI tests fail but local tests pass
- Check for timing issues
- Verify retry configuration
- Review CI logs for specific errors

## Future Enhancements

- [ ] Add visual regression tests
- [ ] Add accessibility tests (a11y)
- [ ] Add performance tests
- [ ] Test recording functionality in detail
- [ ] Test configuration changes and device hot-reload
- [ ] Add mobile viewport tests
- [ ] Add cross-browser tests (Firefox, Safari)
