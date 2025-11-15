/**
 * DisclaimerModal - Startup safety disclaimer
 *
 * Shows important safety information on first app load:
 * - Instrument connection requirements
 * - Testing scope limitations
 * - Liability disclaimer
 *
 * Cannot be dismissed except by accepting. Optional "don't show again" checkbox.
 */

import React, { useState } from 'react';

interface DisclaimerModalProps {
  isOpen: boolean;
  onAccept: (dontShowAgain: boolean) => void;
}

export function DisclaimerModal({ isOpen, onAccept }: DisclaimerModalProps) {
  const [dontShowAgain, setDontShowAgain] = useState(false);

  if (!isOpen) return null;

  const handleAccept = () => {
    onAccept(dontShowAgain);
  };

  return (
    <div className="modal-overlay" style={{ zIndex: 1000 }}>
      <div className="modal-content" style={{ maxWidth: '700px' }}>
        <div className="modal-header" style={{ borderBottom: '2px solid var(--warn)' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '28px' }}>⚠️</span>
            Important Safety Information
          </h2>
        </div>

        <div className="modal-body">
          <p style={{ fontSize: '14px', color: 'var(--text-1)', marginBottom: '24px' }}>
            Before using BenchMesh, please read and acknowledge the following:
          </p>

          <div className="disclaimer-points">
            <div className="disclaimer-point">
              <div className="disclaimer-number">1</div>
              <div className="disclaimer-content">
                <h3>Connect Instruments Before Starting</h3>
                <p>
                  Some instruments may not handle being connected while the software is
                  actively communicating with them. <strong>Always connect all instruments
                  to your computer and power them on BEFORE starting BenchMesh.</strong>
                </p>
              </div>
            </div>

            <div className="disclaimer-point">
              <div className="disclaimer-number">2</div>
              <div className="disclaimer-content">
                <h3>Limited Testing Scope</h3>
                <p>
                  This software has been tested on a limited number of instrument models.
                  While no damage or issues have been observed during testing, your specific
                  instrument configuration may behave differently.
                </p>
              </div>
            </div>

            <div className="disclaimer-point">
              <div className="disclaimer-number">3</div>
              <div className="disclaimer-content">
                <h3>No Warranty or Liability</h3>
                <p>
                  BenchMesh is provided "as-is" without any warranty. The creators and
                  maintainers assume no responsibility for any damage, data loss, or issues
                  that may occur from using this software.
                </p>
              </div>
            </div>
          </div>

          <label className="disclaimer-checkbox">
            <input
              type="checkbox"
              checked={dontShowAgain}
              onChange={(e) => setDontShowAgain(e.target.checked)}
            />
            <span>Don't show this message again</span>
          </label>
        </div>

        <div className="modal-footer">
          <button
            className="btn-primary"
            onClick={handleAccept}
            style={{ fontSize: '14px', padding: '10px 24px', fontWeight: 600 }}
          >
            I Agree and Continue
          </button>
        </div>
      </div>
    </div>
  );
}
