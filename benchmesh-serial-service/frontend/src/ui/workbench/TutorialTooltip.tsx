/**
 * TutorialTooltip - Onboarding tooltip pointing to the Add Instrument button
 *
 * Shows a dismissible tooltip when no instruments are configured,
 * guiding users to click the "+" icon to add their first instrument.
 */

import React, { useState, useEffect } from 'react';
import { VscClose } from 'react-icons/vsc';
import './styles/tutorial-tooltip.css';

interface TutorialTooltipProps {
  show: boolean;
}

export const TutorialTooltip: React.FC<TutorialTooltipProps> = ({ show }) => {
  const [dismissed, setDismissed] = useState(() => {
    try {
      return localStorage.getItem('benchmesh:tutorial-dismissed') === 'true';
    } catch {
      return false;
    }
  });

  const handleDismiss = () => {
    setDismissed(true);
    try {
      localStorage.setItem('benchmesh:tutorial-dismissed', 'true');
    } catch (e) {
      console.error('Failed to save tutorial dismissal:', e);
    }
  };

  if (!show || dismissed) {
    return null;
  }

  return (
    <div className="tutorial-tooltip" data-testid="tutorial-tooltip">
      <div className="tutorial-tooltip__content">
        <button
          className="tutorial-tooltip__close"
          onClick={handleDismiss}
          aria-label="Dismiss tutorial"
        >
          <VscClose size={16} />
        </button>
        <div className="tutorial-tooltip__title">Get Started</div>
        <div className="tutorial-tooltip__text">
          Click the <strong>+</strong> icon to add your first instrument
        </div>
      </div>
      <div className="tutorial-tooltip__arrow" />
    </div>
  );
};
