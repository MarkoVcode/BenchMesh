export type InstrumentClassCode = 'DMM' | 'AWG' | 'PSU' | 'ELL' | 'OSC' | 'LCR' | 'SAL'

export const INSTRUMENT_CLASSES: Record<string, { description: string; reference: string }> = {
  DMM: { description: 'Digital Multimeter', reference: 'https://en.wikipedia.org/wiki/Multimeter' },
  AWG: { description: 'Arbitrary Waveform Generator', reference: 'https://en.wikipedia.org/wiki/Function_generator' },
  PSU: { description: 'Power Supply Unit', reference: 'https://en.wikipedia.org/wiki/Regulated_power_supply#D.C._variable_bench_supply' },
  ELL: { description: 'Electronic Load', reference: 'https://en.wikipedia.org/wiki/Electronic_load' },
  OSC: { description: 'Oscilloscope', reference: 'https://en.wikipedia.org/wiki/Oscilloscope' },
  LCR: { description: 'LCR Meter', reference: 'https://en.wikipedia.org/wiki/LCR_meter' },
  SAL: { description: 'Spectrum Analyzer', reference: 'https://en.wikipedia.org/wiki/Spectrum_analyzer' },
}

export function getClassInfo(code: string) {
  const k = (code || '').toUpperCase()
  return INSTRUMENT_CLASSES[k] || { description: k || 'Class', reference: '' }
}

export function getClassDescription(code: string) {
  return getClassInfo(code).description
}
