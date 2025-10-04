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
    expect(screen.getAllByText('Settings').length).toBe(2)
    expect(screen.getAllByText('Readings').length).toBe(2)
  })
})
