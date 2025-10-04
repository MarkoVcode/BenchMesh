import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'
import { ClassPodResolver } from '../ClassPods'

const channels = ['/instruments/PSU/psu-1/1','/instruments/PSU/psu-1/2']

describe('ClassPodResolver', () => {
  it('renders PSU class pod with GenericPSU and both channel paths', () => {
    render(<ClassPodResolver klass="PSU" channels={channels} />)
    expect(screen.getByText('/instruments/PSU/psu-1/1')).toBeInTheDocument()
    expect(screen.getByText('/instruments/PSU/psu-1/2')).toBeInTheDocument()
    // There are two channels, so labels appear twice
    expect(screen.getAllByText('V').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText('A').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText('P').length).toBeGreaterThanOrEqual(2)
  })
})
