import React, { useEffect, useState } from 'react'

interface DeviceMetric {
  device_id: string
  window_duration_s: number
  utilization_pct: number
  qps: number
  api_request_count: number
  api_latency_p95_ms: number | null
  api_latency_p99_ms: number | null
  avg_queue_depth: number
  avg_poll_duration_ms: number
  total_operations: number
}

interface MetricsViewerProps {
  onClose: () => void
  apiBase: string
}

function useMetricsSocket(apiBase: string) {
  const [metrics, setMetrics] = useState<Record<string, DeviceMetric>>({})
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    let ws: WebSocket | null = null

    function connect() {
      const wsProto = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const url = `${wsProto}://${window.location.hostname}:57666/ws/metrics`

      try {
        ws = new WebSocket(url)
      } catch (e) {
        setConnected(false)
        setTimeout(connect, 2000)
        return
      }

      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        setTimeout(connect, 2000)
      }
      ws.onerror = () => setConnected(false)
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data)
          setMetrics(data)
        } catch (e) {
          console.error('Failed to parse metrics:', e)
        }
      }
    }

    connect()
    return () => { if (ws) ws.close() }
  }, [apiBase])

  return { metrics, connected }
}

export function MetricsViewer({ onClose, apiBase }: MetricsViewerProps) {
  const { metrics, connected } = useMetricsSocket(apiBase)
  const deviceIds = Object.keys(metrics)

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '1200px', width: '90%' }}>
        <div className="modal-header">
          <h2>Serial Port Utilization Metrics</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: connected ? 'var(--good)' : 'var(--bad)'
              }}
            />
            <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
              {connected ? 'Connected • Updates every 30s' : 'Disconnected'}
            </span>
          </div>

          {deviceIds.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
              No metrics data available yet. Metrics will appear after devices start polling.
            </div>
          ) : (
            <div style={{ display: 'grid', gap: '16px' }}>
              {deviceIds.map((deviceId) => {
                const metric = metrics[deviceId]
                return (
                  <div
                    key={deviceId}
                    style={{
                      border: '1px solid var(--border)',
                      borderRadius: '8px',
                      padding: '16px',
                      backgroundColor: 'var(--bg-secondary)'
                    }}
                  >
                    <h3 style={{ margin: '0 0 16px 0', fontSize: '16px' }}>{deviceId}</h3>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
                      <MetricCard
                        label="Utilization"
                        value={`${metric.utilization_pct.toFixed(2)}%`}
                        good={metric.utilization_pct < 80}
                      />
                      <MetricCard
                        label="QPS"
                        value={metric.qps.toFixed(2)}
                      />
                      <MetricCard
                        label="Window Duration"
                        value={`${metric.window_duration_s.toFixed(1)}s`}
                      />
                      <MetricCard
                        label="Total Operations"
                        value={metric.total_operations.toString()}
                      />
                      <MetricCard
                        label="API Requests"
                        value={metric.api_request_count.toString()}
                      />
                      {metric.api_latency_p95_ms !== null && (
                        <MetricCard
                          label="API Latency P95"
                          value={`${metric.api_latency_p95_ms.toFixed(2)}ms`}
                          good={metric.api_latency_p95_ms < 50}
                        />
                      )}
                      {metric.api_latency_p99_ms !== null && (
                        <MetricCard
                          label="API Latency P99"
                          value={`${metric.api_latency_p99_ms.toFixed(2)}ms`}
                          good={metric.api_latency_p99_ms < 100}
                        />
                      )}
                      {metric.avg_queue_depth > 0 && (
                        <MetricCard
                          label="Avg Queue Depth"
                          value={metric.avg_queue_depth.toFixed(2)}
                          good={metric.avg_queue_depth < 2}
                        />
                      )}
                      {metric.avg_poll_duration_ms > 0 && (
                        <MetricCard
                          label="Avg Poll Duration"
                          value={`${metric.avg_poll_duration_ms.toFixed(2)}ms`}
                        />
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

interface MetricCardProps {
  label: string
  value: string
  good?: boolean
}

function MetricCard({ label, value, good }: MetricCardProps) {
  const color = good === undefined ? 'var(--text)' : good ? 'var(--good)' : 'var(--warning)'

  return (
    <div style={{
      padding: '12px',
      backgroundColor: 'var(--bg)',
      borderRadius: '6px',
      border: '1px solid var(--border)'
    }}>
      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
        {label}
      </div>
      <div style={{ fontSize: '18px', fontWeight: 'bold', color }}>
        {value}
      </div>
    </div>
  )
}
