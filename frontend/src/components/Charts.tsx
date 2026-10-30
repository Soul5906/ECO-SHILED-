// Recharts-based telemetry charts
import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  Cell,
  ScatterChart,
  Scatter,
  ZAxis,
} from 'recharts';

interface TelemetryPoint {
  timestamp?: string;
  power_kw?: number;
  irradiance_wm2?: number;
  temperature_c?: number;
}

function formatTs(ts: string | undefined) {
  if (!ts) return '';
  try {
    const d = new Date(ts as string);
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  } catch { return ts as string; }
}

const TOOLTIP_STYLE = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 8,
  fontSize: 12,
  boxShadow: 'var(--shadow)',
};

export function PowerIrradianceChart({ data }: { data: TelemetryPoint[] }) {
  const sample = data.length > 300 ? data.filter((_, i) => i % Math.ceil(data.length / 300) === 0) : data;
  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={sample} margin={{ top: 4, right: 16, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" />
          <XAxis dataKey="timestamp" tickFormatter={formatTs} tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} minTickGap={40} />
          <YAxis yAxisId="power" tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} width={45} />
          <YAxis yAxisId="irr" orientation="right" tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} width={50} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
          <Line yAxisId="power" type="monotone" dataKey="power_kw" stroke="var(--blue-600)" strokeWidth={1.5} dot={false} name="Power (kW)" />
          <Line yAxisId="irr" type="monotone" dataKey="irradiance_wm2" stroke="var(--amber-500)" strokeWidth={1.5} dot={false} name="Irradiance (W/m²)" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function TemperatureChart({ data }: { data: TelemetryPoint[] }) {
  const sample = data.length > 300 ? data.filter((_, i) => i % Math.ceil(data.length / 300) === 0) : data;
  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={sample} margin={{ top: 4, right: 16, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" />
          <XAxis dataKey="timestamp" tickFormatter={formatTs} tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} minTickGap={40} />
          <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} width={40} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Line type="monotone" dataKey="temperature_c" stroke="var(--rose-500)" strokeWidth={1.5} dot={false} name="Temp (°C)" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

const SEV_COLORS: Record<string, string> = {
  critical: '#e11d48',
  high:     '#f97316',
  medium:   '#f59e0b',
  low:      '#0ea5e9',
  info:     '#94a3b8',
};

export function AnomalyBarChart({ bySeverity }: { bySeverity: Record<string, number> }) {
  // Consistent severity ordering
  const ORDER = ['critical', 'high', 'medium', 'low', 'info'];
  const data = ORDER
    .filter((s) => bySeverity[s] !== undefined)
    .map((sev) => ({ sev, count: bySeverity[sev] }));

  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" />
        <XAxis dataKey="sev" tick={{ fontSize: 11, fill: 'var(--text-tertiary)' }} />
        <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: 'var(--text-tertiary)' }} />
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => [v, 'Anomalies']} />
        <Bar dataKey="count" name="Anomalies" radius={[4, 4, 0, 0]}>
          {data.map((entry) => (
            <Cell key={entry.sev} fill={SEV_COLORS[entry.sev] ?? '#94a3b8'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// Proper scatter chart for Power vs Irradiance
export function PowerVsIrradianceScatter({ data }: { data: TelemetryPoint[] }) {
  const sample = data.length > 400 ? data.filter((_, i) => i % Math.ceil(data.length / 400) === 0) : data;
  const scatterData = sample
    .filter((r) => r.irradiance_wm2 != null && r.power_kw != null)
    .map((r) => ({ x: r.irradiance_wm2 as number, y: r.power_kw as number }));

  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height={220}>
        <ScatterChart margin={{ top: 8, right: 16, left: -10, bottom: 24 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" />
          <XAxis
            dataKey="x"
            type="number"
            name="Irradiance"
            unit=" W/m²"
            tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }}
            label={{ value: 'Irradiance (W/m²)', position: 'insideBottom', offset: -16, fontSize: 10, fill: 'var(--text-tertiary)' }}
          />
          <YAxis
            dataKey="y"
            type="number"
            name="Power"
            unit=" kW"
            tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }}
            width={48}
          />
          <ZAxis range={[16, 16]} />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            cursor={{ strokeDasharray: '3 3' }}
            formatter={(v, name) => [
              `${Number(v).toFixed(2)}${name === 'Power' ? ' kW' : ' W/m²'}`,
              name,
            ]}
          />
          <Scatter
            name="Data points"
            data={scatterData}
            fill="#3b82f6"
            fillOpacity={0.55}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

// Quality score mini-bar for column quality table
export function ColumnQualityMiniBar({ pct }: { pct: number }) {
  const color = pct >= 95 ? 'var(--emerald-500)' : pct >= 80 ? 'var(--amber-500)' : 'var(--rose-500)';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ flex: 1, height: 6, background: 'var(--border)', borderRadius: 99, overflow: 'hidden', minWidth: 60 }}>
        <div style={{ width: `${Math.min(100, pct)}%`, height: '100%', background: color, borderRadius: 99, transition: 'width 0.4s ease' }} />
      </div>
      <span style={{ fontSize: 11, fontWeight: 600, color, minWidth: 36, textAlign: 'right' }}>{pct.toFixed(1)}%</span>
    </div>
  );
}
