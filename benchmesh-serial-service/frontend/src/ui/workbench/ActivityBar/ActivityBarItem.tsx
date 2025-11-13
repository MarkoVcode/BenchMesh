/**
 * ActivityBarItem - Single item in the Activity Bar
 *
 * Represents either an instrument or a view with an icon and optional LED badge
 */

import React from 'react';
import { IconType } from 'react-icons';
import { LEDBadge, HealthStatus } from './LEDBadge';
import './activity-bar.css';

interface ActivityBarItemProps {
  id: string;
  icon: IconType;
  label: string;
  active?: boolean;
  healthStatus?: HealthStatus | undefined;
  onClick: () => void;
  isParent?: boolean;
  isChild?: boolean;
}

export const ActivityBarItem: React.FC<ActivityBarItemProps> = ({
  id,
  icon: Icon,
  label,
  active = false,
  healthStatus,
  onClick,
  isParent = false,
  isChild = false,
}) => {
  const classNames = [
    'activity-bar-item',
    active && 'activity-bar-item--active',
    isParent && 'activity-bar-item--parent',
    isChild && 'activity-bar-item--child',
  ].filter(Boolean).join(' ');

  return (
    <button
      className={classNames}
      onClick={onClick}
      title={label}
      aria-label={label}
      data-testid={`activity-bar-item-${id}`}
      disabled={isParent}
    >
      <div className="activity-bar-item__icon">
        <Icon size={isChild ? 20 : 24} />
        {healthStatus && (
          <LEDBadge status={healthStatus} className="activity-bar-item__badge" />
        )}
      </div>
    </button>
  );
};
