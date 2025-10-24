import React from 'react'
import './TestingInstrumentGrid.css'

/**
 * TestingInstrumentGrid - Visual layout test component
 * Fixed size: 310px × 70px
 * Layout matches instrument display with invisible grid structure
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

      {/* Number Button 1 */}
      <div className="testing-grid-cell testing-grid-num-1">
        1
      </div>

      {/* Number Button 2 */}
      <div className="testing-grid-cell testing-grid-num-2">
        2
      </div>

      {/* SET Button */}
      <div className="testing-grid-cell testing-grid-set-button">
        SET
      </div>

      {/* Button A */}
      <div className="testing-grid-cell testing-grid-btn-a">
        A
      </div>

      {/* Button C */}
      <div className="testing-grid-cell testing-grid-btn-c">
        C
      </div>

      {/* Button B */}
      <div className="testing-grid-cell testing-grid-btn-b">
        B
      </div>

      {/* Button D */}
      <div className="testing-grid-cell testing-grid-btn-d">
        D
      </div>
    </div>
  )
}
