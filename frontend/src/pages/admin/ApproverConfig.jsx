import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import { Save, ArrowRight, User, Users, ShieldCheck, AlertCircle } from 'lucide-react';
import HRSettingsLayout from '@/components/hr/HRSettingsLayout';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DEPARTMENTS = ['sales', 'marketing', 'operations', 'hr', 'accounts', 'it', 'admin', 'compliance'];

export default function ApproverConfig() {
  const [config, setConfig] = useState(null);
  const [original, setOriginal] = useState(null);
  const [eligible, setEligible] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [simUser, setSimUser] = useState('');
  const [simResult, setSimResult] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      const [c, e, emps] = await Promise.all([
        axios.get(`${API}/hr/approvers/config`, { headers }),
        axios.get(`${API}/hr/eligible-approvers`, { headers }),
        axios.get(`${API}/employees?limit=200`, { headers }),
      ]);
      setConfig(c.data);
      setOriginal(JSON.parse(JSON.stringify(c.data)));
      setEligible(e.data || []);
      setEmployees(emps.data?.items || emps.data || []);
    } catch (e) {
      toast.error('Failed to load approver config');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const dirty = config && original && JSON.stringify(config) !== JSON.stringify(original);

  const computeDiff = () => {
    const diff = {};
    if (!config || !original) return diff;
    const fields = [
      'final_approver_logic', 'final_approver_user_id', 'final_approvers_by_department',
      'backup_approver_user_id', 'allow_skip_l1_emergency', 'allow_manager_self_approve',
      'auto_approve_l1_after_days', 'auto_approve_final_after_days',
      'escalate_after_days', 'long_leave_requires_dept_head', 'lwp_requires_admin',
    ];
    for (const f of fields) {
      if (JSON.stringify(config[f]) !== JSON.stringify(original[f])) {
        diff[f] = config[f];
      }
    }
    return diff;
  };

  const save = async () => {
    const diff = computeDiff();
    if (Object.keys(diff).length === 0) {
      toast.info('No changes to save');
      return;
    }
    if (!window.confirm(`Save ${Object.keys(diff).length} approver config change(s)?`)) return;
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      await axios.patch(`${API}/hr/approvers/config`, diff, {
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success(`✅ Approver config updated. New leave requests will use this config.`);
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const simulate = async (uid) => {
    if (!uid) { setSimResult(null); return; }
    try {
      const token = localStorage.getItem('token');
      const r = await axios.get(`${API}/hr/approvers/simulate/${uid}`, { headers: { Authorization: `Bearer ${token}` } });
      setSimResult(r.data);
    } catch (e) {
      toast.error('Simulation failed');
      setSimResult(null);
    }
  };

  if (loading || !config) {
    return (
      <HRSettingsLayout title="Approval Configuration" breadcrumb="Approvers">
        <div className="text-slate-500 text-sm">Loading...</div>
      </HRSettingsLayout>
    );
  }

  const set = (k, v) => setConfig({ ...config, [k]: v });

  return (
    <HRSettingsLayout
      title="Approval Configuration"
      subtitle="Define who approves leave requests at each stage"
      breadcrumb="Approvers"
    >
      <div className="space-y-4">
        {/* Section 1: Approval Flow Type */}
        <Card className="p-4" data-testid="flow-type-section">
          <h3 className="text-sm font-bold text-slate-800 mb-3">1. Approval Flow Type</h3>
          <div className="space-y-2">
            <RadioRow
              checked={config.final_approver_logic === 'specific_user'}
              onClick={() => set('final_approver_logic', 'specific_user')}
              label="Single Final Approver for All Leaves"
              description="One designated user (e.g., Admin Owner) approves the final stage for every leave."
              testid="flow-specific"
            >
              {config.final_approver_logic === 'specific_user' && (
                <select
                  value={config.final_approver_user_id || ''}
                  onChange={(e) => set('final_approver_user_id', e.target.value)}
                  className="w-full mt-2 px-3 py-2 border rounded text-sm"
                  data-testid="final-approver-select"
                >
                  <option value="">-- Select Final Approver --</option>
                  {eligible.map((u) => (
                    <option key={u.id} value={u.id}>{u.name} ({u.designation || u.rbac_role})</option>
                  ))}
                </select>
              )}
            </RadioRow>

            <RadioRow
              checked={config.final_approver_logic === 'by_department'}
              onClick={() => set('final_approver_logic', 'by_department')}
              label="Department-Wise Final Approver"
              description="Each department has its own final approver."
              testid="flow-dept"
            >
              {config.final_approver_logic === 'by_department' && (
                <div className="mt-2 space-y-1.5">
                  {DEPARTMENTS.map((dept) => (
                    <div key={dept} className="flex items-center gap-2">
                      <span className="text-xs uppercase tracking-wide text-slate-600 w-24">{dept}</span>
                      <select
                        value={(config.final_approvers_by_department || {})[dept] || ''}
                        onChange={(e) => set('final_approvers_by_department', {
                          ...(config.final_approvers_by_department || {}),
                          [dept]: e.target.value || null,
                        })}
                        className="flex-1 px-2 py-1.5 border rounded text-xs"
                        data-testid={`dept-approver-${dept}`}
                      >
                        <option value="">-- Not set --</option>
                        {eligible.map((u) => (
                          <option key={u.id} value={u.id}>{u.name}</option>
                        ))}
                      </select>
                    </div>
                  ))}
                </div>
              )}
            </RadioRow>
          </div>
        </Card>

        {/* Section 2: L1 Settings */}
        <Card className="p-4" data-testid="l1-section">
          <h3 className="text-sm font-bold text-slate-800 mb-3">2. L1 Approval Settings</h3>
          <p className="text-xs text-slate-600 mb-3">L1 approver = user's direct manager (from <code>reports_to</code> field). Configured per-employee.</p>
          <div className="space-y-2 border-t border-slate-100 pt-3">
            <ToggleRow
              label="Allow Manager to Approve Own Leave"
              description="When a manager applies for leave, skip L1 stage (they are L1 of themselves)."
              value={!!config.allow_manager_self_approve}
              onChange={(v) => set('allow_manager_self_approve', v)}
              testid="self-approve"
            />
            <NumRow
              label="Auto-approve at L1 After (days)"
              description="If L1 doesn't decide in X days, auto-approve. 0 = disabled."
              value={config.auto_approve_l1_after_days || 0}
              onChange={(v) => set('auto_approve_l1_after_days', v)}
              testid="auto-l1"
            />
          </div>
        </Card>

        {/* Section 3: Final/HR */}
        <Card className="p-4" data-testid="final-section">
          <h3 className="text-sm font-bold text-slate-800 mb-3">3. Final / HR Approval Settings</h3>
          <div className="space-y-2">
            <NumRow
              label="Auto-approve at Final After (days)"
              description="If final approver doesn't decide in X days, auto-approve. 0 = disabled."
              value={config.auto_approve_final_after_days || 0}
              onChange={(v) => set('auto_approve_final_after_days', v)}
              testid="auto-final"
            />
            <div>
              <p className="text-xs font-semibold text-slate-700 uppercase mb-1">Backup Approver</p>
              <p className="text-[11px] text-slate-500 mb-1">Used when primary final approver is on leave.</p>
              <select
                value={config.backup_approver_user_id || ''}
                onChange={(e) => set('backup_approver_user_id', e.target.value || null)}
                className="w-full px-3 py-2 border rounded text-sm"
                data-testid="backup-approver"
              >
                <option value="">-- None --</option>
                {eligible.map((u) => (
                  <option key={u.id} value={u.id}>{u.name} ({u.designation || u.rbac_role})</option>
                ))}
              </select>
            </div>
          </div>
        </Card>

        {/* Section 4: Simulator */}
        <Card className="p-4 bg-leamss-teal-50/30 border-leamss-teal-200" data-testid="simulator-section">
          <h3 className="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-leamss-teal-600" /> 4. Approval Chain Simulator
          </h3>
          <p className="text-xs text-slate-600 mb-3">Test the configuration — see who would approve for any employee.</p>
          <select
            value={simUser}
            onChange={(e) => { setSimUser(e.target.value); simulate(e.target.value); }}
            className="w-full px-3 py-2 border rounded text-sm mb-3"
            data-testid="sim-user-select"
          >
            <option value="">-- Select an employee --</option>
            {employees.filter((u) => u.user_type === 'internal').map((u) => (
              <option key={u.id} value={u.id}>{u.name} · {u.department} · {u.designation || u.rbac_role}</option>
            ))}
          </select>
          {simResult && (
            <Card className="p-3 bg-white" data-testid="sim-result">
              <div className="flex items-center gap-2 flex-wrap text-sm">
                <ChainNode user={simResult.applicant} role="Applicant" color="indigo" />
                {!simResult.skips_l1 && (
                  <>
                    <ArrowRight className="h-4 w-4 text-slate-400" />
                    <ChainNode user={simResult.l1_manager} role="L1 Manager" color="amber" />
                  </>
                )}
                {!simResult.single_stage && (
                  <>
                    <ArrowRight className="h-4 w-4 text-slate-400" />
                    <ChainNode user={simResult.final_approver} role="Final Approver" color="emerald" />
                  </>
                )}
              </div>
              {simResult.skips_l1 && (
                <p className="text-xs text-amber-700 mt-2"><AlertCircle className="h-3 w-3 inline mr-1" /> L1 skipped — applicant is their own manager.</p>
              )}
              {simResult.single_stage && (
                <p className="text-xs text-emerald-700 mt-2"><AlertCircle className="h-3 w-3 inline mr-1" /> Single-stage — L1 IS the final approver.</p>
              )}
            </Card>
          )}
        </Card>

        {/* Section 5: Escalation & Special Rules */}
        <Card className="p-4" data-testid="rules-section">
          <h3 className="text-sm font-bold text-slate-800 mb-3">5. Escalation & Special Rules</h3>
          <div className="space-y-2">
            <NumRow
              label="Escalate If Not Acted In (days)"
              description="Reminder sent to approver if they don't decide within X days. 0 = no escalation."
              value={config.escalate_after_days || 3}
              onChange={(v) => set('escalate_after_days', v)}
              testid="escalate-days"
            />
            <ToggleRow
              label="Long Leave Requires Department Head"
              description="Leaves over 5 days require an extra approval from the department head."
              value={!!config.long_leave_requires_dept_head}
              onChange={(v) => set('long_leave_requires_dept_head', v)}
              testid="long-dept-head"
            />
            <ToggleRow
              label="LWP Requires Admin Approval"
              description="Loss-of-pay regularizations must be approved by an Admin user."
              value={!!config.lwp_requires_admin}
              onChange={(v) => set('lwp_requires_admin', v)}
              testid="lwp-admin"
            />
          </div>
        </Card>
      </div>

      {/* Footer */}
      <div className="mt-6 pt-4 border-t border-slate-200 flex items-center justify-between" data-testid="save-footer">
        <div className="text-xs text-slate-500">
          {dirty ? (
            <span className="text-amber-600 font-semibold">● Unsaved changes</span>
          ) : (
            <span className="text-emerald-600">✓ All changes saved</span>
          )}
        </div>
        <Button onClick={save} disabled={!dirty || saving} data-testid="save-approver-btn">
          <Save className="h-4 w-4 mr-1.5" /> {saving ? 'Saving...' : 'Save Configuration'}
        </Button>
      </div>
    </HRSettingsLayout>
  );
}


function RadioRow({ checked, onClick, label, description, children, testid }) {
  return (
    <div className={`rounded border-2 p-3 cursor-pointer transition-colors ${checked ? 'border-leamss-teal-500 bg-leamss-teal-50/50' : 'border-slate-200 hover:border-slate-300'}`} onClick={onClick} data-testid={testid}>
      <div className="flex items-start gap-2">
        <div className={`w-4 h-4 rounded-full border-2 mt-0.5 ${checked ? 'border-leamss-teal-600 bg-leamss-teal-600' : 'border-slate-300'}`}>
          {checked && <div className="w-full h-full rounded-full bg-white scale-50" />}
        </div>
        <div className="flex-1">
          <p className="text-sm font-semibold text-slate-800">{label}</p>
          <p className="text-xs text-slate-500">{description}</p>
          {children}
        </div>
      </div>
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

function NumRow({ label, description, value, onChange, testid }) {
  return (
    <div className="flex items-start justify-between gap-3 py-2 border-b border-slate-100 last:border-0">
      <div className="flex-1">
        <p className="text-sm font-medium text-slate-800">{label}</p>
        {description && <p className="text-xs text-slate-500 mt-0.5">{description}</p>}
      </div>
      <input
        type="number"
        min="0"
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value) || 0)}
        className="w-24 px-2 py-1.5 border rounded text-sm tabular-nums text-right"
        data-testid={testid}
      />
    </div>
  );
}

function ChainNode({ user, role, color }) {
  if (!user) return <span className="text-xs text-slate-400 italic">(not configured)</span>;
  const COLORS = {
    indigo: 'bg-leamss-teal-100 text-leamss-teal-800 border-leamss-teal-300',
    amber: 'bg-amber-100 text-amber-800 border-amber-300',
    emerald: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  };
  const userId = user.user_id || user.id;
  return (
    <div className={`rounded border-2 p-2 ${COLORS[color]}`} data-testid={`chain-${role.toLowerCase().replace(/ /g, '-')}`}>
      <p className="text-[10px] uppercase tracking-wide font-bold">{role}</p>
      <p className="text-xs font-semibold">{user.name || '?'}</p>
      {user.designation && <p className="text-[10px]">{user.designation}</p>}
    </div>
  );
}
