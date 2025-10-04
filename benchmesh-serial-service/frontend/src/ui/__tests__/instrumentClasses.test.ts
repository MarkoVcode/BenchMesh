import { describe, it, expect } from 'vitest'
import { getClassDescription } from '../instrumentClasses'

describe('instrumentClasses', () => {
  it('returns full descriptions for known classes', () => {
    expect(getClassDescription('DMM')).toContain('Digital')
    expect(getClassDescription('AWG')).toContain('Waveform')
    expect(getClassDescription('PSU')).toContain('Power')
    expect(getClassDescription('ELL')).toContain('Load')
    expect(getClassDescription('OSC')).toContain('Oscilloscope')
    expect(getClassDescription('LCR')).toContain('LCR')
    expect(getClassDescription('SAL')).toContain('Spectrum')
  })

  it('falls back to code for unknown class', () => {
    expect(getClassDescription('FOO')).toBe('FOO')
  })
})
