import React, { useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useAnalysis } from '../hooks/useAnalysis';
import './AnalyzingPage.css';

type InputType = 'url' | 'text' | 'file';

interface Stage {
  getLabel: (type: InputType) => string;
  shortLabel: string;
  doneAt: number;
}

const STAGES: Stage[] = [
  {
    getLabel: (type) =>
      type === 'url'
        ? 'Fetching from the web'
        : type === 'file'
        ? 'Reading your file'
        : 'Preparing your text',
    shortLabel: 'Fetching',
    doneAt: 10,
  },
  {
    getLabel: () => 'Checking the content',
    shortLabel: 'Checking',
    doneAt: 30,
  },
  {
    getLabel: () => 'Scanning through the terms',
    shortLabel: 'Scanning',
    doneAt: 80,
  },
  {
    getLabel: () => 'Preparing your report',
    shortLabel: 'Preparing',
    doneAt: 100,
  },
];

function getStageIndex(progress: number): number {
  if (progress <= 10) return 0;
  if (progress <= 30) return 1;
  if (progress <= 80) return 2;
  return 3;
}

const AnalyzingPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const inputType: InputType = (location.state as { inputType?: InputType })?.inputType ?? 'url';

  const { status, progress, result, error, streamProgress } = useAnalysis();

  useEffect(() => {
    if (id) streamProgress(id);
  }, [id, streamProgress]);

  useEffect(() => {
    if (status === 'complete' && id) {
      const timer = setTimeout(() => {
        navigate(`/results/${id}`, { state: { result } });
      }, 800);
      return () => clearTimeout(timer);
    }
  }, [status, id, result, navigate]);

  if (error) {
    return (
      <div className="analyzing-page">
        <div className="container">
          <div className="analyzing-content animate-fade-in">
            <div className="analyzing-error">
              <div className="analyzing-error__icon">⚠</div>
              <h2>Analysis failed</h2>
              <p>{error}</p>
              <button className="btn btn-primary" onClick={() => navigate('/')}>
                Try again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const currentStageIndex = getStageIndex(progress);
  const isComplete = status === 'complete';
  const currentLabel = isComplete
    ? 'Analysis complete'
    : STAGES[currentStageIndex].getLabel(inputType);

  const clampedProgress = Math.min(100, Math.max(0, progress));

  return (
    <div className="analyzing-page">
      <div className="container">
        <div className="analyzing-content animate-fade-in">

          {/* Current stage label — the hero */}
          <div className="analyzing-headline">
            <span className="analyzing-headline__text">{currentLabel}</span>
            {!isComplete && (
              <span className="analyzing-ellipsis" aria-hidden="true">
                <span />
                <span />
                <span />
              </span>
            )}
          </div>

          {/* Progress bar + percentage */}
          <div className="analyzing-bar-wrapper">
            <div className="analyzing-bar-track">
              <div
                className={`analyzing-bar-fill${isComplete ? ' analyzing-bar-fill--complete' : ''}`}
                style={{ width: `${clampedProgress}%` }}
              />
            </div>
            <span className="analyzing-percentage">{Math.round(clampedProgress)}%</span>
          </div>

          {/* Stage nodes — desktop */}
          <div className="analyzing-stages" aria-hidden="true">
            {STAGES.map((stage, i) => {
              const isDone = isComplete || progress > stage.doneAt || i < currentStageIndex;
              const isActive = !isComplete && i === currentStageIndex;
              return (
                <React.Fragment key={i}>
                  {i > 0 && (
                    <div
                      className={`analyzing-connector${isDone || i <= currentStageIndex ? ' analyzing-connector--lit' : ''}`}
                    />
                  )}
                  <div className="analyzing-node">
                    <div
                      className={`analyzing-dot${isDone ? ' analyzing-dot--done' : isActive ? ' analyzing-dot--active' : ''}`}
                    >
                      {isDone && <CheckIcon />}
                    </div>
                    <span
                      className={`analyzing-node-label${isDone ? ' analyzing-node-label--done' : isActive ? ' analyzing-node-label--active' : ''}`}
                    >
                      {stage.shortLabel}
                    </span>
                  </div>
                </React.Fragment>
              );
            })}
          </div>

          {/* Step counter — shown on all sizes, primary on mobile */}
          <div className="analyzing-step-count">
            Step {Math.min(currentStageIndex + 1, 4)} of 4
          </div>

        </div>
      </div>
    </div>
  );
};

const CheckIcon: React.FC = () => (
  <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
    <path
      d="M1.5 5l2.5 2.5 4.5-4.5"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

export default AnalyzingPage;
