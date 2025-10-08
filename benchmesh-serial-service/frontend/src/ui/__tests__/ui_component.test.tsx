import { describe, it, expect } from 'vitest'
/* eslint-disable @typescript-eslint/no-explicit-any */

import { render, screen } from '@testing-library/react'
import React from 'react'
import { InstrumentPod } from '../InstrumentPod'
import { MeasurementProvider } from '../MeasurementContext'

const instruments = [
  {
    id: 'psu-1',
    IDN: 'OWON,SPM3103,24460763,FV:V2.1.0',
    classes: [
      {
        class: 'DMM',
        channels: ['/instruments/DMM/psu-1/1'],
        ui_component: 'GenericDMM'
      },
      {
        class: 'PSU',
        channels: ['/instruments/PSU/psu-1/1'],
        ui_component: 'GenericPSU'
      }
    ]
  },
  {
    id: 'eol-1',
    IDN: 'OWON,OEL1515,25130087,FV:V1.1.0',
    classes: [
      {
        class: 'ELL',
        channels: ['/instruments/ELL/eol-1/1'],
        ui_component: 'GenericELL'
      }
    ]
  },
  {
    id: 'tenmapsu-1',
    IDN: 'TENMA 72-2540 V2.1',
    classes: [
      {
        class: 'PSU',
        channels: ['/instruments/PSU/tenmapsu-1/1','/instruments/PSU/tenmapsu-1/2'],
        ui_component: 'GenericPSU'
      }
    ]
  },
  {
    id: 'dmm-1',
    IDN: 'OWON,XDM1241,24512010,V4.3.0,3',
    classes: [
      {
        class: 'DMM',
        channels: ['/instruments/DMM/dmm-1/1'],
        ui_component: 'GenericDMM'
      }
    ]
  }
]

function renderAll() {
  return instruments.map((inst) =>
    render(
      <MeasurementProvider>
        <InstrumentPod instrument={inst as any} registry={{}} />
      </MeasurementProvider>
    )
  )
}

describe('ui_component-driven rendering', () => {
  it('renders correct per-class components from ui_component field', () => {
    renderAll()

    // PSU entries should render GenericPSU face content
    expect(screen.getAllByText('Settings').length).toBeGreaterThanOrEqual(3)
    expect(screen.getAllByText('Readings').length).toBeGreaterThanOrEqual(3)

    // ELL Generic face should at least render the channel path and exist in DOM
    expect(screen.getByText('/instruments/ELL/eol-1/1')).toBeInTheDocument()

    // DMM Generic face should render with its channel path
    expect(screen.getByText('/instruments/DMM/psu-1/1')).toBeInTheDocument()
    expect(screen.getByText('/instruments/DMM/dmm-1/1')).toBeInTheDocument()
  })

  it('falls back to UnknownInstrument when ui_component is unrecognized', () => {
    const bogus = {
      id: 'weird-1',
      IDN: 'ACME,WEIRD,1.0',
      classes: [
        { class: 'FOO', channels: ['/instruments/FOO/weird-1/1'], ui_component: 'NonExistingComponent' }
      ]
    }
    render(
      <MeasurementProvider>
        <InstrumentPod instrument={bogus as any} registry={{}} />
      </MeasurementProvider>
    )
    // UnknownInstrument shows text including "Unknown Instrument" and component name
    expect(screen.getByText('Unknown Instrument')).toBeInTheDocument()
    expect(screen.getByText('Component: NonExistingComponent')).toBeInTheDocument()
  })
})
