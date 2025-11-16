import React, { useEffect, useMemo, useState } from 'react'
import { useRequestLog, loggedFetch } from '../../RequestLogContext'

// Minimal generic Spectrum Analyzer UI placeholder
export function GenericSAL({ channelPath, registry }: { channelPath?: string, registry?: any }) {
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
    <div className="sal-face">
      <div className="sal-main">
        <div className="sal-section">
          <div className="sal-section-title">Spectrum Analyzer</div>
          <div className="sal-row"><span className="sal-label">Center</span><span className="sal-value">—</span></div>
          <div className="sal-row"><span className="sal-label">Span</span><span className="sal-value">—</span></div>
        </div>
      </div>
      {channelPath && (
        <div className="sal-actions">
          <span className="psu-api" title={`GET /instruments/${klass || 'SAL'}/${deviceId || '{id}'}`}>API</span>
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

export default GenericSAL
