import React, { useState } from 'react'

// A compact PSU face: editable V, A, P values as concealed text inputs
// Large numeric display on the left, labels on the right
export function GenericPSU() {
  const [voltage, setVoltage] = useState('00.000')
  const [current, setCurrent] = useState('0.0000')
  const [power, setPower] = useState('000.00')

  return (
    <div className="psu-face">
      <div className="psu-main">
        <EditableBigNumber label="V" value={voltage} onChange={setVoltage} />
        <EditableBigNumber label="A" value={current} onChange={setCurrent} />
        <EditableBigNumber label="P" value={power} onChange={setPower} />
      </div>
    </div>
  )
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
        <span aria-hidden>{value}</span>
      </label>
    </div>
  )
}

export default GenericPSU
