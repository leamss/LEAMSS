import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { Plus, Download, Copy, Trash2, Pencil, X, Sparkles } from 'lucide-react';
import HRSettingsLayout from '@/components/hr/HRSettingsLayout';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const TYPE_COLOR = {
  public: 'bg-emerald-100 text-emerald-800',
  regional: 'bg-amber-100 text-amber-800',
  optional: 'bg-slate-100 text-slate-700',
};

export default function HolidayManager() {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [view, setView] = useState('list'); // list | calendar

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.get(`${API}/hr/holidays?year=${year}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setItems(r.data || []);
    } catch (e) {
      toast.error('Failed to load holidays');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [year]);

  const handleDelete = async (h) => {
    if (!window.confirm(`Delete "${h.name}" (${h.date})?\n\nThis affects employees who may have leaves planned around this date.`)) return;
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API}/hr/holidays/${h.id}`, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Holiday deleted');
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Delete failed');
    }
  };

  const importIndian = async () => {
    if (!window.confirm(`Import 9 standard Indian holidays for ${year}?`)) return;
    try {
      const token = localStorage.getItem('token');
      const r = await axios.post(`${API}/hr/holidays/import-indian/${year}`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success(`✅ ${r.data.inserted} inserted, ${r.data.skipped} skipped (already existed)`);
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Import failed');
    }
  };

  const copyFromYear = async () => {
    const from = window.prompt('Copy holidays from which year?', String(year - 1));
    if (!from) return;
    try {
      const token = localStorage.getItem('token');
      const r = await axios.post(`${API}/hr/holidays/copy-from/${parseInt(from)}/to/${year}`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success(`✅ ${r.data.inserted} copied, ${r.data.skipped} skipped`);
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Copy failed');
    }
  };

  const exportCSV = () => {
    const rows = [['Date', 'Day', 'Holiday Name', 'Type', 'Optional']];
    items.forEach((h) => {
      const d = new Date(h.date);
      rows.push([
        h.date,
        d.toLocaleDateString('en-IN', { weekday: 'long' }),
        h.name,
        h.type,
        h.is_optional ? 'Yes' : 'No',
      ]);
    });
    const csv = rows.map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `holidays-${year}.csv`; a.click();
  };

  return (
    <HRSettingsLayout
      title="Holiday Calendar"
      subtitle="Manage company-wide holidays and weekly-off variations"
      breadcrumb="Holiday Calendar"
    >
      {/* Top toolbar */}
      <div className="flex items-center justify-between flex-wrap gap-3 mb-4" data-testid="toolbar">
        <div className="flex items-center gap-3">
          <select value={year} onChange={(e) => setYear(parseInt(e.target.value))} className="px-3 py-2 border rounded text-sm" data-testid="year-selector">
            {[2024, 2025, 2026, 2027, 2028].map((y) => <option key={y} value={y}>{y}</option>)}
          </select>
          <Badge variant="outline" className="text-xs">{items.length} holiday{items.length !== 1 ? 's' : ''}</Badge>
          <div className="hidden md:flex gap-1 border rounded p-0.5 ml-2">
            <button onClick={() => setView('list')} className={`px-2 py-1 text-xs rounded ${view === 'list' ? 'bg-indigo-600 text-white' : 'text-slate-600'}`} data-testid="tab-list">List</button>
            <button onClick={() => setView('calendar')} className={`px-2 py-1 text-xs rounded ${view === 'calendar' ? 'bg-indigo-600 text-white' : 'text-slate-600'}`} data-testid="tab-calendar">Calendar</button>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button size="sm" onClick={() => setModal({ mode: 'create' })} className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-holiday-btn">
            <Plus className="h-3.5 w-3.5 mr-1.5" /> Add Holiday
          </Button>
          <Button size="sm" variant="outline" onClick={importIndian} data-testid="import-indian-btn">
            <Sparkles className="h-3.5 w-3.5 mr-1.5" /> Import India Holidays
          </Button>
          <Button size="sm" variant="outline" onClick={copyFromYear} data-testid="copy-year-btn">
            <Copy className="h-3.5 w-3.5 mr-1.5" /> Copy from Year
          </Button>
          <Button size="sm" variant="outline" onClick={exportCSV} data-testid="export-csv-btn">
            <Download className="h-3.5 w-3.5 mr-1.5" /> Export CSV
          </Button>
        </div>
      </div>

      {loading ? (
        <p className="text-slate-500 text-sm">Loading...</p>
      ) : items.length === 0 ? (
        <Card className="p-10 text-center" data-testid="empty-state">
          <p className="text-sm text-slate-500 mb-3">No holidays configured for {year}</p>
          <Button size="sm" onClick={importIndian} data-testid="empty-import-btn">
            <Sparkles className="h-3.5 w-3.5 mr-1.5" /> Import 9 Standard India Holidays
          </Button>
        </Card>
      ) : view === 'calendar' ? (
        <CalendarView items={items} year={year} onEdit={(h) => setModal({ mode: 'edit', holiday: h })} />
      ) : (
        <ListView items={items} onEdit={(h) => setModal({ mode: 'edit', holiday: h })} onDelete={handleDelete} />
      )}

      {modal && (
        <HolidayModal
          mode={modal.mode}
          holiday={modal.holiday}
          year={year}
          onClose={() => setModal(null)}
          onSuccess={() => { setModal(null); load(); }}
        />
      )}
    </HRSettingsLayout>
  );
}


function ListView({ items, onEdit, onDelete }) {
  return (
    <Card className="overflow-hidden" data-testid="list-view">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 border-b border-slate-200">
          <tr>
            <th className="text-left px-4 py-2 text-xs font-semibold text-slate-600 uppercase">Date</th>
            <th className="text-left px-4 py-2 text-xs font-semibold text-slate-600 uppercase">Day</th>
            <th className="text-left px-4 py-2 text-xs font-semibold text-slate-600 uppercase">Holiday</th>
            <th className="text-left px-4 py-2 text-xs font-semibold text-slate-600 uppercase">Type</th>
            <th className="text-right px-4 py-2 text-xs font-semibold text-slate-600 uppercase">Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((h) => {
            const d = new Date(h.date);
            return (
              <tr key={h.id} className="border-b border-slate-100 hover:bg-slate-50" data-testid={`holiday-row-${h.id}`}>
                <td className="px-4 py-2 font-mono text-xs">{h.date}</td>
                <td className="px-4 py-2 text-slate-600">{d.toLocaleDateString('en-IN', { weekday: 'short' })}</td>
                <td className="px-4 py-2 font-medium text-slate-800">{h.name}</td>
                <td className="px-4 py-2">
                  <Badge className={`text-[10px] ${TYPE_COLOR[h.type] || TYPE_COLOR.public}`}>{h.type}</Badge>
                  {h.is_optional && <Badge variant="outline" className="text-[10px] ml-1">optional</Badge>}
                </td>
                <td className="px-4 py-2 text-right">
                  <Button size="sm" variant="ghost" onClick={() => onEdit(h)} data-testid={`edit-${h.id}`}>
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => onDelete(h)} className="text-rose-600 hover:text-rose-700" data-testid={`delete-${h.id}`}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Card>
  );
}


function CalendarView({ items, year, onEdit }) {
  const map = {};
  items.forEach((h) => { map[h.date] = h; });

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="calendar-view">
      {Array.from({ length: 12 }).map((_, m) => {
        const monthName = new Date(year, m).toLocaleDateString('en-US', { month: 'long' });
        const daysInMonth = new Date(year, m + 1, 0).getDate();
        const firstWeekday = (new Date(year, m, 1).getDay() + 6) % 7; // Mon=0
        return (
          <Card key={m} className="p-3">
            <p className="text-xs font-bold text-slate-700 mb-2">{monthName} {year}</p>
            <div className="grid grid-cols-7 gap-0.5 text-[10px] text-center text-slate-400 mb-1">
              {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((d, i) => <div key={i}>{d}</div>)}
            </div>
            <div className="grid grid-cols-7 gap-0.5 text-[10px]">
              {Array.from({ length: firstWeekday }).map((_, i) => <div key={`e-${i}`} />)}
              {Array.from({ length: daysInMonth }).map((_, d) => {
                const dnum = d + 1;
                const dateStr = `${year}-${String(m + 1).padStart(2, '0')}-${String(dnum).padStart(2, '0')}`;
                const h = map[dateStr];
                return (
                  <button
                    key={dnum}
                    onClick={() => h && onEdit(h)}
                    className={`p-1 rounded ${h ? `${TYPE_COLOR[h.type] || TYPE_COLOR.public} font-bold cursor-pointer` : 'text-slate-400'}`}
                    title={h?.name || ''}
                  >
                    {dnum}
                  </button>
                );
              })}
            </div>
          </Card>
        );
      })}
    </div>
  );
}


function HolidayModal({ mode, holiday, year, onClose, onSuccess }) {
  const [form, setForm] = useState(holiday || {
    date: `${year}-01-01`,
    name: '',
    type: 'public',
    is_optional: false,
    applicable_locations: ['all'],
  });
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!form.name || form.name.length < 2) {
      toast.error('Name is required');
      return;
    }
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      if (mode === 'edit') {
        const { id, ...payload } = form;
        const fieldsToUpdate = ['name', 'type', 'is_optional', 'applicable_locations'].reduce((acc, k) => {
          if (payload[k] !== undefined) acc[k] = payload[k];
          return acc;
        }, {});
        await axios.patch(`${API}/hr/holidays/${id}`, fieldsToUpdate, { headers: { Authorization: `Bearer ${token}` } });
        toast.success('Holiday updated');
      } else {
        await axios.post(`${API}/hr/holidays`, form, { headers: { Authorization: `Bearer ${token}` } });
        toast.success('Holiday created');
      }
      onSuccess();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Save failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <Card className="max-w-md w-full p-5 bg-white" onClick={(e) => e.stopPropagation()} data-testid="holiday-modal">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-slate-900">{mode === 'edit' ? 'Edit Holiday' : 'Add Holiday'}</h2>
          <Button variant="ghost" size="sm" onClick={onClose}><X className="h-4 w-4" /></Button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-semibold text-slate-700 uppercase">Date</label>
            <input
              type="date"
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
              disabled={mode === 'edit'}
              className="w-full mt-1 px-3 py-2 border rounded text-sm"
              data-testid="holiday-date"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-slate-700 uppercase">Holiday Name</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full mt-1 px-3 py-2 border rounded text-sm"
              placeholder="e.g., Diwali"
              data-testid="holiday-name"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-slate-700 uppercase">Type</label>
            <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} className="w-full mt-1 px-3 py-2 border rounded text-sm" data-testid="holiday-type">
              <option value="public">National (entire India)</option>
              <option value="regional">Regional (state-specific)</option>
              <option value="optional">Optional (employee choice)</option>
            </select>
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.is_optional} onChange={(e) => setForm({ ...form, is_optional: e.target.checked })} data-testid="holiday-optional" />
            <span className="text-xs text-slate-700">Optional Holiday (employees can choose to take or skip)</span>
          </label>
          <div className="flex gap-2 justify-end pt-2">
            <Button variant="outline" onClick={onClose} data-testid="modal-cancel">Cancel</Button>
            <Button onClick={submit} disabled={submitting} data-testid="modal-submit">
              {submitting ? 'Saving...' : (mode === 'edit' ? 'Update' : 'Create')}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
