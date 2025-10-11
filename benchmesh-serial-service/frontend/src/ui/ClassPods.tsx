import React from 'react'
import { getClassDescription } from './instrumentClasses'
import { GenericPSU } from './classes/PSU/GenericPSU'
import { GenericDMM } from './classes/DMM/GenericDMM'
import { GenericELL } from './classes/ELL/GenericELL'
import { OwonOELELL } from './classes/ELL/OwonOELELL'
import { GenericAWG } from './classes/AWG/GenericAWG'
import { GenericOSC } from './classes/OSC/GenericOSC'
import { GenericLCR } from './classes/LCR/GenericLCR'
import { GenericSAL } from './classes/SAL/GenericSAL'
import { UnknownInstrument } from './classes/Unknown/UnknownInstrument'

export function ChannelPod({ path, klass, uiComponent, registry }: { path: string, klass?: string, uiComponent?: string, registry?: any }) {
  const upper = (klass || '').toUpperCase()
  return (
    <div className="channel-card">
      <code className="channel-path">{path}</code>
      {/* Prefer explicit ui_component from API if provided, otherwise fallback by klass */}
      <div className="channel-extra">
        {uiComponent === 'GenericPSU' || (uiComponent == null && upper === 'PSU') ? <GenericPSU channelPath={path} registry={registry} /> : null}
        {uiComponent === 'GenericDMM' || (uiComponent == null && upper === 'DMM') ? <GenericDMM channelPath={path} registry={registry} /> : null}
        {uiComponent === 'GenericELL' || (uiComponent == null && upper === 'ELL') ? <GenericELL channelPath={path} registry={registry} /> : null}
        {uiComponent === 'OwonOELELL' ? <OwonOELELL channelPath={path} registry={registry} /> : null}
        {uiComponent === 'GenericAWG' || (uiComponent == null && upper === 'AWG') ? <GenericAWG channelPath={path} registry={registry} /> : null}
        {uiComponent === 'GenericOSC' || (uiComponent == null && upper === 'OSC') ? <GenericOSC channelPath={path} registry={registry} /> : null}
        {uiComponent === 'GenericLCR' || (uiComponent == null && upper === 'LCR') ? <GenericLCR channelPath={path} registry={registry} /> : null}
        {uiComponent === 'GenericSAL' || (uiComponent == null && upper === 'SAL') ? <GenericSAL channelPath={path} registry={registry} /> : null}
        {(uiComponent && !['GenericPSU','GenericDMM','GenericELL','OwonOELELL','GenericAWG','GenericOSC','GenericLCR','GenericSAL'].includes(uiComponent)) ? <UnknownInstrument uiComponent={uiComponent} channelPath={path} /> : null}
      </div>
    </div>
  )
}

function BaseClassPod({ title, channels, klass, uiComponent, registry }: { title: string, channels: string[], klass: string, uiComponent?: string, registry?: any }) {
  return (
    <div className="subcard">
      <div className="subcard-title">{title}</div>
      <div className="channels">
        {channels.map((p) => (
          <ChannelPod key={p} path={p} klass={klass} uiComponent={uiComponent} registry={registry} />
        ))}
      </div>
    </div>
  )
}

// Dedicated class components (content is presently the hardcoded class display name)
export const DMMClassPod   = ({ channels, uiComponent }: { channels: string[], uiComponent?: string }) => <BaseClassPod title={getClassDescription('DMM')} channels={channels} klass={'DMM'} uiComponent={uiComponent} />
export const AWGClassPod   = ({ channels, uiComponent }: { channels: string[], uiComponent?: string }) => <BaseClassPod title={getClassDescription('AWG')} channels={channels} klass={'AWG'} uiComponent={uiComponent} />
export const PSUClassPod   = ({ channels, uiComponent }: { channels: string[], uiComponent?: string }) => <BaseClassPod title={getClassDescription('PSU')} channels={channels} klass={'PSU'} uiComponent={uiComponent} />
export const ELLClassPod   = ({ channels, uiComponent }: { channels: string[], uiComponent?: string }) => <BaseClassPod title={getClassDescription('ELL')} channels={channels} klass={'ELL'} uiComponent={uiComponent} />
export const OSCClassPod   = ({ channels, uiComponent }: { channels: string[], uiComponent?: string }) => <BaseClassPod title={getClassDescription('OSC')} channels={channels} klass={'OSC'} uiComponent={uiComponent} />
export const LCRClassPod   = ({ channels, uiComponent }: { channels: string[], uiComponent?: string }) => <BaseClassPod title={getClassDescription('LCR')} channels={channels} klass={'LCR'} uiComponent={uiComponent} />
export const SALClassPod   = ({ channels, uiComponent }: { channels: string[], uiComponent?: string }) => <BaseClassPod title={getClassDescription('SAL')} channels={channels} klass={'SAL'} uiComponent={uiComponent} />

export function ClassPodResolver({ klass, channels, uiComponent, registry }: { klass: string, channels: string[], uiComponent?: string, registry?: any }) {
  const k = (klass || '').toUpperCase()
  return <BaseClassPod title={getClassDescription(k)} channels={channels} klass={k} uiComponent={uiComponent} registry={registry} />
}
