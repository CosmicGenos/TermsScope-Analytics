import React, { useEffect, useState } from 'react';
import './ScoreGauge.css';

interface ScoreGaugeProps {
  score: number; // 0-100
  size?: number;
  label?: string;
}

const ScoreGauge: React.FC<ScoreGaugeProps> = ({ score, size = 200, label = 'Trust Score' }) => {
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => setAnimatedScore(score), 100);
    return () => clearTimeout(timer);
  }, [score]);

  const radius = (size - 20) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (animatedScore / 100) * circumference;

  const getColor = (s: number): string => {
    if (s >= 70) return 'var(--color-positive)';
    if (s >= 40) return 'var(--color-moderate)';
    return 'var(--color-critical)';
  };

  const getLabel = (s: number): string => {
    if (s >= 80) return 'Excellent';
    if (s >= 70) return 'Good';
    if (s >= 50) return 'Fair';
    if (s >= 30) return 'Concerning';
    return 'High Risk';
  };

  const color = getColor(animatedScore);

  return (
    <div className="score-gauge" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--border-color)"
          strokeWidth="8"
        />
        {/* Score arc */}
        <circle
          className="score-gauge__arc"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{
            filter: `drop-shadow(0 0 8px ${color})`,
          }}
        />
      </svg>
      <div className="score-gauge__content">
        <span className="score-gauge__number" style={{ color }}>
          {animatedScore}
        </span>
        <span className="score-gauge__label">{label}</span>
        <span className="score-gauge__verdict" style={{ color }}>
          {getLabel(animatedScore)}
        </span>
      </div>
    </div>
  );
};

export default ScoreGauge;
