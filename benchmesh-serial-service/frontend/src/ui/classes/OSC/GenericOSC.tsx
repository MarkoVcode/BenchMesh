import React, { useEffect, useMemo, useState } from 'react'

// Minimal generic Oscilloscope UI placeholder
export function GenericOSC({ channelPath, registry }: { channelPath?: string, registry?: any }) {
  const apiBase = `${window.location.protocol}//${window.location.hostname}:57666`
  const { klass, deviceId } = useMemo(() => parsePath(channelPath), [channelPath])
  const [features, setFeatures] = useState<any>({})

  useEffect(() => {
    let cancelled = false
    async function loadFeatures() {
      if (!klass || !deviceId) return
      try {
        const r = await fetch(`${apiBase}/instruments/${klass}/${deviceId}`)
        if (!cancelled && r.ok) setFeatures(await r.json().catch(() => ({})))
      } catch {}
    }
    loadFeatures();
    return () => { cancelled = true }
  }, [apiBase, klass, deviceId])

  return (
    <div className="osc-face">
      <div className="osc-main">
        <div className="osc-section">
          <div className="osc-section-title">Oscilloscope</div>
          <div className="osc-row"><span className="osc-label">Timebase</span><span className="osc-value">—</span></div>
          <div className="osc-row"><span className="osc-label">Channel</span><span className="osc-value">—</span></div>
        </div>
      </div>
      {channelPath && (
        <div className="osc-actions">
          <span className="psu-api" title={`GET /instruments/${klass || 'OSC'}/${deviceId || '{id}'}`}>API</span>
        </div>
      )}
    </div>
  )
}

function parsePath(channelPath?: string): { klass?: string, deviceId?: string } {
  if (!channelPath) return {}
  const parts = channelPath.split('/').filter(Boolean)
  if (parts.length < 3) return {}
  return { klass: parts[1], deviceId: parts[2] }
}

export default GenericOSC
