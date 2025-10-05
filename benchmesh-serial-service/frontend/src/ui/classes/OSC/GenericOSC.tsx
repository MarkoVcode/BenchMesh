import React from 'react'

// Minimal generic Oscilloscope UI placeholder
export function GenericOSC({ channelPath }: { channelPath?: string }) {
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
          <span className="psu-api" title={`GET ${channelPath}/poll_status`}>API</span>
        </div>
      )}
    </div>
  )
}

export default GenericOSC
