import React from 'react'
import { getClassDescription } from './instrumentClasses'
import { GenericPSU } from './classes/PSU/GenericPSU'

export function ChannelPod({ path, klass }: { path: string, klass?: string }) {
  const upper = (klass || '').toUpperCase()
  return (
    <div className="channel-card">
      <code className="channel-path">{path}</code>
      {upper === 'PSU' && (
        <div className="channel-extra">
          <GenericPSU channelPath={path} />
        </div>
      )}
    </div>
  )
}

function BaseClassPod({ title, channels, klass }: { title: string, channels: string[], klass: string }) {
  return (
    <div className="subcard">
      <div className="subcard-title">{title}</div>
      <div className="channels">
        {channels.map((p) => (
          <ChannelPod key={p} path={p} klass={klass} />
        ))}
      </div>
    </div>
  )
}

// Dedicated class components (content is presently the hardcoded class display name)
export const DMMClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title={getClassDescription('DMM')} channels={channels} klass={'DMM'} />
export const AWGClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title={getClassDescription('AWG')} channels={channels} klass={'AWG'} />
export const PSUClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title={getClassDescription('PSU')} channels={channels} klass={'PSU'} />
export const ELLClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title={getClassDescription('ELL')} channels={channels} klass={'ELL'} />
export const OSCClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title={getClassDescription('OSC')} channels={channels} klass={'OSC'} />
export const LCRClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title={getClassDescription('LCR')} channels={channels} klass={'LCR'} />
export const SALClassPod   = ({ channels }: { channels: string[] }) => <BaseClassPod title={getClassDescription('SAL')} channels={channels} klass={'SAL'} />

export function ClassPodResolver({ klass, channels }: { klass: string, channels: string[] }) {
  const k = (klass || '').toUpperCase()
  return <BaseClassPod title={getClassDescription(k)} channels={channels} klass={k} />
}
