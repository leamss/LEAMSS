/**
 * Phase 9.6 — Admin Calculator Rules Editor
 *
 * Lets admins view + edit the deterministic scoring tables (age bands, English
 * tiers, education categories, partner bonuses, state nomination multipliers)
 * used by /api/sales/calculator/calculate. Edits persist to kb_settings.
 *
 * Rules apply to AU / CA / NZ — each country has its own JSON document.
 * No code deploy needed when a new program year is published by Home Affairs / IRCC / INZ.
 */
import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Loader2, Save, RotateCcw, AlertTriangle, CheckCircle2, Award,
  Sliders, Database, FileWarning,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const C = {
  teal: '#0F766E', tealDeep: '#115E59', tealWash: '#F0FDFA', tealWash2: '#CCFBF1',
  orange: '#EA7C2E', orangeDeep: '#C2410C', orangeWash: '#FFF7ED', orangeWash2: '#FFEDD5',
  gold: '#D4A017', goldWash: '#FEF3C7',
  red: '#D32F2F', redWash: '#FEE2E2',
  ink: '#1F2937', body: '#475569', muted: '#94A3B8',
  border: '#E5E7EB', card: '#FFFFFF', bg: '#F8FAFC',
};

const COUNTRIES = [
  { code: 'AU', name: 'Australia', flag: '🇦🇺', description: 'Skill assessment, GSM (189/190/491)' },
  { code: 'CA', name: 'Canada',    flag: '🇨🇦', description: 'Express Entry CRS' },
  { code: 'NZ', name: 'New Zealand', flag: '🇳🇿', description: 'Skilled Migrant Category' },
];

export default function CalculatorRulesEditor() {
  const [country, setCountry] = useState('AU');
  const [rules, setRules] = useState(null);
  const [draftJson, setDraftJson] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [parseError, setParseError] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => { loadRules(); }, [country]); // eslint-disable-line

  const loadRules = async () => {
    setLoading(true);
    setSaveSuccess(false);
    try {
      const r = await axios.get(`${API}/anz-intel/calculator-rules/${country}`, { headers });
      setRules(r.data);
      setDraftJson(JSON.stringify(r.data.tables, null, 2));
      setParseError(null);
    } catch (e) {
      setRules({ error: e.response?.data?.detail || String(e) });
    }
    setLoading(false);
  };

  const onDraftChange = (e) => {
    const txt = e.target.value;
    setDraftJson(txt);
    setSaveSuccess(false);
    let err = null;
    try { JSON.parse(txt); } catch (ex) { err = ex.message; }
    setParseError(err);
  };

  const save = async () => {
    if (parseError) return;
    if (!window.confirm(`Sir, ${country} ka calculator rules override save karein? Yeh PRODUCTION calculator par effect karega.`)) return;
    setSaving(true);
    try {
      const tables = JSON.parse(draftJson);
      await axios.put(`${API}/anz-intel/calculator-rules/${country}`, {
        tables, version: rules?.version,
      }, { headers });
      setSaveSuccess(true);
      await loadRules();
    } catch (e) {
      alert('Save failed: ' + (e.response?.data?.detail || e.message));
    }
    setSaving(false);
  };

  const reset = async () => {
    if (!window.confirm(`Sir, ${country} ka override delete karein aur hardcoded defaults par wapas jayein? (Reversible — aap aage edit kar sakte hain)`)) return;
    setResetting(true);
    try {
      await axios.post(`${API}/anz-intel/calculator-rules/${country}/reset`, {}, { headers });
      await loadRules();
    } catch (e) {
      alert('Reset failed: ' + (e.response?.data?.detail || e.message));
    }
    setResetting(false);
  };

  return (
    <div className="min-h-screen p-6" style={{ background: C.bg }} data-testid="calculator-rules-editor">
      {/* Hero */}
      <div className="rounded-xl p-5 mb-5"
           style={{ background: `linear-gradient(135deg, ${C.tealDeep} 0%, ${C.teal} 100%)`, color: '#fff' }}>
        <p className="text-[10px] uppercase tracking-widest opacity-90 font-bold"
           style={{ letterSpacing: '0.16em' }}>
          Phase 9.6 — Rule-Based Scoring Engine
        </p>
        <h1 className="text-2xl font-bold mt-1" style={{ fontFamily: "'Playfair Display', serif" }}>
          Calculator Rules Editor
        </h1>
        <p className="text-sm opacity-90 mt-1">
          Edit deterministic scoring tables per country. Changes persist to <code>kb_settings</code>.
          Calculator reads override if present, else falls back to hardcoded defaults — zero downtime.
        </p>
      </div>

      {/* Country tabs */}
      <div className="flex gap-2 mb-5">
        {COUNTRIES.map(c => (
          <button
            key={c.code}
            onClick={() => setCountry(c.code)}
            className="flex-1 px-4 py-3 rounded-lg text-left border-2 transition-all"
            style={{
              borderColor: country === c.code ? C.teal : C.border,
              background:  country === c.code ? C.tealWash : C.card,
            }}
            data-testid={`rules-country-${c.code}`}
          >
            <div className="text-2xl mb-1">{c.flag}</div>
            <div className="text-sm font-bold" style={{ color: country === c.code ? C.tealDeep : C.ink }}>
              {c.name}
            </div>
            <div className="text-[10px]" style={{ color: C.muted }}>{c.description}</div>
          </button>
        ))}
      </div>

      {loading && (
        <Card className="p-8 text-center">
          <Loader2 className="h-6 w-6 animate-spin mx-auto" style={{ color: C.teal }} />
          <p className="text-sm mt-2" style={{ color: C.body }}>Loading rules…</p>
        </Card>
      )}

      {!loading && rules?.error && (
        <Card className="p-4" style={{ background: C.redWash, border: '1px solid #FCA5A5' }}>
          <p className="text-sm font-bold" style={{ color: C.red }}>Failed to load rules</p>
          <p className="text-xs mt-1" style={{ color: C.body }}>{rules.error}</p>
        </Card>
      )}

      {!loading && rules && !rules.error && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Sidebar — Summary */}
          <div className="space-y-3">
            <Card className="p-4" data-testid="rules-summary-card">
              <p className="text-[10px] uppercase font-bold tracking-wider" style={{ color: C.muted }}>
                Active Source
              </p>
              <p className="mt-1 flex items-center gap-2">
                <Badge style={{
                  background: rules.source === 'db_override' ? C.gold : C.tealWash2,
                  color:      rules.source === 'db_override' ? '#fff' : C.tealDeep,
                  fontSize: 10,
                }}>
                  {rules.source === 'db_override' ? '✏️ DB Override' : '🔒 Hardcoded Defaults'}
                </Badge>
              </p>
              <p className="text-xs mt-2" style={{ color: C.body }}>
                <strong>Version:</strong> {rules.version}
              </p>
              {rules.updated_at && (
                <p className="text-xs" style={{ color: C.muted }}>
                  Last edit: {new Date(rules.updated_at).toLocaleString()}
                </p>
              )}
              {rules.updated_by && (
                <p className="text-xs" style={{ color: C.muted }}>By: <code>{rules.updated_by}</code></p>
              )}
            </Card>

            <Card className="p-4">
              <p className="text-[10px] uppercase font-bold tracking-wider mb-2" style={{ color: C.muted }}>
                Tables in this rule set
              </p>
              <div className="space-y-1">
                {Object.entries(rules.tables || {}).map(([key, tbl]) => (
                  <div key={key} className="flex items-start gap-2 text-xs">
                    <Award className="h-3 w-3 mt-0.5" style={{ color: C.teal }} />
                    <div>
                      <p className="font-bold" style={{ color: C.ink }}>{key}</p>
                      <p className="text-[10px]" style={{ color: C.muted }}>{tbl.rule || tbl.type}</p>
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="p-3" style={{ background: C.goldWash, border: `1px solid ${C.gold}` }}>
              <p className="text-xs font-bold flex items-center gap-1" style={{ color: C.orangeDeep }}>
                <FileWarning className="h-3 w-3" />
                Production caution
              </p>
              <p className="text-[10px] mt-1" style={{ color: C.body }}>
                Saved edits IMMEDIATELY affect live point calculations. Always cross-check with the official
                Home Affairs / IRCC / INZ publication before saving.
              </p>
            </Card>
          </div>

          {/* Main editor — JSON */}
          <div className="lg:col-span-2">
            <Card className="p-4" data-testid="rules-editor-card">
              <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
                <h3 className="font-bold flex items-center gap-2" style={{ color: C.ink }}>
                  <Sliders className="h-4 w-4" style={{ color: C.teal }} />
                  Tables JSON ({country})
                </h3>
                <div className="flex gap-2">
                  <Button
                    variant="outline" size="sm"
                    onClick={reset}
                    disabled={resetting || rules.source !== 'db_override'}
                    data-testid="rules-reset-btn"
                  >
                    {resetting ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <RotateCcw className="h-3.5 w-3.5 mr-1" />}
                    Reset to Defaults
                  </Button>
                  <Button
                    size="sm"
                    onClick={save}
                    disabled={saving || !!parseError}
                    style={{ background: C.teal, color: '#fff' }}
                    data-testid="rules-save-btn"
                  >
                    {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <Save className="h-3.5 w-3.5 mr-1" />}
                    Save Override
                  </Button>
                </div>
              </div>

              {saveSuccess && (
                <div className="mb-2 p-2 rounded text-xs flex items-center gap-1"
                     style={{ background: C.tealWash, color: C.tealDeep }}
                     data-testid="rules-save-success">
                  <CheckCircle2 className="h-3.5 w-3.5" />Saved successfully — calculator will use these rules immediately
                </div>
              )}

              {parseError && (
                <div className="mb-2 p-2 rounded text-xs flex items-start gap-1"
                     style={{ background: C.redWash, color: C.red }}
                     data-testid="rules-parse-error">
                  <AlertTriangle className="h-3.5 w-3.5 mt-0.5" />
                  <span><strong>JSON parse error:</strong> {parseError}</span>
                </div>
              )}

              <textarea
                value={draftJson}
                onChange={onDraftChange}
                className="w-full px-3 py-2 rounded border text-xs font-mono"
                style={{ borderColor: parseError ? C.red : C.border, minHeight: 580 }}
                data-testid="rules-json-editor"
                spellCheck={false}
              />
              <p className="text-[10px] mt-1" style={{ color: C.muted }}>
                {draftJson.length} chars · Tip: Use the sidebar Tables list as reference. Each table must keep its <code>type</code> and primary collection (bands/categories/tiers/items).
              </p>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
