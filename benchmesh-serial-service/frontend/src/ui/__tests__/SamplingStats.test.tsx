import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React, { act } from 'react'
import { SamplingStats } from '../SamplingStats'

describe('SamplingStats', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  // Helper function to expand the component
  const expandComponent = () => {
    const header = screen.getByText(/Statistical Sampling|Test Sampling/)
    act(() => {
      fireEvent.click(header)
    })
  }

  it('renders with initial collapsed state', () => {
    const getCurrentValue = vi.fn(() => 5.0)
    render(<SamplingStats getCurrentValue={getCurrentValue} label="Test Sampling" />)

    expect(screen.getByText('Test Sampling')).toBeInTheDocument()
    expect(screen.getByText('▶')).toBeInTheDocument() // Collapsed indicator

    // Controls should not be visible when collapsed
    expect(screen.queryByText('MIN')).not.toBeInTheDocument()
    expect(screen.queryByText('START')).not.toBeInTheDocument()
  })

  it('expands and shows controls when clicked', () => {
    const getCurrentValue = vi.fn(() => 5.0)
    render(<SamplingStats getCurrentValue={getCurrentValue} label="Test Sampling" />)

    // Click to expand
    act(() => {
      fireEvent.click(screen.getByText('Test Sampling'))
    })

    // Now controls should be visible
    expect(screen.getByText('▼')).toBeInTheDocument() // Expanded indicator
    expect(screen.getByText('MIN')).toBeInTheDocument()
    expect(screen.getByText('MAX')).toBeInTheDocument()
    expect(screen.getByText('AVG')).toBeInTheDocument()
    expect(screen.getByText('COUNT')).toBeInTheDocument()

    // Stats should be empty initially
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
    expect(screen.getByText('0')).toBeInTheDocument() // COUNT should be 0
  })

  it('starts sampling when START button is clicked', () => {
    const getCurrentValue = vi.fn(() => 5.0)
    render(<SamplingStats getCurrentValue={getCurrentValue} />)

    expandComponent()

    const startButton = screen.getByText('START')

    act(() => {
      fireEvent.click(startButton)
    })

    // Advance timer by 1 second (default interval)
    act(() => {
      vi.advanceTimersByTime(1000)
    })

    expect(getCurrentValue).toHaveBeenCalled()
  })

  it('collects samples and calculates stats correctly', () => {
    let currentValue = 5.0
    const getCurrentValue = vi.fn(() => currentValue)

    render(<SamplingStats getCurrentValue={getCurrentValue} />)

    expandComponent()

    act(() => {
      fireEvent.click(screen.getByText('START'))
    })

    // Collect first sample (5.0)
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(screen.getByText('1')).toBeInTheDocument() // COUNT = 1

    // Change value and collect second sample (7.0)
    currentValue = 7.0
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(screen.getByText('2')).toBeInTheDocument() // COUNT = 2

    // Change value and collect third sample (3.0)
    currentValue = 3.0
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(screen.getByText('3')).toBeInTheDocument() // COUNT = 3

    // Verify stats: MIN=3.0, MAX=7.0, AVG=5.0
    expect(screen.getByText('3.0000')).toBeInTheDocument() // MIN
    expect(screen.getByText('7.0000')).toBeInTheDocument() // MAX
    expect(screen.getByText('5.0000')).toBeInTheDocument() // AVG
  })

  it('updates MIN when value decreases', () => {
    let currentValue = 10.0
    const getCurrentValue = vi.fn(() => currentValue)

    render(<SamplingStats getCurrentValue={getCurrentValue} />)

    expandComponent()

    act(() => {
      fireEvent.click(screen.getByText('START'))
    })

    // Collect first sample (10.0)
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    // With one sample, MIN = MAX = AVG = 10.0
    const minMaxAvgElements = screen.getAllByText('10.0000')
    expect(minMaxAvgElements.length).toBe(3) // Should appear 3 times (MIN, MAX, AVG)

    // Drastically lower the value (2.0)
    currentValue = 2.0
    act(() => {
      vi.advanceTimersByTime(1000)
    })

    // MIN should update to 2.0
    expect(screen.getByText('2.0000')).toBeInTheDocument() // MIN
  })

  it('maintains sliding window when max samples reached', () => {
    let currentValue = 1.0
    const getCurrentValue = vi.fn(() => currentValue)

    render(<SamplingStats getCurrentValue={getCurrentValue} />)

    expandComponent()

    // Select 5 samples
    act(() => {
      fireEvent.change(screen.getByDisplayValue('10'), { target: { value: '5' } })
    })

    act(() => {
      fireEvent.click(screen.getByText('START'))
    })

    // Collect 7 samples (more than max of 5)
    for (let i = 0; i < 7; i++) {
      currentValue = i + 1 // Values: 1, 2, 3, 4, 5, 6, 7
      act(() => {
        vi.advanceTimersByTime(1000)
      })
    }

    // Should only keep last 5 samples (3, 4, 5, 6, 7)
    // Query for COUNT value specifically (not the "5" in the dropdown option)
    const countElements = screen.getAllByText('5')
    const countValue = countElements.find(el =>
      el.style.fontWeight === '700' &&
      el.style.color === 'var(--text-1)'
    )
    expect(countValue).toBeInTheDocument() // COUNT = 5

    // MIN should be 3 (oldest remaining sample)
    expect(screen.getByText('3.0000')).toBeInTheDocument() // MIN
    expect(screen.getByText('7.0000')).toBeInTheDocument() // MAX
    expect(screen.getByText('5.0000')).toBeInTheDocument() // AVG = (3+4+5+6+7)/5 = 5
  })

  it('stops sampling when STOP button is clicked', () => {
    const getCurrentValue = vi.fn(() => 5.0)

    render(<SamplingStats getCurrentValue={getCurrentValue} />)

    expandComponent()

    act(() => {
      fireEvent.click(screen.getByText('START'))
    })

    // Collect one sample
    act(() => {
      vi.advanceTimersByTime(1000)
    })

    const callCountBeforeStop = getCurrentValue.mock.calls.length

    act(() => {
      fireEvent.click(screen.getByText('STOP'))
    })

    // Advance time - should not collect more samples
    act(() => {
      vi.advanceTimersByTime(5000)
    })

    // Call count should not increase
    expect(getCurrentValue).toHaveBeenCalledTimes(callCountBeforeStop)
  })

  it('resets stats when RESET button is clicked', () => {
    const getCurrentValue = vi.fn(() => 5.0)

    render(<SamplingStats getCurrentValue={getCurrentValue} />)

    expandComponent()

    act(() => {
      fireEvent.click(screen.getByText('START'))
    })

    // Collect samples
    act(() => {
      vi.advanceTimersByTime(3000)
    })
    expect(screen.getByText('3')).toBeInTheDocument() // COUNT = 3

    act(() => {
      fireEvent.click(screen.getByText('RESET'))
    })

    // Stats should be reset
    expect(screen.getByText('0')).toBeInTheDocument() // COUNT = 0
    expect(screen.getAllByText('—').length).toBeGreaterThan(0) // Stats should show —
  })

  it('respects custom sampling interval', () => {
    const getCurrentValue = vi.fn(() => 5.0)

    render(<SamplingStats getCurrentValue={getCurrentValue} />)

    expandComponent()

    // Select 2 second interval
    act(() => {
      fireEvent.change(screen.getByDisplayValue('1s'), { target: { value: '2' } })
    })

    act(() => {
      fireEvent.click(screen.getByText('START'))
    })

    // Advance by 1 second - should not sample yet
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(getCurrentValue).not.toHaveBeenCalled()

    // Advance by another second - should sample now
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(getCurrentValue).toHaveBeenCalled()
  })

  it('ignores null and NaN values', () => {
    const getCurrentValue = vi.fn()
      .mockReturnValueOnce(5.0)
      .mockReturnValueOnce(null)
      .mockReturnValueOnce(NaN)
      .mockReturnValueOnce(7.0)

    render(<SamplingStats getCurrentValue={getCurrentValue} />)

    expandComponent()

    act(() => {
      fireEvent.click(screen.getByText('START'))
    })

    // Advance time to collect 4 samples
    act(() => {
      vi.advanceTimersByTime(4000)
    })

    // Should only count valid samples (5.0 and 7.0)
    expect(screen.getByText('2')).toBeInTheDocument() // COUNT = 2
    expect(screen.getByText('5.0000')).toBeInTheDocument() // MIN
    expect(screen.getByText('7.0000')).toBeInTheDocument() // MAX
  })

  it('disables dropdowns while sampling is running', () => {
    const getCurrentValue = vi.fn(() => 5.0)

    render(<SamplingStats getCurrentValue={getCurrentValue} />)

    expandComponent()

    const samplesDropdown = screen.getByDisplayValue('10') as HTMLSelectElement
    const intervalDropdown = screen.getByDisplayValue('1s') as HTMLSelectElement

    // Dropdowns should be enabled initially
    expect(samplesDropdown.disabled).toBe(false)
    expect(intervalDropdown.disabled).toBe(false)

    act(() => {
      fireEvent.click(screen.getByText('START'))
    })

    // Dropdowns should be disabled while running
    expect(samplesDropdown.disabled).toBe(true)
    expect(intervalDropdown.disabled).toBe(true)

    act(() => {
      fireEvent.click(screen.getByText('STOP'))
    })

    // Dropdowns should be enabled again after stopping
    expect(samplesDropdown.disabled).toBe(false)
    expect(intervalDropdown.disabled).toBe(false)
  })

  it('calculates average correctly with decimal values', () => {
    const values = [1.5, 2.5, 3.5]
    let index = 0
    const getCurrentValue = vi.fn(() => values[index++])

    render(<SamplingStats getCurrentValue={getCurrentValue} />)

    expandComponent()

    act(() => {
      fireEvent.click(screen.getByText('START'))
    })

    // Collect 3 samples
    act(() => {
      vi.advanceTimersByTime(3000)
    })

    // AVG should be (1.5 + 2.5 + 3.5) / 3 = 2.5
    expect(screen.getByText('3')).toBeInTheDocument() // COUNT = 3
    expect(screen.getByText('1.5000')).toBeInTheDocument() // MIN
    expect(screen.getByText('3.5000')).toBeInTheDocument() // MAX
    expect(screen.getByText('2.5000')).toBeInTheDocument() // AVG
  })
})
