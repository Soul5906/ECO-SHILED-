// Global analysis context — shared state across pages
// Persists currentAnalysis in sessionStorage so refreshes don't lose the loaded analysis.
import React, { createContext, useCallback, useContext, useState } from 'react';
import type { AnalysisResult } from '../types';

const SESSION_KEY = 'ecoshield_analysis';

function loadFromSession(): AnalysisResult | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (raw) return JSON.parse(raw) as AnalysisResult;
  } catch { /* ignore corrupt data */ }
  return null;
}

interface AnalysisCtx {
  currentAnalysis: AnalysisResult | null;
  setCurrentAnalysis: (a: AnalysisResult | null) => void;
  datasetRows: Record<string, unknown>[];
  setDatasetRows: (r: Record<string, unknown>[]) => void;
  clearAnalysis: () => void;
}

const Ctx = createContext<AnalysisCtx>({
  currentAnalysis: null,
  setCurrentAnalysis: () => {},
  datasetRows: [],
  setDatasetRows: () => {},
  clearAnalysis: () => {},
});

export function AnalysisProvider({ children }: { children: React.ReactNode }) {
  const [currentAnalysis, _setCurrentAnalysis] = useState<AnalysisResult | null>(loadFromSession);
  const [datasetRows, setDatasetRows] = useState<Record<string, unknown>[]>([]);

  const setCurrentAnalysis = useCallback((a: AnalysisResult | null) => {
    _setCurrentAnalysis(a);
    if (a) {
      try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(a)); } catch { /* storage full */ }
    } else {
      sessionStorage.removeItem(SESSION_KEY);
    }
  }, []);

  const clearAnalysis = useCallback(() => {
    _setCurrentAnalysis(null);
    setDatasetRows([]);
    sessionStorage.removeItem(SESSION_KEY);
  }, []);

  return (
    <Ctx.Provider value={{ currentAnalysis, setCurrentAnalysis, datasetRows, setDatasetRows, clearAnalysis }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAnalysis() { return useContext(Ctx); }
