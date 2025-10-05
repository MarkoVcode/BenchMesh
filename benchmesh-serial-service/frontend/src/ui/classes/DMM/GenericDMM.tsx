import React from 'react'

// Minimal generic DMM UI placeholder
// Shows the channel path and simple readout placeholders
export function GenericDMM({ channelPath }: { channelPath?: string }) {
  return (
    <div className="dmm-face">
      <div className="dmm-main">
        <div className="dmm-section">
          <div className="dmm-section-title">Measurements</div>
          <div className="dmm-row"><span className="dmm-label">V</span><span className="dmm-value">—</span></div>
          <div className="dmm-row"><span className="dmm-label">A</span><span className="dmm-value">—</span></div>
          <div className="dmm-row"><span className="dmm-label">Ω</span><span className="dmm-value">—</span></div>
        </div>
      </div>
      {channelPath && (
        <div className="dmm-actions">
          <span className="psu-api" title={`GET ${channelPath}/poll_status`}>API</span>
        </div>
      )}
    </div>
  )
}

export default GenericDMM
