import React, { useEffect, useMemo, useState } from 'react'

// Minimal generic AWG UI placeholder
export function GenericAWG({ channelPath }: { channelPath?: string }) {
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
    <div className="awg-face">
      <div className="awg-main">
        <div className="awg-section">
          <div className="awg-section-title">AWG</div>
          <div className="awg-row"><span className="awg-label">Waveform</span><span className="awg-value">—</span></div>
          <div className="awg-row"><span className="awg-label">Frequency</span><span className="awg-value">—</span></div>
        </div>
      </div>
      {channelPath && (
        <div className="awg-actions">
          <span className="psu-api" title={`GET /instruments/${klass || 'AWG'}/${deviceId || '{id}'}`}>API</span>
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

export default GenericAWG
