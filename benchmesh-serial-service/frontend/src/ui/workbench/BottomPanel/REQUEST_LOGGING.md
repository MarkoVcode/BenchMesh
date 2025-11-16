# Request Logging System

The request logging system provides comprehensive tracking of all API requests made to instruments, displaying them in the Logs panel of the workbench bottom panel.

## Overview

- **RequestLogContext**: Global context for storing request logs
- **LogsPanel**: UI component displaying request history with filtering
- **loggedFetch**: Wrapper function that automatically logs fetch requests

## Features

- ✅ Chronological history of all API requests
- ✅ Detailed timestamp (date + time with milliseconds)
- ✅ HTTP method badges (GET, POST, PUT, DELETE)
- ✅ Status code and success/error indicators
- ✅ Request duration tracking
- ✅ Instrument and channel context
- ✅ Action and parameter details
- ✅ Filter by HTTP method and status
- ✅ Clear all logs functionality
- ✅ Automatic 1000-entry limit (prevents memory issues)

## Usage in Components

### Method 1: Using `useRequestLog` Hook

```typescript
import { useRequestLog } from '../../../RequestLogContext';

function MyInstrumentComponent() {
  const { addLog } = useRequestLog();
  const apiBase = `${window.location.protocol}//${window.location.hostname}:57666`;

  const setVoltage = async (channel: string, value: number) => {
    const url = `${apiBase}/instruments/PSU/device-1/${channel}/voltage/${value}`;
    const startTime = Date.now();

    try {
      const response = await fetch(url, { method: 'POST' });
      const duration = Date.now() - startTime;

      addLog({
        method: 'POST',
        url,
        status: response.status,
        statusText: response.statusText,
        duration,
        instrument: 'device-1',
        channel,
        action: 'Set Voltage',
        parameters: { voltage: value },
      });

      return await response.json();
    } catch (error: any) {
      const duration = Date.now() - startTime;

      addLog({
        method: 'POST',
        url,
        duration,
        error: error.message,
        instrument: 'device-1',
        channel,
        action: 'Set Voltage',
        parameters: { voltage: value },
      });

      throw error;
    }
  };

  return <div>...</div>;
}
```

### Method 2: Using `loggedFetch` Wrapper

```typescript
import { loggedFetch, useRequestLog } from '../../../RequestLogContext';

function MyInstrumentComponent() {
  const { addLog } = useRequestLog();
  const apiBase = `${window.location.protocol}//${window.location.hostname}:57666`;

  const setVoltage = async (channel: string, value: number) => {
    const url = `${apiBase}/instruments/PSU/device-1/${channel}/voltage/${value}`;

    const response = await loggedFetch(url, {
      method: 'POST',
      instrument: 'device-1',
      channel,
      action: 'Set Voltage',
      parameters: { voltage: value },
      addLog, // Pass the addLog function
    });

    return await response.json();
  };

  return <div>...</div>;
}
```

## Log Entry Fields

| Field          | Type     | Description                                    |
| -------------- | -------- | ---------------------------------------------- |
| `id`           | string   | Unique log entry ID (auto-generated)           |
| `timestamp`    | Date     | Request timestamp (auto-generated)             |
| `method`       | string   | HTTP method (GET, POST, PUT, DELETE)           |
| `url`          | string   | Full request URL                               |
| `status`       | number?  | HTTP status code (200, 404, 500, etc.)         |
| `statusText`   | string?  | HTTP status text ("OK", "Not Found", etc.)     |
| `duration`     | number?  | Request duration in milliseconds               |
| `error`        | string?  | Error message if request failed                |
| `instrument`   | string?  | Instrument ID for context                      |
| `channel`      | string?  | Channel number for context                     |
| `action`       | string?  | Human-readable action description              |
| `parameters`   | any?     | Request parameters (will be JSON.stringified)  |

## UI Features

### Filtering

- **Method Filter**: Show only GET, POST, PUT, DELETE, or All
- **Status Filter**: Show Success (2xx/3xx), Error (4xx/5xx), or All

### Visual Indicators

- **Success** (green check): Status 200-399 or no error
- **Warning** (yellow warning): Status 400-499
- **Error** (red X): Status 500+ or network error

### Method Badges

- **GET**: Blue badge
- **POST**: Green badge
- **PUT**: Orange badge
- **DELETE**: Red badge

### Entry Count

Displays current number of filtered entries (e.g., "127 entries")

### Clear Logs

Red button to clear all request history

## Log Display Format

```
Nov 15  14:32:45.123    POST  /instruments/PSU/device-1/1/voltage/5.0    ✓ 200    45ms
Instrument: device-1 / Ch1    Action: Set Voltage    Parameters: {"voltage":5.0}
```

Each log entry shows:
- Date and precise time (HH:MM:SS.mmm)
- HTTP method badge
- Endpoint path
- Status indicator and code
- Request duration
- Detailed context (instrument, action, parameters) when available

## Best Practices

1. **Always log user-initiated actions** (button clicks, value changes)
2. **Include meaningful action descriptions** ("Set Voltage", "Enable Output", "Query Current")
3. **Log parameters** to make debugging easier
4. **Include instrument and channel** for multi-instrument setups
5. **Let errors propagate** - the logging system captures them automatically

## Example: Complete PSU Control Integration

```typescript
import { useRequestLog, loggedFetch } from '../../../RequestLogContext';

export function GenericPSU({ channelPath, registry }: Props) {
  const { addLog } = useRequestLog();
  const apiBase = `${window.location.protocol}//${window.location.hostname}:57666`;

  const [deviceId, channel] = channelPath.split('/').slice(3, 5);

  const handleSetVoltage = async (voltage: number) => {
    const url = `${apiBase}/instruments/PSU/${deviceId}/${channel}/voltage/${voltage}`;

    try {
      await loggedFetch(url, {
        method: 'POST',
        instrument: deviceId,
        channel,
        action: 'Set Voltage',
        parameters: { voltage },
        addLog,
      });
    } catch (error) {
      console.error('Failed to set voltage:', error);
      // Error automatically logged by loggedFetch
    }
  };

  const handleSetCurrent = async (current: number) => {
    const url = `${apiBase}/instruments/PSU/${deviceId}/${channel}/current/${current}`;

    try {
      await loggedFetch(url, {
        method: 'POST',
        instrument: deviceId,
        channel,
        action: 'Set Current',
        parameters: { current },
        addLog,
      });
    } catch (error) {
      console.error('Failed to set current:', error);
    }
  };

  const handleToggleOutput = async (enabled: boolean) => {
    const url = `${apiBase}/instruments/PSU/${deviceId}/${channel}/output/${enabled ? 1 : 0}`;

    try {
      await loggedFetch(url, {
        method: 'POST',
        instrument: deviceId,
        channel,
        action: enabled ? 'Enable Output' : 'Disable Output',
        addLog,
      });
    } catch (error) {
      console.error('Failed to toggle output:', error);
    }
  };

  return (
    <div className="psu-face">
      {/* PSU controls... */}
    </div>
  );
}
```

## Viewing Logs

1. Open the workbench bottom panel (toggle button in status bar or topbar)
2. Click the "Logs" tab
3. View real-time request history as you control instruments
4. Use filters to focus on specific methods or status codes
5. Click "Clear" to reset the log history

## Notes

- Logs are **session-only** (cleared on page reload)
- Maximum **1000 entries** kept in memory (oldest deleted first)
- **No sensitive data** should be included in parameters
- Logs are **not persisted** to disk or sent to any server
