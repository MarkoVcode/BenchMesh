import React, { useEffect, useMemo, useState, useRef } from 'react'
import { TimeSeriesGraph } from './TimeSeriesGraph'
import { useMeasurement } from '../../MeasurementContext'
import { SamplingStats } from '../../SamplingStats'
import { RemoteLockWarning } from '../../components/RemoteLockWarning'
import { useRequestLog, loggedFetch } from '../../RequestLogContext'

// PSU face with two columns: Settings (editable V/A) and Readings (readonly V/A/P)
// - Settings: V and A stacked vertically. 5-digit display limit for both V and A (digits only; '.' not counted)
// - Readings: mirrors V and A and derives P = V*A, all readonly but styled identically
export function GenericOWONPSU({ channelPath, registry }: { channelPath?: string, registry?: any }) {
  const apiBase = `${window.location.protocol}//${window.location.hostname}:57666`
  const { registerSource } = useMeasurement()
  const { addLog } = useRequestLog()

  const [voltage, setVoltage] = useState('0')
  const [current, setCurrent] = useState('0')
  const [voltageLimit, setVoltageLimit] = useState('0')
  const [currentLimit, setCurrentLimit] = useState('0')
  const [outputEnabled, setOutputEnabled] = useState(false)
  const [busyOutput, setBusyOutput] = useState(false)
  const [remoteMode, setRemoteMode] = useState(false)
  const [busyRemote, setBusyRemote] = useState(false)
  const [lockEnabled, setLockEnabled] = useState(false)
  const [compulsoryLock, setCompulsoryLock] = useState(false)

  // Reading values from registry
  const [readVoltage, setReadVoltage] = useState<number | null>(null)
  const [readCurrent, setReadCurrent] = useState<number | null>(null)
  const [readPower, setReadPower] = useState<number | null>(null)
  const [voltageSymbol, setVoltageSymbol] = useState<string>('')
  const [currentSymbol, setCurrentSymbol] = useState<string>('')
  const [powerSymbol, setPowerSymbol] = useState<string>('')

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
  const onChangeVoltageLimit = (v: string) => setVoltageLimit(limitDigits(sanitizeNumber(v), 5))
  const onChangeCurrentLimit = (v: string) => setCurrentLimit(limitDigits(sanitizeNumber(v), 5))

  const vNum = useMemo(() => parseFloat(voltage || '0') || 0, [voltage])
  const aNum = useMemo(() => parseFloat(current || '0') || 0, [current])
  const pNum = useMemo(() => vNum * aNum, [vNum, aNum])

  const vDisp = voltage
  const aDisp = current
  const vLimitDisp = voltageLimit
  const aLimitDisp = currentLimit
  const pDisp = numberToDisplay(pNum)

  // Load initial voltage/current/limit values
  useEffect(() => {
    let cancelled = false
    async function loadInitial() {
      if (!channelPath) return
      const deviceId = channelPath.split('/')[3] || 'unknown'
      const channel = channelPath.split('/')[4] || '1'
      try {
        const [rv, rc, rvl, rcl] = await Promise.all([
          loggedFetch(`${apiBase}${channelPath}/voltage`, {
            method: 'GET',
            instrument: deviceId,
            channel,
            action: 'Query Voltage',
            addLog,
          }),
          loggedFetch(`${apiBase}${channelPath}/current`, {
            method: 'GET',
            instrument: deviceId,
            channel,
            action: 'Query Current',
            addLog,
          }),
          loggedFetch(`${apiBase}${channelPath}/voltage_limit`, {
            method: 'GET',
            instrument: deviceId,
            channel,
            action: 'Query Voltage Limit',
            addLog,
          }),
          loggedFetch(`${apiBase}${channelPath}/current_limit`, {
            method: 'GET',
            instrument: deviceId,
            channel,
            action: 'Query Current Limit',
            addLog,
          }),
        ])
        if (!cancelled) {
          if (rv.ok) {
            const jv = await rv.json().catch(() => null as any)
            // New format: value is an object with {si, sci, val}
            const v = (jv && jv.value?.val != null) ? String(jv.value.val).trim() : '0'
            setVoltage(limitDigits(sanitizeNumber(v), 5) || '0')
          }
          if (rc.ok) {
            const ja = await rc.json().catch(() => null as any)
            // New format: value is an object with {si, sci, val}
            const a = (ja && ja.value?.val != null) ? String(ja.value.val).trim() : '0'
            setCurrent(limitDigits(sanitizeNumber(a), 5) || '0')
          }
          if (rvl.ok) {
            const jvl = await rvl.json().catch(() => null as any)
            // New format: value is an object with {si, sci, val}
            const vl = (jvl && jvl.value?.val != null) ? String(jvl.value.val).trim() : '0'
            setVoltageLimit(limitDigits(sanitizeNumber(vl), 5) || '0')
          }
          if (rcl.ok) {
            const jcl = await rcl.json().catch(() => null as any)
            // New format: value is an object with {si, sci, val}
            const cl = (jcl && jcl.value?.val != null) ? String(jcl.value.val).trim() : '0'
            setCurrentLimit(limitDigits(sanitizeNumber(cl), 5) || '0')
          }
        }
      } catch {}
    }
    loadInitial()
    return () => { cancelled = true }
  }, [channelPath, addLog])

  // Load manifest features (lock settings)
  useEffect(() => {
    let cancelled = false
    async function loadFeatures() {
      if (!channelPath) return
      const parts = channelPath.split('/').filter(Boolean)
      if (parts.length < 3) return
      const klass = parts[1]
      const deviceId = parts[2]
      const channel = parts[3] || '1'
      const url = `${apiBase}/instruments/${klass}/${deviceId}`
      try {
        const r = await loggedFetch(url, {
          method: 'GET',
          cache: 'no-store',
          instrument: deviceId,
          channel,
          action: 'Query Features',
          addLog,
        })
        if (!r.ok) return
        const j = await r.json().catch(() => ({} as any))
        if (!cancelled) {
          if (typeof j?.lock === 'boolean') {
            setLockEnabled(j.lock)
          }
          if (typeof j?.compulsory_lock === 'boolean') {
            setCompulsoryLock(j.compulsory_lock)
          }
        }
      } catch {}
    }
    loadFeatures()
    return () => { cancelled = true }
  }, [apiBase, channelPath, addLog])

  // Monitor WebSocket registry for readings (VOUT, IOUT, POUT)
  useEffect(() => {
    if (!registry || !channelPath) return

    const parts = channelPath.split('/').filter(Boolean)
    if (parts.length < 4) return

    const deviceId = parts[2]
    const channel = parts[3]
    const klass = parts[1]

    const deviceData = registry[deviceId]
    if (!deviceData) return

    const statusKey = `status_ch${channel}`
    const status = deviceData[klass]?.[statusKey]
    if (!status) return

    // Update readings from registry
    // New format: VOUT, IOUT, POUT with nested structure {si: {number, symbol?}, sci, val}
    if (status.VOUT?.si?.number) {
      const num = parseFloat(status.VOUT.si.number)
      if (!isNaN(num)) setReadVoltage(num)
      setVoltageSymbol(status.VOUT.si.symbol || '')
    }

    if (status.IOUT?.si?.number) {
      const num = parseFloat(status.IOUT.si.number)
      if (!isNaN(num)) setReadCurrent(num)
      setCurrentSymbol(status.IOUT.si.symbol || '')
    }

    if (status.POUT?.si?.number) {
      const num = parseFloat(status.POUT.si.number)
      if (!isNaN(num)) setReadPower(num)
      setPowerSymbol(status.POUT.si.symbol || '')
    }

    // Update output enabled status
    if (typeof status.OUTPUT === 'string') {
      setOutputEnabled(status.OUTPUT === 'ON')
    }

    // Update remote mode status
    if (typeof status.REMOTE === 'string') {
      setRemoteMode(status.REMOTE === 'ON')
    }
  }, [registry, channelPath])

  const handleRemoteToggle = async () => {
    if (!channelPath || busyRemote) return
    setBusyRemote(true)
    const deviceId = channelPath.split('/')[3] || 'unknown'
    const channel = channelPath.split('/')[4] || '1'
    try {
      const next = !remoteMode
      const cmd = next ? 'ON' : 'OFF'
      await loggedFetch(`${apiBase}${channelPath}/remote/${cmd}`, {
        method: 'POST',
        instrument: deviceId,
        channel,
        action: next ? 'Enable Remote Mode' : 'Disable Remote Mode',
        addLog,
      })
      setRemoteMode(next)
    } catch (err) {
      console.debug('Remote toggle failed', err)
    } finally {
      setBusyRemote(false)
    }
  }

  // Determine if controls should be shown based on lock settings
  const shouldShowControls = !lockEnabled || !compulsoryLock || remoteMode
  const shouldShowWarning = lockEnabled && compulsoryLock && !remoteMode

  return (
    <div className="psu-face">
      <div className="psu-main">
        <div className="psu-section">
          <div className="psu-section-title">Settings</div>

          {/* Remote Mode Toggle - visible only when lock is enabled */}
          {lockEnabled && (
            <div className="psu-block" style={{ gridTemplateColumns: 'auto 1fr', marginBottom: '12px' }}>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  cursor: busyRemote ? 'wait' : 'pointer',
                  fontSize: '14px',
                  fontWeight: 600,
                  color: remoteMode ? 'var(--good)' : 'var(--text-2)',
                  gap: '8px',
                  opacity: busyRemote ? 0.5 : 1
                }}
                title={`POST ${channelPath}/remote/${remoteMode ? 'OFF' : 'ON'}`}
              >
                <input
                  type="checkbox"
                  checked={remoteMode}
                  onChange={handleRemoteToggle}
                  disabled={busyRemote}
                  style={{
                    width: '16px',
                    height: '16px',
                    cursor: busyRemote ? 'wait' : 'pointer',
                    accentColor: 'var(--good)'
                  }}
                />
                <span>Enable Remote Mode</span>
                {busyRemote && <span className="spinner" style={{ marginLeft: '4px' }} />}
              </label>
            </div>
          )}

          {/* Settings controls - visibility depends on lock settings */}
          {shouldShowControls && (
            <>
              <EditableBigNumber kind="U" label={<Label symbol="U" unit="V"/>} value={vDisp} onChange={onChangeVoltage} withSet channelPath={channelPath} apiBase={apiBase} addLog={addLog} />
              <EditableBigNumber kind="I" label={<Label symbol="I" unit="A"/>} value={aDisp} onChange={onChangeCurrent} withSet channelPath={channelPath} apiBase={apiBase} addLog={addLog} />
              <div className="psu-section-title" style={{ marginTop: '16px' }}>Limits</div>
              <EditableBigNumber kind="UL" label={<Label symbol="U Limit" unit="V"/>} value={vLimitDisp} onChange={onChangeVoltageLimit} withSet channelPath={channelPath} apiBase={apiBase} addLog={addLog} />
              <EditableBigNumber kind="IL" label={<Label symbol="I Limit" unit="A"/>} value={aLimitDisp} onChange={onChangeCurrentLimit} withSet channelPath={channelPath} apiBase={apiBase} addLog={addLog} />
            </>
          )}

          {/* Warning when compulsory lock is enabled and in local mode */}
          {shouldShowWarning && <RemoteLockWarning />}
        </div>
        <div className="psu-section">
          <div className="psu-section-title">Readings</div>
          <ReadonlyBigNumber kind="U" label={<Label symbol="U" unit={`${voltageSymbol}V`}/>} value={readVoltage !== null ? readVoltage.toFixed(4) : "—"} channelPath={channelPath} parameter="voltage" />
          <ReadonlyBigNumber kind="I" label={<Label symbol="I" unit={`${currentSymbol}A`}/>} value={readCurrent !== null ? readCurrent.toFixed(4) : "—"} channelPath={channelPath} parameter="current" />
          <ReadonlyBigNumber kind="P" label={<Label symbol="P" unit={`${powerSymbol}W`}/>} value={readPower !== null ? readPower.toFixed(4) : "—"} channelPath={channelPath} parameter="power" />
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
            const deviceId = channelPath.split('/')[3] || 'unknown'
            const channel = channelPath.split('/')[4] || '1'
            try {
              const next = !outputEnabled
              const cmd = next ? 'ON' : 'OFF'
              // Use partial name - API will resolve to set_output
              await loggedFetch(`${apiBase}${channelPath}/output/${cmd}`, {
                method: 'POST',
                instrument: deviceId,
                channel,
                action: next ? 'Enable Output' : 'Disable Output',
                addLog,
              })
              setOutputEnabled(next)
            } catch {} finally { setBusyOutput(false) }
          }}
          title={`POST ${channelPath}/output/${outputEnabled ? 'OFF' : 'ON'}`}
        >
          {busyOutput ? (<><span className="spinner"/>{outputEnabled ? 'DISABLE OUTPUT' : 'ENABLE OUTPUT'}</>) : (outputEnabled ? 'DISABLE OUTPUT' : 'ENABLE OUTPUT')}
        </button>
      </div>
      <TimeSeriesGraph
        channelPath={channelPath}
        getValue={() => vNum}
        label="Voltage"
        unit="V"
        color="#ff4444"
      />
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

function EditableBigNumber({ kind, label, value, onChange, withSet, channelPath, apiBase, addLog }: { kind?: 'U' | 'I' | 'UL' | 'IL', label: React.ReactNode, value: string, onChange: (v: string) => void, withSet?: boolean, channelPath?: string, apiBase?: string, addLog?: (entry: any) => void }) {
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
            kind === 'I' ? `POST ${channelPath}/current/{value}` :
            kind === 'UL' ? `POST ${channelPath}/voltage_limit/{value}` :
            kind === 'IL' ? `POST ${channelPath}/current_limit/{value}` : ''
          } onClick={async (e) => {
            e.preventDefault(); e.stopPropagation();
            if (busy) return
            setBusy(true)
            const deviceId = channelPath?.split('/')[3] || 'unknown'
            const channel = channelPath?.split('/')[4] || '1'
            try {
              const endp = (kind as string | undefined) || ((label as any)?.props?.symbol as string | undefined)
              const val = value || '0'
              let url: string | undefined
              let action = 'Set'
              let paramName = ''
              if (endp === 'U') {
                url = `${apiBase}${channelPath}/voltage/${val}`
                action = 'Set Voltage'
                paramName = 'voltage'
              }
              if (endp === 'I') {
                url = `${apiBase}${channelPath}/current/${val}`
                action = 'Set Current'
                paramName = 'current'
              }
              if (endp === 'UL') {
                url = `${apiBase}${channelPath}/voltage_limit/${val}`
                action = 'Set Voltage Limit'
                paramName = 'voltage_limit'
              }
              if (endp === 'IL') {
                url = `${apiBase}${channelPath}/current_limit/${val}`
                action = 'Set Current Limit'
                paramName = 'current_limit'
              }
              if (url && addLog) {
                await loggedFetch(url, {
                  method: 'POST',
                  instrument: deviceId,
                  channel,
                  action,
                  parameters: { [paramName]: parseFloat(val) },
                  addLog,
                })
              }
            } catch (err) {
              console.debug('SET failed', err)
            } finally { setBusy(false) }
          }}>{busy ? (<><span className="spinner"/>SET</>) : 'SET'}</button>
          <span className="psu-api" title={
            kind === 'U' ? `GET ${channelPath}/voltage` :
            kind === 'I' ? `GET ${channelPath}/current` :
            kind === 'UL' ? `GET ${channelPath}/voltage_limit` :
            kind === 'IL' ? `GET ${channelPath}/current_limit` : (channelPath || '')
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


export default GenericOWONPSU
