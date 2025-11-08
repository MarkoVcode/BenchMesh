import React, { useEffect, useMemo, useState } from 'react'

// Channel color mapping
const CHANNEL_COLORS: Record<number, string> = {
  1: '#FFD700', // yellow
  2: '#00CED1', // cyan
  3: '#FF69B4', // pink
  4: '#4169E1'  // blue
}

// Minimal generic Oscilloscope UI - displays single channel data
export function GenericOSC({ channelPath, registry }: { channelPath?: string, registry?: any }) {
  const apiBase = `${window.location.protocol}//${window.location.hostname}:57666`
  const { klass, deviceId, channel } = useMemo(() => parsePath(channelPath), [channelPath])
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

  // Extract channel data from registry
  const channelData = useMemo(() => {
    if (!registry || !deviceId || !klass || !channel) return null
    
    const deviceData = registry[deviceId]?.[klass]
    if (!deviceData) return null

    const statusKey = `status_ch${channel}`
    return deviceData[statusKey] || null
  }, [registry, deviceId, klass, channel])

  const formatValue = (data: any, unit: string) => {
    if (!data?.si?.number) return '—'
    const symbol = data.si.symbol || ''
    return `${data.si.number} ${symbol}${unit}`
  }

  const channelColor = CHANNEL_COLORS[parseInt(channel || '0')] || '#808080'

  return (
    <div className="psu-face">
      <div className="psu-main">
        <div className="psu-section">
          <div className="psu-section-title" style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px' 
          }}>
            <span style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              background: channelColor,
              display: 'inline-block'
            }}/>
            <span style={{ color: channelColor }}>Channel {channel || '?'}</span>
          </div>
          
          {!channelData ? (
            <div className="psu-block">
              <span className="psu-label" style={{ color: 'var(--text-2)', fontStyle: 'italic' }}>
                No data available
              </span>
            </div>
          ) : (
            <>
              <div className="psu-block">
                <div className="psu-label">
                  <span className="psu-symbol">Scale</span>
                  <span className="psu-unit">[V]</span>
                </div>
                <span className="psu-number readonly">
                  <span>{formatValue(channelData.SCALE, 'V')}</span>
                </span>
              </div>
              
              <div className="psu-block">
                <div className="psu-label">
                  <span className="psu-symbol">Offset</span>
                  <span className="psu-unit">[V]</span>
                </div>
                <span className="psu-number readonly">
                  <span>{formatValue(channelData.OFFSET, 'V')}</span>
                </span>
              </div>
              
              <div className="psu-block">
                <div className="psu-label">
                  <span className="psu-symbol">Coupling</span>
                </div>
                <span className="psu-number readonly">
                  <span>{channelData.COUPLING || '—'}</span>
                </span>
              </div>
              
              <div className="psu-block">
                <div className="psu-label">
                  <span className="psu-symbol">Timebase</span>
                  <span className="psu-unit">[s]</span>
                </div>
                <span className="psu-number readonly">
                  <span>{formatValue(channelData.TIMEBASE, 's')}</span>
                </span>
              </div>
            </>
          )}
        </div>
        <hr className="sep"/>
      </div>
      {channelPath && (
        <div className="psu-actions">
          <span className="psu-api" title={`GET /instruments/${klass || 'OSC'}/${deviceId || '{id}'}/${channel || '{ch}'}`}>API</span>
        </div>
      )}
    </div>
  )
}

function parsePath(channelPath?: string): { klass?: string, deviceId?: string, channel?: string } {
  if (!channelPath) return {}
  const parts = channelPath.split('/').filter(Boolean)
  // Path format: /instruments/OSC/device-id/channel
  if (parts.length < 4) return {}
  return { klass: parts[1], deviceId: parts[2], channel: parts[3] }
}

export default GenericOSC
