import React, { useEffect, useMemo, useState } from 'react'
import { InstrumentPod, Instrument } from './InstrumentPod'
import { MeasurementProvider } from './MeasurementContext'
import { MeasurementStatusBar } from './MeasurementStatusBar'
import { ConfigModal } from './ConfigModal'
import { DocsViewer } from './DocsViewer'

function useApiBase() {
  // API is served by FastAPI app; assume same origin during production.
  // For local dev, we can compute from window.location.
  return useMemo(() => {
    return `${window.location.protocol}//${window.location.hostname}:57666`
  }, [])
}

function useInstruments(apiBase: string) {
  const [data, setData] = useState<Instrument[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    let timer: any
    let lastETag: string | null = null

    async function load() {
      let ok = false
      try {
        // Send If-None-Match header if we have an ETag
        const headers: HeadersInit = {}
        if (lastETag) {
          headers['If-None-Match'] = lastETag
        }

        const resp = await fetch(`${apiBase}/instruments`, { headers })

        // 304 Not Modified - data hasn't changed, skip update
        if (resp.status === 304) {
          if (!cancelled) {
            setError(null)
            ok = true
          }
          return
        }

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`)

        const json = await resp.json()
        const newETag = resp.headers.get('ETag')

        if (!cancelled) {
          // Only update state if data actually changed (deep equality check)
          const dataChanged = JSON.stringify(data) !== JSON.stringify(json)
          if (dataChanged) {
            setData(json)
          }
          setError(null)
          if (newETag) {
            lastETag = newETag
          }
          ok = true
        }
      } catch (e: any) {
        if (!cancelled) setError(String(e))
      } finally {
        if (!cancelled) {
          setLoading(false)
          // Normal: poll every 5s; on failure: retry after 1s
          const delay = ok ? 5000 : 1000
          timer = setTimeout(load, delay)
        }
      }
    }
    load()
    return () => { cancelled = true; if (timer) clearTimeout(timer) }
  }, [apiBase])

  return { data, loading, error }
}

function useRegistrySocket(apiBase: string) {
  const [registry, setRegistry] = useState<any>({})
  const [wsDiag, setWsDiag] = useState<{ ok: boolean, msg: string, last: number | null }>({ ok: false, msg: 'connecting…', last: null })

  useEffect(() => {
    let ws: WebSocket | null = null
    let aliveTimer: any
    function connect() {
      const wsProto = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const url = `${wsProto}://${window.location.hostname}:57666/ws/registry`
      try {
        ws = new WebSocket(url)
      } catch (e: any) {
        setWsDiag({ ok: false, msg: 'ws create failed', last: wsDiag.last })
        setTimeout(connect, 1000)
        return
      }
      setWsDiag({ ok: false, msg: 'connecting…', last: wsDiag.last })
      ws.onopen = () => setWsDiag((d) => ({ ...d, ok: true, msg: 'connected' }))
      ws.onclose = () => {
        setWsDiag((d) => ({ ...d, ok: false, msg: 'disconnected' }))
        setTimeout(connect, 1000)
      }
      ws.onerror = () => setWsDiag((d) => ({ ...d, ok: false, msg: 'error' }))
      ws.onmessage = (ev) => {
        try {
          const obj = JSON.parse(ev.data)
          setRegistry(obj)
          const now = Date.now()
          setWsDiag({ ok: true, msg: 'receiving', last: now })
          if (aliveTimer) clearTimeout(aliveTimer)
          aliveTimer = setTimeout(() => {
            // if no updates in 1s, mark as stale
            setWsDiag((d) => ({ ...d, ok: false, msg: 'no data >1s' }))
          }, 1000)
        } catch {}
      }
    }
    connect()
    return () => { if (ws) ws.close(); if (aliveTimer) clearTimeout(aliveTimer) }
  }, [apiBase])

  return { registry, wsDiag }
}

export default function App() {
  const apiBase = useApiBase()
  const { data: instruments, loading, error } = useInstruments(apiBase)
  const { registry, wsDiag } = useRegistrySocket(apiBase)
  const [configModalOpen, setConfigModalOpen] = useState(false)
  const [docsModalOpen, setDocsModalOpen] = useState(false)
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const [autoOpenedConfig, setAutoOpenedConfig] = useState(false)

  const apiOk = !loading && !error
  const hasInstruments = instruments && instruments.length > 0

  // Auto-open config modal if registry is active but no instruments configured
  useEffect(() => {
    // Only auto-open after initial load completes
    if (!autoOpenedConfig && !loading && !error && instruments !== null && instruments.length === 0) {
      const timer = setTimeout(() => {
        setConfigModalOpen(true)
        setAutoOpenedConfig(true)
      }, 500) // Small delay to ensure everything is rendered
      return () => clearTimeout(timer)
    }
  }, [autoOpenedConfig, loading, error, instruments])

  function handleConfigUpdated() {
    setRefreshTrigger(prev => prev + 1)
  }

  return (
    <MeasurementProvider registry={registry}>
      <div style={{ paddingBottom: '48px' }}>
        <div className="topbar">
          <div className="brand">BenchMesh</div>
          <div className="topbar-center">
            <button
              className="config-button"
              onClick={() => setConfigModalOpen(true)}
              title="Configure Instruments"
            >
              ⚙️ Configuration
            </button>
            <button
              className="config-button"
              onClick={() => setDocsModalOpen(true)}
              title="View Documentation"
            >
              📚 Documentation
            </button>
          </div>
          <div className="statusbar">
            <div className="statuspill" title="WebSocket data flow">
              <span className="dot" style={{ background: wsDiag.ok ? 'var(--good)' : 'var(--bad)' }} />
              <span>{wsDiag.msg}</span>
            </div>
            <div className="statuspill" title="API connectivity">
              <span className="dot" style={{ background: apiOk ? 'var(--good)' : 'var(--bad)' }} />
              <span>{apiOk ? 'API ok' : error ? 'API unreachable' : 'Loading...'}</span>
            </div>
          </div>
        </div>

        <ConfigModal
          isOpen={configModalOpen}
          onClose={() => setConfigModalOpen(false)}
          apiBase={apiBase}
          onConfigUpdated={handleConfigUpdated}
        />

        {docsModalOpen && (
          <DocsViewer
            onClose={() => setDocsModalOpen(false)}
            apiBase={apiBase}
          />
        )}

        {hasInstruments && instruments && (
          <div className="container">
            <div className="grid">
              {instruments.map((ins) => (
                <InstrumentPod key={ins.id} instrument={ins} registry={registry} />
              ))}
            </div>
          </div>
        )}
      </div>
      <MeasurementStatusBar />
    </MeasurementProvider>
  )
}
