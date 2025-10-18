import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useMeasurement } from '../MeasurementContext'
import { SamplingStats } from '../SamplingStats'
import { TimeSeriesGraph } from '../classes/PSU/TimeSeriesGraph'

interface CompactReadingProps {
  symbol: string              // e.g., "U", "I", "P"
  unit: string               // e.g., "V", "A", "W", "mV"
  value: string              // The numeric reading
  acdc?: 'AC' | 'DC' | null  // AC/DC indicator, null/undefined for neither
  channelPath?: string       // For API calls
  parameter?: string         // e.g., "voltage", "current", "power"
}

export function CompactReading({ symbol, unit, value, acdc, channelPath, parameter }: CompactReadingProps) {
  const { selectedForRecord, toggleRecord } = useMeasurement()
  const [showStats, setShowStats] = useState(false)
  const [showGraph, setShowGraph] = useState(false)
  const valueRef = useRef<string>(value)

  // Keep ref updated with latest value
  useEffect(() => {
    valueRef.current = value
  }, [value])

  const sourceId = useMemo(() => {
    if (!channelPath || !parameter) return ''
    const deviceId = channelPath.split('/')[3] || 'unknown'
    const channel = channelPath.split('/')[4] || '1'
    return `${deviceId}-${channel}-${symbol}`
  }, [channelPath, parameter, symbol])

  const getCurrentValue = () => {
    const numericValue = parseFloat(valueRef.current)
    return isNaN(numericValue) ? null : numericValue
  }

  const apiEndpoint = channelPath && parameter ? `GET ${channelPath}/${parameter}` : ''

  const handleApiClick = () => {
    if (apiEndpoint) {
      navigator.clipboard.writeText(apiEndpoint).catch(() => {})
    }
  }

  const isRecording = selectedForRecord.has(sourceId)

  return (
    <div className="compact-reading">
      <div className="compact-reading-main">
        {/* Left section: Symbol, Unit, and AC/DC indicator */}
        <div className="compact-reading-label">
          <div className="compact-reading-symbol">{symbol}</div>
          <div className="compact-reading-unit">[{unit}]</div>
          {acdc && <div className="compact-reading-acdc">{acdc}</div>}
        </div>

        {/* Center section: Large numeric display */}
        <div className="compact-reading-value">
          {value || '0'}
        </div>

        {/* Right section: Control buttons in 2x2 grid */}
        <div className="compact-reading-controls">
          <button
            className="compact-btn"
            title={apiEndpoint}
            onClick={handleApiClick}
          >
            API
          </button>
          <button
            className={`compact-btn ${isRecording ? 'active' : ''}`}
            onClick={() => toggleRecord(sourceId)}
            title="Record in table"
          >
            REC
          </button>
          <button
            className={`compact-btn ${showStats ? 'active' : ''}`}
            onClick={() => setShowStats(!showStats)}
            title="Show statistics"
          >
            MAX<br/>MIN
          </button>
          <button
            className={`compact-btn ${showGraph ? 'active' : ''}`}
            onClick={() => setShowGraph(!showGraph)}
            title="Show graph"
          >
            📈
          </button>
        </div>
      </div>

      {/* Expandable stats section */}
      {showStats && (
        <div className="compact-reading-stats">
          <SamplingStats getCurrentValue={getCurrentValue} label="Statistical Sampling" />
        </div>
      )}

      {/* Expandable graph section */}
      {showGraph && channelPath && (
        <div className="compact-reading-graph">
          <TimeSeriesGraph
            channelPath={channelPath}
            getValue={getCurrentValue}
            label={symbol}
            unit={unit}
            color="#c26a1a"
          />
        </div>
      )}
    </div>
  )
}
