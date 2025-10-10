import React, { useState, useEffect, useRef, useCallback } from 'react'

interface SamplingStatsProps {
  getCurrentValue: () => number | null
  label?: string
}

export function SamplingStats({ getCurrentValue, label }: SamplingStatsProps) {
  const [maxSamples, setMaxSamples] = useState<number>(10)
  const [samplingInterval, setSamplingInterval] = useState<number>(1)
  const [isRunning, setIsRunning] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const [autoStop, setAutoStop] = useState(false)

  const [samples, setSamples] = useState<number[]>([])

  const timerRef = useRef<number | null>(null)

  // Compute stats directly from samples (no separate state needed)
  const stats = React.useMemo(() => {
    if (samples.length === 0) {
      return { min: null, max: null, avg: null }
    }

    const minVal = Math.min(...samples)
    const maxVal = Math.max(...samples)
    const avgVal = samples.reduce((acc, val) => acc + val, 0) / samples.length

    return { min: minVal, max: maxVal, avg: avgVal }
  }, [samples])

  // Sampling logic
  useEffect(() => {
    if (isRunning) {
      timerRef.current = window.setInterval(() => {
        const val = getCurrentValue()
        if (val !== null && !isNaN(val)) {
          setSamples((prev) => {
            // Add new sample to the end
            const updated = [...prev, val]
            // Sliding window: keep only the most recent maxSamples (remove oldest)
            if (updated.length > maxSamples) {
              return updated.slice(-maxSamples)
            }
            // Auto-stop when we reach maxSamples (only on first fill)
            if (autoStop && updated.length >= maxSamples && prev.length < maxSamples) {
              setIsRunning(false)
            }
            return updated
          })
        }
      }, samplingInterval * 1000)

      return () => {
        if (timerRef.current !== null) {
          window.clearInterval(timerRef.current)
        }
      }
    } else {
      if (timerRef.current !== null) {
        window.clearInterval(timerRef.current)
        timerRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isRunning, samplingInterval, maxSamples, autoStop])

  const handleStart = () => setIsRunning(true)
  const handleStop = () => setIsRunning(false)
  const handleReset = () => {
    setIsRunning(false)
    setSamples([])
  }

  const formatValue = (val: number | null) => {
    if (val === null) return '—'
    return val.toFixed(4)
  }

  return (
    <div style={{
      background: 'rgba(255,255,255,.02)',
      border: '1px solid rgba(255,255,255,.1)',
      borderRadius: '6px',
      padding: '8px',
      marginTop: '8px',
      fontSize: '11px'
    }}>
      {/* Toggle Header */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          cursor: 'pointer',
          userSelect: 'none',
          marginBottom: isExpanded ? '8px' : '0'
        }}
      >
        <span style={{ fontSize: '10px', color: 'var(--text-2)' }}>
          {isExpanded ? '▼' : '▶'}
        </span>
        <span style={{ fontSize: '10px', color: 'var(--text-2)', fontWeight: 600 }}>
          {label || 'Statistical Sampling'}
        </span>
        {!isExpanded && isRunning && (
          <span style={{
            fontSize: '9px',
            color: 'var(--good)',
            background: 'rgba(0,255,0,.1)',
            padding: '2px 6px',
            borderRadius: '3px',
            fontWeight: 600
          }}>
            ● RUNNING
          </span>
        )}
        {!isExpanded && samples.length > 0 && (
          <span style={{ fontSize: '9px', color: 'var(--text-2)' }}>
            {samples.length} samples
          </span>
        )}
      </div>

      {isExpanded && (
        <>
          {/* Controls */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'auto 1fr auto 1fr',
        gap: '6px',
        alignItems: 'center',
        marginBottom: '8px'
      }}>
        <label style={{ fontSize: '10px', color: 'var(--text-2)' }}>Samples:</label>
        <select
          value={maxSamples}
          onChange={(e) => setMaxSamples(Number(e.target.value))}
          disabled={isRunning}
          style={{
            padding: '2px 4px',
            background: 'var(--bg-2)',
            color: 'var(--text-0)',
            border: '1px solid var(--border)',
            borderRadius: '3px',
            fontSize: '10px',
            cursor: isRunning ? 'not-allowed' : 'pointer',
            opacity: isRunning ? 0.5 : 1
          }}
        >
          <option value={5}>5</option>
          <option value={10}>10</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
          <option value={500}>500</option>
        </select>

        <label style={{ fontSize: '10px', color: 'var(--text-2)' }}>Interval:</label>
        <select
          value={samplingInterval}
          onChange={(e) => setSamplingInterval(Number(e.target.value))}
          disabled={isRunning}
          style={{
            padding: '2px 4px',
            background: 'var(--bg-2)',
            color: 'var(--text-0)',
            border: '1px solid var(--border)',
            borderRadius: '3px',
            fontSize: '10px',
            cursor: isRunning ? 'not-allowed' : 'pointer',
            opacity: isRunning ? 0.5 : 1
          }}
        >
          <option value={0.5}>0.5s</option>
          <option value={1}>1s</option>
          <option value={2}>2s</option>
          <option value={3}>3s</option>
          <option value={5}>5s</option>
          <option value={10}>10s</option>
        </select>
      </div>

      {/* Auto-stop checkbox */}
      <div style={{ marginBottom: '8px' }}>
        <label style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          cursor: 'pointer',
          fontSize: '10px',
          color: 'var(--text-2)',
          userSelect: 'none'
        }}>
          <input
            type="checkbox"
            checked={autoStop}
            onChange={(e) => setAutoStop(e.target.checked)}
            disabled={isRunning}
            style={{
              width: '12px',
              height: '12px',
              cursor: isRunning ? 'not-allowed' : 'pointer',
              accentColor: 'var(--accent)'
            }}
          />
          Auto-stop when samples collected
        </label>
      </div>

      {/* Buttons */}
      <div style={{ display: 'flex', gap: '4px', marginBottom: '8px' }}>
        <button
          onClick={handleStart}
          disabled={isRunning}
          style={{
            flex: 1,
            padding: '4px 8px',
            background: isRunning ? 'rgba(255,255,255,.05)' : 'var(--good)',
            color: isRunning ? 'var(--text-2)' : '#fff',
            border: '1px solid rgba(255,255,255,.15)',
            borderRadius: '3px',
            fontSize: '10px',
            fontWeight: 600,
            cursor: isRunning ? 'not-allowed' : 'pointer',
            opacity: isRunning ? 0.5 : 1
          }}
        >
          START
        </button>
        <button
          onClick={handleStop}
          disabled={!isRunning}
          style={{
            flex: 1,
            padding: '4px 8px',
            background: !isRunning ? 'rgba(255,255,255,.05)' : 'var(--warn)',
            color: !isRunning ? 'var(--text-2)' : '#fff',
            border: '1px solid rgba(255,255,255,.15)',
            borderRadius: '3px',
            fontSize: '10px',
            fontWeight: 600,
            cursor: !isRunning ? 'not-allowed' : 'pointer',
            opacity: !isRunning ? 0.5 : 1
          }}
        >
          STOP
        </button>
        <button
          onClick={handleReset}
          style={{
            flex: 1,
            padding: '4px 8px',
            background: 'rgba(255,255,255,.05)',
            color: 'var(--text-1)',
            border: '1px solid rgba(255,255,255,.15)',
            borderRadius: '3px',
            fontSize: '10px',
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          RESET
        </button>
      </div>

      {/* Stats Display */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '4px',
        padding: '6px',
        background: 'rgba(0,0,0,.2)',
        borderRadius: '3px'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '9px', color: 'var(--text-2)', marginBottom: '2px' }}>MIN</div>
          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--good)', fontVariantNumeric: 'tabular-nums' }}>
            {formatValue(stats.min)}
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '9px', color: 'var(--text-2)', marginBottom: '2px' }}>MAX</div>
          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--bad)', fontVariantNumeric: 'tabular-nums' }}>
            {formatValue(stats.max)}
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '9px', color: 'var(--text-2)', marginBottom: '2px' }}>AVG</div>
          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent)', fontVariantNumeric: 'tabular-nums' }}>
            {formatValue(stats.avg)}
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '9px', color: 'var(--text-2)', marginBottom: '2px' }}>COUNT</div>
          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-1)', fontVariantNumeric: 'tabular-nums' }}>
            {samples.length}
          </div>
        </div>
      </div>
        </>
      )}
    </div>
  )
}
