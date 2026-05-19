/**
 * Phase 6.7 Part 2 — Public Info Sheet Form
 *
 * Route: /info-sheet/:token  (NO LOGIN — public link)
 *
 * Client opens the shared link → fills basic profile fields → submits.
 * Backend creates a "pending_review" profile for the partner to approve.
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import {
  Sparkles, CheckCircle2, AlertCircle, Heart, User, Briefcase, GraduationCap, MessageSquare,
  UsersIcon, Globe, Send, Loader2,
} from 'lucide-react';

import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const MARITAL_OPTIONS = [
  { v: 'single', l: 'Single' },
  { v: 'married', l: 'Married' },
  { v: 'de_facto', l: 'De facto / Partnership' },
  { v: 'separated', l: 'Separated' },
  { v: 'divorced', l: 'Divorced' },
  { v: 'widowed', l: 'Widowed' },
];

const QUALIFICATIONS = [
  { v: 'doctorate', l: 'Doctorate / PhD' },
  { v: 'master', l: "Master's Degree" },
  { v: 'bachelor', l: "Bachelor's Degree" },
  { v: 'diploma', l: 'Diploma' },
  { v: 'trade', l: 'Trade Qualification' },
  { v: 'high_school', l: 'High School' },
];

const COUNTRIES = [
  { code: 'AU', name: 'Australia' },
  { code: 'CA', name: 'Canada' },
  { code: 'NZ', name: 'New Zealand' },
  { code: 'UK', name: 'United Kingdom' },
  { code: 'US', name: 'United States' },
  { code: 'DE', name: 'Germany' },
];

export default function PublicInfoSheet() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState(null);
  const [linkInfo, setLinkInfo] = useState(null);
  const [data, setData] = useState({
    full_name: '', email: '', phone: '', date_of_birth: '', nationality: 'Indian',
    current_country: 'India', current_city: '',
    marital_status: '',
    current_profession: '', designation: '', years_experience_total: 0,
    employer_name: '', industry: '',
    highest_qualification: '', field_of_study: '', year_completed: '',
    language_test_taken: false, language_overall_score: '',
    spouse_full_name: '', spouse_age: '', spouse_profession: '',
    spouse_education: '', spouse_english_overall: '', spouse_on_visa: true,
    preferred_countries: [], timeline_months: 12,
  });

  useEffect(() => {
    (async () => {
      try {
        const r = await axios.get(`${API}/eligibility/info-sheet/public/${token}`);
        setLinkInfo(r.data);
        if (r.data?.prefill) {
          setData(d => ({
            ...d,
            full_name: r.data.prefill.full_name || '',
            email: r.data.prefill.email || '',
            phone: r.data.prefill.phone || '',
          }));
        }
      } catch (e) {
        setError(formatApiError(e, 'This link is invalid or has expired'));
      } finally { setLoading(false); }
    })();
  }, [token]);

  const update = (field, val) => setData(d => ({ ...d, [field]: val }));
  const toggleCountry = (code) => setData(d => ({
    ...d,
    preferred_countries: d.preferred_countries.includes(code)
      ? d.preferred_countries.filter(c => c !== code)
      : [...d.preferred_countries, code],
  }));

  const submit = async () => {
    if (!data.full_name || !data.current_profession || !data.highest_qualification || !data.marital_status) {
      toast.error('Please fill in Name, Marital Status, Current Profession, and Highest Qualification');
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        ...data,
        years_experience_total: parseFloat(data.years_experience_total) || 0,
        language_overall_score: data.language_overall_score ? parseFloat(data.language_overall_score) : null,
        year_completed: data.year_completed ? parseInt(data.year_completed) : null,
        spouse_age: data.spouse_age ? parseInt(data.spouse_age) : null,
        spouse_english_overall: data.spouse_english_overall ? parseFloat(data.spouse_english_overall) : null,
        timeline_months: parseInt(data.timeline_months) || 12,
      };
      await axios.post(`${API}/eligibility/info-sheet/public/${token}/submit`, payload);
      setSubmitted(true);
      toast.success('Submitted successfully!');
    } catch (e) {
      toast.error(formatApiError(e, 'Submission failed'));
    } finally { setSubmitting(false); }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-6">
        <Card className="max-w-md p-8 text-center">
          <AlertCircle className="h-12 w-12 text-rose-500 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-rose-900">Link Unavailable</h2>
          <p className="text-sm text-slate-600 mt-2">{error}</p>
          <p className="text-[11px] text-slate-400 mt-4">Please contact your immigration consultant for a fresh link.</p>
        </Card>
      </div>
    );
  }
  if (submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-emerald-50 to-indigo-50 p-6">
        <Card className="max-w-md p-8 text-center" data-testid="info-sheet-success">
          <CheckCircle2 className="h-16 w-16 text-emerald-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-emerald-900">Thank you!</h2>
          <p className="text-sm text-slate-600 mt-2">Your information has been submitted successfully.</p>
          <p className="text-[11px] text-slate-500 mt-4">
            {linkInfo?.invited_by ? `${linkInfo.invited_by} from your immigration consultancy will review your details and follow up soon.` : 'Your immigration consultant will review your details and follow up soon.'}
          </p>
          <Badge className="mt-4 bg-amber-100 text-amber-700">PENDING REVIEW</Badge>
        </Card>
      </div>
    );
  }

  const isMarried = data.marital_status === 'married' || data.marital_status === 'de_facto';

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-emerald-50 p-4" data-testid="public-info-sheet">
      <div className="max-w-3xl mx-auto py-6">
        {/* Header */}
        <Card className="p-6 mb-4 bg-white" data-testid="info-sheet-header">
          <div className="flex items-center gap-3 mb-2">
            <Sparkles className="h-7 w-7 text-indigo-600" />
            <h1 className="text-2xl font-bold">Immigration Eligibility — Info Sheet</h1>
          </div>
          <p className="text-sm text-slate-600">
            {linkInfo?.invited_by && <>Invited by <strong>{linkInfo.invited_by}</strong>. </>}
            Please fill in your details below. We'll use this to assess your eligibility for permanent residency in your preferred countries.
          </p>
          <p className="text-[11px] text-slate-400 mt-2">Takes ~5 minutes · Auto-saved once submitted</p>
        </Card>

        {/* Section 1: Personal */}
        <Section icon={User} title="1. Personal Information" testid="section-personal">
          <Row>
            <Field label="Full Name *">
              <Input value={data.full_name} onChange={e => update('full_name', e.target.value)} placeholder="As on passport" data-testid="is-full-name" />
            </Field>
            <Field label="Email">
              <Input type="email" value={data.email} onChange={e => update('email', e.target.value)} placeholder="you@example.com" />
            </Field>
          </Row>
          <Row>
            <Field label="Phone">
              <Input value={data.phone} onChange={e => update('phone', e.target.value)} placeholder="+91 98xxxxxxxx" />
            </Field>
            <Field label="Date of Birth">
              <Input type="date" value={data.date_of_birth} onChange={e => update('date_of_birth', e.target.value)} />
            </Field>
          </Row>
          <Row>
            <Field label="Nationality">
              <Input value={data.nationality} onChange={e => update('nationality', e.target.value)} />
            </Field>
            <Field label="Current City">
              <Input value={data.current_city} onChange={e => update('current_city', e.target.value)} placeholder="Mumbai" />
            </Field>
          </Row>
        </Section>

        {/* Section 2: Marital */}
        <Section icon={Heart} title="2. Marital Status" testid="section-marital">
          <Field label="Marital Status *">
            <Select value={data.marital_status} onValueChange={v => update('marital_status', v)}>
              <SelectTrigger data-testid="is-marital-status"><SelectValue placeholder="Select…" /></SelectTrigger>
              <SelectContent>
                {MARITAL_OPTIONS.map(o => <SelectItem key={o.v} value={o.v}>{o.l}</SelectItem>)}
              </SelectContent>
            </Select>
          </Field>
        </Section>

        {/* Section 3: Profession */}
        <Section icon={Briefcase} title="3. Profession & Experience" testid="section-profession">
          <Row>
            <Field label="Current Profession *">
              <Input value={data.current_profession} onChange={e => update('current_profession', e.target.value)} placeholder="e.g., Software Engineer" data-testid="is-current-profession" />
            </Field>
            <Field label="Current Designation">
              <Input value={data.designation} onChange={e => update('designation', e.target.value)} placeholder="e.g., Senior Developer" />
            </Field>
          </Row>
          <Row>
            <Field label="Years of Experience">
              <Input type="number" step="0.5" value={data.years_experience_total} onChange={e => update('years_experience_total', e.target.value)} />
            </Field>
            <Field label="Industry">
              <Input value={data.industry} onChange={e => update('industry', e.target.value)} placeholder="e.g., IT, Marketing" />
            </Field>
          </Row>
          <Field label="Current Employer">
            <Input value={data.employer_name} onChange={e => update('employer_name', e.target.value)} />
          </Field>
        </Section>

        {/* Section 4: Education */}
        <Section icon={GraduationCap} title="4. Education" testid="section-education">
          <Row>
            <Field label="Highest Qualification *">
              <Select value={data.highest_qualification} onValueChange={v => update('highest_qualification', v)}>
                <SelectTrigger data-testid="is-qualification"><SelectValue placeholder="Select…" /></SelectTrigger>
                <SelectContent>
                  {QUALIFICATIONS.map(q => <SelectItem key={q.v} value={q.v}>{q.l}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Field of Study">
              <Input value={data.field_of_study} onChange={e => update('field_of_study', e.target.value)} placeholder="e.g., Computer Science" />
            </Field>
          </Row>
          <Field label="Year Completed">
            <Input type="number" value={data.year_completed} onChange={e => update('year_completed', e.target.value)} placeholder="e.g., 2018" />
          </Field>
        </Section>

        {/* Section 5: Language */}
        <Section icon={MessageSquare} title="5. English Proficiency" testid="section-language">
          <div className="flex items-center gap-3 mb-3">
            <Switch checked={data.language_test_taken} onCheckedChange={v => update('language_test_taken', v)} />
            <Label className="text-sm">I have taken IELTS / PTE / TOEFL</Label>
          </div>
          {data.language_test_taken && (
            <Field label="Overall Score (e.g., IELTS 7.0)">
              <Input type="number" step="0.5" value={data.language_overall_score} onChange={e => update('language_overall_score', e.target.value)} />
            </Field>
          )}
        </Section>

        {/* Section 6: Spouse (conditional) */}
        {isMarried && (
          <Section icon={UsersIcon} title="6. Spouse Information" testid="section-spouse">
            <Row>
              <Field label="Spouse Full Name">
                <Input value={data.spouse_full_name} onChange={e => update('spouse_full_name', e.target.value)} />
              </Field>
              <Field label="Spouse Age">
                <Input type="number" value={data.spouse_age} onChange={e => update('spouse_age', e.target.value)} />
              </Field>
            </Row>
            <Row>
              <Field label="Spouse Profession">
                <Input value={data.spouse_profession} onChange={e => update('spouse_profession', e.target.value)} />
              </Field>
              <Field label="Spouse Education">
                <Select value={data.spouse_education} onValueChange={v => update('spouse_education', v)}>
                  <SelectTrigger><SelectValue placeholder="Select…" /></SelectTrigger>
                  <SelectContent>
                    {QUALIFICATIONS.map(q => <SelectItem key={q.v} value={q.v}>{q.l}</SelectItem>)}
                  </SelectContent>
                </Select>
              </Field>
            </Row>
            <Row>
              <Field label="Spouse IELTS Overall (if any)">
                <Input type="number" step="0.5" value={data.spouse_english_overall} onChange={e => update('spouse_english_overall', e.target.value)} />
              </Field>
              <Field label="Spouse will migrate with you">
                <div className="flex items-center gap-2 mt-2">
                  <Switch checked={data.spouse_on_visa} onCheckedChange={v => update('spouse_on_visa', v)} />
                  <span className="text-xs text-slate-600">{data.spouse_on_visa ? 'Yes' : 'No'}</span>
                </div>
              </Field>
            </Row>
          </Section>
        )}

        {/* Section 7: Preferences */}
        <Section icon={Globe} title="7. Country Preferences" testid="section-preferences">
          <p className="text-[11px] text-slate-500 mb-2">Select countries you're considering (or leave blank if open to all):</p>
          <div className="flex flex-wrap gap-2">
            {COUNTRIES.map(c => (
              <button
                key={c.code}
                onClick={() => toggleCountry(c.code)}
                data-testid={`is-country-${c.code}`}
                className={`px-3 py-1.5 text-xs rounded-full border-2 transition ${
                  data.preferred_countries.includes(c.code)
                    ? 'bg-indigo-100 border-indigo-500 text-indigo-700'
                    : 'bg-white border-slate-200 hover:border-slate-300'
                }`}
              >
                {c.name}
              </button>
            ))}
          </div>
        </Section>

        {/* Submit */}
        <Card className="p-5 bg-gradient-to-r from-indigo-500 to-emerald-500 text-white" data-testid="info-sheet-submit-card">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div>
              <h3 className="font-bold">Ready to submit?</h3>
              <p className="text-[11px] opacity-90 mt-0.5">Your consultant will review and follow up within 24-48 hours.</p>
            </div>
            <Button
              size="lg"
              className="bg-white text-indigo-700 hover:bg-slate-100"
              onClick={submit}
              disabled={submitting}
              data-testid="is-submit-btn"
            >
              {submitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Send className="h-4 w-4 mr-2" />}
              {submitting ? 'Submitting…' : 'Submit Info Sheet'}
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}

function Section({ icon: Icon, title, children, testid }) {
  return (
    <Card className="p-5 mb-3" data-testid={testid}>
      <h2 className="text-sm font-bold flex items-center gap-2 mb-3">
        <Icon className="h-4 w-4 text-indigo-600" />{title}
      </h2>
      <div className="space-y-3">{children}</div>
    </Card>
  );
}

function Row({ children }) {
  return <div className="grid grid-cols-1 md:grid-cols-2 gap-3">{children}</div>;
}

function Field({ label, children }) {
  return (
    <div>
      <Label className="text-[11px] text-slate-600 mb-1 block">{label}</Label>
      {children}
    </div>
  );
}
