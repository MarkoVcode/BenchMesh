import React from 'react'

// Minimal generic Spectrum Analyzer UI placeholder
export function GenericSAL({ channelPath }: { channelPath?: string }) {
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
          <span className="psu-api" title={`GET ${channelPath}/poll_status`}>API</span>
        </div>
      )}
    </div>
  )
}

export default GenericSAL
