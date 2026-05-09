import React from 'react';
import './ProgressBar.css';

interface ProgressBarProps {
  progress: number;
  message?: string;
  showPercentage?: boolean;
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  message,
  showPercentage = true,
}) => {
  const clamped = Math.min(100, Math.max(0, progress));

  return (
    <div className="progress-bar-wrapper">
      <div className="progress-bar">
        <div className="progress-bar__fill" style={{ width: `${clamped}%` }} />
      </div>
      {(message || showPercentage) && (
        <div className="progress-bar__info">
          {message && <span className="progress-bar__message">{message}</span>}
          {showPercentage && (
            <span className="progress-bar__percentage">{Math.round(clamped)}%</span>
          )}
        </div>
      )}
    </div>
  );
};

export default ProgressBar;
