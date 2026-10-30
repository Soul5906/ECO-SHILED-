// Settings page — configurable thresholds and limits
import React, { useEffect, useState } from 'react';
import { getSettings, updateSettings } from '../services/api';
import { LoadingSpinner, ErrorAlert, PageHeader, InfoRow } from '../components/Shared';
import type { AppSettings } from '../types';

function NumberField({ label, value, onChange, min, max, step = 0.1 }: {
  label: string; value: number; onChange: (v: number) => void; min?: number; max?: number; step?: number;
}) {
  return (
    <div className="form-group">
      <label className="form-label">{label}</label>
      <input
        type="number"
        className="input"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
    </div>
  );
}

export default function Settings() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  const load = () => {
    setLoading(true);
    setError('');
    getSettings()
      .then(setSettings)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    setError('');
    setSaved(false);
    try {
      const updated = await updateSettings(settings);
      setSettings(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const upd = (path: string[], val: number | string | boolean) => {
    if (!settings) return;
    const clone = JSON.parse(JSON.stringify(settings));
    let obj: any = clone;
    for (let i = 0; i < path.length - 1; i++) obj = obj[path[i]];
    obj[path[path.length - 1]] = val;
    setSettings(clone);
  };

  if (loading) return <div className="flex gap-2 items-center"><LoadingSpinner /><span>Loading settings…</span></div>;

  return (
    <div>
      <PageHeader
        title="Settings & Configuration"
        subtitle="Adjust thresholds, limits, and defaults. Invalid values will be rejected before saving."
        actions={
          <div className="flex gap-2 items-center">
            {saved && <span className="badge badge-success">✓ Saved</span>}
            <button className="btn btn-secondary btn-sm" onClick={load}>↺ Reset</button>
            <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? <><LoadingSpinner size="sm" /> Saving…</> : 'Save Settings'}
            </button>
          </div>
        }
      />

      {error && <ErrorAlert message={error} />}

      {settings && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Anomaly thresholds */}
          <div className="card">
            <div className="card-header"><span className="card-title">Anomaly Detection Thresholds</span></div>
            <div className="card-body">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16 }}>
                <NumberField label="MAD Threshold (1–10)" value={settings.anomaly_thresholds.mad_threshold} onChange={(v) => upd(['anomaly_thresholds', 'mad_threshold'], v)} min={1} max={10} />
                <NumberField label="Z-Score Threshold (1–10)" value={settings.anomaly_thresholds.zscore_threshold} onChange={(v) => upd(['anomaly_thresholds', 'zscore_threshold'], v)} min={1} max={10} />
                <NumberField label="Rate-of-Change Threshold" value={settings.anomaly_thresholds.rate_of_change_threshold} onChange={(v) => upd(['anomaly_thresholds', 'rate_of_change_threshold'], v)} min={0} />
                <NumberField label="Gap Detection (minutes)" value={settings.anomaly_thresholds.gap_minutes} onChange={(v) => upd(['anomaly_thresholds', 'gap_minutes'], v)} min={1} />
                <NumberField label="Flatline Detection (minutes)" value={settings.anomaly_thresholds.flatline_minutes} onChange={(v) => upd(['anomaly_thresholds', 'flatline_minutes'], v)} min={1} />
                <NumberField label="Power/Irradiance Drop Ratio (0–1)" value={settings.anomaly_thresholds.power_irradiance_drop_ratio} onChange={(v) => upd(['anomaly_thresholds', 'power_irradiance_drop_ratio'], v)} min={0} max={1} step={0.05} />
              </div>
            </div>
          </div>

          {/* Physical limits */}
          <div className="card">
            <div className="card-header"><span className="card-title">Physical Validation Limits</span></div>
            <div className="card-body">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16 }}>
                <NumberField label="Max Power (kW)" value={settings.physical_limits.max_power_kw} onChange={(v) => upd(['physical_limits', 'max_power_kw'], v)} min={0} step={100} />
                <NumberField label="Max Irradiance (W/m²)" value={settings.physical_limits.max_irradiance_wm2} onChange={(v) => upd(['physical_limits', 'max_irradiance_wm2'], v)} min={0} step={100} />
                <NumberField label="Min Temperature (°C)" value={settings.physical_limits.min_temperature_c} onChange={(v) => upd(['physical_limits', 'min_temperature_c'], v)} />
                <NumberField label="Max Temperature (°C)" value={settings.physical_limits.max_temperature_c} onChange={(v) => upd(['physical_limits', 'max_temperature_c'], v)} />
                <NumberField label="Max Voltage (V)" value={settings.physical_limits.max_voltage_v} onChange={(v) => upd(['physical_limits', 'max_voltage_v'], v)} min={0} />
                <NumberField label="Max Current (A)" value={settings.physical_limits.max_current_a} onChange={(v) => upd(['physical_limits', 'max_current_a'], v)} min={0} />
              </div>
            </div>
          </div>

          {/* General settings */}
          <div className="card">
            <div className="card-header"><span className="card-title">General Configuration</span></div>
            <div className="card-body">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16 }}>
                <NumberField label="Expected Interval (minutes)" value={settings.expected_interval_minutes} onChange={(v) => upd(['expected_interval_minutes'], v)} min={1} step={5} />
                <NumberField label="Max Upload Size (MB)" value={settings.max_upload_size_mb} onChange={(v) => upd(['max_upload_size_mb'], v)} min={1} max={500} step={10} />
                <NumberField label="Max Rows per Upload" value={settings.max_rows} onChange={(v) => upd(['max_rows'], v)} min={100} step={10000} />
                <NumberField label="Report Retention (days, 0=forever)" value={settings.report_retention_days} onChange={(v) => upd(['report_retention_days'], v)} min={0} step={1} />
                <div className="form-group">
                  <label className="form-label">Default Timezone</label>
                  <select className="input select" value={settings.default_timezone} onChange={(e) => upd(['default_timezone'], e.target.value)}>
                    <option value="UTC">UTC</option>
                    <option value="America/New_York">America/New_York</option>
                    <option value="America/Los_Angeles">America/Los_Angeles</option>
                    <option value="Europe/London">Europe/London</option>
                    <option value="Asia/Kolkata">Asia/Kolkata</option>
                    <option value="Australia/Sydney">Australia/Sydney</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* Active detectors */}
          <div className="card">
            <div className="card-header"><span className="card-title">Active Anomaly Detectors</span></div>
            <div className="card-body">
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                {['mad_outlier','zscore_outlier','rate_of_change','missing_gaps','flatline','duplicate_timestamps','power_irradiance_drop','temperature_anomaly','sensor_drift','periodic_pattern'].map((det) => {
                  const active = settings.active_detectors.includes(det);
                  return (
                    <label key={det} style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 13 }}>
                      <input
                        type="checkbox"
                        checked={active}
                        onChange={() => {
                          const arr = active
                            ? settings.active_detectors.filter((d) => d !== det)
                            : [...settings.active_detectors, det];
                          upd(['active_detectors'], arr as any);
                        }}
                      />
                      <code style={{ fontSize: 11.5 }}>{det}</code>
                    </label>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Active rules */}
          <div className="card">
            <div className="card-header"><span className="card-title">Active Diagnostic Rules</span></div>
            <div className="card-body">
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                {['telemetry_failure','sensor_drift','reduced_resource','shading_soiling','module_performance','inverter_electrical','temperature_issue','unexpected_decline'].map((rule) => {
                  const active = settings.active_rules.includes(rule);
                  return (
                    <label key={rule} style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 13 }}>
                      <input
                        type="checkbox"
                        checked={active}
                        onChange={() => {
                          const arr = active
                            ? settings.active_rules.filter((r) => r !== rule)
                            : [...settings.active_rules, rule];
                          upd(['active_rules'], arr as any);
                        }}
                      />
                      <code style={{ fontSize: 11.5 }}>{rule}</code>
                    </label>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Disclaimer */}
          <div className="alert alert-info">
            <span className="text-sm">Settings take effect on the next analysis run. Active settings are stored in each analysis report for reproducibility. Invalid threshold values will be rejected by the backend.</span>
          </div>
        </div>
      )}
    </div>
  );
}
