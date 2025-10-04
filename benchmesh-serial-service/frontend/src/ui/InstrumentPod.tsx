import React, { useMemo } from 'react'

export type Instrument = {
  id: string
  IDN?: string
  classes: { class: string, channels: string[] }[]
}

function StatusDot({ online }: { online: boolean }) {
  const color = online ? '#16a34a' : '#dc2626'
  return (
    <span title={online ? 'online' : 'offline'}
          style={{
            display: 'inline-block',
            width: 10,
            height: 10,
            borderRadius: '50%',
            background: color,
            boxShadow: `0 0 0 2px white, 0 0 2px ${color}`
          }} />
  )
}

export function InstrumentPod({ instrument, registry }: { instrument: Instrument, registry: any }) {
  const online = useMemo(() => {
    const r = registry?.[instrument.id]
    const idn = r?.IDN ?? instrument.IDN
    return Boolean(idn && String(idn).trim().length > 0)
  }, [registry, instrument])

  return (
    <div style={{
      border: '1px solid #e5e7eb',
      borderRadius: 8,
      padding: 12,
      position: 'relative',
      minHeight: 140,
      background: '#fff'
    }}>
      <div style={{ position: 'absolute', top: 8, right: 8 }}>
        <StatusDot online={online} />
      </div>
      <h3 style={{ margin: '0 0 8px 0' }}>{instrument.id}</h3>
      <div style={{ fontSize: 12, color: '#6b7280', position: 'absolute', right: 12, bottom: 10 }}>
        {instrument.IDN || registry?.[instrument.id]?.IDN || '—'}
      </div>
      <div>
        {instrument.classes.map((c) => (
          <div key={c.class} style={{ fontSize: 12, color: '#374151', marginTop: 4 }}>
            <b>{c.class}</b>: {c.channels.join(', ')}
          </div>
        ))}
      </div>
    </div>
  )
}
