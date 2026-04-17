import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('termsscope_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('termsscope_token');
      // Only redirect if not already on auth pages
      if (!window.location.pathname.includes('/auth')) {
        // Don't redirect, just clear token — user can still use app anonymously
      }
    }
    return Promise.reject(error);
  }
);

// ── Analysis API ──────────────────────────────────────────

export interface AnalysisSubmitResponse {
  analysis_id: string;
  status: string;
  cached: boolean;
  result?: AnalysisResult;
}

export interface AnalysisResult {
  overall_score: number;
  overall_summary: string;
  categories: CategoryResult[];
  document_title: string | null;
  total_clauses_analyzed: number;
  disclaimer: string;
}

export interface CategoryResult {
  category: string;
  risk_score: number;
  clauses: ClauseClassification[];
  summary: string;
  key_concerns: string[];
}

export interface ClauseClassification {
  clause_text: string;
  risk_level: 'critical' | 'moderate' | 'positive' | 'neutral';
  summary: string;
  implication: string;
  section_reference: string | null;
}

export interface SSEEvent {
  status: string;
  message?: string;
  progress?: number;
  error?: string;
  analysis_id?: string;
  result?: AnalysisResult;
}

export const submitUrlAnalysis = (url: string, llmProvider?: string, llmModel?: string) =>
  api.post<AnalysisSubmitResponse>('/analyze', {
    input_type: 'url',
    url,
    llm_provider: llmProvider,
    llm_model: llmModel,
  });

export const submitTextAnalysis = (text: string, llmProvider?: string, llmModel?: string) =>
  api.post<AnalysisSubmitResponse>('/analyze', {
    input_type: 'text',
    text,
    llm_provider: llmProvider,
    llm_model: llmModel,
  });

export const submitFileAnalysis = (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post<AnalysisSubmitResponse>('/analyze/file', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const getAnalysis = (analysisId: string) =>
  api.get(`/analyze/${analysisId}`);

export const getHistory = (limit = 20, offset = 0) =>
  api.get('/history', { params: { limit, offset } });

export const getHistoryItem = (analysisId: string) =>
  api.get(`/history/${analysisId}`);

export const getCurrentUser = () =>
  api.get('/auth/me');

export default api;
