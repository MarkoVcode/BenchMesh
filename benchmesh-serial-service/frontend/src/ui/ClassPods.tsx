import React from 'react'

export function ChannelPod({ path }: { path: string }) {
  return (
    <div className="channel-card">
      <code className="channel-path">{path}</code>
    </div>
  )
}

function BaseClassPod({ title, channels }: { title: string, channels: string[] }) {
  return (
    <div className="subcard">
      <div className="subcard-title">{title}</div>
      <div className="channels">
        {channels.map((p) => (
          <ChannelPod key={p} path={p} />
        ))}
      </div>
    </div>
  )
}

// Dedicated class components (content is presently the hardcoded class display name)
export const DMMClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title="DMM" channels={channels} />
export const AWGClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title="AWG" channels={channels} />
export const PSUClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title="PSU" channels={channels} />
export const ELLClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title="ELL" channels={channels} />
export const OSCClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title="OSC" channels={channels} />
export const LCRClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title="LCR" channels={channels} />
export const SALClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title="SAL" channels={channels} />

export function ClassPodResolver({ klass, channels }: { klass: string, channels: string[] }) {
  const k = (klass || '').toUpperCase()
  switch (k) {
    case 'DMM': return <DMMClassPod channels={channels} />
    case 'AWG': return <AWGClassPod channels={channels} />
    case 'PSU': return <PSUClassPod channels={channels} />
    case 'ELL': return <ELLClassPod channels={channels} />
    case 'OSC': return <OSCClassPod channels={channels} />
    case 'LCR': return <LCRClassPod channels={channels} />
    case 'SAL': return <SALClassPod channels={channels} />
    default:    return <BaseClassPod title={k || 'CLASS'} channels={channels} />
  }
}
