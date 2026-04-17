import React from 'react';
import './ProgressBar.css';

interface ProgressBarProps {
  progress: number; // 0-100
  message?: string;
  showPercentage?: boolean;
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  message,
  showPercentage = true,
}) => {
  return (
    <div className="progress-bar-wrapper">
      <div className="progress-bar">
        <div
          className="progress-bar__fill"
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        />
        <div className="progress-bar__glow" />
      </div>
      <div className="progress-bar__info">
        {message && <span className="progress-bar__message">{message}</span>}
        {showPercentage && (
          <span className="progress-bar__percentage">{Math.round(progress)}%</span>
        )}
      </div>
    </div>
  );
};

export default ProgressBar;
