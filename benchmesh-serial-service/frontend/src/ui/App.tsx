import React, { useEffect, useMemo, useState } from 'react'
import { InstrumentPod, Instrument } from './InstrumentPod'

function useApiBase() {
  // API is served by FastAPI app; assume same origin during production.
  // For local dev, we can compute from window.location.
  return useMemo(() => {
    return `${window.location.protocol}//${window.location.hostname}:57665`
  }, [])
}

function useInstruments(apiBase: string) {
  const [data, setData] = useState<Instrument[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const resp = await fetch(`${apiBase}/instruments`)
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
        const json = await resp.json()
        if (!cancelled) setData(json)
      } catch (e: any) {
        if (!cancelled) setError(String(e))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [apiBase])

  return { data, loading, error }
}

function useRegistrySocket(apiBase: string) {
  const [registry, setRegistry] = useState<any>({})

  useEffect(() => {
    const wsProto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${wsProto}://${window.location.hostname}:57665/ws/registry`
    const ws = new WebSocket(url)
    ws.onmessage = (ev) => {
      try {
        const obj = JSON.parse(ev.data)
        setRegistry(obj)
      } catch {}
    }
    return () => ws.close()
  }, [apiBase])

  return registry
}

export default function App() {
  const apiBase = useApiBase()
  const { data: instruments, loading, error } = useInstruments(apiBase)
  const registry = useRegistrySocket(apiBase)

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', padding: 16 }}>
      <h1>BenchMesh Instruments</h1>
      {loading && <p>Loading…</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
        {instruments.map((ins) => (
          <InstrumentPod key={ins.id} instrument={ins} registry={registry} />
        ))}
      </div>
    </div>
  )
}
