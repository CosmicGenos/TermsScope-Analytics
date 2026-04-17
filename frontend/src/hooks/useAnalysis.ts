import { useState, useCallback, useRef } from 'react';
import {
  submitUrlAnalysis,
  submitTextAnalysis,
  submitFileAnalysis,
  getAnalysis,
  type AnalysisResult,
  type SSEEvent,
} from '../services/api';

interface UseAnalysisReturn {
  analysisId: string | null;
  status: string;
  progress: number;
  message: string;
  result: AnalysisResult | null;
  error: string | null;
  isLoading: boolean;
  submitUrl: (url: string) => Promise<string | null>;
  submitText: (text: string) => Promise<string | null>;
  submitFile: (file: File) => Promise<string | null>;
  streamProgress: (analysisId: string) => void;
  fetchResult: (analysisId: string) => Promise<void>;
  reset: () => void;
}

export const useAnalysis = (): UseAnalysisReturn => {
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [status, setStatus] = useState('idle');
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const reset = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setAnalysisId(null);
    setStatus('idle');
    setProgress(0);
    setMessage('');
    setResult(null);
    setError(null);
    setIsLoading(false);
  }, []);

  const handleSubmitResponse = useCallback(
    (data: { analysis_id: string; status: string; cached: boolean; result?: AnalysisResult }) => {
      setAnalysisId(data.analysis_id);

      if (data.cached && data.result) {
        setStatus('complete');
        setProgress(100);
        setMessage('Analysis complete (cached)!');
        setResult(data.result);
        setIsLoading(false);
        return data.analysis_id;
      }

      setStatus(data.status);
      setIsLoading(true);
      return data.analysis_id;
    },
    []
  );

  const submitUrl = useCallback(
    async (url: string): Promise<string | null> => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await submitUrlAnalysis(url);
        return handleSubmitResponse(response.data);
      } catch (err: unknown) {
        const errorMsg =
          err instanceof Error ? err.message : 'Failed to submit URL for analysis.';
        setError(errorMsg);
        setIsLoading(false);
        return null;
      }
    },
    [handleSubmitResponse]
  );

  const submitText = useCallback(
    async (text: string): Promise<string | null> => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await submitTextAnalysis(text);
        return handleSubmitResponse(response.data);
      } catch (err: unknown) {
        const errorMsg =
          err instanceof Error ? err.message : 'Failed to submit text for analysis.';
        setError(errorMsg);
        setIsLoading(false);
        return null;
      }
    },
    [handleSubmitResponse]
  );

  const submitFile = useCallback(
    async (file: File): Promise<string | null> => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await submitFileAnalysis(file);
        return handleSubmitResponse(response.data);
      } catch (err: unknown) {
        const errorMsg =
          err instanceof Error ? err.message : 'Failed to submit file for analysis.';
        setError(errorMsg);
        setIsLoading(false);
        return null;
      }
    },
    [handleSubmitResponse]
  );

  const streamProgress = useCallback((id: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const es = new EventSource(`/api/analyze/${id}/stream`);
    eventSourceRef.current = es;

    es.addEventListener('status', (event) => {
      const data: SSEEvent = JSON.parse(event.data);
      setStatus(data.status);
      if (data.progress !== undefined) setProgress(data.progress);
      if (data.message) setMessage(data.message);
    });

    es.addEventListener('complete', (event) => {
      const data: SSEEvent = JSON.parse(event.data);
      setStatus('complete');
      setProgress(100);
      setMessage('Analysis complete!');
      if (data.result) setResult(data.result);
      setIsLoading(false);
      es.close();
      eventSourceRef.current = null;
    });

    es.addEventListener('error', (event) => {
      try {
        const data: SSEEvent = JSON.parse((event as MessageEvent).data);
        setError(data.error || 'An error occurred during analysis.');
      } catch {
        setError('Connection lost. Please try again.');
      }
      setStatus('error');
      setIsLoading(false);
      es.close();
      eventSourceRef.current = null;
    });

    es.addEventListener('keepalive', () => {
      // Just a keepalive, do nothing
    });
  }, []);

  const fetchResult = useCallback(async (id: string) => {
    try {
      setIsLoading(true);
      const response = await getAnalysis(id);
      const data = response.data;
      setAnalysisId(data.analysis_id);
      setStatus(data.status);
      if (data.result) {
        setResult(data.result);
        setProgress(100);
      }
      if (data.error) {
        setError(data.error);
      }
    } catch {
      setError('Failed to fetch analysis result.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    analysisId,
    status,
    progress,
    message,
    result,
    error,
    isLoading,
    submitUrl,
    submitText,
    submitFile,
    streamProgress,
    fetchResult,
    reset,
  };
};
