import { describe, it, expect } from 'vitest'

/**
 * Test data extraction logic for GenericDMM component
 * 
 * The component now supports both old and new registry data formats:
 * 
 * Old format:
 *   channelData.measurement1_si = "-22.519"
 *   channelData.measurement1_symbol = "m"
 * 
 * New format (prioritized):
 *   channelData.MEAS.si.number = "-22.5337"
 *   channelData.MEAS.si.symbol = "m"
 */

describe('GenericDMM data extraction', () => {
  // Helper function to replicate the useMemo logic
  function extractMeasurement(channelData: any) {
    if (!channelData) {
      return { measurementValue: '00000', unitPrefix: '' }
    }

    const rawValue = String(channelData.MEAS?.si?.number || '0')
    const prefix = channelData.MEAS?.si?.symbol || ''

    // Ensure 5 numerical digits (excluding decimal point and sign)
    const isNegative = rawValue.startsWith('-') || rawValue.startsWith('+')
    const absoluteValue = isNegative ? rawValue.slice(1) : rawValue
    const parts = absoluteValue.split('.')

    // Count total digits needed (excluding decimal point)
    const totalDigits = parts.join('').length
    const zerosNeeded = Math.max(0, 5 - totalDigits)

    // Add leading zeros and reconstruct with decimal point if present
    const paddedInteger = '0'.repeat(zerosNeeded) + parts[0]
    const formattedValue = parts.length > 1 ? `${paddedInteger}.${parts[1]}` : paddedInteger
    const value = rawValue.startsWith('-') ? `-${formattedValue}` : formattedValue

    return { measurementValue: value, unitPrefix: prefix }
  }

  it('should extract data from new format', () => {
    const channelData = {
      MEAS: {
        si: {
          number: "-22.5337",
          symbol: "m",
          prefix: "milli"
        },
        sci: "-2.25337E-02",
        val: "-2.253373E-02"
      },
      MODE: "VOLT"
    }

    const result = extractMeasurement(channelData)
    // Total digits = 6 (22 + 5337), so no padding needed (5 digit minimum)
    expect(result.measurementValue).toBe('-22.5337')
    expect(result.unitPrefix).toBe('m')
  })

  it('should handle positive values', () => {
    const channelData = {
      MEAS: {
        si: {
          number: "3.142",
          symbol: "μ"
        }
      }
    }

    const result = extractMeasurement(channelData)
    // Total digits = 4 (3 + 142), needs 1 zero padding
    expect(result.measurementValue).toBe('03.142')
    expect(result.unitPrefix).toBe('μ')
  })

  it('should handle missing symbol', () => {
    const channelData = {
      MEAS: {
        si: {
          number: "123.45"
        }
      }
    }

    const result = extractMeasurement(channelData)
    // Total digits = 5 (123 + 45), exactly 5 digits so no padding
    expect(result.measurementValue).toBe('123.45')
    expect(result.unitPrefix).toBe('')
  })

  it('should return default values for null data', () => {
    const result = extractMeasurement(null)
    expect(result.measurementValue).toBe('00000')
    expect(result.unitPrefix).toBe('')
  })

  it('should handle integer values without decimal', () => {
    const channelData = {
      MEAS: {
        si: {
          number: "5",
          symbol: "k"
        }
      }
    }

    const result = extractMeasurement(channelData)
    expect(result.measurementValue).toBe('00005')
    expect(result.unitPrefix).toBe('k')
  })
})
