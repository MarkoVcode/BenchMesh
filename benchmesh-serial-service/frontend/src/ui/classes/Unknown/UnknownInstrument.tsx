import React from 'react'

export function UnknownInstrument({ uiComponent, channelPath }: { uiComponent?: string, channelPath?: string }) {
  return (
    <div className="unknown-face">
      <div className="unknown-section-title">Unknown Instrument</div>
      <div className="unknown-details">
        {uiComponent ? (<span>Component: {uiComponent}</span>) : (<span>No component specified</span>)}
      </div>
      {channelPath && (<code className="channel-path">{channelPath}</code>)}
    </div>
  )}

export default UnknownInstrument
