import React, { useEffect, useMemo, useState } from 'react'

// Generic DMM component styled similarly to GenericPSU
// - Before rendering, fetch GET /instruments/DMM/{device_id} to obtain features (modes list)
// - Settings: full-width dropdown to select mode; hover tooltip shows POST endpoint template
// - Readings: placeholder big-number display U[V] with 5-digit readonly value
export function GenericDMM({ channelPath }: { channelPath?: string }) {
  const apiBase = `${window.location.protocol}//${window.location.hostname}:57666`

  // Parse class, device id, and channel from channelPath like /instruments/DMM/{id}/{ch}
  const { klass, deviceId, channel } = useMemo(() => parsePath(channelPath), [channelPath])

  const [modes, setModes] = useState<string[]>([])
  const [mode, setMode] = useState<string>('')

  // Fetch class features (modes) before rendering content
  useEffect(() => {
    let cancelled = false
    async function loadFeatures() {
      if (!deviceId || !klass) return
      try {
        const r = await fetch(`${apiBase}/instruments/${klass}/${deviceId}`)
        if (!r.ok) return
        const j = await r.json().catch(() => ({} as any))
        if (!cancelled) {
          const mm = Array.isArray(j?.modes) ? (j.modes as any[]).map(String) : []
          setModes(mm)
          if (!mode && mm.length) setMode(String(mm[0]))
        }
      } catch {}
    }
    loadFeatures()
    return () => { cancelled = true }
  }, [apiBase, deviceId, klass])

  const endpointTemplate = useMemo(() => {
    const k = klass || 'DMM'
    const did = deviceId || '{id}'
    const ch = channel || '1'
    return `/instruments/${k}/${did}/${ch}/set_mode/{value}`
  }, [klass, deviceId, channel])

  return (
    <div className="psu-face">
      <div className="psu-main">
        <div className="psu-section">
          <div className="psu-section-title">Settings</div>
          <div className="psu-block" style={{ width: '100%' }}>
            <div className="psu-label">Modes</div>
            <select
              className="psu-input" // reuse input style for full-width select
              value={mode}
              onChange={async (e) => {
                const v = e.target.value
                setMode(v)
                if (!klass || !deviceId) return
                try {
                  const ch = channel || '1'
                  await fetch(`${apiBase}/instruments/${klass}/${deviceId}/${ch}/set_mode/${encodeURIComponent(v)}`, { method: 'POST' })
                } catch {}
              }}
              title={`POST ${endpointTemplate}`}
              style={{ width: '100%', padding: '6px 8px' }}
            >
              {modes.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
            <span className="psu-api" title={`GET /instruments/${klass || 'DMM'}/${deviceId || '{id}'}`}>API</span>
          </div>
        </div>
        <div className="psu-section">
          <div className="psu-section-title">Readings</div>
          <ReadonlyBigNumber kind="U" label={<Label symbol="U" unit="V"/>} value={"00000"} channelPath={channelPath} />
        </div>
        <hr className="sep"/>
      </div>
    </div>
  )
}

function parsePath(channelPath?: string): { klass?: string, deviceId?: string, channel?: string } {
  if (!channelPath) return {}
  const parts = channelPath.split('/').filter(Boolean)
  // [instruments, CLASS, device_id, channel, ...]
  if (parts.length < 4) return {}
  return { klass: parts[1], deviceId: parts[2], channel: parts[3] }
}

function ReadonlyBigNumber({ kind, label, value, channelPath }: { kind?: 'U' | 'I' | 'P', label: React.ReactNode, value: string, channelPath?: string }) {
  return (
    <div className="psu-block">
      <div className="psu-label">{label}</div>
      <span className="psu-number readonly" aria-hidden>
        <span>{value || '0'}</span>
      </span>
      {channelPath && (
        <span className="psu-api" title={
          kind === 'U' ? `GET ${channelPath}/query_voltage` :
          kind === 'I' ? `GET ${channelPath}/query_current` :
          kind === 'P' ? `GET ${channelPath}/query_power` : ''
        }>API</span>
      )}
    </div>
  )
}

function Label({ symbol, unit }: { symbol: string, unit: string }) {
  return (
    <>
      <span className="psu-symbol">{symbol}</span><span className="psu-unit">[{unit}]</span>
    </>
  )
}

export default GenericDMM
