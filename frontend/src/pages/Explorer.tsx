// Data Explorer — sortable, filterable, paginated table with column selector
import React, { useState, useMemo } from 'react';
import { useAnalysis } from '../context/AnalysisContext';
import { EmptyState, PageHeader, Pagination } from '../components/Shared';
import { PowerVsIrradianceScatter } from '../components/Charts';
import { downloadCsvString } from '../utils/helpers';

const PAGE_SIZE = 50;

export default function Explorer() {
  const { currentAnalysis, datasetRows } = useAnalysis();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [selectedCols, setSelectedCols] = useState<Set<string> | null>(null);
  const [showColPicker, setShowColPicker] = useState(false);

  const allCols = useMemo(() => {
    if (datasetRows.length === 0) return [];
    return Object.keys(datasetRows[0]);
  }, [datasetRows]);

  const visibleCols = selectedCols ? Array.from(selectedCols) : allCols;

  const filtered = useMemo(() => {
    if (!search) return datasetRows;
    const q = search.toLowerCase();
    return datasetRows.filter((r) =>
      Object.values(r).some((v) => String(v ?? '').toLowerCase().includes(q))
    );
  }, [datasetRows, search]);

  const pageData = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const anomalyRows = useMemo(() => {
    const s = new Set<number>();
    (currentAnalysis?.anomaly_summary?.anomalies ?? []).forEach((a) => {
      if (a.row_index !== null && a.row_index !== undefined) s.add(a.row_index);
    });
    return s;
  }, [currentAnalysis]);

  const exportCsv = () => {
    const header = visibleCols.join(',');
    const rows = filtered.map((r) => visibleCols.map((c) => {
      const v = r[c];
      if (v === null || v === undefined) return '';
      const s = String(v);
      return s.includes(',') ? `"${s}"` : s;
    }).join(','));
    downloadCsvString([header, ...rows].join('\n'), 'ecoshield_data_export.csv');
  };

  const toggleCol = (col: string) => {
    const cur = selectedCols ? new Set(selectedCols) : new Set(allCols);
    if (cur.has(col)) cur.delete(col);
    else cur.add(col);
    setSelectedCols(cur);
  };

  if (!currentAnalysis) {
    return (
      <div>
        <PageHeader title="Data Explorer" subtitle="Load an analysis to explore the dataset." />
        <EmptyState title="No data loaded" description="Load a demo scenario or upload a CSV to explore data." />
      </div>
    );
  }

  const qa = currentAnalysis.quality_report;

  return (
    <div>
      <PageHeader
        title="Data Explorer"
        subtitle={`${datasetRows.length.toLocaleString()} rows · ${allCols.length} columns · showing ${visibleCols.length} columns`}
        actions={
          <div className="flex gap-2">
            <button className="btn btn-secondary btn-sm" onClick={() => setShowColPicker((v) => !v)}>
              Columns
            </button>
            <button className="btn btn-secondary btn-sm" onClick={exportCsv} disabled={filtered.length === 0}>
              Export CSV
            </button>
          </div>
        }
      />

      {/* Stats */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
        <div className="metric-card" style={{ minWidth: 120 }}>
          <div className="metric-label">Total Rows</div>
          <div className="metric-value" style={{ fontSize: 20 }}>{qa?.total_rows?.toLocaleString()}</div>
        </div>
        <div className="metric-card" style={{ minWidth: 120 }}>
          <div className="metric-label">Completeness</div>
          <div className="metric-value" style={{ fontSize: 20 }}>{qa?.completeness_pct?.toFixed(1)}%</div>
        </div>
        <div className="metric-card" style={{ minWidth: 120 }}>
          <div className="metric-label">Anomaly Rows</div>
          <div className="metric-value" style={{ fontSize: 20 }}>{anomalyRows.size}</div>
        </div>
      </div>

      {/* Column picker */}
      {showColPicker && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header">
            <span className="card-title">Column Selector</span>
            <button className="btn btn-ghost btn-sm" onClick={() => setSelectedCols(null)}>Reset</button>
          </div>
          <div className="card-body" style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {allCols.map((c) => (
              <label key={c} style={{ display: 'flex', alignItems: 'center', gap: 5, cursor: 'pointer', fontSize: 13 }}>
                <input type="checkbox" checked={selectedCols ? selectedCols.has(c) : true} onChange={() => toggleCol(c)} />
                <code style={{ fontSize: 12 }}>{c}</code>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Power vs Irradiance scatter (if data present) */}
      {datasetRows.length > 10 && allCols.includes('power_kw') && allCols.includes('irradiance_wm2') && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header"><span className="card-title">Power vs Irradiance</span></div>
          <div className="card-body">
            <PowerVsIrradianceScatter data={datasetRows as any} />
          </div>
        </div>
      )}

      {/* Filter */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
        <input
          className="input"
          style={{ maxWidth: 320 }}
          placeholder="Search all values…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        />
        <span className="text-sm text-secondary" style={{ lineHeight: '36px' }}>
          {filtered.length} rows
        </span>
      </div>

      {/* Quality legend */}
      <div style={{ marginBottom: 10, display: 'flex', gap: 14, fontSize: 12, color: 'var(--text-secondary)' }}>
        <span><span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 2, background: 'var(--rose-50)', border: '1px solid var(--rose-200)', marginRight: 4 }} />Anomaly row</span>
        <span><span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 2, background: 'var(--amber-50)', border: '1px solid var(--amber-200)', marginRight: 4 }} />Missing value</span>
        <span>Values shown as received — no silent replacement of missing values.</span>
      </div>

      {datasetRows.length === 0 ? (
        <EmptyState title="No data rows available" description="Raw dataset rows are available after uploading a CSV. Scenario data shows analysis results only." />
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th style={{ width: 50 }}>#</th>
                  {visibleCols.map((c) => <th key={c}>{c}</th>)}
                </tr>
              </thead>
              <tbody>
                {pageData.map((row, i) => {
                  const globalIdx = (page - 1) * PAGE_SIZE + i;
                  const isAnomaly = anomalyRows.has(globalIdx);
                  return (
                    <tr key={i} style={isAnomaly ? { background: 'var(--rose-50)' } : undefined}>
                      <td className="text-xs text-tertiary">{globalIdx}</td>
                      {visibleCols.map((c) => {
                        const v = row[c];
                        const isEmpty = v === null || v === undefined || v === '';
                        return (
                          <td key={c} className="td-mono" style={isEmpty ? { background: 'var(--amber-50)' } : undefined}>
                            {isEmpty ? <span style={{ color: 'var(--amber-600)', fontStyle: 'italic', fontSize: 11 }}>—</span> : String(v)}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div style={{ padding: '0 22px' }}>
            <Pagination page={page} pageSize={PAGE_SIZE} total={filtered.length} onChange={setPage} />
          </div>
        </div>
      )}
    </div>
  );
}
