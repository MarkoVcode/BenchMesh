# CompactReading Component

A professional, compact reading component for displaying instrument measurements with integrated controls.

## Overview

The `CompactReading` component provides a sleek, space-efficient way to display instrument readings with built-in controls for API access, recording, statistics, and graphing. It's designed to match the screenshot specification with a clean 3-column layout.

## Features

- **Compact Layout**: Three-column design (Label | Value | Controls)
- **AC/DC Indicator**: Optional indicator that appears only when applicable
- **Large Numeric Display**: Easy-to-read tabular numbers with proper overflow handling
- **2x2 Button Grid**: Four compact control buttons in organized layout
- **Expandable Sections**: Statistics and graph sections expand below when activated
- **API Integration**: Hover to see endpoint, click to copy to clipboard
- **Recording Intent**: Toggle to mark measurement for recording
- **Statistical Sampling**: Toggle MAX/MIN stats window
- **Time Series Graph**: Toggle graph display for the reading

## Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│                                                               │
│  Symbol      Value Display         ┌─────┬─────┐           │
│  [Unit]      (Large Numbers)       │ API │ REC │           │
│  [AC/DC]                            ├─────┼─────┤           │
│                                     │ MAX │  📈 │           │
│                                     │ MIN │     │           │
│                                     └─────┴─────┘           │
│                                                               │
│  ─────────────────────────────────────────────────────────  │
│  [Statistical Sampling - shown when MAX/MIN active]         │
│  ─────────────────────────────────────────────────────────  │
│  [Time Series Graph - shown when 📈 active]                 │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `symbol` | `string` | Yes | Measurement symbol (e.g., "U", "I", "P") |
| `unit` | `string` | Yes | Unit of measurement (e.g., "V", "A", "W", "mV") |
| `value` | `string` | Yes | The numeric reading to display |
| `acdc` | `'AC' \| 'DC' \| null` | No | AC/DC indicator (omit or null for neither) |
| `channelPath` | `string` | No | API channel path for endpoint generation |
| `parameter` | `string` | No | Parameter name for API calls (e.g., "voltage", "current") |

## Usage Examples

### Basic Usage

```tsx
import { CompactReading } from './components/CompactReading'

<CompactReading
  symbol="U"
  unit="V"
  value="12.345"
  channelPath="/instruments/PSU/device-1/1"
  parameter="voltage"
/>
```

### With AC/DC Indicator

```tsx
<CompactReading
  symbol="I"
  unit="mA"
  value="123.45"
  acdc="AC"
  channelPath="/instruments/DMM/device-2/1"
  parameter="current"
/>
```

### Without AC/DC (Power Example)

```tsx
<CompactReading
  symbol="P"
  unit="W"
  value="61.725"
  channelPath="/instruments/PSU/device-1/1"
  parameter="power"
/>
```

## Button Behaviors

### API Button
- **Hover**: Displays REST endpoint in tooltip (e.g., `GET /instruments/PSU/device-1/1/voltage`)
- **Click**: Copies the endpoint to clipboard for easy testing

### REC Button
- **Click**: Toggles recording intent for this measurement
- **Active State**: Button highlights with accent color when recording is enabled
- **Functionality**: Integrates with `MeasurementContext` for centralized recording management

### MAX/MIN Button
- **Click**: Toggles statistical sampling window
- **Display**: Shows min, max, average, standard deviation
- **Active State**: Button highlights when stats are visible
- **Animation**: Smooth slide-down animation when opening

### Graph Button (📈)
- **Click**: Toggles time series graph display
- **Display**: Shows historical data over time
- **Active State**: Button highlights when graph is visible
- **Animation**: Smooth slide-down animation when opening
- **Configuration**: 100 data points with 1-second update interval

## Styling

The component uses BenchMesh's design system variables:
- `--bg-0`, `--bg-1`, `--bg-2`: Background colors
- `--border`: Border color
- `--text-0`, `--text-1`, `--text-2`: Text hierarchy
- `--accent`: Accent/highlight color
- `--card`: Card background

### Key CSS Classes

- `.compact-reading`: Main container
- `.compact-reading-main`: Three-column grid layout
- `.compact-reading-label`: Left section (symbol, unit, AC/DC)
- `.compact-reading-value`: Center section (large numeric display)
- `.compact-reading-controls`: Right section (2x2 button grid)
- `.compact-btn`: Individual control buttons
- `.compact-btn.active`: Active/highlighted button state
- `.compact-reading-stats`: Expandable stats section
- `.compact-reading-graph`: Expandable graph section

## Size Considerations

The component is designed to be:
- **Compact**: Similar height to existing READINGS fields
- **Flexible**: Handles values of various lengths with ellipsis overflow
- **Responsive**: Minimum widths ensure buttons and labels don't collapse
- **Clean**: Numbers don't overflow onto buttons or symbols

### Dimensions

- Minimum height: `48px` (excluding expanded sections)
- Label section: `80px` minimum width
- Controls section: `120px` minimum width (60px per column)
- Button height: `28px` each
- Button gap: `4px` between buttons

## Integration with Existing Components

### In GenericPSU / GenericOWONPSU

Replace `ReadonlyBigNumber` with `CompactReading`:

```tsx
// Old
<ReadonlyBigNumber
  kind="U"
  label={<Label symbol="U" unit="V"/>}
  value={"00000"}
  channelPath={channelPath}
  parameter="voltage"
/>

// New
<CompactReading
  symbol="U"
  unit="V"
  value={measuredVoltage}
  acdc="DC"
  channelPath={channelPath}
  parameter="output_voltage"
/>
```

### In GenericDMM

```tsx
<CompactReading
  symbol="U"
  unit="mV"
  value={dmmVoltage}
  acdc={acMode ? "AC" : "DC"}
  channelPath={channelPath}
  parameter="voltage"
/>
```

## Benefits Over Previous Implementation

1. **More Compact**: Takes up less vertical space
2. **Better Organization**: Controls in dedicated 2x2 grid
3. **Cleaner Look**: Professional layout matching screenshot
4. **No Overflow**: Numbers properly constrained with ellipsis
5. **Intuitive Controls**: Clear button labels and hover states
6. **Smooth Animations**: Expandable sections slide down smoothly
7. **Clipboard Integration**: Easy API endpoint copying
8. **Consistent Design**: Follows BenchMesh design system

## Browser Compatibility

- Modern browsers (Chrome, Firefox, Safari, Edge)
- CSS Grid support required
- Clipboard API for copy functionality

## Accessibility

- Semantic HTML structure
- Keyboard accessible buttons
- Clear button titles for screen readers
- High contrast text and borders
- Focus states on interactive elements
