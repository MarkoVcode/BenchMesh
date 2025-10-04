import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'
import { InstrumentPod } from '../InstrumentPod'

const baseInstrument = {
  id: 'psu-1',
  IDN: 'ACME PSU-1000',
  classes: [
    { class: 'PSU', channels: ['/instruments/PSU/psu-1/1'] }
  ]
}

describe('InstrumentPod', () => {
  it('renders instrument id and IDN', () => {
    render(<InstrumentPod instrument={baseInstrument as any} registry={{}} />)
    expect(screen.getByText('psu-1')).toBeInTheDocument()
    expect(screen.getByText('ACME PSU-1000')).toBeInTheDocument()
  })

  it('shows channel path and PSU face under PSU class', () => {
    render(<InstrumentPod instrument={baseInstrument as any} registry={{}} />)
    expect(screen.getByText('/instruments/PSU/psu-1/1')).toBeInTheDocument()
    // PSU face now renders Settings and Readings columns
    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.getByText('Readings')).toBeInTheDocument()
    // No editable P in Settings; P present in Readings only
    expect(screen.getAllByText('V').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText('A').length).toBeGreaterThanOrEqual(2)
  })
})
