import React, { useEffect, useMemo, useState, useRef } from 'react'
import { TimeSeriesGraph } from './TimeSeriesGraph'
import { useMeasurement } from '../../MeasurementContext'
import { SamplingStats } from '../../SamplingStats'

// PSU face with two columns: Settings (editable V/A) and Readings (readonly V/A/P)
// - Settings: V and A stacked vertically. 5-digit display limit for both V and A (digits only; '.' not counted)
// - Readings: mirrors V and A and derives P = V*A, all readonly but styled identically
export function GenericPSU({ channelPath, registry }: { channelPath?: string, registry?: any }) {
  const apiBase = `${window.location.protocol}//${window.location.hostname}:57666`
  const { registerSource } = useMeasurement()

  const [voltage, setVoltage] = useState('0')
  const [current, setCurrent] = useState('0')
  const [outputEnabled, setOutputEnabled] = useState(false)
  const [busyOutput, setBusyOutput] = useState(false)

  // Register measurement sources
  useEffect(() => {
    if (!channelPath) return

    const deviceId = channelPath.split('/')[3] || 'unknown'
    const channel = channelPath.split('/')[4] || '1'

    registerSource({
      id: `${deviceId}-${channel}-U`,
      deviceId,
      channelPath,
      parameter: 'voltage',
      label: `${deviceId} Ch${channel} U`,
      unit: 'V'
    })

    registerSource({
      id: `${deviceId}-${channel}-I`,
      deviceId,
      channelPath,
      parameter: 'current',
      label: `${deviceId} Ch${channel} I`,
      unit: 'A'
    })

    registerSource({
      id: `${deviceId}-${channel}-P`,
      deviceId,
      channelPath,
      parameter: 'power',
      label: `${deviceId} Ch${channel} P`,
      unit: 'W'
    })
  }, [channelPath, registerSource])

  const onChangeVoltage = (v: string) => setVoltage(limitDigits(sanitizeNumber(v), 5))
  const onChangeCurrent = (v: string) => setCurrent(limitDigits(sanitizeNumber(v), 5))

  const vNum = useMemo(() => parseFloat(voltage || '0') || 0, [voltage])
  const aNum = useMemo(() => parseFloat(current || '0') || 0, [current])
  const pNum = useMemo(() => vNum * aNum, [vNum, aNum])

  const vDisp = voltage
  const aDisp = current
  const pDisp = numberToDisplay(pNum)

  useEffect(() => {
    let cancelled = false
    async function loadInitial() {
      if (!channelPath) return
      try {
        const [rv, rc] = await Promise.all([
          fetch(`${apiBase}${channelPath}/voltage`),
          fetch(`${apiBase}${channelPath}/current`),
        ])
        if (!cancelled) {
          if (rv.ok) {
            const jv = await rv.json().catch(() => null as any)
            const v = (jv && jv.value != null) ? String(jv.value).trim() : '0'
            setVoltage(limitDigits(sanitizeNumber(v), 5) || '0')
          }
          if (rc.ok) {
            const ja = await rc.json().catch(() => null as any)
            const a = (ja && ja.value != null) ? String(ja.value).trim() : '0'
            setCurrent(limitDigits(sanitizeNumber(a), 5) || '0')
          }
        }
      } catch {}
    }
    loadInitial()
    return () => { cancelled = true }
  }, [channelPath])

  return (
    <div className="psu-face">
      <div className="psu-main">
        <div className="psu-section">
          <div className="psu-section-title">Settings</div>
          <EditableBigNumber kind="U" label={<Label symbol="U" unit="V"/>} value={vDisp} onChange={onChangeVoltage} withSet channelPath={channelPath} apiBase={apiBase} />
          <EditableBigNumber kind="I" label={<Label symbol="I" unit="A"/>} value={aDisp} onChange={onChangeCurrent} withSet channelPath={channelPath} apiBase={apiBase} />
        </div>
        <div className="psu-section">
          <div className="psu-section-title">Readings</div>
          <ReadonlyBigNumber kind="U" label={<Label symbol="U" unit="V"/>} value={"00000"} channelPath={channelPath} parameter="voltage" />
          <ReadonlyBigNumber kind="I" label={<Label symbol="I" unit="A"/>} value={"00000"} channelPath={channelPath} parameter="current" />
          <ReadonlyBigNumber kind="P" label={<Label symbol="P" unit="W"/>} value={"00000"} channelPath={channelPath} parameter="power" />
        </div>
      <hr className="sep"/>
      </div>
      <div className="psu-actions">
        <button
          className={`psu-set psu-output ${outputEnabled ? 'danger' : ''}`}
          style={{ width: '100%', padding: '8px 12px', fontSize: '12px' }}
          onClick={async (e) => {
            e.preventDefault(); e.stopPropagation();
            if (!channelPath || busyOutput) return
            setBusyOutput(true)
            try {
              const next = !outputEnabled
              const cmd = next ? 'ON' : 'OFF'
              // Use partial name - API will resolve to set_output
              await fetch(`${apiBase}${channelPath}/output/${cmd}`, { method: 'POST' })
              setOutputEnabled(next)
            } catch {} finally { setBusyOutput(false) }
          }}
          title={`POST ${channelPath}/output/${outputEnabled ? 'OFF' : 'ON'}`}
        >
          {busyOutput ? (<><span className="spinner"/>{outputEnabled ? 'DISABLE OUTPUT' : 'ENABLE OUTPUT'}</>) : (outputEnabled ? 'DISABLE OUTPUT' : 'ENABLE OUTPUT')}
        </button>
      </div>
      <TimeSeriesGraph channelPath={channelPath} maxDataPoints={100} updateInterval={1000} />
    </div>
  )
}

function sanitizeNumber(input: string): string {
  // Keep digits and at most one '.'
  let s = (input || '').replace(/[^\d.]/g, '')
  const firstDot = s.indexOf('.')
  if (firstDot !== -1) s = s.slice(0, firstDot + 1) + s.slice(firstDot + 1).replace(/\./g, '')
  return s
}

function limitDigits(input: string, maxDigits: number): string {
  let digits = 0
  let out = ''
  for (const ch of input) {
    if (ch >= '0' && ch <= '9') {
      if (digits >= maxDigits) break
      digits++
      out += ch
    } else if (ch === '.') {
      out += ch
    }
  }
  return out
}

function numberToDisplay(n: number): string {
  // Keep a compact representation while not exceeding 5 significant digits where feasible
  if (!isFinite(n)) return '0'
  const abs = Math.abs(n)
  if (abs === 0) return '0'
  if (abs >= 10000) return n.toExponential(2)
  const s = n.toString()
  const [i, f = ''] = s.split('.')
  const room = Math.max(0, 5 - i.replace('-', '').length)
  const frac = f.slice(0, room)
  return frac.length ? `${i}.${frac}` : i
}

function EditableBigNumber({ kind, label, value, onChange, withSet, channelPath, apiBase }: { kind?: 'U' | 'I', label: React.ReactNode, value: string, onChange: (v: string) => void, withSet?: boolean, channelPath?: string, apiBase?: string }) {
  const [busy, setBusy] = useState(false)
  return (
    <div className="psu-block">
      <div className="psu-label">{label}</div>
      <label className="psu-number editable" title="Click to edit">
        <input
          className="psu-input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        <span aria-hidden>{value || '0'}</span>
      </label>
      {withSet && channelPath && (
        <>
          <button className="psu-set" type="button" disabled={busy} title={
            kind === 'U' ? `POST ${channelPath}/voltage/{value}` :
            kind === 'I' ? `POST ${channelPath}/current/{value}` : ''
          } onClick={async (e) => {
            e.preventDefault(); e.stopPropagation();
            if (busy) return
            setBusy(true)
            try {
              const endp = (kind as string | undefined) || ((label as any)?.props?.symbol as string | undefined)
              const val = value || '0'
              let url: string | undefined
              if (endp === 'U') url = `${apiBase}${channelPath}/voltage/${val}`
              if (endp === 'I') url = `${apiBase}${channelPath}/current/${val}`
              if (url) await fetch(url, { method: 'POST' })
            } catch (err) {
              console.debug('SET failed', err)
            } finally { setBusy(false) }
          }}>{busy ? (<><span className="spinner"/>SET</>) : 'SET'}</button>
          <span className="psu-api" title={
            kind === 'U' ? `GET ${channelPath}/voltage` :
            kind === 'I' ? `GET ${channelPath}/current` : (channelPath || '')
          }>API</span>
        </>
      )}
    </div>
  )
}

function ReadonlyBigNumber({ kind, label, value, channelPath, parameter }: { kind?: 'U' | 'I' | 'P', label: React.ReactNode, value: string, channelPath?: string, parameter?: string }) {
  const { selectedForRecord, selectedForGraph, toggleRecord, toggleGraph } = useMeasurement()
  const valueRef = useRef<string>(value)

  // Keep ref updated with latest value
  useEffect(() => {
    valueRef.current = value
  }, [value])

  const sourceId = useMemo(() => {
    if (!channelPath || !parameter) return ''
    const deviceId = channelPath.split('/')[3] || 'unknown'
    const channel = channelPath.split('/')[4] || '1'
    return `${deviceId}-${channel}-${kind}`
  }, [channelPath, parameter, kind])

  const getCurrentValue = () => {
    const numericValue = parseFloat(valueRef.current)
    return isNaN(numericValue) ? null : numericValue
  }

  return (
    <>
      <div className="psu-block" style={{ gridTemplateColumns: 'auto 1fr auto auto auto' }}>
        <div className="psu-label">{label}</div>
        <span className="psu-number readonly" aria-hidden>
          <span>{value || '0'}</span>
        </span>
        {channelPath && (
          <>
            <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
              <label
                style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '10px', color: 'var(--text-2)' }}
                title="Record in table"
              >
                <input
                  type="checkbox"
                  checked={selectedForRecord.has(sourceId)}
                  onChange={() => toggleRecord(sourceId)}
                  style={{ width: '12px', height: '12px', cursor: 'pointer', accentColor: 'var(--accent)' }}
                />
                <span style={{ marginLeft: '2px' }}>📊</span>
              </label>
              <label
                style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '10px', color: 'var(--text-2)' }}
                title="Show in graph"
              >
                <input
                  type="checkbox"
                  checked={selectedForGraph.has(sourceId)}
                  onChange={() => toggleGraph(sourceId)}
                  style={{ width: '12px', height: '12px', cursor: 'pointer', accentColor: 'var(--good)' }}
                />
                <span style={{ marginLeft: '2px' }}>📈</span>
              </label>
            </div>
            <span className="psu-api" title={
              kind === 'U' ? `GET ${channelPath}/output_voltage` :
              kind === 'I' ? `GET ${channelPath}/output_current` :
              kind === 'P' ? `GET ${channelPath}/output_power` : ''
            }>API</span>
          </>
        )}
      </div>
      <SamplingStats getCurrentValue={getCurrentValue} label="Statistical Sampling" />
    </>
  )
}

function Label({ symbol, unit }: { symbol: string, unit: string }) {
  return (
    <>
      <span className="psu-symbol">{symbol}</span><span className="psu-unit">[{unit}]</span>
    </>
  )
}


export default GenericPSU
