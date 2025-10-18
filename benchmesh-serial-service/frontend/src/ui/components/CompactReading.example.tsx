import React from 'react'
import { CompactReading } from './CompactReading'

/**
 * Example usage of CompactReading component
 *
 * This component provides a compact, professional display for instrument readings
 * with integrated controls for API access, recording, statistics, and graphing.
 */

export function CompactReadingExamples() {
  return (
    <div style={{ padding: '20px', background: 'var(--bg-0)' }}>
      <h2 style={{ color: 'var(--text-0)', marginBottom: '20px' }}>CompactReading Examples</h2>

      {/* Example 1: Basic voltage reading */}
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ color: 'var(--text-1)', fontSize: '14px' }}>Basic Voltage Reading</h3>
        <CompactReading
          symbol="U"
          unit="V"
          value="12.345"
          channelPath="/instruments/PSU/device-1/1"
          parameter="voltage"
        />
      </div>

      {/* Example 2: DC voltage reading */}
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ color: 'var(--text-1)', fontSize: '14px' }}>DC Voltage with AC/DC Indicator</h3>
        <CompactReading
          symbol="U"
          unit="V"
          value="5.000"
          acdc="DC"
          channelPath="/instruments/PSU/device-1/1"
          parameter="voltage"
        />
      </div>

      {/* Example 3: AC current reading in mA */}
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ color: 'var(--text-1)', fontSize: '14px' }}>AC Current in milliamps</h3>
        <CompactReading
          symbol="I"
          unit="mA"
          value="123.45"
          acdc="AC"
          channelPath="/instruments/DMM/device-2/1"
          parameter="current"
        />
      </div>

      {/* Example 4: Power reading (no AC/DC) */}
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ color: 'var(--text-1)', fontSize: '14px' }}>Power Reading (no AC/DC indicator)</h3>
        <CompactReading
          symbol="P"
          unit="W"
          value="61.725"
          channelPath="/instruments/PSU/device-1/1"
          parameter="power"
        />
      </div>

      {/* Example 5: Frequency reading */}
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ color: 'var(--text-1)', fontSize: '14px' }}>Frequency Reading</h3>
        <CompactReading
          symbol="f"
          unit="Hz"
          value="50.02"
          channelPath="/instruments/DMM/device-2/1"
          parameter="frequency"
        />
      </div>

      {/* Example 6: Very large number */}
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ color: 'var(--text-1)', fontSize: '14px' }}>Large Number Handling</h3>
        <CompactReading
          symbol="R"
          unit="Ω"
          value="1234567.89"
          channelPath="/instruments/DMM/device-3/1"
          parameter="resistance"
        />
      </div>

      <div style={{ marginTop: '30px', padding: '16px', background: 'var(--card)', borderRadius: '8px', border: '1px solid var(--border)' }}>
        <h3 style={{ color: 'var(--text-0)', marginTop: 0 }}>Button Functions:</h3>
        <ul style={{ color: 'var(--text-1)', fontSize: '14px', lineHeight: '1.8' }}>
          <li><strong>API</strong> - Hover to see REST endpoint, click to copy to clipboard</li>
          <li><strong>REC</strong> - Toggle recording in data table (highlighted when active)</li>
          <li><strong>MAX/MIN</strong> - Toggle statistical sampling window</li>
          <li><strong>📈</strong> - Toggle time series graph</li>
        </ul>
      </div>
    </div>
  )
}

/**
 * Usage in PSU/DMM components:
 *
 * // In Readings section, replace ReadonlyBigNumber with:
 * <CompactReading
 *   symbol="U"
 *   unit="V"
 *   value={measuredVoltage}
 *   acdc="DC"  // Optional: "AC", "DC", or omit
 *   channelPath={channelPath}
 *   parameter="output_voltage"
 * />
 *
 * <CompactReading
 *   symbol="I"
 *   unit="A"
 *   value={measuredCurrent}
 *   acdc="DC"
 *   channelPath={channelPath}
 *   parameter="output_current"
 * />
 *
 * <CompactReading
 *   symbol="P"
 *   unit="W"
 *   value={calculatedPower}
 *   channelPath={channelPath}
 *   parameter="output_power"
 * />
 */
