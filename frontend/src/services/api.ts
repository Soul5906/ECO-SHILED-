// API service layer — all backend communication
import axios, { AxiosError } from 'axios';
import type {
  AnalysisResult,
  AnalysisSummary,
  AppSettings,
  CompareResponse,
  DatasetValidationResponse,
  HealthResponse,
  ScenarioDetail,
  ScenarioSummary,
} from '../types';

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const api = axios.create({ baseURL: BASE, timeout: 120_000 });

function extractMessage(err: unknown): string {
  if (err instanceof AxiosError) {
    const data = err.response?.data;
    if (data?.detail) return String(data.detail);
    if (data?.error) return String(data.error);
    if (err.code === 'ECONNREFUSED' || err.code === 'ERR_NETWORK') {
      return 'Cannot reach the backend. Is the server running on port 8000?';
    }
    return err.message;
  }
  return String(err);
}

export class ApiServiceError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ApiServiceError';
    this.status = status;
  }
}

async function safe<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (err) {
    const msg = extractMessage(err);
    const status = err instanceof AxiosError ? err.response?.status : undefined;
    throw new ApiServiceError(msg, status);
  }
}

// Health
export const getHealth = () => safe<HealthResponse>(() => api.get('/health').then(r => r.data));

// Scenarios
export const getScenarios = () => safe<ScenarioSummary[]>(() => api.get('/scenarios').then(r => r.data));
export const getScenarioDetail = (id: string) => safe<ScenarioDetail>(() => api.get(`/scenarios/${id}`).then(r => r.data));

// Dataset validation
export const validateCsv = (file: File) => {
  const form = new FormData();
  form.append('file', file);
  return safe<DatasetValidationResponse>(() => api.post('/datasets/validate', form).then(r => r.data));
};

// Analysis
export const analyzeDataset = (datasetId: string, configOverrides?: Record<string, unknown>) =>
  safe<AnalysisResult>(() =>
    api.post('/analyze', { dataset_id: datasetId, config_overrides: configOverrides }).then(r => r.data)
  );

export const analyzeCsv = (file: File) => {
  const form = new FormData();
  form.append('file', file);
  return safe<AnalysisResult>(() => api.post('/analyze-csv', form).then(r => r.data));
};

export const analyzeScenario = (scenarioId: string) =>
  safe<AnalysisResult>(() => api.post(`/analyze-scenario/${scenarioId}`).then(r => r.data));

// History
export const getAnalyses = (params?: { source?: string; limit?: number; offset?: number }) =>
  safe<AnalysisSummary[]>(() => api.get('/analyses', { params }).then(r => r.data));

export const getAnalysis = (id: string) =>
  safe<AnalysisResult>(() => api.get(`/analyses/${id}`).then(r => r.data));

export const downloadReport = async (id: string): Promise<void> => {
  const r = await api.get(`/analyses/${id}/report`, { responseType: 'blob' });
  const url = URL.createObjectURL(new Blob([r.data], { type: 'application/json' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = `ecoshield_report_${id.slice(0, 8)}.json`;
  a.click();
  URL.revokeObjectURL(url);
};

export const downloadAnomalyCsv = async (id: string): Promise<void> => {
  const r = await api.get(`/analyses/${id}/csv`, { responseType: 'blob' });
  const url = URL.createObjectURL(new Blob([r.data], { type: 'text/csv' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = `anomalies_${id.slice(0, 8)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
};

export const compareAnalyses = (firstId: string, secondId: string) =>
  safe<CompareResponse>(() =>
    api.get('/analyses/compare', { params: { first_id: firstId, second_id: secondId } }).then(r => r.data)
  );

// Settings
export const getSettings = () => safe<AppSettings>(() => api.get('/settings').then(r => r.data));
export const updateSettings = (settings: AppSettings) =>
  safe<AppSettings>(() => api.put('/settings', settings).then(r => r.data));
