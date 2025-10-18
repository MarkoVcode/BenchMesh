import React from 'react'

/**
 * RemoteLockWarning - A reusable warning component for remote mode requirements
 *
 * Displays a warning message when an instrument requires remote mode to be enabled
 * before settings can be changed.
 *
 * Used by GenericPSU and OwonOELELL components when compulsory_lock is enabled.
 */
export function RemoteLockWarning() {
  return (
    <div style={{
      padding: '12px',
      background: 'rgba(255, 165, 0, 0.1)',
      border: '1px solid rgba(255, 165, 0, 0.3)',
      borderRadius: '6px',
      color: 'rgba(255, 165, 0, 0.9)',
      fontSize: '12px',
      textAlign: 'center'
    }}>
      ⚠️ Instrument is in LOCAL mode. Enable remote mode to control settings.
    </div>
  )
}

export default RemoteLockWarning
