import React from 'react'
import './TestingInstrumentGrid.css'

/**
 * TestingInstrumentGrid - Visual layout test component
 * Creates a complex grid layout for visual inspection
 */
export function TestingInstrumentGrid() {
  return (
    <div className="testing-grid-container">
      {/* Cell 1 - Large left cell (2 rows) */}
      <div className="testing-grid-cell testing-grid-cell-1">
        <div className="psu-label">{"U"}</div>
      </div>

      {/* Cell 2 - Medium cell (2 rows) */}
      <div className="testing-grid-cell testing-grid-cell-2">
        <span className="psu-number readonly" aria-hidden>
          <span>{'U'}</span>
        </span>
      </div>

      {/* Cell 3 - Small top-left middle */}
      <div className="testing-grid-cell testing-grid-cell-3">
      </div>

      {/* Cell 4 - Small top-right middle */}
      <div className="testing-grid-cell testing-grid-cell-4">
      </div>

      {/* Cell 5 - Tall right-center cell (3 rows) */}
      <div className="testing-grid-cell testing-grid-cell-5">
      </div>

      {/* Cell 6 - Small top-right quad 1 */}
      <div className="testing-grid-cell testing-grid-cell-6">
      </div>

      {/* Cell 7 - Small top-right quad 2 */}
      <div className="testing-grid-cell testing-grid-cell-7">
      </div>

      {/* Cell 8 - Small middle-right quad 1 */}
      <div className="testing-grid-cell testing-grid-cell-8">
      </div>

      {/* Cell 9 - Small middle-right quad 2 */}
      <div className="testing-grid-cell testing-grid-cell-9">
      </div>

      {/* Cell 10 - Wide bottom cell */}
      <div className="testing-grid-cell testing-grid-cell-10">
      </div>

      {/* Cell 11 - Wide bottom-left cell */}
      <div className="testing-grid-cell testing-grid-cell-11">
      </div>

      {/* Cell 12 - Wide bottom-center cell */}
      <div className="testing-grid-cell testing-grid-cell-12">
      </div>

      {/* Cell 13 - Small bottom-right quad 1 */}
      <div className="testing-grid-cell testing-grid-cell-13">
      </div>

      {/* Cell 14 - Small bottom-right quad 2 */}
      <div className="testing-grid-cell testing-grid-cell-14">
      </div>
    </div>
  )
}
