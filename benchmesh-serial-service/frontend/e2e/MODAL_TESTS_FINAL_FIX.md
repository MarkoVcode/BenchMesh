# Modal Tests Final Fix - Metrics & Recording

## Additional Issues Found

After fixing the `.modal` → `.modal-overlay` selector issue, two tests were still failing:
1. **"should open and close metrics modal"**
2. **"should open and close recording modal"**

Visual evidence showed these modals working perfectly, but tests continued to timeout.

## Root Causes

### Issue 1: Metrics Modal - WebSocket Connection

**Problem**: MetricsViewer tries to connect to `/ws/metrics` WebSocket endpoint.

```typescript
// MetricsViewer.tsx
const url = `${wsProto}://${window.location.hostname}:57666/ws/metrics`
ws = new WebSocket(url)
```

**Impact**:
- Mock API doesn't handle WebSocket connections for `/ws/metrics`
- Only `/ws/registry` was mocked
- MetricsViewer hangs waiting for connection
- Test times out waiting for modal to fully render

**Solution**: Extended WebSocket mock to handle both endpoints:

```typescript
// In setupWebSocketMock()
if (this.url.includes('/ws/registry')) {
  // Send registry data...
} else if (this.url.includes('/ws/metrics')) {
  // Send mock metrics data
  const mockMetrics = {
    'test-psu-1': {
      device_id: 'test-psu-1',
      utilization_pct: 12.5,
      qps: 2.5,
      // ... other metrics
    }
  };
}
```

### Issue 2: Recording Modal - Complex Inline Styles

**Problem**: RecordingModal uses inline styles, not CSS classes.

```typescript
// RecordingModal.tsx
<div style={{
  position: 'fixed',
  background: 'rgba(0,0,0,0.7)',
  // ... lots of inline styles
}}>
```

**Original Test Approach (Too Complex)**:
```typescript
await mockPage.waitForSelector('[style*="position: fixed"]', { timeout: 5000 });
const modalOverlay = mockPage.locator('[style*="position: fixed"][style*="rgba(0,0,0,0.7)"]');
```

**Why This Failed**:
- Multiple elements might have `position: fixed`
- Inline style string matching is unreliable
- Background color format might vary
- Selector was too specific and fragile

**Better Solution**: Wait for unique modal content instead:

```typescript
// Wait for modal heading (unique and reliable)
await mockPage.waitForSelector('h2:has-text("📊 Data Recording")', { timeout: 5000 });
```

## Improved Test Strategy

### Before (Unreliable):
```typescript
// Wait for generic overlay
await page.waitForSelector('.modal-overlay', { timeout: 5000 });
```

### After (More Reliable):
```typescript
// Wait for specific modal heading
await page.waitForSelector('h2:has-text("Serial Port Utilization Metrics")', { timeout: 5000 });
await page.waitForSelector('h2:has-text("📊 Data Recording")', { timeout: 5000 });
```

**Benefits**:
1. ✅ **More specific** - Each modal has unique heading text
2. ✅ **More reliable** - Heading only appears when modal is fully rendered
3. ✅ **Immune to style changes** - Doesn't depend on CSS implementation
4. ✅ **Self-documenting** - Test clearly shows which modal it's testing

## Complete Fix Summary

### Metrics Modal Test
**Changes**:
1. Wait for heading: `h2:has-text("Serial Port Utilization Metrics")`
2. Verify close button is visible before clicking
3. Added WebSocket mock for `/ws/metrics` endpoint

**Why It Works Now**:
- WebSocket connects immediately (mocked)
- Modal renders with metrics data (mocked)
- Heading appears reliably
- Test can proceed

### Recording Modal Test
**Changes**:
1. Wait for heading: `h2:has-text("📊 Data Recording")`
2. Simplified close button selector to `button:has-text("×")`
3. Verify heading disappears after close

**Why It Works Now**:
- Doesn't rely on fragile inline style matching
- Heading is unique and always present
- Close button is simple and reliable
- Clear pass/fail criteria

## Files Modified

1. **`e2e/app-navigation.spec.ts`**
   - Updated metrics modal test to wait for heading
   - Updated recording modal test to use heading instead of styles
   - Added close button visibility checks

2. **`e2e/utils/api-mock.ts`**
   - Extended `setupWebSocketMock()` to handle `/ws/metrics` endpoint
   - Added mock metrics data structure
   - Maintains backward compatibility with registry WebSocket

## Testing the Fix

Run tests to verify all modals work:

```bash
# All modal tests
npx playwright test app-navigation.spec.ts -g "modal"

# Specific tests
npx playwright test app-navigation.spec.ts -g "metrics modal"
npx playwright test app-navigation.spec.ts -g "recording modal"

# Watch them pass
npx playwright test --headed app-navigation.spec.ts -g "modal"
```

## Key Learnings

### 1. Wait for Specific Content, Not Generic Containers

**Bad**:
```typescript
await page.waitForSelector('.modal-overlay');
```

**Good**:
```typescript
await page.waitForSelector('h2:has-text("Unique Modal Title")');
```

### 2. Mock All External Dependencies

**Before**: Only `/ws/registry` was mocked
**After**: Both `/ws/registry` and `/ws/metrics` mocked

**Lesson**: Modal components may have hidden dependencies (WebSockets, API calls, etc.)

### 3. Avoid Inline Style Selectors

**Bad**:
```typescript
page.locator('[style*="position: fixed"][style*="background"]')
```

**Good**:
```typescript
page.locator('h2:has-text("Modal Title")')
```

**Lesson**: Inline styles are implementation details. Test user-visible content instead.

### 4. Verify Visibility Before Interaction

**Before**:
```typescript
const closeButton = page.locator('.modal-close').first();
await closeButton.click(); // Might fail if not visible
```

**After**:
```typescript
const closeButton = page.locator('.modal-close').first();
await expect(closeButton).toBeVisible(); // Explicit check
await closeButton.click();
```

**Lesson**: Explicit visibility checks make failures clearer.

## Test Stability Improvements

These changes make tests more stable by:

1. **Reducing timing sensitivity**
   - Wait for actual content, not just container
   - Content appears when modal is fully ready

2. **Reducing false positives**
   - Unique headings ensure we're testing the right modal
   - Can't accidentally test wrong modal

3. **Improving error messages**
   - "Cannot find 'Serial Port Utilization Metrics'" is clearer than
   - "Cannot find '.modal-overlay'" (which overlay?)

4. **Making tests maintainable**
   - Change CSS classes? Tests still work
   - Change inline styles? Tests still work
   - Only breaks if actual UI text changes (which it shouldn't)

## All Modal Tests Now Pass

After all fixes:
- ✅ Configuration modal - Uses `.modal-overlay` + heading
- ✅ Documentation modal - Uses `.modal-overlay` + `.docs-modal-content`
- ✅ Metrics modal - Uses heading + WebSocket mock
- ✅ Recording modal - Uses heading instead of styles

Total: **4/4 modal tests passing** 🎉

## Next Time

When adding new modal tests:

1. Identify the modal's unique heading or title
2. Wait for that specific text, not generic containers
3. Check what external connections it makes (WebSocket, API)
4. Mock those connections in the test setup
5. Use semantic selectors (headings, text) over style selectors
6. Verify element visibility before interaction
