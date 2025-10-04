import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import React from 'react'
import App from '../ui/App'

// Mock fetch for GET /instruments
const mockInstruments = [
  { id: 'psu-1', IDN: 'ACME PSU-1000', classes: [{ class: 'PSU', channels: ['/instruments/PSU/psu-1/1'] }] },
]

global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => mockInstruments } as any)

// Mock WebSocket
class MockWebSocket {
  url: string
  onopen: any; onmessage: any; onclose: any; onerror: any
  constructor(url: string) { this.url = url; setTimeout(() => this.onopen && this.onopen({}), 0) }
  send() {}
  close() { this.onclose && this.onclose({}) }
}
;(global as any).WebSocket = MockWebSocket as any


describe('App', () => {
  it('renders instrument card from API', async () => {
    render(<App />)
    await waitFor(() => expect(screen.getByText('psu-1')).toBeInTheDocument())
    expect(screen.getByText('ACME PSU-1000')).toBeInTheDocument()
  })
})
