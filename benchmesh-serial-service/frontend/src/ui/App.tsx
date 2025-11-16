import React, { useEffect, useMemo, useState, lazy, Suspense } from 'react'
import { Instrument } from './InstrumentPod'
import { MeasurementProvider } from './MeasurementContext'
import { RequestLogProvider } from './RequestLogContext'
import { WorkbenchLayout } from './workbench/WorkbenchLayout'
import { ClassicLayout } from './ClassicLayout'
import { DisclaimerModal } from './DisclaimerModal'

// Lazy load modal components to reduce initial bundle size
const ConfigModal = lazy(() => import('./ConfigModal').then(m => ({ default: m.ConfigModal })))
const DocsViewer = lazy(() => import('./DocsViewer').then(m => ({ default: m.DocsViewer })))
const MetricsViewer = lazy(() => import('./MetricsViewer').then(m => ({ default: m.MetricsViewer })))
const RecordingModal = lazy(() => import('./recording/RecordingModal').then(m => ({ default: m.RecordingModal })))

function useApiBase() {
  // API is served by FastAPI app; assume same origin during production.
  // For local dev, we can compute from window.location.
  return useMemo(() => {
    return `${window.location.protocol}//${window.location.hostname}:57666`
  }, [])
}

function useInstruments(apiBase: string, refreshTrigger: number) {
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
  }, [apiBase, refreshTrigger])

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
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const { data: instruments, loading, error } = useInstruments(apiBase, refreshTrigger)
  const { registry, wsDiag } = useRegistrySocket(apiBase)
  const [configModalOpen, setConfigModalOpen] = useState(false)
  const [docsModalOpen, setDocsModalOpen] = useState(false)
  const [metricsModalOpen, setMetricsModalOpen] = useState(false)
  const [recordingModalOpen, setRecordingModalOpen] = useState(false)
  const [autoOpenedConfig, setAutoOpenedConfig] = useState(false)

  // Check if running in Electron - use state to ensure preload script has time to run
  const [isElectron, setIsElectron] = useState(false)

  // Interface mode: 'classic' or 'workbench' (default: workbench)
  const [interfaceMode, setInterfaceMode] = useState<'classic' | 'workbench'>(() => {
    const saved = localStorage.getItem('benchmesh-interface-mode')
    return (saved === 'classic' || saved === 'workbench') ? saved : 'workbench'
  })

  // Disclaimer modal state - shows on first app load if not previously accepted
  const [disclaimerOpen, setDisclaimerOpen] = useState(() => {
    const accepted = localStorage.getItem('benchmesh:disclaimer-accepted')
    return accepted !== 'true' // Show if not accepted
  })

  // Check for Electron context after mount
  useEffect(() => {
    const checkElectron = () => {
      const inElectron = window.electron?.isElectron === true
      console.log('Electron context check:', {
        electron: window.electron,
        isElectron: inElectron
      })
      setIsElectron(inElectron)
    }

    // Check immediately and after a short delay to ensure preload has run
    checkElectron()
    const timer = setTimeout(checkElectron, 100)
    return () => clearTimeout(timer)
  }, [])

  const apiOk = !loading && !error
  const hasInstruments = instruments && instruments.length > 0

  // Auto-open docs modal if openDocs URL parameter is present (for Electron documentation window)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('openDocs') === 'true') {
      setDocsModalOpen(true)
    }
  }, [])

  // Auto-open config modal disabled - replaced with tutorial tooltip in workbench
  // useEffect(() => {
  //   if (!autoOpenedConfig && !loading && !error && instruments !== null && instruments.length === 0) {
  //     const timer = setTimeout(() => {
  //       setConfigModalOpen(true)
  //       setAutoOpenedConfig(true)
  //     }, 500)
  //     return () => clearTimeout(timer)
  //   }
  // }, [autoOpenedConfig, loading, error, instruments])

  function handleConfigUpdated() {
    setRefreshTrigger(prev => prev + 1)
  }

  function toggleInterface() {
    const newMode = interfaceMode === 'classic' ? 'workbench' : 'classic'
    setInterfaceMode(newMode)
    localStorage.setItem('benchmesh-interface-mode', newMode)
  }

  function handleDisclaimerAccept(dontShowAgain: boolean) {
    setDisclaimerOpen(false)
    if (dontShowAgain) {
      localStorage.setItem('benchmesh:disclaimer-accepted', 'true')
    }
  }

  return (
    <RequestLogProvider>
      <MeasurementProvider registry={registry}>
        {interfaceMode === 'classic' ? (
        <ClassicLayout
          instruments={instruments || []}
          registry={registry}
          apiBase={apiBase}
          loading={loading}
          error={error}
          wsDiag={wsDiag}
          onOpenConfig={() => setConfigModalOpen(true)}
          onOpenRecording={() => setRecordingModalOpen(true)}
          onOpenDocs={() => setDocsModalOpen(true)}
          onOpenMetrics={() => setMetricsModalOpen(true)}
          onSwitchToWorkbench={toggleInterface}
          isElectron={isElectron}
        />
      ) : (
        <WorkbenchLayout
          instruments={instruments || []}
          registry={registry}
          apiBase={apiBase}
          loading={loading}
          error={error}
          wsDiag={wsDiag}
          onConfigUpdated={handleConfigUpdated}
          onOpenRecording={() => setRecordingModalOpen(true)}
          onOpenMetrics={() => setMetricsModalOpen(true)}
          onSwitchToClassic={toggleInterface}
          isElectron={isElectron}
        />
      )}

      <Suspense fallback={<div className="modal-loading">Loading...</div>}>
        <ConfigModal
          isOpen={configModalOpen}
          onClose={() => setConfigModalOpen(false)}
          apiBase={apiBase}
          onConfigUpdated={handleConfigUpdated}
        />
      </Suspense>

      <Suspense fallback={<div className="modal-loading">Loading...</div>}>
        <RecordingModal
          isOpen={recordingModalOpen}
          onClose={() => setRecordingModalOpen(false)}
          apiBase={apiBase}
          instruments={instruments || []}
        />
      </Suspense>

      {docsModalOpen && (
        <Suspense fallback={<div className="modal-loading">Loading...</div>}>
          <DocsViewer
            onClose={() => setDocsModalOpen(false)}
            apiBase={apiBase}
          />
        </Suspense>
      )}

      {metricsModalOpen && (
        <Suspense fallback={<div className="modal-loading">Loading...</div>}>
          <MetricsViewer
            onClose={() => setMetricsModalOpen(false)}
            apiBase={apiBase}
          />
        </Suspense>
      )}

        {/* Disclaimer modal - highest priority, shown on first app load */}
        <DisclaimerModal
          isOpen={disclaimerOpen}
          onAccept={handleDisclaimerAccept}
        />
      </MeasurementProvider>
    </RequestLogProvider>
  )
}
