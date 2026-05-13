import { useEffect, useState } from 'react';
import axios from 'axios';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import {
  X, Eye, Sparkles, Bell, Clock, CheckSquare,
  Shield, TrendingUp, Megaphone, Briefcase, Users, Receipt, Server, ScrollText,
  ChevronRight, Building2,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DEPT_ICONS = { Shield, TrendingUp, Megaphone, Briefcase, Users, Receipt, Server, ScrollText, Building2 };

/**
 * Read-only "View Dashboard As User" preview.
 * No session switch. No token issued. Pure data peek with audit log.
 */
export default function DashboardPreviewModal({ userId, onClose }) {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const token = localStorage.getItem('token');

  useEffect(() => {
    const load = async () => {
      try {
        const r = await axios.get(`${API}/admin/users/${userId}/dashboard-preview`, { headers: { Authorization: `Bearer ${token}` } });
        setPreview(r.data);
      } catch (err) {
        const msg = err?.response?.data?.detail || 'Failed to load preview';
        toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg));
        onClose();
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [userId, token, onClose]);

  const moduleClick = (m) => toast.info(`🔒 Preview only — "${m}" not interactive`);

  if (loading || !preview) {
    return (
      <Dialog open onOpenChange={onClose}>
        <DialogContent className="max-w-5xl p-12 text-center text-slate-500">Loading preview...</DialogContent>
      </Dialog>
    );
  }

  const u = preview.viewing_as;
  const role = preview.role_info;
  const dept = preview.department_info;
  const DeptIcon = DEPT_ICONS[dept.icon] || Building2;
  const modules = preview.ui_modules || [];

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-5xl max-h-[95vh] overflow-y-auto p-0" data-testid="dashboard-preview-modal">
        {/* Warning banner */}
        <div className="bg-amber-50 border-b-2 border-amber-400 px-6 py-3 flex items-center gap-3 sticky top-0 z-10" data-testid="preview-banner">
          <Eye className="h-5 w-5 text-amber-700 flex-shrink-0" />
          <div className="flex-1">
            <p className="font-bold text-amber-900 text-sm">
              👁️ Previewing dashboard as: <span className="underline">{u.name}</span>
            </p>
            <p className="text-xs text-amber-700">Read-only · Your admin session remains active · Action logged for audit</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-amber-100 rounded-md" data-testid="close-preview"><X className="h-4 w-4 text-amber-900" /></button>
        </div>

        <div className="p-6 space-y-6">
          {/* Welcome banner mimicking PortalWelcome */}
          <Card className="p-6 border-l-4" style={{ borderLeftColor: dept.color, background: `${dept.color}08` }}>
            <div className="flex items-start justify-between flex-wrap gap-4">
              <div>
                <h2 className="text-2xl font-bold text-slate-900">Welcome, {u.name?.split(' ')[0] || 'there'}!</h2>
                <div className="flex items-center gap-3 mt-3 flex-wrap">
                  <Badge className="text-xs" style={{ background: dept.color, color: 'white' }}>
                    <DeptIcon className="h-3 w-3 mr-1" /> {(u.department || 'no-dept').toUpperCase()}
                  </Badge>
                  <span className="text-sm font-medium text-slate-700">{u.designation || u.rbac_role}</span>
                  <span className="text-slate-400">·</span>
                  <span className="text-sm text-slate-600">{u.employee_id || u.partner_code || '—'}</span>
                </div>
              </div>
              <Badge variant="outline" className="text-xs">L{role.hierarchy_level} · {role.name}</Badge>
            </div>
          </Card>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <PreviewStat icon={CheckSquare} label="My Tasks" value={preview.stats.my_tasks} color="text-indigo-600" />
            <PreviewStat icon={Bell} label="Notifications" value={preview.stats.unread_notifications} color="text-amber-600" />
            <PreviewStat icon={Clock} label="Attendance" value={preview.stats.attendance_this_month} color="text-emerald-600" />
            <PreviewStat icon={Sparkles} label="Modules" value={preview.stats.modules_count} color="text-violet-600" />
          </div>

          {/* Modules */}
          <Card className="p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
                <Sparkles className="h-4 w-4" style={{ color: dept.color }} /> Their Access ({modules.length} modules)
              </h3>
            </div>
            {modules.length === 0 ? (
              <p className="text-slate-400 text-sm italic">No modules assigned</p>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                {modules.map(m => (
                  <button
                    key={m}
                    onClick={() => moduleClick(m)}
                    className="p-3 bg-white border border-slate-200 rounded-md hover:bg-slate-50 text-left"
                    data-testid={`preview-module-${m}`}
                  >
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded" style={{ background: `${dept.color}15` }}>
                        <ChevronRight className="h-3 w-3" style={{ color: dept.color }} />
                      </div>
                      <span className="text-xs font-medium text-slate-700 capitalize truncate">{m.replace(/_/g, ' ')}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </Card>

          {/* Footer audit info */}
          <Card className="p-3 bg-slate-50 border-slate-200 text-xs text-slate-500 flex items-center justify-between">
            <span>👁️ Previewed by {preview.previewed_by?.name} at {new Date(preview.previewed_at).toLocaleString()}</span>
            <span>Logged to activity_log</span>
          </Card>
        </div>
      </DialogContent>
    </Dialog>
  );
}

const PreviewStat = ({ icon: Icon, label, value, color }) => (
  <Card className="p-3">
    <div className="flex items-start justify-between">
      <div>
        <p className="text-[10px] uppercase tracking-wider text-slate-500 font-medium">{label}</p>
        <p className={`text-xl font-bold mt-1 ${color}`}>{value}</p>
      </div>
      <Icon className={`h-4 w-4 ${color}`} />
    </div>
  </Card>
);
