import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAnalysis } from '../hooks/useAnalysis';
import ProgressBar from '../components/ProgressBar';
import './AnalyzingPage.css';

const AnalyzingPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { status, progress, message, result, error, streamProgress } = useAnalysis();

  useEffect(() => {
    if (id) {
      streamProgress(id);
    }
  }, [id, streamProgress]);

  useEffect(() => {
    if (status === 'complete' && id) {
      // Short delay for visual satisfaction
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
          <div className="analyzing-content glass-card animate-fade-in">
            <div className="analyzing-error">
              <span className="analyzing-error__icon">❌</span>
              <h2>Analysis Failed</h2>
              <p>{error}</p>
              <button className="btn btn-primary" onClick={() => navigate('/')}>
                ← Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="analyzing-page">
      <div className="container">
        <div className="analyzing-content glass-card animate-fade-in">
          <div className="analyzing-visual">
            <div className="analyzing-rings">
              <div className="analyzing-ring analyzing-ring--1" />
              <div className="analyzing-ring analyzing-ring--2" />
              <div className="analyzing-ring analyzing-ring--3" />
              <div className="analyzing-center">🔍</div>
            </div>
          </div>

          <h2 className="analyzing-title">
            {status === 'complete' ? 'Analysis Complete!' : 'Analyzing Document...'}
          </h2>

          <div className="analyzing-progress">
            <ProgressBar progress={progress} message={message} />
          </div>

          <div className="analyzing-stages">
            <StageIndicator label="Fetch" done={progress > 5} active={progress <= 5} />
            <StageIndicator label="Validate" done={progress > 15} active={progress > 5 && progress <= 15} />
            <StageIndicator label="Chunk" done={progress > 25} active={progress > 15 && progress <= 25} />
            <StageIndicator label="Analyze" done={progress > 40} active={progress > 25 && progress <= 80} />
            <StageIndicator label="Compile" done={progress >= 100} active={progress > 80 && progress < 100} />
          </div>
        </div>
      </div>
    </div>
  );
};

const StageIndicator: React.FC<{ label: string; done: boolean; active: boolean }> = ({
  label,
  done,
  active,
}) => (
  <div className={`stage ${done ? 'stage--done' : ''} ${active ? 'stage--active' : ''}`}>
    <div className="stage__dot">
      {done ? '✓' : active ? <span className="stage__pulse" /> : ''}
    </div>
    <span className="stage__label">{label}</span>
  </div>
);

export default AnalyzingPage;
