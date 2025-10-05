import React from 'react'

// Minimal generic AWG UI placeholder
export function GenericAWG({ channelPath }: { channelPath?: string }) {
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
          <span className="psu-api" title={`GET ${channelPath}/poll_status`}>API</span>
        </div>
      )}
    </div>
  )
}

export default GenericAWG
