import React, { useMemo } from 'react'
import { ClassPodResolver } from './ClassPods'

export type Instrument = {
  id: string
  IDN?: string
  classes: { class: string, channels: string[], ui_component?: string }[]
}

function StatusDot({ online }: { online: boolean }) {
  const color = online ? 'var(--good)' : 'var(--bad)'
  return (
    <span title={online ? 'online' : 'offline'} className="dot" style={{ background: color }} />
  )
}

export function InstrumentPod({ instrument, registry }: { instrument: Instrument, registry: any }) {
  const online = useMemo(() => {
    const r = registry?.[instrument.id]
    const idn = r?.IDN ?? instrument.IDN
    return Boolean(idn && String(idn).trim().length > 0)
  }, [registry, instrument])

  return (
    <div className="card">
      <div className="wsdiag">
        <StatusDot online={online} />
        <span>{online ? 'online' : 'offline'}</span>
      </div>
      <h3 className="card-title">{instrument.id}</h3>
      <div className="card-idn">
        {instrument.IDN || registry?.[instrument.id]?.IDN || '—'}
      </div>
      <div className="card-classes">
        {instrument.classes.map((c) => (
          <div key={c.class}>
            <div>
              {/* Render dedicated nested class pod, honoring ui_component from API */}
              <ClassPodResolver klass={c.class} channels={c.channels} uiComponent={c.ui_component} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
