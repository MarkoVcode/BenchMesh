import React from 'react'

export function ChannelPod({ path }: { path: string }) {
  return (
    <div className="channel-card">
      <code className="channel-path">{path}</code>
    </div>
  )
}

import { getClassDescription } from './instrumentClasses'

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
export const DMMClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title={getClassDescription('DMM')} channels={channels} />
export const AWGClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title={getClassDescription('AWG')} channels={channels} />
export const PSUClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title={getClassDescription('PSU')} channels={channels} />
export const ELLClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title={getClassDescription('ELL')} channels={channels} />
export const OSCClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title={getClassDescription('OSC')} channels={channels} />
export const LCRClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title={getClassDescription('LCR')} channels={channels} />
export const SALClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title={getClassDescription('SAL')} channels={channels} />

export function ClassPodResolver({ klass, channels }: { klass: string, channels: string[] }) {
  const k = (klass || '').toUpperCase()
  return <BaseClassPod title={getClassDescription(k)} channels={channels} />
}
