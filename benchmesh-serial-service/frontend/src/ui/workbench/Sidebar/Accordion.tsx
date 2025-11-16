/**
 * Accordion - Simple accordion component for collapsible content
 *
 * Features:
 * - Single-expand mode (opening one closes others)
 * - Smooth expand/collapse animation
 * - Accessible keyboard navigation
 * - Chevron icon rotation
 */

import React from 'react';
import { VscChevronDown, VscChevronRight } from 'react-icons/vsc';

interface AccordionItemProps {
  id: string;
  header: React.ReactNode;
  children: React.ReactNode;
  isExpanded: boolean;
  onToggle: (id: string) => void;
  errorBadge?: boolean; // Show error indicator
}

export const AccordionItem: React.FC<AccordionItemProps> = ({
  id,
  header,
  children,
  isExpanded,
  onToggle,
  errorBadge = false,
}) => {
  const handleClick = () => {
    onToggle(id);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onToggle(id);
    }
  };

  return (
    <div className="accordion-item" data-testid={`accordion-item-${id}`}>
      <button
        className={`accordion-header ${isExpanded ? 'accordion-header--expanded' : ''}`}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        aria-expanded={isExpanded}
        aria-controls={`accordion-content-${id}`}
        data-testid={`accordion-header-${id}`}
      >
        <span className="accordion-header__icon">
          {isExpanded ? <VscChevronDown size={16} /> : <VscChevronRight size={16} />}
        </span>
        <span className="accordion-header__title">{header}</span>
        {errorBadge && (
          <span className="accordion-header__error-badge" title="Has validation errors">
            ⚠
          </span>
        )}
      </button>
      {isExpanded && (
        <div
          className="accordion-content"
          id={`accordion-content-${id}`}
          role="region"
          aria-labelledby={`accordion-header-${id}`}
          data-testid={`accordion-content-${id}`}
        >
          {children}
        </div>
      )}
    </div>
  );
};

interface AccordionProps {
  children: React.ReactNode;
}

export const Accordion: React.FC<AccordionProps> = ({ children }) => {
  return (
    <div className="accordion" data-testid="accordion">
      {children}
    </div>
  );
};
