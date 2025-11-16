import React, { useEffect, useMemo, useState } from 'react'
import { useRequestLog, loggedFetch } from '../../RequestLogContext'

// Minimal generic LCR Meter UI placeholder
export function GenericLCR({ channelPath, registry }: { channelPath?: string, registry?: any }) {
  const apiBase = `${window.location.protocol}//${window.location.hostname}:57666`
  const { addLog } = useRequestLog()
  const { klass, deviceId } = useMemo(() => parsePath(channelPath), [channelPath])
  const [features, setFeatures] = useState<any>({})

  useEffect(() => {
    let cancelled = false
    async function loadFeatures() {
      if (!klass || !deviceId) return
      try {
        const r = await loggedFetch(`${apiBase}/instruments/${klass}/${deviceId}`, {
          method: 'GET',
          instrument: deviceId,
          channel: '1',
          action: 'Query Features',
          addLog,
        })
        if (!cancelled && r.ok) setFeatures(await r.json().catch(() => ({})))
      } catch {}
    }
    loadFeatures();
    return () => { cancelled = true }
  }, [apiBase, klass, deviceId, addLog])

  return (
    <div className="lcr-face">
      <div className="lcr-main">
        <div className="lcr-section">
          <div className="lcr-section-title">LCR Meter</div>
          <div className="lcr-row"><span className="lcr-label">L</span><span className="lcr-value">—</span></div>
          <div className="lcr-row"><span className="lcr-label">C</span><span className="lcr-value">—</span></div>
          <div className="lcr-row"><span className="lcr-label">R</span><span className="lcr-value">—</span></div>
        </div>
      </div>
      {channelPath && (
        <div className="lcr-actions">
          <span className="psu-api" title={`GET /instruments/${klass || 'LCR'}/${deviceId || '{id}'}`}>API</span>
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

export default GenericLCR
