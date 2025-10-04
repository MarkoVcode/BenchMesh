import React, { useMemo, useState } from 'react'

// PSU face with two columns: Settings (editable V/A) and Readings (readonly V/A/P)
// - Settings: V and A stacked vertically. 5-digit display limit for both V and A (digits only; '.' not counted)
// - Readings: mirrors V and A and derives P = V*A, all readonly but styled identically
export function GenericPSU() {
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

  return (
    <div className="psu-face">
      <div className="psu-main">
        <div className="psu-section">
          <div className="psu-section-title">Settings</div>
          <EditableBigNumber label="V" value={vDisp} onChange={onChangeVoltage} />
          <EditableBigNumber label="A" value={aDisp} onChange={onChangeCurrent} />
        </div>
        <div className="psu-section">
          <div className="psu-section-title">Readings</div>
          <ReadonlyBigNumber label="V" value={vDisp} />
          <ReadonlyBigNumber label="A" value={aDisp} />
          <ReadonlyBigNumber label="P" value={pDisp} />
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
  if (abs >= 10000) return n.toExponential(2) // fallback to exponential for large values
  // Limit fractional part so total digits (ignoring '.') are ~5
  const s = n.toString()
  const [i, f = ''] = s.split('.')
  const room = Math.max(0, 5 - i.replace('-', '').length)
  const frac = f.slice(0, room)
  return frac.length ? `${i}.${frac}` : i
}

function EditableBigNumber({ label, value, onChange }: { label: string, value: string, onChange: (v: string) => void }) {
  return (
    <div className="psu-block">
      <div className="psu-label">{label}</div>
      <label className="psu-number" title="Click to edit">
        <input
          className="psu-input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        <span aria-hidden>{value || '0'}</span>
      </label>
    </div>
  )
}

function ReadonlyBigNumber({ label, value }: { label: string, value: string }) {
  return (
    <div className="psu-block">
      <div className="psu-label">{label}</div>
      <span className="psu-number" aria-hidden>
        <span>{value || '0'}</span>
      </span>
    </div>
  )
}

export default GenericPSU
