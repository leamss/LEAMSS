import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { ArrowLeft, ChevronLeft, ChevronRight, Clock, TrendingDown, Calendar as CalendarIcon, AlertTriangle, FileText } from 'lucide-react';
import PunchWidget from '@/components/attendance/PunchWidget';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const STATUS_COLORS = {
  present: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  late: 'bg-amber-100 text-amber-800 border-amber-300',
  absent: 'bg-rose-100 text-rose-800 border-rose-300',
  leave: 'bg-indigo-100 text-indigo-800 border-indigo-300',
  holiday: 'bg-purple-100 text-purple-800 border-purple-300',
  weekly_off: 'bg-slate-100 text-slate-600 border-slate-300',
  lwp: 'bg-rose-200 text-rose-900 border-rose-400',
  future: 'bg-slate-50 text-slate-400 border-slate-200',
  half_day: 'bg-orange-100 text-orange-800 border-orange-300',
};

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function MyAttendance() {
  const navigate = useNavigate();
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showRegularize, setShowRegularize] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.get(`${API}/attendance/my-month?year=${year}&month=${month}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setData(r.data);
    } catch (e) {
      toast.error('Failed to load attendance');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [year, month]);

  const prevMonth = () => {
    if (month === 1) { setMonth(12); setYear(year - 1); }
    else setMonth(month - 1);
  };
  const nextMonth = () => {
    if (month === 12) { setMonth(1); setYear(year + 1); }
    else setMonth(month + 1);
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-slate-500">Loading attendance...</div>;
  }

  const counters = data?.counters || {};
  const lateMarks = data?.late_marks || {};
  const settings = data?.settings || {};

  // Build calendar grid — start with Monday
  const firstDay = data?.days?.[0];
  const startOffset = firstDay ? firstDay.day_of_week : 0; // Mon=0..Sun=6
  const grid = [];
  for (let i = 0; i < startOffset; i++) grid.push(null);
  (data?.days || []).forEach((d) => grid.push(d));

  return (
    <div className="min-h-screen bg-slate-50" data-testid="my-attendance-page">
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/portal/welcome')} data-testid="back-btn">
            <ArrowLeft className="h-4 w-4 mr-1.5" /> Back
          </Button>
          <h1 className="font-bold text-slate-900 flex items-center gap-2">
            <CalendarIcon className="h-5 w-5 text-emerald-600" /> My Attendance
          </h1>
        </div>
        <Button variant="outline" size="sm" onClick={() => setShowRegularize({ open: true })} data-testid="regularize-btn">
          <FileText className="h-4 w-4 mr-1.5" /> Request Regularization
        </Button>
      </header>

      <main className="max-w-6xl mx-auto p-6 space-y-5">
        {/* Punch Widget */}
        <PunchWidget />

        {/* Top stat cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3" data-testid="stat-cards">
          <StatCard label="Present" value={counters.present || 0} color="text-emerald-600" icon={Clock} />
          <StatCard label="Late" value={counters.late || 0} color="text-amber-600" icon={AlertTriangle} sublabel={`${lateMarks.count || 0}/${lateMarks.threshold || 3} this month`} />
          <StatCard label="Absent" value={counters.absent || 0} color="text-rose-600" icon={TrendingDown} />
          <StatCard label="On Leave" value={counters.leave || 0} color="text-indigo-600" icon={CalendarIcon} />
          <StatCard label="LWP" value={counters.lwp || 0} color="text-rose-700" icon={TrendingDown} />
          <StatCard label="Hours" value={counters.total_hours || 0} color="text-slate-700" icon={Clock} sublabel="this month" />
        </div>

        {/* Late marks warning */}
        {lateMarks.count >= (lateMarks.threshold || 3) - 1 && lateMarks.count < (lateMarks.threshold || 3) && (
          <Card className="p-3 bg-amber-50 border-amber-300 border-l-4" data-testid="late-warning">
            <p className="text-sm text-amber-900 font-semibold">
              ⚠️ You have {lateMarks.count} late mark{lateMarks.count > 1 ? 's' : ''} this month.
              1 more late punch = 1 CL auto-deducted from your balance.
            </p>
          </Card>
        )}
        {lateMarks.deductions > 0 && (
          <Card className="p-3 bg-rose-50 border-rose-300 border-l-4" data-testid="deduction-warning">
            <p className="text-sm text-rose-900 font-semibold">
              ❌ {lateMarks.deductions} Casual Leave auto-deducted this month due to late marks
            </p>
          </Card>
        )}

        {/* Calendar */}
        <Card className="p-5" data-testid="calendar-card">
          <div className="flex items-center justify-between mb-4">
            <Button variant="outline" size="sm" onClick={prevMonth} data-testid="prev-month-btn">
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <h2 className="text-lg font-bold text-slate-900">
              {new Date(year, month - 1).toLocaleString('en-US', { month: 'long', year: 'numeric' })}
            </h2>
            <Button variant="outline" size="sm" onClick={nextMonth} data-testid="next-month-btn">
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>

          {/* Day headers */}
          <div className="grid grid-cols-7 gap-1.5 mb-2">
            {DAY_LABELS.map((d) => (
              <div key={d} className="text-center text-xs font-semibold text-slate-500 uppercase tracking-wide py-1">
                {d}
              </div>
            ))}
          </div>

          {/* Days grid */}
          <div className="grid grid-cols-7 gap-1.5">
            {grid.map((day, idx) => {
              if (!day) return <div key={`empty-${idx}`} />;
              const color = STATUS_COLORS[day.status] || STATUS_COLORS.future;
              return (
                <button
                  key={day.date}
                  onClick={() => day.status === 'absent' || day.status === 'lwp' ? setShowRegularize({ open: true, date: day.date }) : null}
                  className={`min-h-[64px] rounded border p-1.5 text-left transition-all hover:shadow-sm ${color} ${day.is_future ? 'opacity-50' : ''}`}
                  disabled={day.is_future}
                  data-testid={`day-${day.date}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold">{day.day_of_month}</span>
                    {day.is_holiday && <span className="text-[9px]">🎉</span>}
                  </div>
                  {day.status === 'late' && (
                    <p className="text-[9px] mt-0.5 font-medium">{day.punch_in} (+{day.late_by_minutes}m)</p>
                  )}
                  {day.status === 'present' && day.punch_in && (
                    <p className="text-[9px] mt-0.5">{day.punch_in}</p>
                  )}
                  {day.status === 'leave' && (
                    <p className="text-[9px] mt-0.5 truncate">{(day.leave_type || '').replace(/_/g, ' ').replace('leave', '').trim()}</p>
                  )}
                  {day.status === 'holiday' && (
                    <p className="text-[9px] mt-0.5 truncate" title={day.holiday_name}>{day.holiday_name}</p>
                  )}
                  {day.status === 'lwp' && <p className="text-[9px] mt-0.5 font-bold">LWP</p>}
                  {day.status === 'weekly_off' && <p className="text-[9px] mt-0.5 text-slate-400">off</p>}
                </button>
              );
            })}
          </div>

          {/* Legend */}
          <div className="flex flex-wrap gap-2 mt-4 pt-3 border-t border-slate-200">
            {Object.entries({
              present: 'Present', late: 'Late', absent: 'Absent',
              leave: 'On Leave', lwp: 'LWP', holiday: 'Holiday', weekly_off: 'Weekly Off',
            }).map(([key, label]) => (
              <div key={key} className="flex items-center gap-1.5">
                <span className={`w-3 h-3 rounded border ${STATUS_COLORS[key]}`} />
                <span className="text-xs text-slate-600">{label}</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Settings card */}
        <Card className="p-4 bg-slate-100" data-testid="settings-card">
          <p className="text-xs text-slate-600">
            <strong>Company Policy:</strong> Office hours {settings.office_start_time} — {settings.office_end_time} ({settings.min_work_hours}h),
            late after {settings.late_threshold_minutes} min grace.
            Every {settings.late_marks_for_leave_deduction} late marks = 1 CL auto-deducted.
          </p>
        </Card>
      </main>

      {/* Regularize Modal */}
      {showRegularize?.open && (
        <RegularizeModal
          initialDate={showRegularize.date}
          onClose={() => setShowRegularize(null)}
          onSuccess={() => { setShowRegularize(null); load(); }}
        />
      )}
    </div>
  );
}

const StatCard = ({ label, value, color, icon: Icon, sublabel }) => (
  <Card className="p-3">
    <div className="flex items-start justify-between">
      <div>
        <p className="text-[10px] uppercase tracking-wide text-slate-500 font-semibold">{label}</p>
        <p className={`text-2xl font-bold tabular-nums ${color}`}>{value}</p>
        {sublabel && <p className="text-[10px] text-slate-400 mt-0.5">{sublabel}</p>}
      </div>
      <Icon className={`h-4 w-4 ${color}`} />
    </div>
  </Card>
);

const RegularizeModal = ({ initialDate, onClose, onSuccess }) => {
  const [date, setDate] = useState(initialDate || new Date().toISOString().slice(0, 10));
  const [reason, setReason] = useState('');
  const [requestType, setRequestType] = useState('missed_punch');
  const [punchIn, setPunchIn] = useState('10:00');
  const [punchOut, setPunchOut] = useState('19:00');
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (reason.length < 10) {
      toast.error('Reason must be at least 10 characters');
      return;
    }
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/attendance/regularize`, {
        date, reason, request_type: requestType,
        correct_punch_in: requestType === 'missed_punch' || requestType === 'wrong_time' ? punchIn : null,
        correct_punch_out: requestType === 'missed_punch' || requestType === 'wrong_time' ? punchOut : null,
      }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('✅ Regularization submitted to your manager');
      onSuccess();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to submit');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <Card className="max-w-md w-full p-5 bg-white" onClick={(e) => e.stopPropagation()} data-testid="regularize-modal">
        <h2 className="text-lg font-bold text-slate-900 mb-3">Request Regularization</h2>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-semibold text-slate-700 uppercase">Date</label>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} max={new Date().toISOString().slice(0, 10)} className="w-full mt-1 px-3 py-2 border rounded text-sm" data-testid="reg-date" />
          </div>
          <div>
            <label className="text-xs font-semibold text-slate-700 uppercase">Type</label>
            <select value={requestType} onChange={(e) => setRequestType(e.target.value)} className="w-full mt-1 px-3 py-2 border rounded text-sm" data-testid="reg-type">
              <option value="missed_punch">Missed punch / Forgot to punch</option>
              <option value="wrong_time">Wrong punch time</option>
              <option value="lwp_dispute">LWP dispute (was on duty)</option>
            </select>
          </div>
          {(requestType === 'missed_punch' || requestType === 'wrong_time') && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-700 uppercase">Punch In</label>
                <input type="time" value={punchIn} onChange={(e) => setPunchIn(e.target.value)} className="w-full mt-1 px-3 py-2 border rounded text-sm" data-testid="reg-punch-in" />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700 uppercase">Punch Out</label>
                <input type="time" value={punchOut} onChange={(e) => setPunchOut(e.target.value)} className="w-full mt-1 px-3 py-2 border rounded text-sm" data-testid="reg-punch-out" />
              </div>
            </div>
          )}
          <div>
            <label className="text-xs font-semibold text-slate-700 uppercase">
              Reason <span className="text-slate-400">(min 10 chars)</span>
            </label>
            <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} className="w-full mt-1 px-3 py-2 border rounded text-sm" placeholder="Explain why this regularization is needed..." data-testid="reg-reason" />
            <p className="text-[10px] text-slate-400 mt-0.5">{reason.length}/10 chars</p>
          </div>
          <div className="flex gap-2 justify-end pt-2">
            <Button variant="outline" onClick={onClose} data-testid="reg-cancel">Cancel</Button>
            <Button onClick={submit} disabled={submitting || reason.length < 10} data-testid="reg-submit">
              {submitting ? 'Submitting...' : 'Submit Request'}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};
