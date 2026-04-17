import React, { useState } from 'react';
import ClauseItem from './ClauseItem';
import type { CategoryResult } from '../services/api';
import './CategoryCard.css';

interface CategoryCardProps {
  category: CategoryResult;
  index: number;
}

const CATEGORY_LABELS: Record<string, { label: string; icon: string }> = {
  privacy: { label: 'Privacy', icon: '🔐' },
  financial: { label: 'Financial', icon: '💰' },
  data_rights: { label: 'Data Rights', icon: '📊' },
  cancellation: { label: 'Cancellation', icon: '🚪' },
  liability: { label: 'Liability', icon: '⚖️' },
};

const getScoreColor = (score: number): string => {
  if (score >= 60) return 'var(--color-critical)';
  if (score >= 30) return 'var(--color-moderate)';
  return 'var(--color-positive)';
};

const CategoryCard: React.FC<CategoryCardProps> = ({ category, index }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const info = CATEGORY_LABELS[category.category] || {
    label: category.category,
    icon: '📋',
  };
  const scoreColor = getScoreColor(category.risk_score);

  return (
    <div
      className={`category-card glass-card animate-fade-in-up delay-${index + 1}`}
    >
      <div className="category-card__header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="category-card__title-row">
          <span className="category-card__icon">{info.icon}</span>
          <h3 className="category-card__name">{info.label}</h3>
          <div className="category-card__score" style={{ color: scoreColor }}>
            {category.risk_score}
            <span className="category-card__score-label">risk</span>
          </div>
        </div>

        <div className="category-card__risk-bar">
          <div
            className="category-card__risk-bar-fill"
            style={{
              width: `${category.risk_score}%`,
              background: scoreColor,
              boxShadow: `0 0 10px ${scoreColor}`,
            }}
          />
        </div>

        <p className="category-card__summary">{category.summary}</p>

        {category.key_concerns.length > 0 && (
          <div className="category-card__concerns">
            {category.key_concerns.map((concern, i) => (
              <div key={i} className="category-card__concern">
                <span className="category-card__concern-bullet">•</span>
                <span>{concern}</span>
              </div>
            ))}
          </div>
        )}

        {category.clauses.length > 0 && (
          <button className="category-card__toggle">
            {isExpanded ? '▲ Hide' : '▼ Show'} {category.clauses.length} clause
            {category.clauses.length !== 1 ? 's' : ''}
          </button>
        )}
      </div>

      {isExpanded && category.clauses.length > 0 && (
        <div className="category-card__clauses">
          {category.clauses.map((clause, i) => (
            <ClauseItem key={i} clause={clause} index={i} />
          ))}
        </div>
      )}
    </div>
  );
};

export default CategoryCard;
