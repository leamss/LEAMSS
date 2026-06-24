import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  ArrowLeft, Receipt, FileText, Package, ClipboardCheck,
  Download, Check, Clock, AlertCircle,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const TABS = [
  { id: 'payslips', label: 'Payslips', icon: Receipt, accent: 'emerald' },
  { id: 'documents', label: 'Documents', icon: FileText, accent: 'sky' },
  { id: 'assets', label: 'Assets', icon: Package, accent: 'leamss-orange' },
  { id: 'onboarding', label: 'Onboarding', icon: ClipboardCheck, accent: 'leamss-teal' },
];

const STATUS_BADGE = {
  draft: 'bg-slate-100 text-slate-600',
  approved: 'bg-sky-100 text-sky-700',
  paid: 'bg-emerald-100 text-emerald-700',
  uploaded: 'bg-amber-100 text-amber-700',
  verified: 'bg-emerald-100 text-emerald-700',
  rejected: 'bg-leamss-red-100 text-leamss-red-700',
  expired: 'bg-slate-200 text-slate-500',
  issued: 'bg-emerald-100 text-emerald-700',
  in_progress: 'bg-sky-100 text-sky-700',
  completed: 'bg-emerald-100 text-emerald-700',
};

export default function MyWorkspace() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [tab, setTab] = useState(params.get('tab') || 'payslips');
  const [payslips, setPayslips] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [assets, setAssets] = useState([]);
  const [onboarding, setOnboarding] = useState([]);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/'); return; }
    const auth = { headers: { Authorization: `Bearer ${token}` } };
    (async () => {
      try {
        const me = await axios.get(`${API}/auth/me`, auth);
        setUser(me.data);
        const uid = me.data.id;
        const [p, d, a, o] = await Promise.all([
          axios.get(`${API}/employees/me/payslips`, auth).catch(() => ({ data: [] })),
          axios.get(`${API}/employees/${uid}/documents`, auth).catch(() => ({ data: [] })),
          axios.get(`${API}/employees/${uid}/assets`, auth).catch(() => ({ data: [] })),
          axios.get(`${API}/employees/${uid}/onboarding`, auth).catch(() => ({ data: [] })),
        ]);
        setPayslips(p.data);
        setDocuments(d.data);
        setAssets(a.data);
        setOnboarding(o.data);
      } catch (e) {
        navigate('/');
      } finally {
        setLoading(false);
      }
    })();
  }, [navigate]);

  useEffect(() => {
    setParams(p => { p.set('tab', tab); return p; }, { replace: true });
  }, [tab, setParams]);

  const downloadPayslipPDF = async (id) => {
    const token = localStorage.getItem('token');
    const res = await fetch(`${API}/payslips/${id}/pdf`, { headers: { Authorization: `Bearer ${token}` } });
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `payslip-${id}.pdf`;
    a.click();
  };

  if (loading) return <div className="flex items-center justify-center h-screen text-slate-500">Loading…</div>;

  return (
    <div className="min-h-screen bg-slate-50" data-testid="my-workspace-page">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-5xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin/employees')} data-testid="ws-back-hub">
              <ArrowLeft className="h-4 w-4 mr-1.5" /> Hub
            </Button>
            <div>
              <h1 className="text-lg font-bold text-slate-900">My Workspace</h1>
              <p className="text-xs text-slate-500">{user?.name} · {user?.designation || user?.rbac_role}</p>
            </div>
          </div>
          <div className="flex gap-1 bg-slate-100 rounded-lg p-1 overflow-x-auto">
            {TABS.map(t => {
              const Icon = t.icon;
              const counts = { payslips: payslips.length, documents: documents.length, assets: assets.length, onboarding: onboarding.length };
              return (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all flex items-center gap-1.5 whitespace-nowrap ${
                    tab === t.id ? 'bg-white text-leamss-teal-700 shadow-sm' : 'text-slate-500'
                  }`}
                  data-testid={`ws-tab-${t.id}`}
                >
                  <Icon className="h-3.5 w-3.5" /> {t.label} ({counts[t.id]})
                </button>
              );
            })}
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 md:px-6 py-6 space-y-3">
        {/* PAYSLIPS */}
        {tab === 'payslips' && (
          <div data-testid="ws-payslips">
            {payslips.length === 0 && (
              <Card className="p-8 text-center text-slate-500 italic">No payslips yet — HR will generate them monthly.</Card>
            )}
            {payslips.map(p => (
              <Card key={p.id} className="p-4 mb-3" data-testid={`payslip-${p.id}`}>
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-semibold text-slate-900">{p.period}</h3>
                      <Badge className={STATUS_BADGE[p.status] || 'bg-slate-100'}>{p.status}</Badge>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      Gross: ₹ {p.gross_inr?.toLocaleString()} · Deductions: ₹ {p.total_deductions_inr?.toLocaleString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-500">Net pay</p>
                    <p className="text-2xl font-bold text-leamss-orange-600">₹ {p.net_pay_inr?.toLocaleString()}</p>
                  </div>
                  <Button size="sm" variant="outline" onClick={() => downloadPayslipPDF(p.id)} data-testid={`payslip-pdf-${p.id}`}>
                    <Download className="h-3.5 w-3.5 mr-1" /> PDF
                  </Button>
                </div>
                {p.attendance_summary && (
                  <p className="text-[10px] text-slate-400 mt-2">
                    Days present: {p.attendance_summary.present_days} · LWP: {p.attendance_summary.lwp_days}
                  </p>
                )}
              </Card>
            ))}
          </div>
        )}

        {/* DOCUMENTS */}
        {tab === 'documents' && (
          <div data-testid="ws-documents">
            {documents.length === 0 && (
              <Card className="p-8 text-center text-slate-500 italic">No documents uploaded yet.</Card>
            )}
            {documents.map(d => (
              <Card key={d.id} className="p-4 mb-3" data-testid={`doc-${d.id}`}>
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-sky-50 rounded">
                      <FileText className="h-4 w-4 text-sky-600" />
                    </div>
                    <div>
                      <h4 className="font-medium text-slate-800">{d.document_name}</h4>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-[10px] capitalize">{d.document_type.replace('_', ' ')}</Badge>
                        <Badge className={`${STATUS_BADGE[d.status]} text-[10px]`}>{d.status}</Badge>
                        <Badge variant="outline" className="text-[10px] font-mono">v{d.version}</Badge>
                      </div>
                    </div>
                  </div>
                  <a href={d.file_url} target="_blank" rel="noreferrer">
                    <Button size="sm" variant="outline" data-testid={`doc-view-${d.id}`}>
                      <Download className="h-3.5 w-3.5 mr-1" /> Open
                    </Button>
                  </a>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* ASSETS */}
        {tab === 'assets' && (
          <div data-testid="ws-assets">
            {assets.length === 0 && (
              <Card className="p-8 text-center text-slate-500 italic">No assets currently assigned.</Card>
            )}
            {assets.map(a => (
              <Card key={a.id} className="p-4 mb-3" data-testid={`asset-${a.id}`}>
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-leamss-orange-50 rounded">
                      <Package className="h-4 w-4 text-leamss-orange-600" />
                    </div>
                    <div>
                      <h4 className="font-medium text-slate-800 capitalize">{a.asset_type}: {a.brand} {a.model}</h4>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-[10px] font-mono">{a.asset_tag}</Badge>
                        {a.serial_number && <span className="text-[10px] text-slate-400">SN: {a.serial_number}</span>}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    {a.expected_return_date && (
                      <p className="text-[10px] text-slate-500 inline-flex items-center gap-1">
                        <Clock className="h-3 w-3" /> Return by {new Date(a.expected_return_date).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* ONBOARDING */}
        {tab === 'onboarding' && (
          <div data-testid="ws-onboarding">
            {onboarding.length === 0 && (
              <Card className="p-8 text-center text-slate-500 italic">No onboarding workflow assigned.</Card>
            )}
            {onboarding.map(wf => (
              <Card key={wf.id} className="p-5 mb-4" data-testid={`onb-${wf.id}`}>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="text-base font-semibold text-slate-900">{wf.template_name}</h3>
                    <p className="text-xs text-slate-500">Started {wf.started_at ? new Date(wf.started_at).toLocaleDateString() : '—'}</p>
                  </div>
                  <Badge className={STATUS_BADGE[wf.status]}>{wf.status}</Badge>
                </div>
                <div className="space-y-2">
                  {(wf.steps || []).map(s => (
                    <div key={s.step_number} className={`flex items-center gap-3 p-2 rounded ${s.status === 'completed' ? 'bg-emerald-50' : 'bg-slate-50'}`} data-testid={`step-${wf.id}-${s.step_number}`}>
                      <div className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-bold ${s.status === 'completed' ? 'bg-emerald-500 text-white' : 'bg-slate-300 text-slate-600'}`}>
                        {s.status === 'completed' ? <Check className="h-3.5 w-3.5" /> : s.step_number}
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-slate-800">{s.name}</p>
                        <p className="text-[10px] text-slate-500 capitalize">{(s.type || '').replace('_', ' ')} · assigned to {s.assigned_to_role}</p>
                      </div>
                      {s.status !== 'completed' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={async () => {
                            const token = localStorage.getItem('token');
                            await axios.patch(
                              `${API}/onboarding/${wf.id}/step/${s.step_number}/complete`,
                              { notes: 'Done from My Workspace' },
                              { headers: { Authorization: `Bearer ${token}` } },
                            );
                            window.location.reload();
                          }}
                          data-testid={`complete-step-${wf.id}-${s.step_number}`}
                        >
                          Mark done
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
