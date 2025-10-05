import React from 'react'

// Minimal generic LCR Meter UI placeholder
export function GenericLCR({ channelPath }: { channelPath?: string }) {
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
          <span className="psu-api" title={`GET ${channelPath}/poll_status`}>API</span>
        </div>
      )}
    </div>
  )
}

export default GenericLCR
