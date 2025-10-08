import React, { createContext, useContext, useState, ReactNode, useCallback } from 'react'

export interface MeasurementSource {
  id: string // unique identifier like "deviceId-channel-parameter"
  deviceId: string
  channelPath: string
  parameter: string // "U", "I", "P", etc.
  label: string // display label like "PSU-1 Ch1 Voltage"
  unit: string // "V", "A", "W", etc.
}

interface MeasurementContextType {
  selectedForRecord: Set<string>
  selectedForGraph: Set<string>
  toggleRecord: (sourceId: string) => void
  toggleGraph: (sourceId: string) => void
  registerSource: (source: MeasurementSource) => void
  sources: Map<string, MeasurementSource>
  registry: any
}

const MeasurementContext = createContext<MeasurementContextType | undefined>(undefined)

export function MeasurementProvider({ children, registry }: { children: ReactNode, registry?: any }) {
  const [selectedForRecord, setSelectedForRecord] = useState<Set<string>>(new Set())
  const [selectedForGraph, setSelectedForGraph] = useState<Set<string>>(new Set())
  const [sources, setSources] = useState<Map<string, MeasurementSource>>(new Map())

  const toggleRecord = useCallback((sourceId: string) => {
    setSelectedForRecord(prev => {
      const next = new Set(prev)
      if (next.has(sourceId)) {
        next.delete(sourceId)
      } else {
        next.add(sourceId)
      }
      return next
    })
  }, [])

  const toggleGraph = useCallback((sourceId: string) => {
    setSelectedForGraph(prev => {
      const next = new Set(prev)
      if (next.has(sourceId)) {
        next.delete(sourceId)
      } else {
        next.add(sourceId)
      }
      return next
    })
  }, [])

  const registerSource = useCallback((source: MeasurementSource) => {
    setSources(prev => {
      // Only update if the source is new or changed
      const existing = prev.get(source.id)
      if (existing &&
          existing.deviceId === source.deviceId &&
          existing.channelPath === source.channelPath &&
          existing.parameter === source.parameter &&
          existing.label === source.label &&
          existing.unit === source.unit) {
        return prev // No change, return same map
      }
      const next = new Map(prev)
      next.set(source.id, source)
      return next
    })
  }, [])

  return (
    <MeasurementContext.Provider value={{
      selectedForRecord,
      selectedForGraph,
      toggleRecord,
      toggleGraph,
      registerSource,
      sources,
      registry: registry || {}
    }}>
      {children}
    </MeasurementContext.Provider>
  )
}

export function useMeasurement() {
  const context = useContext(MeasurementContext)
  if (!context) {
    throw new Error('useMeasurement must be used within MeasurementProvider')
  }
  return context
}
