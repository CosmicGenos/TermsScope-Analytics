import React, { useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useAnalysis } from '../hooks/useAnalysis';
import ScoreGauge from '../components/ScoreGauge';
import CategoryCard from '../components/CategoryCard';
import type { AnalysisResult } from '../services/api';
import './ResultsPage.css';

const ResultsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { result: fetchedResult, fetchResult, isLoading, error } = useAnalysis();

  // Try to get result from navigation state first
  const stateResult = (location.state as { result?: AnalysisResult } | null)?.result;
  const result = stateResult || fetchedResult;

  useEffect(() => {
    if (!stateResult && id) {
      fetchResult(id);
    }
  }, [id, stateResult, fetchResult]);

  if (isLoading && !result) {
    return (
      <div className="results-page">
        <div className="container">
          <div className="results-loading animate-fade-in">
            <span className="spinner" />
            <p>Loading results...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error && !result) {
    return (
      <div className="results-page">
        <div className="container">
          <div className="results-error glass-card animate-fade-in">
            <span>❌</span>
            <h2>Could not load results</h2>
            <p>{error}</p>
            <button className="btn btn-primary" onClick={() => navigate('/')}>
              ← New Analysis
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!result) return null;

  return (
    <div className="results-page">
      <div className="container">
        {/* Header */}
        <div className="results-header animate-fade-in-up">
          {result.document_title && (
            <h1 className="results-title">{result.document_title}</h1>
          )}
          <div className="results-meta">
            <span>{result.total_clauses_analyzed} clauses analyzed</span>
            <span>•</span>
            <span>5 categories</span>
          </div>
        </div>

        {/* Score & Summary */}
        <div className="results-overview animate-fade-in-up delay-1">
          <div className="results-score-card glass-card">
            <ScoreGauge score={result.overall_score} size={220} />
          </div>
          <div className="results-summary-card glass-card">
            <h2>Executive Summary</h2>
            <p className="results-summary-text">{result.overall_summary}</p>
            <div className="results-actions">
              <button className="btn btn-primary" onClick={() => navigate('/')}>
                🔍 New Analysis
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => {
                  navigator.clipboard.writeText(window.location.href);
                }}
              >
                📋 Copy Link
              </button>
            </div>
          </div>
        </div>

        {/* Category Cards */}
        <div className="results-categories">
          <h2 className="results-section-title animate-fade-in">Detailed Analysis</h2>
          <div className="results-categories-grid">
            {result.categories.map((category, i) => (
              <CategoryCard key={category.category} category={category} index={i} />
            ))}
          </div>
        </div>

        {/* Disclaimer */}
        <div className="results-disclaimer glass-card animate-fade-in">
          <p>⚠️ {result.disclaimer}</p>
        </div>
      </div>
    </div>
  );
};

export default ResultsPage;
