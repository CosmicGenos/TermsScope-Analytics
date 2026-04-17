import React from 'react';
import RiskBadge from './RiskBadge';
import type { ClauseClassification } from '../services/api';
import './ClauseItem.css';

interface ClauseItemProps {
  clause: ClauseClassification;
  index: number;
}

const ClauseItem: React.FC<ClauseItemProps> = ({ clause, index }) => {
  return (
    <div
      className={`clause-item animate-fade-in`}
      style={{ animationDelay: `${index * 0.05}s` }}
    >
      <div className="clause-item__header">
        <RiskBadge level={clause.risk_level} size="sm" />
        {clause.section_reference && (
          <span className="clause-item__section">§ {clause.section_reference}</span>
        )}
      </div>

      <blockquote className="clause-item__quote">"{clause.clause_text}"</blockquote>

      <div className="clause-item__body">
        <p className="clause-item__summary">{clause.summary}</p>
        <div className="clause-item__implication">
          <span className="clause-item__implication-icon">⚠️</span>
          <p>{clause.implication}</p>
        </div>
      </div>
    </div>
  );
};

export default ClauseItem;
