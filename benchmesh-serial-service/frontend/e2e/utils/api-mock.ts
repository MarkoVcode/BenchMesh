import { Page, Route } from '@playwright/test';

/**
 * Mock instrument data for testing
 */
export const mockInstruments = [
  {
    id: 'test-psu-1',
    name: 'Test PSU',
    IDN: 'TENMA,72-2540,SN123456,V1.0',
    classes: [
      {
        class: 'PSU',
        channels: ['1', '2', '3'],
        ui_component: 'GenericPSU'
      }
    ]
  },
  {
    id: 'test-dmm-1',
    name: 'Test DMM',
    IDN: 'OWON,XDM1041,SN789012,V2.1',
    classes: [
      {
        class: 'DMM',
        channels: ['1'],
        ui_component: 'GenericDMM'
      }
    ]
  }
];

/**
 * Mock registry data (WebSocket data)
 */
export const mockRegistry = {
  'test-psu-1': {
    IDN: 'TENMA,72-2540,SN123456,V1.0',
    status: {
      '1': {
        voltage: 5.0,
        current: 0.5,
        output: true
      },
      '2': {
        voltage: 3.3,
        current: 0.3,
        output: false
      },
      '3': {
        voltage: 12.0,
        current: 1.0,
        output: true
      }
    }
  },
  'test-dmm-1': {
    IDN: 'OWON,XDM1041,SN789012,V2.1',
    status: {
      '1': {
        mode: 'VDC',
        value: 4.98,
        range: 'AUTO'
      }
    }
  }
};

/**
 * Setup API mocks for testing
 */
export async function setupApiMocks(page: Page) {
  // Mock /instruments endpoint
  await page.route('**/instruments', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockInstruments),
      headers: {
        'ETag': '"test-etag-12345"'
      }
    });
  });

  // Mock /instruments/:id endpoint
  await page.route('**/instruments/*', async (route: Route) => {
    const url = route.request().url();
    const instrumentId = url.split('/instruments/')[1].split('/')[0];
    const instrument = mockInstruments.find(i => i.id === instrumentId);

    if (instrument) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(instrument)
      });
    } else {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Instrument not found' })
      });
    }
  });

  // Mock config endpoint
  await page.route('**/config', async (route: Route) => {
    if (route.request().method() === 'GET') {
      // Return YAML format as expected by the backend
      const yamlConfig = `version: 1
devices:
  - id: test-psu-1
    name: "TENMA PSU"
    driver: tenma_72
    port: /dev/ttyUSB0
    baud: 9600
    serial: 8N1
    model: 72-2540
  - id: test-dmm-1
    name: "OWON DMM"
    driver: owon_xdm
    port: /dev/ttyUSB1
    baud: 115200
    serial: 8N1
    model: XDM1041`;

      await route.fulfill({
        status: 200,
        contentType: 'text/plain',
        body: yamlConfig
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok' })
      });
    }
  });

  // Mock docs endpoint
  await page.route('**/docs', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'text/markdown',
      body: '# BenchMesh Documentation\n\nTest documentation content.'
    });
  });

  // Mock metrics endpoint
  await page.route('**/metrics/connection', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        'test-psu-1': {
          reconnect_count: 0,
          last_reconnect: null,
          identify_count: 1,
          poll_failure_count: 0
        }
      })
    });
  });

  // Mock metrics utilization endpoint
  await page.route('**/metrics/utilization', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        'test-psu-1': {
          window_duration: 30.0,
          utilization_percent: 12.5,
          qps: 2.5,
          total_operations: 75,
          api_requests: 5,
          api_latency_p95: 11.2,
          api_latency_p99: 14.5
        }
      })
    });
  });

  // Mock recordings endpoint
  await page.route('**/recordings', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([])
    });
  });
}

/**
 * Setup WebSocket mock
 */
export async function setupWebSocketMock(page: Page) {
  await page.addInitScript((registryData) => {
    // Mock WebSocket
    class MockWebSocket {
      url: string;
      readyState: number = 1; // OPEN
      onopen: ((event: Event) => void) | null = null;
      onclose: ((event: CloseEvent) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;

      constructor(url: string) {
        this.url = url;
        setTimeout(() => {
          if (this.onopen) {
            this.onopen(new Event('open'));
          }

          // Send appropriate data based on endpoint
          if (this.url.includes('/ws/registry')) {
            // Send registry data
            if (this.onmessage) {
              this.onmessage(new MessageEvent('message', {
                data: JSON.stringify(registryData)
              }));
            }
            // Send updates every 2 seconds
            setInterval(() => {
              if (this.onmessage && this.readyState === 1) {
                this.onmessage(new MessageEvent('message', {
                  data: JSON.stringify(registryData)
                }));
              }
            }, 2000);
          } else if (this.url.includes('/ws/metrics')) {
            // Send mock metrics data
            const mockMetrics = {
              'test-psu-1': {
                device_id: 'test-psu-1',
                window_duration_s: 30.0,
                utilization_pct: 12.5,
                qps: 2.5,
                api_request_count: 5,
                api_latency_p95_ms: 11.2,
                api_latency_p99_ms: 14.5,
                avg_queue_depth: 0.42,
                avg_poll_duration_ms: 120.5,
                total_operations: 75
              }
            };
            if (this.onmessage) {
              this.onmessage(new MessageEvent('message', {
                data: JSON.stringify(mockMetrics)
              }));
            }
          }
        }, 100);
      }

      close() {
        this.readyState = 3; // CLOSED
        if (this.onclose) {
          this.onclose(new CloseEvent('close'));
        }
      }

      send(data: any) {
        // Mock send - do nothing
      }
    }

    // Override global WebSocket
    (window as any).WebSocket = MockWebSocket;
  }, mockRegistry);
}

/**
 * Wait for instruments to load
 */
export async function waitForInstruments(page: Page, count: number = 1) {
  await page.waitForSelector('.card', { timeout: 10000 });
  const instruments = await page.locator('.card').count();
  if (instruments < count) {
    throw new Error(`Expected at least ${count} instruments, found ${instruments}`);
  }
}

/**
 * Wait for WebSocket connection
 */
export async function waitForWebSocket(page: Page) {
  await page.waitForSelector('.statuspill .dot[style*="var(--good)"]', { timeout: 10000 });
}
