import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Calendar, Plus, X, Clock, CheckCircle, Loader2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function Appointments({ token, role }) {
  const [appts, setAppts] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', date: '', time: '10:00', duration_minutes: 30, case_id: '', attendee_id: '' });
  const [cases, setCases] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchAll(); }, []);

  const fetchAll = async () => {
    try {
      const [apptRes, casesRes, usersRes] = await Promise.all([
        fetch(`${API}/api/appointments`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API}/api/cases`, { headers: { Authorization: `Bearer ${token}` } }).catch(() => null),
        fetch(`${API}/api/users`, { headers: { Authorization: `Bearer ${token}` } }).catch(() => null)
      ]);
      setAppts(await apptRes.json());
      if (casesRes?.ok) setCases(await casesRes.json());
      if (usersRes?.ok) setUsers(await usersRes.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const createAppt = async () => {
    if (!form.title || !form.date) return;
    try {
      await fetch(`${API}/api/appointments`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(form)
      });
      setShowForm(false);
      setForm({ title: '', description: '', date: '', time: '10:00', duration_minutes: 30, case_id: '', attendee_id: '' });
      fetchAll();
    } catch (e) { console.error(e); }
  };

  const cancelAppt = async (id) => {
    await fetch(`${API}/api/appointments/${id}/cancel`, { method: 'PUT', headers: { Authorization: `Bearer ${token}` } });
    fetchAll();
  };

  const completeAppt = async (id) => {
    await fetch(`${API}/api/appointments/${id}/complete`, { method: 'PUT', headers: { Authorization: `Bearer ${token}` } });
    fetchAll();
  };

  const statusColor = { scheduled: 'bg-blue-100 text-blue-700', completed: 'bg-green-100 text-green-700', cancelled: 'bg-gray-100 text-gray-500' };

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" /></div>;

  return (
    <div className="space-y-6" data-testid="appointments">
      <div className="flex justify-between items-center">
        <div />
        <Button onClick={() => setShowForm(!showForm)} data-testid="new-appt-btn">
          {showForm ? <X className="w-4 h-4 mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
          {showForm ? 'Cancel' : 'New Appointment'}
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader><CardTitle className="text-lg">Schedule Appointment</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <input className="w-full border rounded-md p-2 text-sm" placeholder="Title" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} data-testid="appt-title" />
            <textarea className="w-full border rounded-md p-2 text-sm" rows={2} placeholder="Description" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
            <div className="grid grid-cols-3 gap-3">
              <input type="date" className="border rounded-md p-2 text-sm" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} data-testid="appt-date" />
              <input type="time" className="border rounded-md p-2 text-sm" value={form.time} onChange={e => setForm({ ...form, time: e.target.value })} data-testid="appt-time" />
              <select className="border rounded-md p-2 text-sm" value={form.duration_minutes} onChange={e => setForm({ ...form, duration_minutes: parseInt(e.target.value) })}>
                <option value={15}>15 min</option><option value={30}>30 min</option><option value={60}>1 hr</option><option value={90}>1.5 hr</option>
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <select className="border rounded-md p-2 text-sm" value={form.case_id} onChange={e => setForm({ ...form, case_id: e.target.value })}>
                <option value="">Link to Case (optional)</option>
                {(Array.isArray(cases) ? cases : []).map(c => <option key={c.id} value={c.id}>{c.case_id}</option>)}
              </select>
              <select className="border rounded-md p-2 text-sm" value={form.attendee_id} onChange={e => setForm({ ...form, attendee_id: e.target.value })}>
                <option value="">Attendee (optional)</option>
                {(Array.isArray(users) ? users : []).map(u => <option key={u.id} value={u.id}>{u.name} ({u.role})</option>)}
              </select>
            </div>
            <Button onClick={createAppt} data-testid="appt-save-btn">Schedule</Button>
          </CardContent>
        </Card>
      )}

      {/* Appointment List */}
      <div className="space-y-3">
        {(Array.isArray(appts) ? appts : []).length === 0 ? (
          <Card><CardContent className="py-8 text-center text-gray-500"><Calendar className="w-12 h-12 mx-auto mb-3 text-gray-300" /><p>No appointments scheduled.</p></CardContent></Card>
        ) : (
          (Array.isArray(appts) ? appts : []).map(a => (
            <Card key={a.id} className="hover:shadow-sm transition-shadow">
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-lg bg-blue-50 flex flex-col items-center justify-center">
                      <span className="text-xs font-bold text-blue-600">{a.date ? new Date(a.date + 'T00:00').toLocaleDateString('en', { month: 'short' }) : ''}</span>
                      <span className="text-lg font-bold text-blue-800">{a.date ? new Date(a.date + 'T00:00').getDate() : ''}</span>
                    </div>
                    <div>
                      <p className="font-medium text-sm">{a.title}</p>
                      <p className="text-xs text-gray-500">
                        <Clock className="w-3 h-3 inline mr-1" />{a.time} — {a.duration_minutes} min
                        {a.attendee_name && ` | ${a.attendee_name}`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={statusColor[a.status] || ''}>{a.status}</Badge>
                    {a.status === 'scheduled' && (
                      <div className="flex gap-1">
                        <Button size="sm" variant="outline" onClick={() => completeAppt(a.id)}><CheckCircle className="w-3 h-3" /></Button>
                        <Button size="sm" variant="ghost" onClick={() => cancelAppt(a.id)}><X className="w-3 h-3 text-red-500" /></Button>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
