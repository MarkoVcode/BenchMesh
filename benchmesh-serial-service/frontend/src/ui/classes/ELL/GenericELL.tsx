import React, { useEffect, useMemo, useState } from 'react'

// Minimal generic Electronic Load (ELL) UI placeholder
export function GenericELL({ channelPath }: { channelPath?: string }) {
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
    <div className="ell-face">
      <div className="ell-main">
        <div className="ell-section">
          <div className="ell-section-title">Electronic Load</div>
          <div className="ell-row"><span className="ell-label">Mode</span><span className="ell-value">—</span></div>
          <div className="ell-row"><span className="ell-label">Setpoint</span><span className="ell-value">—</span></div>
        </div>
      </div>
      {channelPath && (
        <div className="ell-actions">
          <span className="psu-api" title={`GET /instruments/${klass || 'ELL'}/${deviceId || '{id}'}`}>API</span>
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

export default GenericELL
