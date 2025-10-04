import React, { useEffect, useMemo, useState } from 'react'

// PSU face with two columns: Settings (editable V/A) and Readings (readonly V/A/P)
// - Settings: V and A stacked vertically. 5-digit display limit for both V and A (digits only; '.' not counted)
// - Readings: mirrors V and A and derives P = V*A, all readonly but styled identically
export function GenericPSU({ channelPath }: { channelPath?: string }) {
  const [voltage, setVoltage] = useState('0')
  const [current, setCurrent] = useState('0')

  const onChangeVoltage = (v: string) => setVoltage(limitDigits(sanitizeNumber(v), 5))
  const onChangeCurrent = (v: string) => setCurrent(limitDigits(sanitizeNumber(v), 5))

  const vNum = useMemo(() => parseFloat(voltage || '0') || 0, [voltage])
  const aNum = useMemo(() => parseFloat(current || '0') || 0, [current])
  const pNum = useMemo(() => vNum * aNum, [vNum, aNum])

  const vDisp = voltage
  const aDisp = current
  const pDisp = numberToDisplay(pNum)

  useEffect(() => {
    let cancelled = false
    async function loadInitial() {
      if (!channelPath) return
      try {
        const [rv, rc] = await Promise.all([
          fetch(`${channelPath}/query_voltage`),
          fetch(`${channelPath}/query_current`),
        ])
        if (!cancelled) {
          if (rv.ok) {
            const v = await rv.text()
            setVoltage(limitDigits(sanitizeNumber(v), 5) || '0')
          }
          if (rc.ok) {
            const a = await rc.text()
            setCurrent(limitDigits(sanitizeNumber(a), 5) || '0')
          }
        }
      } catch {}
    }
    loadInitial()
    return () => { cancelled = true }
  }, [channelPath])

  return (
    <div className="psu-face">
      <div className="psu-main">
        <div className="psu-section">
          <div className="psu-section-title">Settings</div>
          <EditableBigNumber label={<Label symbol="U" unit="V"/>} value={vDisp} onChange={onChangeVoltage} withSet channelPath={channelPath} />
          <EditableBigNumber label={<Label symbol="I" unit="A"/>} value={aDisp} onChange={onChangeCurrent} withSet channelPath={channelPath} />
        </div>
        <div className="psu-section">
          <div className="psu-section-title">Readings</div>
          <ReadonlyBigNumber label={<Label symbol="U" unit="V"/>} value={vDisp} />
          <ReadonlyBigNumber label={<Label symbol="I" unit="A"/>} value={aDisp} />
          <ReadonlyBigNumber label={<Label symbol="P" unit="W"/>} value={pDisp} />
        </div>
      </div>
    </div>
  )
}

function sanitizeNumber(input: string): string {
  // Keep digits and at most one '.'
  let s = (input || '').replace(/[^\d.]/g, '')
  const firstDot = s.indexOf('.')
  if (firstDot !== -1) s = s.slice(0, firstDot + 1) + s.slice(firstDot + 1).replace(/\./g, '')
  return s
}

function limitDigits(input: string, maxDigits: number): string {
  let digits = 0
  let out = ''
  for (const ch of input) {
    if (ch >= '0' && ch <= '9') {
      if (digits >= maxDigits) break
      digits++
      out += ch
    } else if (ch === '.') {
      out += ch
    }
  }
  return out
}

function numberToDisplay(n: number): string {
  // Keep a compact representation while not exceeding 5 significant digits where feasible
  if (!isFinite(n)) return '0'
  const abs = Math.abs(n)
  if (abs === 0) return '0'
  if (abs >= 10000) return n.toExponential(2)
  const s = n.toString()
  const [i, f = ''] = s.split('.')
  const room = Math.max(0, 5 - i.replace('-', '').length)
  const frac = f.slice(0, room)
  return frac.length ? `${i}.${frac}` : i
}

function EditableBigNumber({ label, value, onChange, withSet, channelPath }: { label: React.ReactNode, value: string, onChange: (v: string) => void, withSet?: boolean, channelPath?: string }) {
  return (
    <div className="psu-block">
      <div className="psu-label">{label}</div>
      <label className="psu-number editable" title="Click to edit">
        <input
          className="psu-input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        <span aria-hidden>{value || '0'}</span>
      </label>
      {withSet && channelPath && (
        <>
          <button className="psu-set" type="button" onClick={async () => {
            try {
              const endp = (label as any)?.props?.symbol as string | undefined
              const val = value || '0'
              if (endp === 'U') await fetch(`${channelPath}/set_voltage/${val}`, { method: 'POST' })
              if (endp === 'I') await fetch(`${channelPath}/set_current/${val}`, { method: 'POST' })
            } catch {}
          }}>SET</button>
          <span className="psu-api" title={channelPath}>API</span>
        </>
      )}
    </div>
  )
}

function ReadonlyBigNumber({ label, value }: { label: React.ReactNode, value: string }) {
  return (
    <div className="psu-block">
      <div className="psu-label">{label}</div>
      <span className="psu-number readonly" aria-hidden>
        <span>{value || '0'}</span>
      </span>
    </div>
  )
}

function Label({ symbol, unit }: { symbol: string, unit: string }) {
  return (
    <>
      <span className="psu-symbol">{symbol}</span><span className="psu-unit">[{unit}]</span>
    </>
  )
}


export default GenericPSU
