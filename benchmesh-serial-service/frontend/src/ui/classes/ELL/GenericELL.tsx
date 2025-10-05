import React from 'react'

// Minimal generic Electronic Load (ELL) UI placeholder
export function GenericELL({ channelPath }: { channelPath?: string }) {
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
          <span className="psu-api" title={`GET ${channelPath}/poll_status`}>API</span>
        </div>
      )}
    </div>
  )
}

export default GenericELL
