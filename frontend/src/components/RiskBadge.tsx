import React from 'react';
import './RiskBadge.css';

interface RiskBadgeProps {
  level: 'critical' | 'moderate' | 'positive' | 'neutral';
  size?: 'sm' | 'md';
}

const LABELS: Record<string, string> = {
  critical: '🔴 Critical',
  moderate: '🟡 Moderate',
  positive: '🟢 Positive',
  neutral: '⚪ Neutral',
};

const RiskBadge: React.FC<RiskBadgeProps> = ({ level, size = 'md' }) => {
  return (
    <span className={`risk-badge risk-badge--${level} risk-badge--${size}`}>
      {LABELS[level] || level}
    </span>
  );
};

export default RiskBadge;
