import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getHistory } from '../services/api';
import './HistoryPage.css';

interface HistoryItem {
  id: string;
  input_type: string;
  input_url: string | null;
  document_title: string | null;
  status: string;
  overall_score: number | null;
  created_at: string | null;
}

const HistoryPage: React.FC = () => {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate('/');
      return;
    }

    if (isAuthenticated) {
      setIsLoading(true);
      getHistory()
        .then((res) => {
          setItems(res.data.items);
        })
        .catch((err) => {
          setError(err.response?.data?.detail || 'Failed to load history.');
        })
        .finally(() => {
          setIsLoading(false);
        });
    }
  }, [isAuthenticated, authLoading, navigate]);

  const getScoreColor = (score: number | null): string => {
    if (score === null) return 'var(--text-muted)';
    if (score >= 70) return 'var(--color-positive)';
    if (score >= 40) return 'var(--color-moderate)';
    return 'var(--color-critical)';
  };

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (authLoading || isLoading) {
    return (
      <div className="history-page">
        <div className="container">
          <div className="history-loading animate-fade-in">
            <span className="spinner" />
            <p>Loading history...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="history-page">
      <div className="container">
        <div className="history-header animate-fade-in">
          <h1>Analysis History</h1>
          <p>Your past document analyses</p>
        </div>

        {error && (
          <div className="history-error animate-fade-in">
            <p>❌ {error}</p>
          </div>
        )}

        {items.length === 0 && !error ? (
          <div className="history-empty glass-card animate-fade-in">
            <span className="history-empty__icon">📋</span>
            <h3>No analyses yet</h3>
            <p>Your analyzed documents will appear here.</p>
            <button className="btn btn-primary" onClick={() => navigate('/')}>
              🔍 Start Analyzing
            </button>
          </div>
        ) : (
          <div className="history-list">
            {items.map((item, i) => (
              <div
                key={item.id}
                className={`history-item glass-card animate-fade-in-up delay-${Math.min(i + 1, 5)}`}
                onClick={() => navigate(`/results/${item.id}`)}
              >
                <div className="history-item__main">
                  <div className="history-item__icon">
                    {item.input_type === 'url' ? '🔗' : item.input_type === 'file' ? '📄' : '📝'}
                  </div>
                  <div className="history-item__info">
                    <h3 className="history-item__title">
                      {item.document_title || item.input_url || 'Text Analysis'}
                    </h3>
                    <span className="history-item__date">{formatDate(item.created_at)}</span>
                  </div>
                </div>
                <div className="history-item__right">
                  {item.overall_score !== null ? (
                    <div
                      className="history-item__score"
                      style={{ color: getScoreColor(item.overall_score) }}
                    >
                      {item.overall_score}
                      <span className="history-item__score-label">score</span>
                    </div>
                  ) : (
                    <span className={`history-item__status history-item__status--${item.status}`}>
                      {item.status}
                    </span>
                  )}
                  <span className="history-item__arrow">→</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default HistoryPage;
