import React, { useState, useEffect, useRef } from 'react'
import { useMeasurement } from './MeasurementContext'

interface MeasurementRecord {
  timestamp: Date
  values: Record<string, number | null>
}

const FREQUENCIES = [
  { label: '0.5s', value: 500 },
  { label: '1s', value: 1000 },
  { label: '2s', value: 2000 },
  { label: '4s', value: 4000 },
  { label: '5s', value: 5000 },
  { label: '10s', value: 10000 }
]

export function MeasurementStatusBar() {
  const [recordOpen, setRecordOpen] = useState(false)
  const [graphOpen, setGraphOpen] = useState(false)
  const [recordHeight, setRecordHeight] = useState(300)
  const [graphHeight, setGraphHeight] = useState(300)
  const [recordFrequency, setRecordFrequency] = useState(1000)
  const [graphFrequency, setGraphFrequency] = useState(1000)
  const [records, setRecords] = useState<MeasurementRecord[]>([])
  const [isRecording, setIsRecording] = useState(false)
  const [isGraphing, setIsGraphing] = useState(false)

  const { selectedForRecord, selectedForGraph, sources } = useMeasurement()

  const apiBase = `${window.location.protocol}//${window.location.hostname}:57666`

  // Recording logic
  useEffect(() => {
    if (!isRecording || selectedForRecord.size === 0) return

    const interval = setInterval(async () => {
      const values: Record<string, number | null> = {}

      for (const sourceId of selectedForRecord) {
        const source = sources.get(sourceId)
        if (!source) continue

        try {
          const endpoint = `${apiBase}${source.channelPath}/query_output_${source.parameter.toLowerCase()}`
          const res = await fetch(endpoint)
          if (res.ok) {
            const data = await res.json()
            values[sourceId] = parseFloat(data.value) || null
          } else {
            values[sourceId] = null
          }
        } catch {
          values[sourceId] = null
        }
      }

      setRecords(prev => [...prev, { timestamp: new Date(), values }])
    }, recordFrequency)

    return () => clearInterval(interval)
  }, [isRecording, recordFrequency, selectedForRecord, sources, apiBase])

  const exportCSV = () => {
    if (records.length === 0) return

    const headers = ['Timestamp', ...Array.from(selectedForRecord).map(id => {
      const source = sources.get(id)
      return source ? `${source.label} [${source.unit}]` : id
    })]

    const rows = records.map(record => {
      const timestamp = record.timestamp.toLocaleString()
      const values = Array.from(selectedForRecord).map(id =>
        record.values[id] !== null ? record.values[id] : ''
      )
      return [timestamp, ...values].join(',')
    })

    const csv = [headers.join(','), ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `measurements_${new Date().toISOString()}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const clearRecords = () => {
    setRecords([])
  }

  return (
    <>
      <div style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        background: 'linear-gradient(180deg, var(--bg-1), var(--bg-2))',
        borderTop: '1px solid var(--border)',
        padding: '8px 16px',
        display: 'flex',
        gap: '8px',
        zIndex: 100
      }}>
        <button
          onClick={() => {
            setRecordOpen(!recordOpen)
            if (graphOpen && !recordOpen) setGraphOpen(false)
          }}
          style={{
            padding: '6px 12px',
            background: recordOpen ? 'var(--accent)' : 'rgba(255,255,255,.05)',
            color: recordOpen ? '#000' : 'var(--text-0)',
            border: '1px solid var(--border)',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '12px',
            fontWeight: 600
          }}
        >
          📊 Measurements Record
        </button>
        <button
          onClick={() => {
            setGraphOpen(!graphOpen)
            if (recordOpen && !graphOpen) setRecordOpen(false)
          }}
          style={{
            padding: '6px 12px',
            background: graphOpen ? 'var(--accent)' : 'rgba(255,255,255,.05)',
            color: graphOpen ? '#000' : 'var(--text-0)',
            border: '1px solid var(--border)',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '12px',
            fontWeight: 600
          }}
        >
          📈 Measurements Graph
        </button>
      </div>

      {recordOpen && (
        <RecordPanel
          height={recordHeight}
          onHeightChange={setRecordHeight}
          frequency={recordFrequency}
          onFrequencyChange={setRecordFrequency}
          records={records}
          isRecording={isRecording}
          onToggleRecording={() => setIsRecording(!isRecording)}
          onExportCSV={exportCSV}
          onClear={clearRecords}
          selectedSources={Array.from(selectedForRecord).map(id => sources.get(id)!).filter(Boolean)}
        />
      )}

      {graphOpen && (
        <GraphPanel
          height={graphHeight}
          onHeightChange={setGraphHeight}
          frequency={graphFrequency}
          onFrequencyChange={setGraphFrequency}
          isGraphing={isGraphing}
          onToggleGraphing={() => setIsGraphing(!isGraphing)}
          selectedSources={Array.from(selectedForGraph).map(id => sources.get(id)!).filter(Boolean)}
        />
      )}
    </>
  )
}

function RecordPanel({
  height,
  onHeightChange,
  frequency,
  onFrequencyChange,
  records,
  isRecording,
  onToggleRecording,
  onExportCSV,
  onClear,
  selectedSources
}: any) {
  const resizeRef = useRef<HTMLDivElement>(null)
  const [isDragging, setIsDragging] = useState(false)

  useEffect(() => {
    if (!isDragging) return

    const handleMouseMove = (e: MouseEvent) => {
      const newHeight = window.innerHeight - e.clientY
      onHeightChange(Math.max(200, Math.min(800, newHeight)))
    }

    const handleMouseUp = () => setIsDragging(false)

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging, onHeightChange])

  return (
    <div style={{
      position: 'fixed',
      bottom: 40,
      left: 0,
      right: 0,
      height: `${height}px`,
      background: 'var(--bg-0)',
      borderTop: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      zIndex: 99
    }}>
      <div
        ref={resizeRef}
        onMouseDown={() => setIsDragging(true)}
        style={{
          height: '6px',
          cursor: 'ns-resize',
          background: 'var(--border)',
          borderBottom: '1px solid var(--border)'
        }}
      />

      <div style={{ padding: '12px', borderBottom: '1px solid var(--border)', display: 'flex', gap: '12px', alignItems: 'center' }}>
        <label style={{ fontSize: '12px', color: 'var(--text-1)' }}>
          Frequency:
          <select
            value={frequency}
            onChange={(e) => onFrequencyChange(Number(e.target.value))}
            style={{
              marginLeft: '8px',
              padding: '4px 8px',
              background: 'var(--bg-2)',
              color: 'var(--text-0)',
              border: '1px solid var(--border)',
              borderRadius: '4px',
              fontSize: '12px'
            }}
          >
            {FREQUENCIES.map(f => (
              <option key={f.value} value={f.value}>{f.label}</option>
            ))}
          </select>
        </label>

        <button
          onClick={onToggleRecording}
          disabled={selectedSources.length === 0}
          style={{
            padding: '6px 12px',
            background: isRecording ? 'var(--bad)' : 'var(--good)',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: selectedSources.length === 0 ? 'not-allowed' : 'pointer',
            fontSize: '12px',
            fontWeight: 600,
            opacity: selectedSources.length === 0 ? 0.5 : 1
          }}
        >
          {isRecording ? '⏹ Stop' : '▶ Start'} Recording
        </button>

        <button
          onClick={onExportCSV}
          disabled={records.length === 0}
          style={{
            padding: '6px 12px',
            background: 'var(--accent)',
            color: '#000',
            border: 'none',
            borderRadius: '4px',
            cursor: records.length === 0 ? 'not-allowed' : 'pointer',
            fontSize: '12px',
            fontWeight: 600,
            opacity: records.length === 0 ? 0.5 : 1
          }}
        >
          💾 Export CSV
        </button>

        <button
          onClick={onClear}
          disabled={records.length === 0}
          style={{
            padding: '6px 12px',
            background: 'rgba(255,255,255,.05)',
            color: 'var(--text-1)',
            border: '1px solid var(--border)',
            borderRadius: '4px',
            cursor: records.length === 0 ? 'not-allowed' : 'pointer',
            fontSize: '12px',
            opacity: records.length === 0 ? 0.5 : 1
          }}
        >
          🗑 Clear
        </button>

        <span style={{ marginLeft: 'auto', fontSize: '12px', color: 'var(--text-2)' }}>
          {records.length} records | {selectedSources.length} sources selected
        </span>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '12px' }}>
        {selectedSources.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-2)', padding: '40px' }}>
            No measurements selected. Check measurement boxes in instrument panels above.
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ background: 'var(--bg-2)', position: 'sticky', top: 0 }}>
                <th style={{ padding: '8px', textAlign: 'left', borderBottom: '1px solid var(--border)', color: 'var(--text-1)' }}>
                  Timestamp
                </th>
                {selectedSources.map((source: any) => (
                  <th key={source.id} style={{ padding: '8px', textAlign: 'right', borderBottom: '1px solid var(--border)', color: 'var(--text-1)' }}>
                    {source.label} [{source.unit}]
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {records.map((record: MeasurementRecord, idx: number) => (
                <tr key={idx} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '6px 8px', color: 'var(--text-2)' }}>
                    {record.timestamp.toLocaleString()}
                  </td>
                  {selectedSources.map((source: any) => (
                    <td key={source.id} style={{ padding: '6px 8px', textAlign: 'right', color: 'var(--text-0)', fontVariantNumeric: 'tabular-nums' }}>
                      {record.values[source.id] !== null ? record.values[source.id]?.toFixed(3) : '-'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function GraphPanel({
  height,
  onHeightChange,
  frequency,
  onFrequencyChange,
  isGraphing,
  onToggleGraphing,
  selectedSources
}: any) {
  const resizeRef = useRef<HTMLDivElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [graphData, setGraphData] = useState<Map<string, Array<{ time: number, value: number }>>>(new Map())

  const apiBase = `${window.location.protocol}//${window.location.hostname}:57666`
  const { sources } = useMeasurement()

  useEffect(() => {
    if (!isDragging) return

    const handleMouseMove = (e: MouseEvent) => {
      const newHeight = window.innerHeight - e.clientY
      onHeightChange(Math.max(200, Math.min(800, newHeight)))
    }

    const handleMouseUp = () => setIsDragging(false)

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging, onHeightChange])

  // Fetch data for graphing
  useEffect(() => {
    if (!isGraphing || selectedSources.length === 0) return

    const interval = setInterval(async () => {
      const now = Date.now()

      for (const source of selectedSources) {
        try {
          const endpoint = `${apiBase}${source.channelPath}/query_output_${source.parameter.toLowerCase()}`
          const res = await fetch(endpoint)
          if (res.ok) {
            const data = await res.json()
            const value = parseFloat(data.value) || 0

            setGraphData(prev => {
              const next = new Map(prev)
              const points = next.get(source.id) || []
              next.set(source.id, [...points, { time: now, value }].slice(-100))
              return next
            })
          }
        } catch {}
      }
    }, frequency)

    return () => clearInterval(interval)
  }, [isGraphing, frequency, selectedSources, apiBase])

  // Draw graph
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const width = canvas.width
    const height = canvas.height
    const padding = { top: 40, right: 80, bottom: 40, left: 80 }

    ctx.fillStyle = '#0f1216'
    ctx.fillRect(0, 0, width, height)

    if (selectedSources.length === 0 || graphData.size === 0) {
      ctx.fillStyle = '#666'
      ctx.font = '14px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText('No data to display', width / 2, height / 2)
      return
    }

    const colors = ['#ff4444', '#44ff44', '#4444ff', '#ffff44', '#ff44ff', '#44ffff']

    // Draw grid
    ctx.strokeStyle = '#202737'
    ctx.lineWidth = 1
    for (let i = 0; i <= 5; i++) {
      const y = padding.top + (i / 5) * (height - padding.top - padding.bottom)
      ctx.beginPath()
      ctx.moveTo(padding.left, y)
      ctx.lineTo(width - padding.right, y)
      ctx.stroke()
    }

    // Draw each source
    selectedSources.forEach((source: any, sourceIdx: number) => {
      const points = graphData.get(source.id) || []
      if (points.length < 2) return

      const color = colors[sourceIdx % colors.length]
      const values = points.map(p => p.value)
      const min = Math.min(...values)
      const max = Math.max(...values)
      const range = max - min || 1

      ctx.strokeStyle = color
      ctx.lineWidth = 2
      ctx.beginPath()

      points.forEach((point, idx) => {
        const x = padding.left + (idx / (points.length - 1)) * (width - padding.left - padding.right)
        const y = padding.top + (height - padding.top - padding.bottom) * (1 - (point.value - min) / range)

        if (idx === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      })
      ctx.stroke()

      // Draw legend
      ctx.fillStyle = color
      ctx.fillRect(padding.left + sourceIdx * 120, 10, 20, 3)
      ctx.fillStyle = '#b7c0d1'
      ctx.font = '11px sans-serif'
      ctx.textAlign = 'left'
      ctx.fillText(`${source.label} [${source.unit}]`, padding.left + sourceIdx * 120 + 25, 15)

      // Draw scale on right
      ctx.fillStyle = color
      ctx.textAlign = 'left'
      ctx.font = '10px sans-serif'
      ctx.fillText(`${max.toFixed(2)} ${source.unit}`, width - padding.right + 5, padding.top + sourceIdx * 20)
      ctx.fillText(`${min.toFixed(2)} ${source.unit}`, width - padding.right + 5, padding.top + sourceIdx * 20 + 10)
    })

  }, [graphData, selectedSources])

  const clearGraph = () => {
    setGraphData(new Map())
  }

  return (
    <div style={{
      position: 'fixed',
      bottom: 40,
      left: 0,
      right: 0,
      height: `${height}px`,
      background: 'var(--bg-0)',
      borderTop: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      zIndex: 99
    }}>
      <div
        ref={resizeRef}
        onMouseDown={() => setIsDragging(true)}
        style={{
          height: '6px',
          cursor: 'ns-resize',
          background: 'var(--border)',
          borderBottom: '1px solid var(--border)'
        }}
      />

      <div style={{ padding: '12px', borderBottom: '1px solid var(--border)', display: 'flex', gap: '12px', alignItems: 'center' }}>
        <label style={{ fontSize: '12px', color: 'var(--text-1)' }}>
          Frequency:
          <select
            value={frequency}
            onChange={(e) => onFrequencyChange(Number(e.target.value))}
            style={{
              marginLeft: '8px',
              padding: '4px 8px',
              background: 'var(--bg-2)',
              color: 'var(--text-0)',
              border: '1px solid var(--border)',
              borderRadius: '4px',
              fontSize: '12px'
            }}
          >
            {FREQUENCIES.map(f => (
              <option key={f.value} value={f.value}>{f.label}</option>
            ))}
          </select>
        </label>

        <button
          onClick={onToggleGraphing}
          disabled={selectedSources.length === 0}
          style={{
            padding: '6px 12px',
            background: isGraphing ? 'var(--bad)' : 'var(--good)',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: selectedSources.length === 0 ? 'not-allowed' : 'pointer',
            fontSize: '12px',
            fontWeight: 600,
            opacity: selectedSources.length === 0 ? 0.5 : 1
          }}
        >
          {isGraphing ? '⏹ Stop' : '▶ Start'} Graphing
        </button>

        <button
          onClick={clearGraph}
          style={{
            padding: '6px 12px',
            background: 'rgba(255,255,255,.05)',
            color: 'var(--text-1)',
            border: '1px solid var(--border)',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          🗑 Clear
        </button>

        <span style={{ marginLeft: 'auto', fontSize: '12px', color: 'var(--text-2)' }}>
          {selectedSources.length} sources selected
        </span>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '12px', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        {selectedSources.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-2)' }}>
            No measurements selected. Check measurement boxes in instrument panels above.
          </div>
        ) : (
          <canvas
            ref={canvasRef}
            width={1200}
            height={(height - 100) * 2}
            style={{ width: '100%', height: height - 100, display: 'block' }}
          />
        )}
      </div>
    </div>
  )
}
