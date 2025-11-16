import React, { useState, useEffect, useRef } from 'react'
import { useRequestLog, loggedFetch } from '../../RequestLogContext'

interface RangeOption {
  value: string
  display: string
}

interface GenericRangeProps {
  mode: string
  ranges?: RangeOption[]
  channelPath?: string
  klass?: string
  deviceId?: string
  channel?: string
}

export function GenericRange({ mode, ranges, channelPath, klass, deviceId, channel }: GenericRangeProps) {
  const apiBase = `${window.location.protocol}//${window.location.hostname}:57666`
  const { addLog } = useRequestLog()
  const [selectedRange, setSelectedRange] = useState<string>('AUTO')
  const [isOpen, setIsOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Set default to AUTO when ranges change
  useEffect(() => {
    if (ranges && ranges.length > 0) {
      const autoOption = ranges.find(r => r.value === 'AUTO')
      if (autoOption) {
        setSelectedRange('AUTO')
      } else {
        setSelectedRange(ranges[0].value)
      }
    }
  }, [ranges])

  const handleRangeChange = async (newRange: string) => {
    setSelectedRange(newRange)
    setIsOpen(false)

    if (!klass || !deviceId || !channelPath) return

    setBusy(true)
    try {
      const ch = channel || '1'
      const endpoint = `${apiBase}/instruments/${klass}/${deviceId}/${ch}/range/${encodeURIComponent(newRange)}`
      await loggedFetch(endpoint, {
        method: 'POST',
        instrument: deviceId,
        channel: ch,
        action: 'Set Range',
        parameters: { range: newRange },
        addLog,
      })
    } catch (err) {
      console.debug('Range change failed', err)
    } finally {
      setBusy(false)
    }
  }

  const getDisplayValue = () => {
    const option = ranges?.find(r => r.value === selectedRange)
    return option?.display || selectedRange
  }

  if (!ranges || ranges.length === 0) {
    return null
  }

  const endpointTemplate = `/instruments/${klass || 'DMM'}/${deviceId || '{id}'}/${channel || '1'}/range/{value}`

  return (
    <div className="psu-block" style={{ gridTemplateColumns: 'auto 1fr auto auto', width: '100%' }}>
      <div className="psu-label">
        <span className="psu-symbol">Range</span>
      </div>

      <div ref={dropdownRef} style={{ position: 'relative', width: '100%' }}>
        <button
          type="button"
          className="psu-number editable"
          disabled={busy}
          onClick={() => !busy && setIsOpen(!isOpen)}
          title={`POST ${endpointTemplate}`}
          style={{
            width: '100%',
            padding: '4px 8px',
            cursor: busy ? 'not-allowed' : 'pointer',
            background: 'rgba(255,255,255,.03)',
            border: '1px solid rgba(255,255,255,.25)',
            borderRadius: '4px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            textAlign: 'left',
            opacity: busy ? 0.5 : 1
          }}
        >
          <span style={{
            fontVariantNumeric: 'tabular-nums',
            fontWeight: 700,
            fontSize: '16px',
            color: '#c26a1a'
          }}>
            {getDisplayValue()}
          </span>
          <span style={{
            fontSize: '12px',
            color: 'rgba(255,255,255,.5)',
            marginLeft: '8px'
          }}>
            {isOpen ? '▲' : '▼'}
          </span>
        </button>

        {isOpen && (
          <div style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            marginTop: '4px',
            background: '#161d2a',
            border: '1px solid #202737',
            borderRadius: '6px',
            boxShadow: '0 4px 12px rgba(0,0,0,.4)',
            zIndex: 1000,
            maxHeight: '200px',
            overflowY: 'auto'
          }}>
            {ranges.map((option) => (
              <div
                key={option.value}
                onClick={() => handleRangeChange(option.value)}
                style={{
                  padding: '8px 12px',
                  cursor: 'pointer',
                  background: option.value === selectedRange ? 'rgba(96,165,250,.15)' : 'transparent',
                  color: option.value === selectedRange ? '#bcd9ff' : '#b7c0d1',
                  fontSize: '14px',
                  fontWeight: option.value === selectedRange ? 600 : 400,
                  borderBottom: '1px solid rgba(255,255,255,.05)',
                  transition: 'background .15s ease'
                }}
                onMouseEnter={(e) => {
                  if (option.value !== selectedRange) {
                    e.currentTarget.style.background = 'rgba(255,255,255,.05)'
                  }
                }}
                onMouseLeave={(e) => {
                  if (option.value !== selectedRange) {
                    e.currentTarget.style.background = 'transparent'
                  }
                }}
              >
                {option.display}
              </div>
            ))}
          </div>
        )}
      </div>

      <button
        className="psu-set"
        type="button"
        disabled={busy}
        title={`POST ${endpointTemplate.replace('{value}', selectedRange)}`}
        onClick={() => handleRangeChange(selectedRange)}
      >
        {busy ? (<><span className="spinner"/>SET</>) : 'SET'}
      </button>
      <span className="psu-api" title={`GET /instruments/${klass || 'DMM'}/${deviceId || '{id}'}`}>API</span>
    </div>
  )
}
