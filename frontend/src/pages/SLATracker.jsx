import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Clock, AlertTriangle, Calendar, Loader2, Save } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function SLATracker({ token, role }) {
  const [overdue, setOverdue] = useState([]);
  const [approaching, setApproaching] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deadlineForm, setDeadlineForm] = useState({ case_id: '', step_name: '', deadline: '', sla_days: 7 });
  const [cases, setCases] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [slaRes, casesRes] = await Promise.all([
        fetch(`${API}/api/cases/overdue-steps`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API}/api/cases`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      const slaData = await slaRes.json();
      setOverdue(slaData.overdue || []);
      setApproaching(slaData.approaching || []);
      const casesData = await casesRes.json();
      setCases(Array.isArray(casesData) ? casesData.filter(c => c.status === 'active') : []);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const setDeadline = async () => {
    if (!deadlineForm.case_id || !deadlineForm.step_name || !deadlineForm.deadline) return;
    setSaving(true);
    try {
      await fetch(`${API}/api/cases/set-step-deadline`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(deadlineForm)
      });
      setDeadlineForm({ case_id: '', step_name: '', deadline: '', sla_days: 7 });
      fetchData();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const selectedCase = cases.find(c => c.id === deadlineForm.case_id);
  const steps = selectedCase?.steps || [];

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" /></div>;

  return (
    <div className="space-y-6" data-testid="sla-tracker">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className={overdue.length > 0 ? 'border-red-300 bg-red-50' : ''}>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className={`w-8 h-8 ${overdue.length > 0 ? 'text-red-500' : 'text-gray-400'}`} />
              <div>
                <p className="text-2xl font-bold">{overdue.length}</p>
                <p className="text-sm text-gray-600">Overdue Steps</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className={approaching.length > 0 ? 'border-amber-300 bg-amber-50' : ''}>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <Clock className={`w-8 h-8 ${approaching.length > 0 ? 'text-amber-500' : 'text-gray-400'}`} />
              <div>
                <p className="text-2xl font-bold">{approaching.length}</p>
                <p className="text-sm text-gray-600">Approaching Deadline</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <Calendar className="w-8 h-8 text-blue-500" />
              <div>
                <p className="text-2xl font-bold">{cases.length}</p>
                <p className="text-sm text-gray-600">Active Cases</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Set Deadline Form */}
      {(role === 'admin' || role === 'case_manager') && (
        <Card>
          <CardHeader><CardTitle className="text-lg">Set Step Deadline</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <select className="border rounded-md p-2 text-sm" value={deadlineForm.case_id} onChange={e => setDeadlineForm({ ...deadlineForm, case_id: e.target.value, step_name: '' })} data-testid="sla-case-select">
                <option value="">Select Case</option>
                {cases.map(c => <option key={c.id} value={c.id}>{c.case_id} — {c.client_name}</option>)}
              </select>
              <select className="border rounded-md p-2 text-sm" value={deadlineForm.step_name} onChange={e => setDeadlineForm({ ...deadlineForm, step_name: e.target.value })} data-testid="sla-step-select">
                <option value="">Select Step</option>
                {steps.filter(s => s.status !== 'completed').map(s => <option key={s.step_name} value={s.step_name}>{s.step_name}</option>)}
              </select>
              <input type="date" className="border rounded-md p-2 text-sm" value={deadlineForm.deadline ? deadlineForm.deadline.split('T')[0] : ''} onChange={e => setDeadlineForm({ ...deadlineForm, deadline: new Date(e.target.value).toISOString() })} data-testid="sla-deadline-input" />
              <Button onClick={setDeadline} disabled={saving} data-testid="sla-save-btn">
                {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />} Set Deadline
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Overdue List */}
      {overdue.length > 0 && (
        <Card className="border-red-200">
          <CardHeader><CardTitle className="text-lg text-red-700">Overdue Steps</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              {overdue.map(s => (
                <div key={s.step_id} className="flex items-center justify-between p-3 bg-red-50 rounded-lg border border-red-200">
                  <div>
                    <p className="font-medium text-sm">{s.case_number} — {s.step_name}</p>
                    <p className="text-xs text-red-600">Deadline: {new Date(s.deadline).toLocaleDateString()}</p>
                  </div>
                  <Badge variant="destructive">{s.overdue_by} days overdue</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Approaching List */}
      {approaching.length > 0 && (
        <Card className="border-amber-200">
          <CardHeader><CardTitle className="text-lg text-amber-700">Approaching Deadline</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              {approaching.map(s => (
                <div key={s.step_id} className="flex items-center justify-between p-3 bg-amber-50 rounded-lg border border-amber-200">
                  <div>
                    <p className="font-medium text-sm">{s.case_number} — {s.step_name}</p>
                    <p className="text-xs text-amber-600">Deadline: {new Date(s.deadline).toLocaleDateString()}</p>
                  </div>
                  <Badge className="bg-amber-100 text-amber-800">{s.days_remaining} days left</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {overdue.length === 0 && approaching.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-gray-500">
            <Clock className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>No deadlines set yet. Use the form above to set SLA deadlines for case steps.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
