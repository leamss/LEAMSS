/**
 * Phase 6.2 — Eligibility Profiles list + detail.
 *
 * URL: /eligibility/profiles  — list with filter
 * URL: /eligibility/profile/:id  — read-only detail (jumping-off for 6.3 assessment)
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import {
  ArrowLeft, Plus, Search, Sparkles, Copy, Trash2, Edit, Globe, FileText,
  CheckCircle2, Clock, AlertCircle, Upload, Link2, Send, Loader2, ClipboardCheck, Inbox,
} from 'lucide-react';

import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_META = {
  draft: { label: 'Draft', color: 'bg-slate-100 text-slate-600', icon: Clock },
  complete: { label: 'Complete', color: 'bg-amber-100 text-amber-700', icon: AlertCircle },
  assessed: { label: 'Assessed', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle2 },
  awaiting_info_sheet: { label: 'Awaiting Client', color: 'bg-sky-100 text-sky-700', icon: Inbox },
  pending_review: { label: 'Pending Review', color: 'bg-leamss-red-100 text-leamss-red-700', icon: ClipboardCheck },
};

export function EligibilityProfilesList() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [pendingCount, setPendingCount] = useState(0);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [showInfoSheetModal, setShowInfoSheetModal] = useState(false);
  const [generatedLink, setGeneratedLink] = useState(null);
  const [uploadingResume, setUploadingResume] = useState(false);
  const fileInputRef = useRef(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (statusFilter !== 'all') params.status = statusFilter;
      if (search) params.search = search;
      const [list, st, pending] = await Promise.all([
        axios.get(`${API}/eligibility/profiles`, { headers, params }),
        axios.get(`${API}/eligibility/profiles/stats/me`, { headers }).catch(() => ({ data: null })),
        axios.get(`${API}/eligibility/info-sheet/pending`, { headers }).catch(() => ({ data: { items: [] } })),
      ]);
      setItems(list.data.items || []);
      setStats(st.data);
      setPendingCount((pending.data.items || []).length);
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to load profiles'));
    } finally { setLoading(false); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, statusFilter]);

  useEffect(() => { load(); }, [load]);

  const duplicate = async (id) => {
    try {
      await axios.post(`${API}/eligibility/profiles/${id}/duplicate`, {}, { headers });
      toast.success('Duplicated');
      load();
    } catch (e) { toast.error('Duplicate failed'); }
  };

  const remove = async (id) => {
    if (!window.confirm('Delete this profile?')) return;
    try {
      await axios.delete(`${API}/eligibility/profiles/${id}`, { headers });
      toast.success('Deleted');
      load();
    } catch (e) { toast.error(formatApiError(e, 'Delete failed')); }
  };

  const handleResumeUpload = async (file) => {
    if (!file) return;
    const validTypes = ['.pdf', '.docx', '.txt'];
    const valid = validTypes.some(ext => file.name.toLowerCase().endsWith(ext));
    if (!valid) {
      toast.error('Only PDF, DOCX, or TXT files allowed');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast.error('File too large — max 10 MB');
      return;
    }
    setUploadingResume(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const r = await axios.post(`${API}/eligibility/profiles/resume-extract`, form, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
        timeout: 60000,
      });
      toast.success('Resume extracted — review and submit');
      // Store extracted data in sessionStorage so wizard can pick it up
      sessionStorage.setItem('eligibility_resume_prefill', JSON.stringify(r.data));
      navigate('/eligibility/new-assessment?source=resume');
    } catch (e) {
      toast.error(formatApiError(e, 'Resume extraction failed'));
    } finally {
      setUploadingResume(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleGenerateInfoSheet = async (clientName, clientEmail) => {
    try {
      const r = await axios.post(`${API}/eligibility/info-sheet/generate-link`, {
        client_name: clientName, client_email: clientEmail, expires_in_days: 14,
      }, { headers });
      setGeneratedLink(r.data);
      toast.success('Info sheet link generated');
      load();
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to generate link'));
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="profiles-list-page">
      <div className="max-w-6xl mx-auto space-y-5">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={() => navigate(-1)}><ArrowLeft className="h-4 w-4 mr-1" />Back</Button>
            <div>
              <h1 className="text-2xl font-semibold flex items-center gap-2">
                <Sparkles className="h-7 w-7 text-leamss-teal-600" />Eligibility Profiles
              </h1>
              <p className="text-sm text-slate-500">Client profiles ready for AI-powered immigration analysis.</p>
            </div>
          </div>
          <div className="flex gap-2 flex-wrap">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              className="hidden"
              onChange={(e) => handleResumeUpload(e.target.files?.[0])}
              data-testid="resume-file-input"
            />
            <Button
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadingResume}
              data-testid="upload-resume-btn"
            >
              {uploadingResume ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Upload className="h-4 w-4 mr-1" />}
              {uploadingResume ? 'Extracting…' : 'Upload Resume'}
            </Button>
            <Button
              variant="outline"
              onClick={() => setShowInfoSheetModal(true)}
              data-testid="send-info-sheet-btn"
            >
              <Send className="h-4 w-4 mr-1" />Send Info Sheet
            </Button>
            <Button onClick={() => navigate('/eligibility/new-assessment')} className="bg-leamss-teal-600 hover:bg-leamss-teal-700" data-testid="new-assessment-btn">
              <Plus className="h-4 w-4 mr-1" />New Assessment
            </Button>
          </div>
        </div>

        {/* Pending Reviews banner (only if any) */}
        {pendingCount > 0 && (
          <Card
            className="p-4 bg-leamss-red-50 border-l-4 border-l-leamss-red-500 cursor-pointer hover:bg-leamss-red-100 transition"
            onClick={() => setStatusFilter('pending_review')}
            data-testid="pending-reviews-banner"
          >
            <div className="flex items-center gap-3">
              <ClipboardCheck className="h-6 w-6 text-leamss-red-600" />
              <div className="flex-1">
                <p className="font-bold text-leamss-red-900">
                  {pendingCount} client info-sheet submission{pendingCount === 1 ? '' : 's'} pending your review
                </p>
                <p className="text-[11px] text-leamss-red-700">Click to filter and review.</p>
              </div>
              <Badge className="bg-leamss-red-600 text-white">{pendingCount}</Badge>
            </div>
          </Card>
        )}

        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Total" value={stats.total} color="indigo" />
            <StatCard label="Drafts" value={stats.draft} color="slate" />
            <StatCard label="Complete" value={stats.complete} color="amber" />
            <StatCard label="Assessed" value={stats.assessed} color="emerald" />
          </div>
        )}

        <Card className="p-3 flex flex-wrap gap-3">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input placeholder="Search by name / email / phone" value={search} onChange={e => setSearch(e.target.value)} className="pl-9" data-testid="search-input" />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-48" data-testid="status-filter"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="draft">Draft</SelectItem>
              <SelectItem value="complete">Complete</SelectItem>
              <SelectItem value="assessed">Assessed</SelectItem>
              <SelectItem value="awaiting_info_sheet">Awaiting Client</SelectItem>
              <SelectItem value="pending_review">Pending Review</SelectItem>
            </SelectContent>
          </Select>
        </Card>

        {showInfoSheetModal && (
          <InfoSheetModal
            onClose={() => { setShowInfoSheetModal(false); setGeneratedLink(null); }}
            onGenerate={handleGenerateInfoSheet}
            generated={generatedLink}
          />
        )}

        {loading ? (
          <p className="text-center text-slate-400 py-8">Loading…</p>
        ) : items.length === 0 ? (
          <Card className="p-10 text-center text-slate-400">
            <Sparkles className="h-12 w-12 mx-auto mb-3 text-slate-200" />
            <p className="text-sm">No profiles yet. Click <strong>New Assessment</strong> to get started.</p>
          </Card>
        ) : (
          <div className="border rounded-md overflow-hidden bg-white">
            <table className="w-full text-sm">
              <thead className="bg-slate-100 text-[10px] uppercase text-slate-600">
                <tr>
                  <th className="text-left px-3 py-2">Client</th>
                  <th className="text-left px-3 py-2">Profession</th>
                  <th className="text-center px-3 py-2">Age</th>
                  <th className="text-center px-3 py-2">Mode</th>
                  <th className="text-center px-3 py-2">Status</th>
                  <th className="text-center px-3 py-2">PA Link</th>
                  <th className="text-right px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map(p => {
                  const meta = STATUS_META[p.status] || STATUS_META.draft;
                  const Icon = meta.icon;
                  return (
                    <tr key={p.id} className="border-t hover:bg-slate-50" data-testid={`profile-row-${p.id}`}>
                      <td className="px-3 py-2">
                        <p className="font-medium">{p.name}</p>
                        <p className="text-[10px] text-slate-500">{p.email || p.phone || '—'}</p>
                      </td>
                      <td className="px-3 py-2 text-xs">{p.current_profession || '—'}</td>
                      <td className="px-3 py-2 text-center">{p.age || '—'}</td>
                      <td className="px-3 py-2 text-center text-[10px]">{p.search_mode || '—'}</td>
                      <td className="px-3 py-2 text-center">
                        <Badge className={`${meta.color} text-[10px]`}><Icon className="h-3 w-3 mr-0.5" />{meta.label}</Badge>
                      </td>
                      <td className="px-3 py-2 text-center text-[10px]">{p.pa_number || '—'}</td>
                      <td className="px-3 py-2 text-right">
                        <div className="flex gap-1 justify-end">
                          {p.status === 'pending_review' && (
                            <Button
                              size="sm"
                              className="h-7 bg-leamss-red-600 hover:bg-leamss-red-700 text-white text-[10px]"
                              onClick={async () => {
                                try {
                                  await axios.post(`${API}/eligibility/info-sheet/${p.id}/approve`, {}, { headers });
                                  toast.success('Approved — profile is now complete');
                                  load();
                                } catch (e) { toast.error(formatApiError(e, 'Approve failed')); }
                              }}
                              title="Approve client submission"
                              data-testid={`approve-${p.id}`}
                            >
                              <ClipboardCheck className="h-3 w-3 mr-1" />Approve
                            </Button>
                          )}
                          {p.status === 'complete' && !p.assessment_id && (
                            <Button
                              size="sm"
                              className="h-7 bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white text-[10px]"
                              onClick={() => navigate(`/sales/occupations`)}
                              title="Use Smart Sales Helper to find right code + calculator"
                              data-testid={`verify-${p.id}`}
                            >
                              <Sparkles className="h-3 w-3 mr-1" />Sales Helper
                            </Button>
                          )}
                          <Button size="sm" variant="outline" className="h-7 w-7 p-0" onClick={() => navigate(`/eligibility/profile/${p.id}`)} title="View" data-testid={`view-${p.id}`}>
                            <FileText className="h-3 w-3" />
                          </Button>
                          <Button size="sm" variant="outline" className="h-7 w-7 p-0" onClick={() => navigate(`/eligibility/edit/${p.id}`)} title="Edit" data-testid={`edit-${p.id}`}>
                            <Edit className="h-3 w-3" />
                          </Button>
                          <Button size="sm" variant="outline" className="h-7 w-7 p-0" onClick={() => duplicate(p.id)} title="Duplicate" data-testid={`dup-${p.id}`}>
                            <Copy className="h-3 w-3" />
                          </Button>
                          <Button size="sm" variant="outline" className="h-7 w-7 p-0 text-rose-600 border-rose-200" onClick={() => remove(p.id)} title="Delete" data-testid={`del-${p.id}`}>
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}


function StatCard({ label, value, color }) {
  const cls = {
    indigo: 'border-l-leamss-teal-500', slate: 'border-l-slate-500',
    amber: 'border-l-amber-500', emerald: 'border-l-emerald-500',
  }[color];
  return (
    <Card className={`p-3 border-l-4 ${cls}`}>
      <p className="text-[10px] uppercase font-bold text-slate-500">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </Card>
  );
}


// ════════════════════════════════════════════════════════════════
// Detail page (read-only summary)
// ════════════════════════════════════════════════════════════════
export function EligibilityProfileDetail() {
  const { profileId } = useParams();
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const r = await axios.get(`${API}/eligibility/profiles/${profileId}`, { headers });
        setProfile(r.data);
      } catch (e) {
        toast.error(formatApiError(e, 'Failed to load'));
      } finally { setLoading(false); }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId]);

  if (loading) return <div className="min-h-screen flex items-center justify-center text-slate-400 text-sm">Loading…</div>;
  if (!profile) return null;

  const meta = STATUS_META[profile.status] || STATUS_META.draft;
  const Icon = meta.icon;

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="profile-detail-page">
      <div className="max-w-4xl mx-auto space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={() => navigate(-1)}><ArrowLeft className="h-4 w-4 mr-1" />Back</Button>
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2">
                {profile.name}
                <Badge className={`${meta.color} text-[10px]`}><Icon className="h-3 w-3 mr-0.5" />{meta.label}</Badge>
              </h1>
              <p className="text-[11px] text-slate-500">{profile.id} · created by {profile.created_by_name || profile.created_by}</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => navigate(`/eligibility/edit/${profile.id}`)} data-testid="edit-detail-btn">
              <Edit className="h-4 w-4 mr-1" />Edit
            </Button>
            {profile.status === 'complete' && !profile.assessment_id && (
              <Button size="sm" className="bg-leamss-teal-600 hover:bg-leamss-teal-700" onClick={() => navigate(`/sales/occupations`)} data-testid="run-ai-btn">
                <Sparkles className="h-4 w-4 mr-1" />Open Sales Helper
              </Button>
            )}
            {profile.assessment_id && (
              <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700" onClick={() => navigate(`/sales/occupations`)} data-testid="view-results-btn">
                <Sparkles className="h-4 w-4 mr-1" />Open Sales Helper
              </Button>
            )}
          </div>
        </div>

        <SectionCard title="Search Strategy" icon={Globe}>
          <KV label="Mode" value={profile.preferences?.search_mode} />
          <KV label="Specific Country" value={profile.preferences?.specific_country} />
          <KV label="Custom Countries" value={(profile.preferences?.custom_countries || []).join(', ')} />
          <KV label="Timeline" value={`${profile.preferences?.timeline_months || '—'} months`} />
          <KV label="Priority" value={profile.preferences?.priority} />
        </SectionCard>

        <SectionCard title="Basic Info" icon={Globe}>
          <KV label="Email" value={profile.email} />
          <KV label="Phone" value={profile.phone} />
          <KV label="DOB" value={profile.basic_info?.date_of_birth} />
          <KV label="Age" value={profile.basic_info?.age} />
          <KV label="Gender" value={profile.basic_info?.gender} />
          <KV label="Marital" value={profile.basic_info?.marital_status} />
          <KV label="Current Country" value={profile.basic_info?.current_country} />
          <KV label="Nationality" value={profile.basic_info?.nationality} />
        </SectionCard>

        <SectionCard title="Professional & Education" icon={FileText}>
          <KV label="Profession" value={profile.professional?.current_profession} />
          <KV label="Designation" value={profile.professional?.designation} />
          <KV label="Industry" value={profile.professional?.industry} />
          <KV label="Total YoE" value={profile.professional?.years_experience_total} />
          <KV label="Current Role YoE" value={profile.professional?.years_in_current_role} />
          <KV label="Salary" value={profile.professional?.salary_inr_per_annum ? `₹${profile.professional.salary_inr_per_annum.toLocaleString('en-IN')}` : '—'} />
          <KV label="Highest Qualification" value={profile.education?.highest_qualification} />
          <KV label="Field" value={profile.education?.field_of_study} />
          <KV label="Year Completed" value={profile.education?.year_completed} />
        </SectionCard>

        <SectionCard title="Language" icon={FileText}>
          <KV label="Test" value={profile.language_proficiency?.primary_test} />
          <KV label="Completed?" value={profile.language_proficiency?.test_completed ? 'Yes' : 'No'} />
          {profile.language_proficiency?.test_completed && (
            <>
              <KV label="Overall" value={profile.language_proficiency?.scores?.overall} />
              <KV label="L / R / W / S" value={`${profile.language_proficiency?.scores?.listening || '-'} / ${profile.language_proficiency?.scores?.reading || '-'} / ${profile.language_proficiency?.scores?.writing || '-'} / ${profile.language_proficiency?.scores?.speaking || '-'}`} />
            </>
          )}
        </SectionCard>

        {(profile.work_history || []).length > 0 && (
          <SectionCard title="Work History" icon={FileText}>
            <div className="col-span-2 space-y-2">
              {profile.work_history.map((h, i) => (
                <div key={i} className="text-xs border-l-2 border-leamss-teal-300 pl-3">
                  <p className="font-medium">{h.designation} @ {h.employer}</p>
                  <p className="text-[10px] text-slate-500">{h.start_date} → {h.end_date || 'present'} · {h.country}</p>
                  {h.duties && <p className="text-[11px] mt-1 text-slate-600">{h.duties}</p>}
                </div>
              ))}
            </div>
          </SectionCard>
        )}
      </div>
    </div>
  );
}


function SectionCard({ title, icon: Icon, children }) {
  return (
    <Card className="p-4">
      <p className="text-[10px] uppercase font-bold text-slate-500 mb-2 flex items-center gap-1">
        <Icon className="h-3.5 w-3.5" />{title}
      </p>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-1.5 text-xs">
        {children}
      </div>
    </Card>
  );
}

function KV({ label, value }) {
  return (
    <div>
      <p className="text-[9px] uppercase text-slate-400">{label}</p>
      <p className="font-medium text-slate-800 break-words">{value || '—'}</p>
    </div>
  );
}


// ════════════════════════════════════════════════════════════════
// Info Sheet Modal — generate + share + copy public link
// ════════════════════════════════════════════════════════════════
function InfoSheetModal({ onClose, onGenerate, generated }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    setSubmitting(true);
    await onGenerate(name, email);
    setSubmitting(false);
  };

  const copy = () => {
    if (generated?.public_url) {
      navigator.clipboard.writeText(generated.public_url);
      toast.success('Link copied to clipboard');
    }
  };

  const whatsappShare = () => {
    if (!generated?.public_url) return;
    const text = `Hi ${name || 'there'}, please fill in your immigration eligibility info sheet here: ${generated.public_url} (Expires in 14 days)`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose} data-testid="info-sheet-modal">
      <Card className="max-w-md w-full p-6 bg-white" onClick={e => e.stopPropagation()}>
        <h2 className="text-lg font-bold flex items-center gap-2 mb-3">
          <Send className="h-5 w-5 text-leamss-teal-600" />Send Info Sheet to Client
        </h2>
        {!generated ? (
          <div className="space-y-3">
            <p className="text-xs text-slate-600">
              Generate a public, no-login link the client can use to self-fill their info. They will land in your "Pending Review" queue.
            </p>
            <div>
              <label className="text-[11px] uppercase font-bold text-slate-500 block mb-1">Client Name *</label>
              <Input value={name} onChange={e => setName(e.target.value)} placeholder="e.g., Aakash Patel" data-testid="info-sheet-modal-name" />
            </div>
            <div>
              <label className="text-[11px] uppercase font-bold text-slate-500 block mb-1">Client Email (optional)</label>
              <Input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="client@example.com" data-testid="info-sheet-modal-email" />
            </div>
            <p className="text-[10px] text-slate-400">Link expires in 14 days. You can revoke it anytime from Active Share Links.</p>
            <div className="flex gap-2 justify-end pt-2">
              <Button variant="outline" size="sm" onClick={onClose}>Cancel</Button>
              <Button
                size="sm"
                className="bg-leamss-teal-600 hover:bg-leamss-teal-700"
                onClick={submit}
                disabled={!name || submitting}
                data-testid="info-sheet-modal-generate"
              >
                {submitting ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Link2 className="h-4 w-4 mr-1" />}
                Generate Link
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded">
              <p className="text-xs font-bold text-emerald-900 mb-1">✓ Link generated</p>
              <p className="text-[11px] text-emerald-700 break-all" data-testid="info-sheet-generated-url">{generated.public_url}</p>
              <p className="text-[10px] text-emerald-600 mt-1">Expires: {new Date(generated.expires_at).toLocaleString('en-IN')}</p>
            </div>
            <div className="flex gap-2 justify-end">
              <Button size="sm" variant="outline" onClick={copy} data-testid="info-sheet-copy"><Copy className="h-4 w-4 mr-1" />Copy</Button>
              <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700" onClick={whatsappShare} data-testid="info-sheet-whatsapp">
                <Send className="h-4 w-4 mr-1" />WhatsApp
              </Button>
              <Button size="sm" variant="outline" onClick={onClose}>Done</Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
