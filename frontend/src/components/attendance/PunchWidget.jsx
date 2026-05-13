import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { Clock, LogIn, LogOut, MapPin, AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const fmtTime = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
};

const fmtDuration = (mins) => {
  if (!mins || mins < 0) return '0h 0m';
  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
};

export default function PunchWidget() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [punching, setPunching] = useState(false);
  const [tick, setTick] = useState(0);

  const fetchStatus = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const r = await axios.get(`${API}/attendance/current-status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setData(r.data);
    } catch (e) {
      // silent — punch widget is optional
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(() => setTick((t) => t + 1), 60000); // refresh time every min
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const getLocation = () => new Promise((resolve) => {
    if (!navigator.geolocation) return resolve({});
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
      () => resolve({}),
      { timeout: 3000 },
    );
  });

  const handlePunchIn = async (workMode = 'office') => {
    setPunching(true);
    try {
      const token = localStorage.getItem('token');
      const loc = await getLocation();
      const r = await axios.post(`${API}/attendance/punch-in`, {
        work_mode: workMode,
        ...loc,
      }, { headers: { Authorization: `Bearer ${token}` } });

      if (r.data.is_late) {
        const lm = r.data.late_marks_this_month;
        let msg = `⚠️ Late by ${r.data.late_by_minutes} mins. Stay till ${fmtTime(r.data.expected_clock_out_at)} for 9h.`;
        if (lm) msg += ` Late mark ${lm.count_after}/${lm.threshold} this month.`;
        if (lm?.deduction_applied) msg += ` ❌ 1 CL auto-deducted!`;
        toast.warning(msg, { duration: 8000 });
      } else {
        toast.success('✅ Punched in on time. Have a productive day!');
      }
      await fetchStatus();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Punch-in failed');
    } finally {
      setPunching(false);
    }
  };

  const handlePunchOut = async (confirmShort = false) => {
    setPunching(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.post(`${API}/attendance/punch-out`, {
        confirm_short_hours: confirmShort,
      }, { headers: { Authorization: `Bearer ${token}` } });

      if (r.data.requires_confirmation && r.data.short_hours) {
        const ok = window.confirm(
          `${r.data.message}\n\nDo you still want to punch out? Manager approval will be required.`
        );
        if (ok) {
          await handlePunchOut(true);
          return;
        }
        return;
      }

      toast.success(`✅ Punched out. Total: ${r.data.total_hours_str}${r.data.short_hours ? ' (short hours)' : ''}`);
      await fetchStatus();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Punch-out failed');
    } finally {
      setPunching(false);
    }
  };

  if (loading) {
    return (
      <Card className="p-4 flex items-center justify-center" data-testid="punch-widget-loading">
        <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
      </Card>
    );
  }

  if (!data) return null;

  const status = data.status;
  const log = data.log || {};
  const lateMarks = data.late_marks || { count: 0, deductions: 0 };
  const threshold = data.late_threshold || 3;
  const warningAtLateMarks = (lateMarks.count + 1) % threshold === 0 && lateMarks.count > 0;

  // ────────────────── Not punched ──────────────────
  if (status === 'not_punched') {
    const isHoliday = data.is_holiday;
    return (
      <Card className="p-5 border-l-4 border-l-emerald-500 bg-gradient-to-r from-emerald-50 to-white" data-testid="punch-widget-not-punched">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center">
              <Clock className="h-6 w-6 text-emerald-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-700">Ready to start your day?</p>
              <p className="text-xs text-slate-500">
                Office hours: {data.office_start_time} — {data.office_end_time} ({data.min_work_hours}h)
              </p>
              {lateMarks.count > 0 && (
                <p className="text-xs text-amber-600 mt-1">
                  ⚠️ {lateMarks.count} late mark{lateMarks.count > 1 ? 's' : ''} this month
                  {lateMarks.deductions > 0 && ` · ${lateMarks.deductions} CL deducted`}
                </p>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <Button onClick={() => handlePunchIn('office')} disabled={punching} className="bg-emerald-600 hover:bg-emerald-700" data-testid="punch-in-office-btn">
              <LogIn className="h-4 w-4 mr-1.5" /> Punch In (Office)
            </Button>
            <Button onClick={() => handlePunchIn('wfh')} disabled={punching} variant="outline" data-testid="punch-in-wfh-btn">
              <LogIn className="h-4 w-4 mr-1.5" /> WFH
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  // ────────────────── In progress ──────────────────
  if (status === 'in_progress') {
    const elapsed = data.elapsed_minutes || 0;
    const minRequired = data.min_required_minutes || 540;
    const progress = Math.min(100, (elapsed / minRequired) * 100);
    const isLate = log.is_late;
    const expectedOut = data.expected_clock_out_at;
    const canPunchOut = elapsed >= minRequired;

    return (
      <Card className={`p-5 border-l-4 ${isLate ? 'border-l-amber-500 bg-gradient-to-r from-amber-50 to-white' : 'border-l-emerald-500 bg-gradient-to-r from-emerald-50 to-white'}`} data-testid="punch-widget-in-progress">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div className="flex-1 min-w-[280px]">
            <div className="flex items-center gap-2 mb-2">
              <div className={`w-2 h-2 rounded-full ${isLate ? 'bg-amber-500' : 'bg-emerald-500'} animate-pulse`} />
              <p className="text-sm font-semibold text-slate-800">
                {isLate ? `Punched in late at ${fmtTime(log.punch_in_at)}` : `Punched in at ${fmtTime(log.punch_in_at)}`}
              </p>
              {log.work_mode && <Badge variant="outline" className="text-xs uppercase">{log.work_mode}</Badge>}
            </div>

            {isLate && (
              <div className="bg-amber-100 border border-amber-300 rounded p-2 mb-3" data-testid="late-banner">
                <p className="text-xs text-amber-800 font-semibold flex items-center gap-1.5">
                  <AlertTriangle className="h-3.5 w-3.5" /> Late by {log.late_by_minutes} mins
                </p>
                <p className="text-xs text-amber-700 mt-0.5">
                  Stay until <strong>{fmtTime(expectedOut)}</strong> to complete 9 hours.
                </p>
                {warningAtLateMarks && (
                  <p className="text-xs text-rose-700 mt-1 font-semibold">
                    🚨 1 more late = 1 CL auto-deduction!
                  </p>
                )}
              </div>
            )}

            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-600">Hours worked</span>
                <span className="font-bold tabular-nums">{fmtDuration(elapsed)} / {fmtDuration(minRequired)}</span>
              </div>
              <div className="h-2 bg-slate-200 rounded overflow-hidden">
                <div className={`h-full transition-all ${canPunchOut ? 'bg-emerald-500' : 'bg-amber-500'}`} style={{ width: `${progress}%` }} />
              </div>
              <p className="text-xs text-slate-500">
                {canPunchOut ? '✅ 9 hours complete — you can punch out!' : `${fmtDuration(data.remaining_minutes)} remaining`}
              </p>
            </div>

            <div className="mt-2 flex gap-3 text-xs">
              <span className="text-slate-500">
                Late marks this month: <strong className={lateMarks.count >= threshold - 1 ? 'text-rose-600' : 'text-slate-700'}>{lateMarks.count}/{threshold}</strong>
              </span>
              {lateMarks.deductions > 0 && (
                <span className="text-rose-600">CL deducted: {lateMarks.deductions}</span>
              )}
            </div>
          </div>

          <Button onClick={() => handlePunchOut(false)} disabled={punching} className={canPunchOut ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-slate-600 hover:bg-slate-700'} data-testid="punch-out-btn">
            <LogOut className="h-4 w-4 mr-1.5" /> Punch Out
          </Button>
        </div>
      </Card>
    );
  }

  // ────────────────── Completed ──────────────────
  if (status === 'completed') {
    const totalMins = log.total_minutes || 0;
    const wasLate = log.is_late;
    return (
      <Card className="p-5 border-l-4 border-l-slate-400 bg-gradient-to-r from-slate-50 to-white" data-testid="punch-widget-completed">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center">
              <CheckCircle2 className="h-6 w-6 text-emerald-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-800">Today's attendance complete</p>
              <p className="text-xs text-slate-500">
                {fmtTime(log.punch_in_at)} — {fmtTime(log.punch_out_at)}
                {' · '}<strong>{fmtDuration(totalMins)}</strong>
              </p>
              <div className="flex gap-2 mt-1 flex-wrap">
                {wasLate && <Badge className="bg-amber-100 text-amber-800 text-xs">Late {log.late_by_minutes}m</Badge>}
                {log.short_hours && <Badge className="bg-rose-100 text-rose-800 text-xs">Short Hours</Badge>}
                {log.work_mode && <Badge variant="outline" className="text-xs uppercase">{log.work_mode}</Badge>}
              </div>
            </div>
          </div>
        </div>
      </Card>
    );
  }

  return null;
}
