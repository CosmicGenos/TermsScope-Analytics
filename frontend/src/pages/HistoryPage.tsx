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

type DateGroup = 'Today' | 'Yesterday' | 'This week' | 'Earlier';

function groupByDate(items: HistoryItem[]): Array<{ label: DateGroup; items: HistoryItem[] }> {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfYesterday = new Date(startOfToday);
  startOfYesterday.setDate(startOfYesterday.getDate() - 1);
  const startOfWeek = new Date(startOfToday);
  startOfWeek.setDate(startOfWeek.getDate() - 7);

  const buckets: Record<DateGroup, HistoryItem[]> = {
    Today: [],
    Yesterday: [],
    'This week': [],
    Earlier: [],
  };

  for (const item of items) {
    if (!item.created_at) {
      buckets.Earlier.push(item);
      continue;
    }
    const d = new Date(item.created_at);
    const dayStart = new Date(d.getFullYear(), d.getMonth(), d.getDate());

    if (dayStart >= startOfToday) {
      buckets.Today.push(item);
    } else if (dayStart >= startOfYesterday) {
      buckets.Yesterday.push(item);
    } else if (dayStart >= startOfWeek) {
      buckets['This week'].push(item);
    } else {
      buckets.Earlier.push(item);
    }
  }

  return (['Today', 'Yesterday', 'This week', 'Earlier'] as DateGroup[])
    .filter((label) => buckets[label].length > 0)
    .map((label) => ({ label, items: buckets[label] }));
}

function getRiskBadge(score: number | null) {
  if (score === null) return null;
  if (score >= 70) return { label: 'Low risk', cls: 'badge--low' };
  if (score >= 40) return { label: 'Med risk', cls: 'badge--med' };
  return { label: 'High risk', cls: 'badge--high' };
}

function formatTime(dateStr: string | null): string {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

const INPUT_ICONS: Record<string, string> = {
  url: '🔗',
  file: '📄',
  text: '📝',
};

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
        .then((res) => setItems(res.data.items))
        .catch((err) => setError(err.response?.data?.detail || 'Failed to load history.'))
        .finally(() => setIsLoading(false));
    }
  }, [isAuthenticated, authLoading, navigate]);

  if (authLoading || isLoading) {
    return (
      <div className="history-page">
        <div className="container">
          <div className="history-loading animate-fade-in">
            <span className="spinner spinner--light" />
            <p>Loading history...</p>
          </div>
        </div>
      </div>
    );
  }

  const groups = groupByDate(items);

  return (
    <div className="history-page">
      <div className="container">
        <div className="history-header animate-fade-in">
          <h1>History</h1>
          <p>Your previous analyses</p>
        </div>

        {error && (
          <div className="history-error animate-fade-in">
            <p>{error}</p>
          </div>
        )}

        {items.length === 0 && !error ? (
          <div className="history-empty glass-card animate-fade-in">
            <span className="history-empty__icon">📋</span>
            <h3>Nothing here yet</h3>
            <p>Analysed documents will appear here.</p>
            <button className="btn btn-primary" onClick={() => navigate('/')}>
              Start analysing
            </button>
          </div>
        ) : (
          <div className="history-groups">
            {groups.map(({ label, items: groupItems }) => (
              <div key={label} className="history-group animate-fade-in">
                <div className="history-group__label">{label}</div>
                <div className="history-list">
                  {groupItems.map((item) => {
                    const badge = getRiskBadge(item.overall_score);
                    const isToday = label === 'Today';
                    return (
                      <div
                        key={item.id}
                        className="history-row"
                        onClick={() => navigate(`/results/${item.id}`)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => e.key === 'Enter' && navigate(`/results/${item.id}`)}
                      >
                        <div className="history-row__left">
                          <span className="history-row__type-icon" aria-hidden="true">
                            {INPUT_ICONS[item.input_type] ?? '📄'}
                          </span>
                          <div className="history-row__info">
                            <span className="history-row__title">
                              {item.document_title || item.input_url || 'Text analysis'}
                            </span>
                            <span className="history-row__meta">
                              {isToday ? formatTime(item.created_at) : formatDate(item.created_at)}
                            </span>
                          </div>
                        </div>
                        <div className="history-row__right">
                          {badge ? (
                            <span className={`risk-badge ${badge.cls}`}>{badge.label}</span>
                          ) : (
                            <span className={`status-pill status-pill--${item.status}`}>
                              {item.status}
                            </span>
                          )}
                          <span className="history-row__chevron" aria-hidden="true">›</span>
                        </div>
                      </div>
                    );
                  })}
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
