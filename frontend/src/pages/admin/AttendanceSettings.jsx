import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import { Save, RotateCcw, ChevronDown, AlertTriangle, Clock, Calendar, FileText, ShieldAlert } from 'lucide-react';
import HRSettingsLayout from '@/components/hr/HRSettingsLayout';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function AttendanceSettings() {
  const [settings, setSettings] = useState(null);
  const [original, setOriginal] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [open, setOpen] = useState({ timing: true, late: true, comp: true, leave: true, lwp: true });

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.get(`${API}/hr/settings`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setSettings(r.data);
      setOriginal(JSON.parse(JSON.stringify(r.data)));
    } catch (e) {
      toast.error('Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const dirty = settings && original && JSON.stringify(settings) !== JSON.stringify(original);

  // Calculate diff for save
  const computeDiff = () => {
    const diff = {};
    if (!settings || !original) return diff;
    for (const key of Object.keys(settings)) {
      if (key === '_id' || key === 'id' || key === 'updated_at' || key === 'created_at' || key === 'updated_by' || key === 'updated_by_name') continue;
      if (JSON.stringify(settings[key]) !== JSON.stringify(original[key])) {
        diff[key] = settings[key];
      }
    }
    return diff;
  };

  const handleSave = async () => {
    const diff = computeDiff();
    if (Object.keys(diff).length === 0) {
      toast.info('No changes to save');
      return;
    }
    if (!window.confirm(`Save ${Object.keys(diff).length} setting change(s)?\n\nThese will affect all employees from next punch onwards.`)) return;
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.patch(`${API}/hr/settings`, diff, {
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success(`✅ ${r.data.fields.length} field(s) updated. Effective from next punch.`);
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const discard = () => {
    setSettings(JSON.parse(JSON.stringify(original)));
    toast.info('Changes discarded');
  };

  const resetToDefaults = () => {
    if (!window.confirm('Reset ALL attendance settings to factory defaults? This cannot be undone (audit-logged).')) return;
    const defaults = {
      office_start_time: '10:00',
      office_end_time: '19:00',
      min_work_hours: 9,
      late_threshold_minutes: 10,
      late_marks_for_leave_deduction: 3,
      enforce_work_hours_compensation: true,
      enforce_sandwich_leave: true,
      enforce_monthly_cl_limit: true,
      monthly_cl_limit: 1,
      max_consecutive_leave_days: 7,
      max_long_leaves_per_year: 1,
      long_leave_threshold_days: 5,
      auto_mark_lwp_for_unapproved_absence: true,
      regularization_grace_days: 3,
      working_days: [0, 1, 2, 3, 4, 5],
      weekly_off_days: [6],
    };
    setSettings({ ...settings, ...defaults });
    toast.info('Defaults loaded. Click "Save Changes" to apply.');
  };

  if (loading || !settings) {
    return (
      <HRSettingsLayout title="Attendance Settings" breadcrumb="Attendance Settings">
        <div className="text-slate-500 text-sm">Loading...</div>
      </HRSettingsLayout>
    );
  }

  const set = (key, val) => setSettings({ ...settings, [key]: val });
  const toggleDay = (idx) => {
    const wo = settings.weekly_off_days || [6];
    const newWO = wo.includes(idx) ? wo.filter((d) => d !== idx) : [...wo, idx].sort();
    setSettings({ ...settings, weekly_off_days: newWO });
  };

  return (
    <HRSettingsLayout
      title="Attendance Settings"
      subtitle="Configure company-wide attendance and punch policies"
      breadcrumb="Attendance Settings"
    >
      <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
        <div className="text-xs text-slate-500">
          {settings.updated_by_name && (
            <>Last updated by <strong>{settings.updated_by_name}</strong> on {settings.updated_at ? new Date(settings.updated_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '—'}</>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={resetToDefaults} data-testid="reset-defaults-btn">
          <RotateCcw className="h-3.5 w-3.5 mr-1.5" /> Reset to Defaults
        </Button>
      </div>

      <div className="space-y-4">
        {/* Section 1: Office Timings */}
        <Section title="Office Timings" icon={Clock} open={open.timing} onToggle={() => setOpen({ ...open, timing: !open.timing })} testid="section-timing">
          <Field label="Office Start Time">
            <input type="time" value={settings.office_start_time || '10:00'} onChange={(e) => set('office_start_time', e.target.value)} className="px-2 py-1.5 border rounded text-sm" data-testid="office-start" />
          </Field>
          <Field label="Office End Time">
            <input type="time" value={settings.office_end_time || '19:00'} onChange={(e) => set('office_end_time', e.target.value)} className="px-2 py-1.5 border rounded text-sm" data-testid="office-end" />
          </Field>
          <Field label="Total Work Hours (per day)">
            <input type="number" min="1" max="24" step="0.5" value={settings.min_work_hours || 9} onChange={(e) => set('min_work_hours', parseFloat(e.target.value))} className="px-2 py-1.5 border rounded text-sm w-24" data-testid="min-work-hours" />
          </Field>
          <Field label="Working Days">
            <div className="flex gap-1.5 flex-wrap" data-testid="working-days">
              {DAY_LABELS.map((d, idx) => {
                const isOff = (settings.weekly_off_days || []).includes(idx);
                return (
                  <button
                    key={d}
                    onClick={() => toggleDay(idx)}
                    className={`px-2.5 py-1 text-xs rounded border ${
                      !isOff ? 'bg-emerald-100 border-emerald-400 text-emerald-800 font-semibold' : 'bg-slate-100 border-slate-300 text-slate-500'
                    }`}
                    data-testid={`day-${d}`}
                  >
                    {isOff ? '✗' : '✓'} {d}
                  </button>
                );
              })}
            </div>
          </Field>
          <div className="bg-leamss-teal-50 border border-leamss-teal-200 rounded p-3 text-xs text-leamss-teal-900 mt-2">
            <p className="font-bold mb-1">Live Preview</p>
            <p>Office: <strong>{settings.office_start_time} — {settings.office_end_time}</strong> ({settings.min_work_hours}h)</p>
            <p>Working: <strong>{7 - (settings.weekly_off_days || []).length} days/week</strong></p>
          </div>
        </Section>

        {/* Section 2: Late Coming */}
        <Section title="Late Coming Rules" icon={AlertTriangle} open={open.late} onToggle={() => setOpen({ ...open, late: !open.late })} testid="section-late">
          <Field label="Grace Period (minutes)">
            <input type="number" min="0" max="120" value={settings.late_threshold_minutes || 10} onChange={(e) => set('late_threshold_minutes', parseInt(e.target.value))} className="px-2 py-1.5 border rounded text-sm w-24" data-testid="grace-period" />
          </Field>
          <Field label="Late Marks for Auto-Deduction">
            <input type="number" min="1" max="30" value={settings.late_marks_for_leave_deduction || 3} onChange={(e) => set('late_marks_for_leave_deduction', parseInt(e.target.value))} className="px-2 py-1.5 border rounded text-sm w-24" data-testid="late-marks-threshold" />
          </Field>
          <div className="bg-amber-50 border border-amber-300 rounded p-3 text-xs text-amber-900 mt-2">
            <p className="font-bold mb-1">Late Logic Preview</p>
            <p>After <strong>{addMinutes(settings.office_start_time, settings.late_threshold_minutes)}</strong> = marked LATE</p>
            <p>Every <strong>{settings.late_marks_for_leave_deduction}</strong> late marks in a month = 1 CL deducted</p>
            <p className="mt-1 text-amber-700 italic">⚠️ Changes affect all employees from next punch onwards</p>
          </div>
        </Section>

        {/* Section 3: Work Hours Compensation */}
        <Section title="Work Hours Compensation" icon={Clock} open={open.comp} onToggle={() => setOpen({ ...open, comp: !open.comp })} testid="section-comp">
          <ToggleRow
            label="Enforce Work Hours Compensation"
            description="Late employees must stay back to complete required hours"
            value={settings.enforce_work_hours_compensation !== false}
            onChange={(v) => set('enforce_work_hours_compensation', v)}
            testid="enforce-comp"
          />
        </Section>

        {/* Section 4: Leave Rules */}
        <Section title="Leave Rules" icon={Calendar} open={open.leave} onToggle={() => setOpen({ ...open, leave: !open.leave })} testid="section-leave">
          <ToggleRow
            label="Enforce Monthly CL Limit"
            description="Limit casual leaves per month per employee"
            value={settings.enforce_monthly_cl_limit !== false}
            onChange={(v) => set('enforce_monthly_cl_limit', v)}
            testid="enforce-cl"
          />
          <Field label="Monthly CL Limit (days)">
            <input type="number" min="0" max="10" value={settings.monthly_cl_limit ?? 1} onChange={(e) => set('monthly_cl_limit', parseInt(e.target.value))} className="px-2 py-1.5 border rounded text-sm w-24" disabled={!settings.enforce_monthly_cl_limit} data-testid="monthly-cl-limit" />
          </Field>
          <Field label="Max Consecutive Leave Days">
            <input type="number" min="1" max="365" value={settings.max_consecutive_leave_days || 7} onChange={(e) => set('max_consecutive_leave_days', parseInt(e.target.value))} className="px-2 py-1.5 border rounded text-sm w-24" data-testid="max-consecutive" />
          </Field>
          <Field label="Max Long Leaves Per Year" tooltip="Long leave = more than long_leave_threshold_days">
            <input type="number" min="0" max="10" value={settings.max_long_leaves_per_year ?? 1} onChange={(e) => set('max_long_leaves_per_year', parseInt(e.target.value))} className="px-2 py-1.5 border rounded text-sm w-24" data-testid="max-long-leaves" />
          </Field>
          <Field label="Long Leave Threshold (days)">
            <input type="number" min="1" max="60" value={settings.long_leave_threshold_days ?? 5} onChange={(e) => set('long_leave_threshold_days', parseInt(e.target.value))} className="px-2 py-1.5 border rounded text-sm w-24" data-testid="long-threshold" />
          </Field>
          <ToggleRow
            label="Enforce Sandwich Leave"
            description="Friday + Monday leaves count weekend too (per company policy)"
            value={settings.enforce_sandwich_leave !== false}
            onChange={(v) => set('enforce_sandwich_leave', v)}
            testid="enforce-sandwich"
          />
        </Section>

        {/* Section 5: LWP & Regularization */}
        <Section title="LWP & Regularization" icon={ShieldAlert} open={open.lwp} onToggle={() => setOpen({ ...open, lwp: !open.lwp })} testid="section-lwp">
          <ToggleRow
            label="Auto-Mark LWP for Unapproved Absence"
            description="Employees absent without approved leave automatically marked LWP"
            value={settings.auto_mark_lwp_for_unapproved_absence !== false}
            onChange={(v) => set('auto_mark_lwp_for_unapproved_absence', v)}
            testid="enforce-lwp"
          />
          <Field label="Regularization Grace Days" tooltip="Days after the absence to submit a regularization request">
            <input type="number" min="0" max="30" value={settings.regularization_grace_days ?? 3} onChange={(e) => set('regularization_grace_days', parseInt(e.target.value))} className="px-2 py-1.5 border rounded text-sm w-24" data-testid="grace-days" />
          </Field>
        </Section>
      </div>

      {/* Sticky footer */}
      <div className="mt-6 pt-4 border-t border-slate-200 flex items-center justify-between" data-testid="save-footer">
        <div className="text-xs text-slate-500">
          {dirty ? (
            <span className="text-amber-600 font-semibold">● Unsaved changes</span>
          ) : (
            <span className="text-emerald-600">✓ All changes saved</span>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={discard} disabled={!dirty || saving} data-testid="discard-btn">
            Discard
          </Button>
          <Button onClick={handleSave} disabled={!dirty || saving} data-testid="save-settings-btn">
            <Save className="h-4 w-4 mr-1.5" /> {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>
    </HRSettingsLayout>
  );
}


function Section({ title, icon: Icon, open, onToggle, children, testid }) {
  return (
    <Card className="overflow-hidden" data-testid={testid}>
      <button onClick={onToggle} className="w-full px-5 py-3 flex items-center justify-between text-left hover:bg-slate-50 border-b border-slate-100">
        <span className="flex items-center gap-2 font-semibold text-slate-800">
          <Icon className="h-4 w-4 text-leamss-teal-600" /> {title}
        </span>
        <ChevronDown className={`h-4 w-4 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && <div className="p-5 space-y-3">{children}</div>}
    </Card>
  );
}

function Field({ label, tooltip, children }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-2 md:gap-4 items-center">
      <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide" title={tooltip}>
        {label}{tooltip && <span className="text-slate-400 ml-1">ⓘ</span>}
      </label>
      <div className="md:col-span-2">{children}</div>
    </div>
  );
}

function ToggleRow({ label, description, value, onChange, testid }) {
  return (
    <div className="flex items-start justify-between gap-3 py-2 border-b border-slate-100 last:border-0">
      <div>
        <p className="text-sm font-medium text-slate-800">{label}</p>
        {description && <p className="text-xs text-slate-500 mt-0.5">{description}</p>}
      </div>
      <Switch checked={!!value} onCheckedChange={onChange} data-testid={testid} />
    </div>
  );
}

function addMinutes(time, mins) {
  if (!time) return '';
  const [h, m] = time.split(':').map(Number);
  const totalMins = h * 60 + m + (mins || 0);
  const h2 = Math.floor(totalMins / 60) % 24;
  const m2 = totalMins % 60;
  return `${String(h2).padStart(2, '0')}:${String(m2).padStart(2, '0')}`;
}
