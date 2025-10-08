import React from 'react'

interface GenericTempProps {
  mode: string
  channelPath?: string
}

// Placeholder component for temperature mode
export function GenericTemp({ mode, channelPath }: GenericTempProps) {
  return (
    <div style={{ padding: '8px', color: 'var(--text-2)', fontSize: '12px', fontStyle: 'italic' }}>
      Temperature mode configuration (placeholder)
    </div>
  )
}
