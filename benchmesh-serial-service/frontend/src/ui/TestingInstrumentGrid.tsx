import React from 'react'
import './TestingInstrumentGrid.css'

/**
 * TestingInstrumentGrid - Visual layout test component
 * Matches instrument display design from reference image
 */
export function TestingInstrumentGrid() {
  return (
    <div className="testing-grid-container">
      {/* U Label - Large left cell */}
      <div className="testing-grid-cell testing-grid-u-label">
        U
      </div>

      {/* DC Label - Top of second column */}
      <div className="testing-grid-cell testing-grid-dc">
        DC
      </div>

      {/* M Label - Bottom of second column */}
      <div className="testing-grid-cell testing-grid-m">
        M
      </div>

      {/* Main Display - Large number display */}
      <div className="testing-grid-cell testing-grid-main-display">
        00000
      </div>

      {/* SCI Label and Secondary Display */}
      <div className="testing-grid-sci-container">
        <div className="testing-grid-sci-label">
          SCI
        </div>
        <div className="testing-grid-secondary-display">
          00000
        </div>
      </div>

      {/* SET Button */}
      <div className="testing-grid-cell testing-grid-set-button">
        SET
      </div>

      {/* Button 1 */}
      <div className="testing-grid-cell testing-grid-btn-1">
        1
      </div>

      {/* Button 2 */}
      <div className="testing-grid-cell testing-grid-btn-2">
        2
      </div>

      {/* Button A */}
      <div className="testing-grid-cell testing-grid-btn-a">
        A
      </div>

      {/* Button B */}
      <div className="testing-grid-cell testing-grid-btn-b">
        B
      </div>
    </div>
  )
}
