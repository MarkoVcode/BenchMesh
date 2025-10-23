import React from 'react'

/**
 * TestingInstrumentGrid - Visual layout test component
 * Creates a complex grid layout for visual inspection
 */
export function TestingInstrumentGrid() {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(12, 1fr)',
        gridTemplateRows: 'repeat(3, 60px)',
        gap: '0',
        border: '2px solid var(--border)',
        width: '100%',
        height: '100%',
        minHeight: '180px'
      }}
    >
      {/* Cell 1 - Large left cell (2 rows) */}
      <div
        style={{
          gridColumn: '1 / 3',
          gridRow: '1 / 3',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '24px',
          fontWeight: 'bold',
          color: 'var(--text)'
        }}
      >
      </div>

      {/* Cell 2 - Medium cell (2 rows) */}
      <div
        style={{
          gridColumn: '3 / 4',
          gridRow: '1 / 3',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '20px',
          fontWeight: 'bold',
          color: 'var(--text)'
        }}
      >
      </div>

      {/* Cell 3 - Small top-left middle */}
      <div
        style={{
          gridColumn: '4 / 6',
          gridRow: '1 / 2',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '18px',
          fontWeight: 'bold',
          color: 'var(--text)'
        }}
      >
      </div>

      {/* Cell 4 - Small top-right middle */}
      <div
        style={{
          gridColumn: '6 / 8',
          gridRow: '1 / 2',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '18px',
          fontWeight: 'bold',
          color: 'var(--text)'
        }}
      >
      </div>

      {/* Cell 5 - Tall right-center cell (3 rows) */}
      <div
        style={{
          gridColumn: '8 / 10',
          gridRow: '1 / 4',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '24px',
          fontWeight: 'bold',
          color: 'var(--text)'
        }}
      >
      </div>

      {/* Cell 6 - Small top-right quad 1 */}
      <div
        style={{
          gridColumn: '10 / 11',
          gridRow: '1 / 2',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '16px',
          fontWeight: 'bold',
          color: 'var(--text)'
        }}
      >
      </div>

      {/* Cell 7 - Small top-right quad 2 */}
      <div
        style={{
          gridColumn: '11 / 13',
          gridRow: '1 / 2',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '16px',
          fontWeight: 'bold',
          color: 'var(--text)'
        }}
      >
      </div>

      {/* Cell 8 - Small middle-right quad 1 */}
      <div
        style={{
          gridColumn: '10 / 11',
          gridRow: '2 / 3',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '16px',
          fontWeight: 'bold',
          color: 'var(--text)'
        }}
      >
      </div>

      {/* Cell 9 - Small middle-right quad 2 */}
      <div
        style={{
          gridColumn: '11 / 13',
          gridRow: '2 / 3',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '16px',
          fontWeight: 'bold',
          color: 'var(--text)'
        }}
      >
      </div>

      {/* Cell 10 - Wide bottom cell */}
      <div
        style={{
          gridColumn: '4 / 8',
          gridRow: '2 / 3',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '18px',
          fontWeight: 'bold',
          color: 'var(--text)'
        }}
      >
      </div>

      {/* Cell 11 - Wide bottom-left cell */}
      <div
        style={{
          gridColumn: '1 / 5',
          gridRow: '3 / 4',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '18px',
          fontWeight: 'bold',
          color: 'var(--text)'
        }}
      >
      </div>

      {/* Cell 12 - Wide bottom-center cell */}
      <div
        style={{
          gridColumn: '5 / 8',
          gridRow: '3 / 4',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '18px',
          fontWeight: 'bold',
          color: 'var(--text)'
        }}
      >
      </div>

      {/* Cell 13 - Small bottom-right quad 1 */}
      <div
        style={{
          gridColumn: '10 / 11',
          gridRow: '3 / 4',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '16px',
          fontWeight: 'bold',
          color: 'var(--text)'
        }}
      >
      </div>

      {/* Cell 14 - Small bottom-right quad 2 */}
      <div
        style={{
          gridColumn: '11 / 13',
          gridRow: '3 / 4',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '16px',
          fontWeight: 'bold',
          color: 'var(--text)'
        }}
      >
      </div>
    </div>
  )
}
