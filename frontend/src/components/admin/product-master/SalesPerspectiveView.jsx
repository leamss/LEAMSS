import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Copy, Sparkles, CheckCircle2, AlertTriangle, ArrowUpRight,
  ExternalLink, DollarSign, MessageSquare, Target, UserCheck, HelpCircle,
  Bot, Send, FileQuestion, FileText, CheckCircle, ListChecks, RefreshCw,
  Search, ShieldCheck, ChevronRight, Edit3, Save, Plus, Trash2, X, RotateCcw,
  Check, Zap, Globe, Compass, PhoneCall, Volume2, ShieldAlert, Languages, Layers
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  return `₹${num.toLocaleString('en-IN')}`;
};

function renderFormattedInline(text) {
  if (!text) return null;
  const parts = [];
  const regex = /(\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*|`([^`]+)`)/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }
    if (match[2] && match[3]) {
      parts.push(
        <a
          key={match.index}
          href={match[3]}
          target="_blank"
          rel="noreferrer"
          className="text-indigo-600 hover:text-indigo-800 underline font-semibold inline-flex items-center gap-1"
        >
          {match[2]}
          <ExternalLink className="w-2.5 h-2.5 inline" />
        </a>
      );
    } else if (match[4]) {
      parts.push(
        <strong key={match.index} className="font-extrabold text-slate-900">
          {match[4]}
        </strong>
      );
    } else if (match[5]) {
      parts.push(
        <code key={match.index} className="bg-slate-200 text-slate-800 px-1 py-0.5 rounded text-[11px] font-mono">
          {match[5]}
        </code>
      );
    }
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }
  return parts.length > 0 ? parts : text;
}

export default function SalesPerspectiveView({ product, onSaved, isAdmin = false }) {
  const [copied, setCopied] = useState(false);
  const [objectionSearch, setObjectionSearch] = useState('');
  const [activeTab, setActiveTab] = useState('handbook'); // 'handbook' | 'ai_assistant' | 'eligibility' | 'quote'

  // Admin Pitch Editing State
  const [isEditingPitch, setIsEditingPitch] = useState(false);
  const [savingPitch, setSavingPitch] = useState(false);

  // Editable Pitch Fields
  const [formElevatorPitch, setFormElevatorPitch] = useState('');
  const [formDiscoveryQuestions, setFormDiscoveryQuestions] = useState([]);
  const [formUsps, setFormUsps] = useState([]);
  const [formTargetAudience, setFormTargetAudience] = useState('');
  const [formObjections, setFormObjections] = useState([]);

  // Editable Government Costs, Document Checklist, and FAQs
  const [formGovCosts, setFormGovCosts] = useState({
    currency: 'AUD',
    primary_applicant: 4770,
    secondary_applicant_adult: '',
    secondary_applicant_child: '',
  });
  const [formChecklist, setFormChecklist] = useState([]);
  const [formFaqs, setFormFaqs] = useState([]);

  // Interactive Quick Eligibility Checker state for sales reps on a call
  const [clientAge, setClientAge] = useState(29);
  const [clientExp, setClientExp] = useState(4);
  const [clientIelts, setClientIelts] = useState('7.0');
  const [clientDegree, setClientDegree] = useState('bachelor');

  // AI Visa Assistant / Research state for Sales Rep
  const [aiQuestion, setAiQuestion] = useState('');
  const [aiAnswer, setAiAnswer] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiModel, setAiModel] = useState('');
  const [aiSources, setAiSources] = useState(null);

  // Multi-Language Translation State (English | Marathi | Hindi)
  const [activeLanguage, setActiveLanguage] = useState('English');
  const [originalAiAnswer, setOriginalAiAnswer] = useState('');
  const [translatedAnswers, setTranslatedAnswers] = useState({});
  const [translatingLang, setTranslatingLang] = useState(null);

  const playbook = product?.sales_playbook || {};
  const pitchPoints = playbook?.pitch_points || [];
  const elevatorPitch = playbook?.elevator_pitch || (
    pitchPoints.length > 0
      ? pitchPoints.join(' ')
      : `${product?.name || 'This visa'} provides direct permanent residency with unrestricted work and study rights from day 1, Medicare healthcare access, and a guaranteed pathway to citizenship without employer sponsorship.`
  );

  const baseFee = parseFloat(product?.service_price || product?.base_fee || 0);
  const gstApplicable = product?.gst_applicable !== undefined
    ? Boolean(product?.gst_applicable)
    : (product?.commercials?.gst_applicable !== undefined
        ? Boolean(product?.commercials?.gst_applicable)
        : true);
  const gstAmount = gstApplicable ? Math.round(baseFee * 0.18) : 0;
  const totalWithGst = baseFee + gstAmount;

  const milestones = product?.commercials?.milestones || [
    { milestone_order: 1, name: 'Milestone 1: Retainer & Case Onboarding', percentage: 40, amount: Math.round(baseFee * 0.4) },
    { milestone_order: 2, name: 'Milestone 2: Skills Assessment Filing', percentage: 30, amount: Math.round(baseFee * 0.3) },
    { milestone_order: 3, name: 'Milestone 3: State EOI / Visa Lodgement', percentage: 30, amount: Math.round(baseFee * 0.3) },
  ];

  const objs = product?.objections_rebuttals || [];
  const faqs = product?.faqs || [];
  const govCosts = product?.government_costs || {};
  const checklist = product?.document_checklist_template || [];

  // Sync edit form with current product data
  useEffect(() => {
    if (!product) return;
    const pb = product.sales_playbook || {};
    const defaultPitch = pb.elevator_pitch || (
      (pb.pitch_points || []).length > 0
        ? (pb.pitch_points || []).join(' ')
        : `${product.name || 'This visa'} provides direct permanent residency with unrestricted work and study rights from day 1, Medicare healthcare access, and a guaranteed pathway to citizenship without employer sponsorship.`
    );
    setFormElevatorPitch(defaultPitch);
    setFormDiscoveryQuestions(
      pb.discovery_questions && pb.discovery_questions.length > 0
        ? [...pb.discovery_questions]
        : [
            'What is your target country and timeline for overseas relocation?',
            'Have you or your spouse appeared for an IELTS or PTE examination?',
            'How many years of paid post-qualification experience do you hold?',
            'Has your qualification been assessed by an overseas evaluating authority (ACS, VETASSESS, EA)?',
            'What is your highest degree and was it full-time regular education?',
            'What is your estimated settlement budget for government fees and initial living costs?',
          ]
    );
    setFormUsps(
      (pb.usps && pb.usps.length > 0) ? [...pb.usps] : (
        (pb.key_benefits && pb.key_benefits.length > 0) ? [...pb.key_benefits] : [
          'Direct PR visa with full work and study rights from day 1',
          'Free public healthcare (Medicare) and subsidised schooling',
          'Guaranteed pathway to citizenship after statutory residency',
          'Freedom to live and work anywhere in the country without employer sponsorship',
        ]
      )
    );
    setFormTargetAudience(pb.target_client || pb.target_audience || 'Skilled professionals, engineers, IT, healthcare seeking permanent overseas settlement.');
    setFormObjections(
      (product.objections_rebuttals && product.objections_rebuttals.length > 0)
        ? product.objections_rebuttals.map((o) => ({ ...o }))
        : [
            { objection: 'The consultancy fee is higher than local agents.', rebuttal: 'LEAMSS provides MARA/statutory-licensed supervision, zero hidden charges, and a contractually guaranteed refund milestone.' },
            { objection: 'Processing time is too long; I want immediate visa.', rebuttal: 'Statutory processing times are set by destination governments; our pre-lodgement vetting eliminates RFI delays by 45%.' }
          ]
    );

    // Sync Government Costs
    const gc = product.government_costs || {};
    setFormGovCosts({
      currency: gc.currency || 'AUD',
      primary_applicant: gc.primary_applicant != null ? gc.primary_applicant : 4770,
      secondary_applicant_adult: gc.secondary_applicant_adult != null ? gc.secondary_applicant_adult : '',
      secondary_applicant_child: gc.secondary_applicant_child != null ? gc.secondary_applicant_child : '',
    });

    // Sync Document Checklist
    const chk = product.document_checklist_template || [];
    setFormChecklist(
      chk.length > 0
        ? chk.map((item) => ({
            document_name: item.document_name || item.name || '',
            description: item.description || ''
          }))
        : [
            { document_name: 'Valid Passport (Current & Previous)', description: 'Color bio-data copy' },
            { document_name: 'Degree Certificates & Transcripts', description: 'Consolidated semester marks' },
            { document_name: 'Reference Letters & Work Experience', description: 'Roles on company letterhead' },
            { document_name: 'Last 3-6 Months Pay Slips & Form 16 / ITR', description: 'Proof of paid employment' },
            { document_name: 'English Scorecard (IELTS / PTE)', description: 'Valid scorecard' },
          ]
    );

    // Sync FAQs
    const fqs = product.faqs || [];
    setFormFaqs(
      fqs.length > 0
        ? fqs.map((f) => ({ question: f.question || '', answer: f.answer || '' }))
        : [
            { question: `Can I bring my spouse and dependent children under ${product.name || 'this visa'}?`, answer: 'Yes. All dependent family members are granted identical Permanent Residency status with Medicare and work rights.' },
            { question: 'How long is the initial visa valid and how does citizenship work?', answer: 'The initial travel facility is valid for 5 years, after which a Resident Return Visa is issued if residency requirements are met.' },
          ]
    );
  }, [product, isEditingPitch]);

  const copyPitch = () => {
    navigator.clipboard.writeText(elevatorPitch);
    setCopied(true);
    toast.success('Elevator pitch copied to clipboard!');
    setTimeout(() => setCopied(false), 2000);
  };

  const copyMigrateLink = () => {
    if (!product?.migrate_page_url) {
      toast.info('No migrate page URL configured for this product');
      return;
    }
    navigator.clipboard.writeText(product.migrate_page_url);
    toast.success('Official migrate link copied!');
  };

  const copyText = (text, label) => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied to clipboard!`);
  };

  // Admin Pitch Edit Handlers
  const handleSaveSalesPitch = async () => {
    if (!product?.id) return;
    setSavingPitch(true);
    try {
      const token = localStorage.getItem('token');
      const headers = token ? { Authorization: `Bearer ${token}` } : {};

      const cleanPitch = formElevatorPitch.trim();
      const payload = {
        elevator_pitch: cleanPitch,
        pitch_points: cleanPitch ? cleanPitch.split('. ').filter(Boolean) : [],
        target_audience: formTargetAudience.trim(),
        target_client: formTargetAudience.trim(),
        usps: formUsps.filter((u) => u.trim()),
        discovery_questions: formDiscoveryQuestions.filter((q) => q.trim()),
        objections_rebuttals: formObjections.filter((o) => (o.objection || '').trim() || (o.rebuttal || '').trim()),
        government_costs: {
          currency: (formGovCosts.currency || 'AUD').trim().toUpperCase(),
          primary_applicant: parseFloat(formGovCosts.primary_applicant) || 0,
          secondary_applicant_adult: formGovCosts.secondary_applicant_adult ? parseFloat(formGovCosts.secondary_applicant_adult) : undefined,
          secondary_applicant_child: formGovCosts.secondary_applicant_child ? parseFloat(formGovCosts.secondary_applicant_child) : undefined,
        },
        document_checklist_template: formChecklist.filter((d) => (d.document_name || '').trim()),
        faqs: formFaqs.filter((f) => (f.question || '').trim() || (f.answer || '').trim()),
      };

      await axios.patch(`${API}/product-master/${product.id}/sales-pitch`, payload, { headers });
      toast.success('Sales pitch and product data updated! Changes are now live for all salespersons.');
      setIsEditingPitch(false);
      if (onSaved) onSaved();
    } catch (err) {
      console.error('Error saving sales pitch:', err);
      toast.error(err.response?.data?.detail || 'Failed to save sales pitch');
    } finally {
      setSavingPitch(false);
    }
  };

  const handleAddDiscoveryQuestion = () => {
    setFormDiscoveryQuestions([...formDiscoveryQuestions, '']);
  };

  const handleUpdateDiscoveryQuestion = (index, value) => {
    const next = [...formDiscoveryQuestions];
    next[index] = value;
    setFormDiscoveryQuestions(next);
  };

  const handleRemoveDiscoveryQuestion = (index) => {
    setFormDiscoveryQuestions(formDiscoveryQuestions.filter((_, i) => i !== index));
  };

  const handleAddUsp = () => {
    setFormUsps([...formUsps, '']);
  };

  const handleUpdateUsp = (index, value) => {
    const next = [...formUsps];
    next[index] = value;
    setFormUsps(next);
  };

  const handleRemoveUsp = (index) => {
    setFormUsps(formUsps.filter((_, i) => i !== index));
  };

  const handleAddObjection = () => {
    setFormObjections([...formObjections, { objection: '', rebuttal: '' }]);
  };

  const handleUpdateObjection = (index, field, value) => {
    const next = [...formObjections];
    next[index] = { ...next[index], [field]: value };
    setFormObjections(next);
  };

  const handleRemoveObjection = (index) => {
    setFormObjections(formObjections.filter((_, i) => i !== index));
  };

  // Checklist Handlers
  const handleAddChecklistItem = () => {
    setFormChecklist([...formChecklist, { document_name: '', description: '' }]);
  };

  const handleUpdateChecklistItem = (index, field, value) => {
    const next = [...formChecklist];
    next[index] = { ...next[index], [field]: value };
    setFormChecklist(next);
  };

  const handleRemoveChecklistItem = (index) => {
    setFormChecklist(formChecklist.filter((_, i) => i !== index));
  };

  // FAQ Handlers
  const handleAddFaq = () => {
    setFormFaqs([...formFaqs, { question: '', answer: '' }]);
  };

  const handleUpdateFaq = (index, field, value) => {
    const next = [...formFaqs];
    next[index] = { ...next[index], [field]: value };
    setFormFaqs(next);
  };

  const handleRemoveFaq = (index) => {
    setFormFaqs(formFaqs.filter((_, i) => i !== index));
  };

  // Quick eligibility calculation
  const pointsTested = product?.eligibility_criteria?.points_based?.is_points_tested;
  const minPoints = product?.eligibility_criteria?.points_based?.minimum_points || 65;

  let estPoints = 0;
  if (clientAge >= 25 && clientAge < 33) estPoints += 30;
  else if (clientAge >= 18 && clientAge < 25) estPoints += 25;
  else if (clientAge >= 33 && clientAge < 40) estPoints += 25;
  else if (clientAge >= 40 && clientAge < 45) estPoints += 15;

  if (clientIelts === '8.0') estPoints += 20;
  else if (clientIelts === '7.0') estPoints += 10;

  if (clientDegree === 'phd') estPoints += 20;
  else if (clientDegree === 'master' || clientDegree === 'bachelor') estPoints += 15;

  if (clientExp >= 8) estPoints += 15;
  else if (clientExp >= 5) estPoints += 10;
  else if (clientExp >= 3) estPoints += 5;

  const qualifies = !pointsTested || estPoints >= minPoints;

  const filteredObjs = objs.filter((o) => {
    if (!objectionSearch.trim()) return true;
    const q = objectionSearch.toLowerCase();
    return (o.objection || '').toLowerCase().includes(q) || (o.rebuttal || '').toLowerCase().includes(q);
  });

  // Handle AI Visa Consultation Query
  const handleAskAi = async (customPrompt) => {
    const q = (customPrompt || aiQuestion).trim();
    if (!q) {
      toast.error('Please enter a question or client scenario');
      return;
    }
    setAiLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await axios.post(
        `${API}/product-master/sales-ai-query`,
        {
          country: product?.country || '',
          visa_name: product?.name || '',
          visa_subclass: product?.visa_subclass || '',
          client_scenario_or_question: q,
        },
        { headers }
      );
      const rawAns = res.data.answer;
      setAiAnswer(rawAns);
      setOriginalAiAnswer(rawAns);
      setAiModel(res.data.model || 'sonar');
      setAiSources(res.data.sources || null);

      // Detect initial answer language
      const hasDevanagari = /[\u0900-\u097F]/.test(rawAns);
      let initialLang = 'English';
      if (hasDevanagari) {
        const isMarathi = /\b(?:आहे|नाही|करावे|साठी|मध्ये|मिळेल|लागेल|करा|कसा|काय|यावे)\b/.test(rawAns);
        initialLang = isMarathi ? 'Marathi' : 'Hindi';
      }
      setActiveLanguage(initialLang);
      setTranslatedAnswers({ [initialLang]: rawAns });

      toast.success('AI advice generated for client call!');
    } catch (err) {
      console.error('AI query error:', err);
      const detail = err.response?.data?.detail || err.message || 'AI query failed';
      toast.error(`AI Assistant error: ${detail}`);
    } finally {
      setAiLoading(false);
    }
  };

  // Instant Multi-Language Translation Handler (English | Marathi | Hindi)
  const handleSelectLanguage = async (targetLang) => {
    if (activeLanguage === targetLang) return;
    const currentBase = originalAiAnswer || aiAnswer;
    if (!currentBase) return;

    if (translatedAnswers[targetLang]) {
      setAiAnswer(translatedAnswers[targetLang]);
      setActiveLanguage(targetLang);
      toast.success(`Switched to ${targetLang}!`);
      return;
    }

    setTranslatingLang(targetLang);
    try {
      const token = localStorage.getItem('token');
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await axios.post(
        `${API}/product-master/sales-ai-translate`,
        {
          text: currentBase,
          target_language: targetLang,
          source_language: activeLanguage,
          country: product?.country || '',
          visa_subclass: product?.visa_subclass || '',
        },
        { headers }
      );
      const translated = res.data?.translated_text || currentBase;
      setTranslatedAnswers((prev) => ({
        ...prev,
        [targetLang]: translated,
      }));
      setAiAnswer(translated);
      setActiveLanguage(targetLang);
      toast.success(`Answer translated to ${targetLang}!`);
    } catch (err) {
      console.error('Translation error:', err);
      toast.error(`Translation error: ${err.response?.data?.detail || err.message}`);
    } finally {
      setTranslatingLang(null);
    }
  };

  // Pre-configured questions to quickly trigger AI assistant
  const sampleAiQueries = [
    `Client is 39 yrs old, 7 yrs IT experience, IELTS 7.0. Can they qualify for ${product?.visa_subclass ? `Subclass ${product.visa_subclass}` : product?.name}?`,
    `Client says processing time is too long and wants a fast-track option. How should I pitch?`,
    `Client is comparing our price with local agents who charge less. What is the best rebuttal?`,
    `Can candidate include spouse and children? What are the English and medical requirements for family?`,
  ];

  return (
    <div className="space-y-4 text-xs">
      {/* ───────────────────────────────────────────────────────────── */}
      {/* ADMIN EDITING NOTIFICATION BANNER                             */}
      {/* ───────────────────────────────────────────────────────────── */}
      {isEditingPitch && (
        <div className="p-3 bg-blue-50 border-2 border-blue-400 rounded-xl flex items-center justify-between flex-wrap gap-2 shadow-xs">
          <div className="flex items-center gap-2">
            <span className="p-1 rounded-full bg-blue-600 text-white">
              <Edit3 className="h-3.5 w-3.5" />
            </span>
            <div>
              <p className="text-xs font-bold text-blue-950">
                Admin Pitch & Product Editing Mode • {product?.name}
              </p>
              <p className="text-[11px] text-blue-700">
                You can edit the Elevator Pitch, Discovery Questions, USPs, Government Fees, Checklist, Objections & FAQs. Changes sync immediately to Salespersons.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsEditingPitch(false)}
              disabled={savingPitch}
              className="h-8 text-xs bg-white text-slate-700 hover:bg-slate-100 border-slate-300 font-semibold"
            >
              <X className="h-3.5 w-3.5 mr-1" />
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleSaveSalesPitch}
              disabled={savingPitch}
              className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-bold gap-1.5 shadow"
              data-testid="save-sales-pitch-top-btn"
            >
              {savingPitch ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-3.5 w-3.5" />
                  Save Pitch Changes
                </>
              )}
            </Button>
          </div>
        </div>
      )}

      {/* ───────────────────────────────────────────────────────────── */}
      {/* TOP ELEVATOR PITCH BANNER WITH 1-CLICK COPY / EDIT            */}
      {/* ───────────────────────────────────────────────────────────── */}
      <Card className="p-4 bg-gradient-to-r from-amber-500/15 via-emerald-500/10 to-blue-500/10 border-2 border-amber-300 shadow-sm space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-amber-600" />
            <div>
              <h2 className="text-base font-extrabold text-slate-900">
                Client Call Elevator Pitch • {product?.name}
              </h2>
              <p className="text-[11px] text-slate-500">
                {isEditingPitch ? 'Write the exact script salespersons should read on client consultation calls.' : 'Read or adapt this 30-second script during consultation calls.'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {isAdmin && !isEditingPitch && (
              <Button
                size="sm"
                onClick={() => setIsEditingPitch(true)}
                className="h-8 text-xs bg-blue-600 hover:bg-blue-700 text-white font-bold gap-1.5 shadow"
                data-testid="admin-edit-pitch-btn"
              >
                <Edit3 className="h-3.5 w-3.5" />
                Edit Sales Pitch
              </Button>
            )}

            {isEditingPitch && (
              <Button
                size="sm"
                onClick={handleSaveSalesPitch}
                disabled={savingPitch}
                className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-bold gap-1.5 shadow"
              >
                {savingPitch ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                Save Pitch
              </Button>
            )}

            {product?.migrate_page_url && (
              <Button
                size="sm"
                variant="outline"
                onClick={copyMigrateLink}
                className="h-8 text-xs bg-white text-blue-700 hover:bg-blue-50 border-blue-300 gap-1 font-semibold"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                Copy Migrate Link
              </Button>
            )}

            {!isEditingPitch && (
              <Button
                size="sm"
                onClick={copyPitch}
                className="h-8 text-xs bg-amber-600 hover:bg-amber-700 text-white font-bold gap-1.5 shadow"
                data-testid="sales-copy-pitch-btn"
              >
                <Copy className="h-3.5 w-3.5" />
                {copied ? 'Copied!' : 'Copy Elevator Pitch'}
              </Button>
            )}
          </div>
        </div>

        {isEditingPitch ? (
          <div className="p-3 bg-white rounded-lg border-2 border-amber-300 space-y-2 shadow-inner">
            <div className="flex items-center justify-between">
              <Label className="text-xs font-bold text-amber-900 flex items-center gap-1.5">
                <Edit3 className="h-3.5 w-3.5 text-amber-600" />
                30-Second Elevator Pitch Script (Admin Input):
              </Label>
              <span className="text-[10px] text-slate-400 font-medium">
                {formElevatorPitch.split(/\s+/).filter(Boolean).length} words • {formElevatorPitch.length} characters
              </span>
            </div>
            <Textarea
              rows={3}
              value={formElevatorPitch}
              onChange={(e) => setFormElevatorPitch(e.target.value)}
              placeholder="Write the 30-second telephone pitch script that salespersons will read to prospects..."
              className="text-xs font-medium border-amber-200 focus:border-amber-500 leading-relaxed bg-amber-50/20"
              data-testid="admin-input-elevator-pitch"
            />
            <p className="text-[10px] text-slate-500 italic">
              💡 Tip: Keep it under 60 words for quick phone delivery. Mention PR status, work rights, and fast qualification.
            </p>
          </div>
        ) : (
          <div className="p-3 bg-white/95 rounded-lg border border-amber-200 text-slate-900 text-xs font-semibold leading-relaxed shadow-inner">
            "{elevatorPitch}"
          </div>
        )}
      </Card>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* INTERACTIVE AI VISA COPILOT & CLIENT QUERY ASSISTANT          */}
      {/* ───────────────────────────────────────────────────────────── */}
      <Card className="p-4 bg-gradient-to-br from-indigo-50/70 via-white to-purple-50/70 border-2 border-indigo-200 shadow-sm space-y-3">
        <div className="flex items-center justify-between gap-2 pb-2 border-b border-indigo-100 flex-wrap">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-indigo-600 text-white">
              <Bot className="h-4 w-4" />
            </div>
            <div>
              <h3 className="font-extrabold text-slate-900 text-sm flex items-center gap-1.5">
                AI Visa Pitch Copilot & Client Query Assistant
                <Badge className="bg-indigo-100 text-indigo-800 text-[10px] font-bold">Live AI Research</Badge>
              </h3>
              <p className="text-[11px] text-slate-500">
                Ask any question or client scenario during a call to receive verified regulatory facts, point evaluations, and telephone pitch scripts.
              </p>
            </div>
          </div>
          {aiAnswer && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setAiAnswer('');
                setAiQuestion('');
              }}
              className="h-7 text-xs text-slate-500"
            >
              Clear Answer
            </Button>
          )}
        </div>

        {/* Input box */}
        <div className="space-y-2">
          <div className="flex gap-2">
            <Input
              placeholder={`Ask anything about ${product?.visa_subclass ? `Subclass ${product.visa_subclass}` : product?.name} (e.g. client age 42 with 8 yrs exp, fee objections, state pathways)...`}
              value={aiQuestion}
              onChange={(e) => setAiQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleAskAi();
                }
              }}
              className="text-xs h-9 bg-white border-indigo-200 focus:border-indigo-500"
            />
            <Button
              onClick={() => handleAskAi()}
              disabled={aiLoading}
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold gap-1.5 h-9 shrink-0 shadow-sm px-4"
              data-testid="sales-ai-ask-btn"
            >
              {aiLoading ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  Researching...
                </>
              ) : (
                <>
                  <Send className="h-3.5 w-3.5" />
                  Ask AI
                </>
              )}
            </Button>
          </div>

          {/* Quick-Prompt Suggestion Chips */}
          <div className="flex items-center gap-1.5 flex-wrap pt-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 shrink-0">Quick Scenarios:</span>
            {sampleAiQueries.map((q, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setAiQuestion(q);
                  handleAskAi(q);
                }}
                disabled={aiLoading}
                className="text-[10px] px-2 py-0.5 rounded-full bg-white hover:bg-indigo-50 text-indigo-700 border border-indigo-200 transition font-medium truncate max-w-xs"
                title={q}
              >
                💡 {q}
              </button>
            ))}
          </div>
        </div>

        {/* AI Answer Display */}
        {aiAnswer && (
          <div className="mt-3 p-3.5 bg-white rounded-xl border border-indigo-200 shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-100 flex-wrap gap-2">
              <span className="text-[11px] font-bold text-indigo-900 flex items-center gap-1">
                <Sparkles className="h-3.5 w-3.5 text-indigo-600" />
                AI Assistant Recommendation (Official Regulatory Fact Check):
              </span>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-[9px] font-mono text-slate-500">
                  Model: {aiModel || 'sonar'}
                </Badge>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => copyText(aiAnswer, 'AI response')}
                  className="h-6 px-2 text-[11px] text-indigo-600 hover:bg-indigo-50 gap-1 font-semibold"
                >
                  <Copy className="h-3 w-3" />
                  Copy Talking Point
                </Button>
                <button
                  onClick={() => {
                    setAiAnswer('');
                    setOriginalAiAnswer('');
                    setTranslatedAnswers({});
                    setActiveLanguage('English');
                  }}
                  className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                  title="Dismiss"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Multi-Language Translation Toggle (English | Marathi | Hindi) */}
            <div className="flex flex-wrap items-center justify-between gap-2 p-2 bg-gradient-to-r from-indigo-50/80 via-purple-50/50 to-indigo-50/80 border border-indigo-200 rounded-lg">
              <div className="flex items-center gap-1.5">
                <Languages className="w-3.5 h-3.5 text-indigo-700" />
                <span className="text-[11px] font-bold text-slate-800">Translate Answer:</span>
                <span className="text-[10px] text-slate-500 hidden sm:inline">(Instant translation into English, Marathi, or Hindi)</span>
              </div>
              <div className="flex items-center gap-1">
                {[
                  { id: 'English', label: 'English', flag: '🇬🇧' },
                  { id: 'Marathi', label: 'मराठी (Marathi)', flag: '🇮🇳' },
                  { id: 'Hindi', label: 'हिंदी (Hindi)', flag: '🇮🇳' },
                ].map((l) => {
                  const isSelected = activeLanguage === l.id;
                  const isLoading = translatingLang === l.id;
                  return (
                    <button
                      key={l.id}
                      onClick={() => handleSelectLanguage(l.id)}
                      disabled={translatingLang !== null}
                      className={`px-2.5 py-1 rounded text-[11px] font-bold transition flex items-center gap-1 cursor-pointer ${
                        isSelected
                          ? 'bg-indigo-700 text-white shadow-2xs'
                          : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-100'
                      }`}
                    >
                      <span>{l.flag}</span>
                      <span>{l.label}</span>
                      {isLoading && <RefreshCw className="w-3 h-3 animate-spin text-indigo-700" />}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Verified Sources Pill Bar */}
            {aiSources && (
              <div className="flex flex-wrap items-center gap-1.5 p-2 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1 mr-1">
                  <ShieldCheck className="w-3 h-3 text-emerald-600" /> Sources:
                </span>
                {aiSources.government_portal && (
                  <a
                    href={aiSources.government_portal}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 text-[10px] font-bold text-emerald-800 transition"
                  >
                    <Globe className="w-2.5 h-2.5 text-emerald-600" />
                    Gov Portal ({aiSources.government_authority || 'Authority'})
                    <ExternalLink className="w-2 h-2 opacity-70" />
                  </a>
                )}
                {aiSources.migrate_page_url && (
                  <a
                    href={aiSources.migrate_page_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-50 hover:bg-blue-100 border border-blue-300 text-[10px] font-bold text-blue-800 transition"
                  >
                    <Globe className="w-2.5 h-2.5 text-blue-600" />
                    LEAMSS Migrate
                    <ExternalLink className="w-2 h-2 opacity-70" />
                  </a>
                )}
                {aiSources.atlas_page_url && (
                  <a
                    href={aiSources.atlas_page_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-purple-50 hover:bg-purple-100 border border-purple-300 text-[10px] font-bold text-purple-800 transition"
                  >
                    <Compass className="w-2.5 h-2.5 text-purple-600" />
                    Migration Atlas
                    <ExternalLink className="w-2 h-2 opacity-70" />
                  </a>
                )}
              </div>
            )}

            {/* Structured Content Blocks */}
            <div className="space-y-3">
              {aiAnswer
                .replace(/\n*[_*]*Sources(?:\s*\(.*?\))?:?[_*]*\s*\n+(?:[-*]\s*https?:\/\/\S+\n*)+/gi, '')
                .replace(/\n*### 🔗\s*(?:6\.)?[\s\S]*?(?=\n*###|\n*>|\Z)/gi, '')
                .split(/(?:\n|^)(?=###\s+|> \*\*LEAMSS Statutory Disclaimer|\[!NOTE\])/)
                .map((block, bIdx) => {
                  const trimmed = block.trim();
                  if (!trimmed) return null;

                  // Filter out raw sources or URL lines
                  if (
                    trimmed.toLowerCase().startsWith('_sources') ||
                    trimmed.toLowerCase().startsWith('sources:') ||
                    trimmed.startsWith('http://') ||
                    trimmed.startsWith('https://')
                  ) {
                    return null;
                  }

                  // 1. Speaking Script Block (Section 1 - Primary Callout)
                  if (
                    trimmed.includes('Speaking Script') ||
                    trimmed.includes('Recommended Phone Pitch') ||
                    trimmed.includes('Recommended Call Script') ||
                    trimmed.startsWith('### 💬 1') ||
                    trimmed.startsWith('### 💬')
                  ) {
                    const lines = trimmed.split('\n');
                    const contentLines = lines.slice(1).filter((l) => l.trim().length > 0);
                    const scriptLines = contentLines.filter(
                      (l) => !l.trim().startsWith('- ') && !l.trim().startsWith('* ')
                    );
                    const rawScript = (scriptLines.length > 0 ? scriptLines : contentLines)
                      .join(' ')
                      .replace(/^>\s*/gm, '')
                      .replace(/^[*_"\s]+|[*_"\s]+$/g, '')
                      .trim();
                    const displayScript = rawScript || 'Review statutory eligibility criteria with the client.';

                    const otherLines = contentLines.filter((l) => l.trim().startsWith('- ') || l.trim().startsWith('* '));

                    return (
                      <div
                        key={bIdx}
                        className="p-3.5 bg-gradient-to-r from-emerald-50 via-teal-50 to-emerald-50/80 border-2 border-emerald-500 rounded-xl shadow-xs space-y-2.5"
                      >
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <span className="text-xs font-black text-emerald-950 uppercase tracking-wide flex items-center gap-1.5">
                            <PhoneCall className="w-3.5 h-3.5 text-emerald-600" />
                            Live Call Speaking Script (Read to Client)
                          </span>
                          <button
                            onClick={() => copyText(displayScript, 'Speaking Script')}
                            className="px-2.5 py-0.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded text-[11px] font-bold flex items-center gap-1 shadow-xs transition"
                          >
                            <Copy className="w-3 h-3" /> Copy Script
                          </button>
                        </div>
                        <div className="p-2.5 bg-white rounded-lg border border-emerald-200/80">
                          <p className="font-semibold text-emerald-950 text-xs leading-relaxed italic">
                            "{displayScript}"
                          </p>
                        </div>
                        {otherLines.length > 0 && (
                          <div className="space-y-1 pt-0.5">
                            {otherLines.map((ol, oIdx) => (
                              <div key={oIdx} className="text-[11px] text-slate-700 font-medium">
                                {renderFormattedInline(ol)}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  }

                  // 2. Direct Quick Answer & Key Facts Card
                  if (
                    trimmed.includes('Direct Quick Answer') ||
                    trimmed.includes('⚡ Quick Answer') ||
                    trimmed.includes('Key Facts & Eligibility')
                  ) {
                    const lines = trimmed.split('\n');
                    const heading = lines[0].replace(/^###\s*/, '');
                    const contentLines = lines.slice(1).filter((l) => l.trim().length > 0);
                    const plainContent = contentLines.map((l) => l.replace(/^[-*]\s*/, '')).join(' ');

                    return (
                      <div
                        key={bIdx}
                        className="p-3 bg-gradient-to-r from-sky-50 via-indigo-50/40 to-sky-50 border-2 border-sky-300 rounded-xl shadow-xs space-y-2"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-black text-slate-900 flex items-center gap-1.5">
                            <Zap className="w-3.5 h-3.5 text-sky-600 fill-sky-500" />
                            {heading}
                          </span>
                          <button
                            onClick={() => copyText(plainContent, 'Quick Facts')}
                            className="px-2 py-0.5 bg-sky-600 hover:bg-sky-700 text-white rounded text-[10px] font-bold flex items-center gap-1 shadow-xs transition"
                          >
                            <Copy className="w-2.5 h-2.5" /> Copy Facts
                          </button>
                        </div>
                        <ul className="space-y-1 pl-1">
                          {contentLines.map((cl, cIdx) => (
                            <li key={cIdx} className="text-xs font-medium text-slate-800 flex items-start gap-1.5">
                              <CheckCircle2 className="w-3.5 h-3.5 text-sky-600 shrink-0 mt-0.5" />
                              <span>{renderFormattedInline(cl.replace(/^[-*]\s*/, ''))}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    );
                  }

                  // 3. Statutory Compliance Disclaimer Block
                  if (
                    trimmed.includes('Statutory Disclaimer') ||
                    trimmed.includes('LEAMSS Statutory Disclaimer') ||
                    trimmed.includes('[!NOTE]')
                  ) {
                    const cleanDisclaimer = trimmed
                      .replace(/\[!NOTE\]\s*/g, '')
                      .replace(/^>\s*/gm, '')
                      .replace(/\*\*/g, '')
                      .trim();
                    return (
                      <div
                        key={bIdx}
                        className="p-2.5 bg-slate-100 rounded-lg border border-slate-200 text-slate-600 text-[11px] flex items-start gap-2 leading-relaxed"
                      >
                        <ShieldAlert className="w-3.5 h-3.5 text-slate-500 shrink-0 mt-0.5" />
                        <div>
                          <strong className="text-slate-800">LEAMSS Statutory Compliance:</strong>{' '}
                          {cleanDisclaimer.replace(/^LEAMSS Statutory Disclaimer:\s*/i, '')}
                        </div>
                      </div>
                    );
                  }

                  // 4. Standard Section Block (###)
                  if (trimmed.startsWith('###')) {
                    const lines = trimmed.split('\n');
                    const heading = lines[0].replace(/^###\s*/, '');

                    return (
                      <div key={bIdx} className="p-3 bg-slate-50/80 rounded-lg border border-slate-200 space-y-1.5">
                        <h5 className="font-extrabold text-slate-900 text-xs flex items-center gap-1.5">
                          {renderFormattedInline(heading)}
                        </h5>
                        <div className="text-xs text-slate-700 space-y-1 pl-1">
                          {lines.slice(1).map((subLine, sIdx) => {
                            const sl = subLine.trim();
                            if (!sl) return null;
                            if (sl.startsWith('- ') || sl.startsWith('* ')) {
                              return (
                                <div key={sIdx} className="flex items-start gap-1.5 py-0.5">
                                  <span className="text-indigo-600 font-bold shrink-0">•</span>
                                  <span className="leading-snug">{renderFormattedInline(sl.replace(/^[-*]\s*/, ''))}</span>
                                </div>
                              );
                            }
                            return (
                              <p key={sIdx} className="leading-relaxed">
                                {renderFormattedInline(sl)}
                              </p>
                            );
                          })}
                        </div>
                      </div>
                    );
                  }

                  return (
                    <p key={bIdx} className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                      {renderFormattedInline(trimmed)}
                    </p>
                  );
                })}
            </div>
          </div>
        )}
      </Card>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* QUICK ELIGIBILITY CHECKER WIDGET FOR PHONE CALLS              */}
      {/* ───────────────────────────────────────────────────────────── */}
      <Card className="p-4 bg-white border border-slate-200 space-y-3">
        <div className="flex items-center justify-between pb-2 border-b">
          <div className="flex items-center gap-2">
            <UserCheck className="h-4 w-4 text-emerald-600" />
            <h3 className="font-extrabold text-slate-900 text-sm">Live Call Eligibility Quick-Checker</h3>
          </div>
          {pointsTested ? (
            <Badge className={qualifies ? 'bg-emerald-100 text-emerald-800 font-bold' : 'bg-rose-100 text-rose-800 font-bold'}>
              Est. Score: {estPoints} / {minPoints} pts required ({qualifies ? 'Pass' : 'Gap to bridge'})
            </Badge>
          ) : (
            <Badge className="bg-blue-100 text-blue-800 font-bold">Direct Criteria Check</Badge>
          )}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <Label className="text-[10px] text-slate-500 font-bold">Client Age ({clientAge} yrs)</Label>
            <Input
              type="number"
              value={clientAge}
              onChange={(e) => setClientAge(parseInt(e.target.value) || 0)}
              className="h-8 text-xs mt-1 font-bold"
            />
          </div>

          <div>
            <Label className="text-[10px] text-slate-500 font-bold">Years Experience</Label>
            <Input
              type="number"
              value={clientExp}
              onChange={(e) => setClientExp(parseFloat(e.target.value) || 0)}
              className="h-8 text-xs mt-1 font-bold"
            />
          </div>

          <div>
            <Label className="text-[10px] text-slate-500 font-bold">English Score</Label>
            <select
              value={clientIelts}
              onChange={(e) => setClientIelts(e.target.value)}
              className="mt-1 flex h-8 w-full rounded border border-input bg-white px-2 text-xs font-bold"
            >
              <option value="6.0">IELTS 6.0 / PTE 50 (Competent - 0 pts)</option>
              <option value="7.0">IELTS 7.0 / PTE 65 (Proficient - 10 pts)</option>
              <option value="8.0">IELTS 8.0 / PTE 79 (Superior - 20 pts)</option>
            </select>
          </div>

          <div>
            <Label className="text-[10px] text-slate-500 font-bold">Highest Qualification</Label>
            <select
              value={clientDegree}
              onChange={(e) => setClientDegree(e.target.value)}
              className="mt-1 flex h-8 w-full rounded border border-input bg-white px-2 text-xs font-bold"
            >
              <option value="bachelor">Bachelor's Degree (15 pts)</option>
              <option value="master">Master's Degree (15 pts)</option>
              <option value="phd">PhD / Doctorate (20 pts)</option>
              <option value="diploma">Trade Diploma (10 pts)</option>
            </select>
          </div>
        </div>

        <div className="p-2.5 bg-slate-50 border rounded text-[11px] flex items-center justify-between">
          <span className="text-slate-600 font-medium">
            {qualifies
              ? '✅ Candidate meets primary statutory threshold! Proceed with booking case assessment.'
              : '⚠️ Candidate currently has a points gap. Suggest state nomination (190: +5 pts, 491: +15 pts) or IELTS 8+ coaching.'}
          </span>
          <span className="font-bold text-slate-800">Target: {minPoints}+ points</span>
        </div>
      </Card>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 2-COLUMN: DISCOVERY QUESTIONS & USPs                          */}
      {/* ───────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Normal Client Discovery Questions */}
        <Card className="p-4 bg-white border border-slate-200 space-y-2.5">
          <div className="flex items-center justify-between pb-1.5 border-b">
            <h4 className="font-bold text-slate-900 flex items-center gap-1.5 text-xs">
              <MessageSquare className="h-4 w-4 text-blue-600" />
              Standard Client Discovery Questions
            </h4>
            {isEditingPitch ? (
              <Button
                size="sm"
                variant="outline"
                onClick={handleAddDiscoveryQuestion}
                className="h-6 text-[10px] gap-1 font-bold text-blue-700 bg-blue-50 border-blue-200 hover:bg-blue-100"
              >
                <Plus className="h-3 w-3" />
                Add Question
              </Button>
            ) : (
              <Badge variant="outline" className="text-[9px] font-bold">Ask on Call</Badge>
            )}
          </div>

          {isEditingPitch ? (
            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {formDiscoveryQuestions.map((q, idx) => (
                <div key={idx} className="flex items-center gap-1.5">
                  <span className="font-bold text-blue-700 text-xs w-5 shrink-0">{idx + 1}.</span>
                  <Input
                    value={q}
                    onChange={(e) => handleUpdateDiscoveryQuestion(idx, e.target.value)}
                    placeholder="Enter discovery question for sales reps to ask..."
                    className="h-7 text-xs flex-1 border-blue-200"
                  />
                  <button
                    onClick={() => handleRemoveDiscoveryQuestion(idx)}
                    className="p-1 rounded text-rose-500 hover:bg-rose-50 shrink-0"
                    title="Remove question"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
              {formDiscoveryQuestions.length === 0 && (
                <p className="text-[11px] text-slate-400 italic">No questions added yet. Click "+ Add Question" above.</p>
              )}
            </div>
          ) : (
            <div className="space-y-1.5">
              {(playbook?.discovery_questions || [
                'What is your target country and timeline for overseas relocation?',
                'Have you or your spouse appeared for an IELTS or PTE examination?',
                'How many years of paid post-qualification experience do you hold?',
                'Has your qualification been assessed by an overseas evaluating authority (ACS, VETASSESS, EA)?',
                'What is your highest degree and was it full-time regular education?',
                'What is your estimated settlement budget for government fees and initial living costs?',
              ]).map((q, idx) => (
                <div
                  key={idx}
                  className="group p-2 bg-blue-50/40 hover:bg-blue-50 border border-blue-100 rounded text-[11px] text-slate-800 flex items-center justify-between gap-2 transition"
                >
                  <div className="flex items-start gap-1.5 min-w-0">
                    <span className="font-bold text-blue-700 shrink-0">{idx + 1}.</span>
                    <span className="font-medium">{q}</span>
                  </div>
                  <button
                    onClick={() => copyText(q, 'Question')}
                    className="p-1 rounded hover:bg-blue-100 text-blue-600 opacity-60 group-hover:opacity-100 transition shrink-0"
                    title="Copy question"
                  >
                    <Copy className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* USPs & Ideal Client Profile */}
        <Card className="p-4 bg-white border border-slate-200 space-y-2.5">
          <div className="flex items-center justify-between pb-1.5 border-b">
            <h4 className="font-bold text-slate-900 flex items-center gap-1.5 text-xs">
              <Target className="h-4 w-4 text-emerald-600" />
              USPs & Target Audience
            </h4>
            {isEditingPitch ? (
              <Button
                size="sm"
                variant="outline"
                onClick={handleAddUsp}
                className="h-6 text-[10px] gap-1 font-bold text-emerald-700 bg-emerald-50 border-emerald-200 hover:bg-emerald-100"
              >
                <Plus className="h-3 w-3" />
                Add USP
              </Button>
            ) : (
              <Badge variant="outline" className="text-[9px] font-bold">Value Props</Badge>
            )}
          </div>

          {/* Target Profile description */}
          {isEditingPitch ? (
            <div className="space-y-1">
              <Label className="text-[10px] font-bold text-slate-600 uppercase">Target Audience Description:</Label>
              <Input
                value={formTargetAudience}
                onChange={(e) => setFormTargetAudience(e.target.value)}
                placeholder="Ideal client persona (e.g. IT, Healthcare professionals under 45)..."
                className="h-7 text-xs font-medium"
              />
            </div>
          ) : (
            <p className="text-[11px] text-slate-600 bg-slate-50 p-2 rounded border">
              <strong className="text-slate-800">Target Profile: </strong>
              {playbook?.target_client || playbook?.target_audience || 'Skilled professionals, engineers, IT, healthcare seeking permanent overseas settlement.'}
            </p>
          )}

          {/* USPs list */}
          {isEditingPitch ? (
            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              <Label className="text-[10px] font-bold text-slate-600 uppercase">Unique Selling Propositions (USPs):</Label>
              {formUsps.map((u, idx) => (
                <div key={idx} className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                  <Input
                    value={u}
                    onChange={(e) => handleUpdateUsp(idx, e.target.value)}
                    placeholder="Enter key USP bullet point..."
                    className="h-7 text-xs flex-1 border-emerald-200"
                  />
                  <button
                    onClick={() => handleRemoveUsp(idx)}
                    className="p-1 rounded text-rose-500 hover:bg-rose-50 shrink-0"
                    title="Remove USP"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
              {formUsps.length === 0 && (
                <p className="text-[11px] text-slate-400 italic">No USPs added yet. Click "+ Add USP" above.</p>
              )}
            </div>
          ) : (
            <div className="space-y-1.5">
              {(playbook?.usps || playbook?.key_benefits || [
                'Direct PR visa with full work and study rights from day 1',
                'Free public healthcare (Medicare) and subsidised schooling',
                'Guaranteed pathway to citizenship after statutory residency',
                'Freedom to live and work anywhere in the country without employer sponsorship',
              ]).map((u, idx) => (
                <div key={idx} className="flex items-center gap-1.5 text-[11px] text-emerald-900 font-medium">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                  <span>{u}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* PRICING & PAYMENT MILESTONES (TRANSPARENT CLIENT QUOTE)       */}
      {/* ───────────────────────────────────────────────────────────── */}
      <Card className="p-4 bg-white border border-slate-200 space-y-3">
        <div className="flex items-center justify-between pb-2 border-b">
          <div className="flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-emerald-600" />
            <h3 className="font-extrabold text-slate-900 text-sm">Quote Breakdown for Prospects</h3>
          </div>
          <span className="text-xs font-extrabold text-emerald-800">
            {gstApplicable ? `Total: ${formatINR(totalWithGst)} (Incl. 18% GST)` : `Total: ${formatINR(baseFee)} (Net Retainer)`}
          </span>
        </div>

        <div className={`grid ${gstApplicable ? 'grid-cols-1 md:grid-cols-3' : 'grid-cols-1 md:grid-cols-2'} gap-3`}>
          <div className="p-3 bg-slate-50 border rounded-lg">
            <p className="text-[10px] text-slate-500 font-bold uppercase">Professional Service Fee</p>
            <p className="text-base font-extrabold text-slate-900">{formatINR(baseFee)}</p>
          </div>
          {gstApplicable && (
            <div className="p-3 bg-slate-50 border rounded-lg">
              <p className="text-[10px] text-slate-500 font-bold uppercase">18% GST (CGST + SGST)</p>
              <p className="text-base font-extrabold text-slate-900">{formatINR(gstAmount)}</p>
            </div>
          )}
          <div className="p-3 bg-emerald-50 border border-emerald-300 rounded-lg">
            <p className="text-[10px] text-emerald-800 font-bold uppercase">
              {gstApplicable ? 'Total Client Invoice Amount' : 'Total Client Invoice (Net)'}
            </p>
            <p className="text-base font-extrabold text-emerald-900">{formatINR(totalWithGst)}</p>
          </div>
        </div>

        <div className="space-y-1.5">
          <p className="text-[10px] font-bold uppercase text-slate-500">Payment Tranches:</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            {milestones.map((m, idx) => (
              <div key={idx} className="p-2 bg-slate-50 border rounded text-[11px] space-y-0.5">
                <p className="font-bold text-slate-800">{m.name}</p>
                <p className="text-emerald-700 font-extrabold">
                  {m.percentage}% • {formatINR(m.amount || Math.round(baseFee * (m.percentage / 100)))}
                </p>
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* REFUND POLICY & CLIENT PROTECTION TERMS (IF ENABLED BY ADMIN) */}
      {/* ───────────────────────────────────────────────────────────── */}
      {product?.refund_policy?.enabled !== false && product?.refund_policy?.policy_type !== 'no_refund' && (
        <Card className="p-4 bg-gradient-to-br from-emerald-50/70 via-white to-blue-50/50 border-2 border-emerald-300 shadow-sm space-y-3" data-testid="salesperson-refund-protection-card">
          <div className="flex items-center justify-between pb-2 border-b border-emerald-100 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-emerald-600" />
              <div>
                <h3 className="font-extrabold text-slate-900 text-sm flex items-center gap-2">
                  Client Protection & Refund Guarantee
                  <Badge className="bg-emerald-600 text-white text-[10px]">
                    {product?.refund_policy?.policy_type === 'protection' ? '100% Protection Policy' : 'Milestone Refund Policy'}
                  </Badge>
                </h3>
                <p className="text-[11px] text-slate-500">
                  Approved statutory guarantees for sales rep pitch during client consultation calls.
                </p>
              </div>
            </div>

            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                const pitch = `🛡️ LEAMSS Client Protection Policy for ${product?.name}:
• Retainer Service Fee: ${product?.refund_policy?.refundable_service_fee_pct ?? 100}% refundable on eligible negative assessment or visa refusal.
• Claim Window: ${product?.refund_policy?.claim_window_days || 30} days | Payout SLA: ${product?.refund_policy?.payout_time_days || 14} days.
• Statutory Safeguard: Transparent maker-checker approved process.`;
                navigator.clipboard.writeText(pitch);
                toast.success('Refund Protection pitch copied to clipboard!');
              }}
              className="h-8 text-xs font-bold text-emerald-800 border-emerald-300 hover:bg-emerald-50 gap-1"
            >
              <Copy className="h-3.5 w-3.5" />
              Copy Guarantee Pitch
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
            <div className="p-2.5 bg-white border border-emerald-200 rounded-lg">
              <p className="text-[10px] uppercase font-bold text-slate-400">Refundable Retainer Fee</p>
              <p className="text-sm font-extrabold text-emerald-700">
                {product?.refund_policy?.refundable_service_fee_pct ?? 100}% Refundable
              </p>
              <p className="text-[10px] text-slate-500">
                GST returned via {product?.refund_policy?.gst_treatment === 'credit_note' ? 'Tax Credit Note' : 'Standard adjustment'}
              </p>
            </div>

            <div className="p-2.5 bg-white border border-emerald-200 rounded-lg">
              <p className="text-[10px] uppercase font-bold text-slate-400">Turnaround SLA</p>
              <p className="text-sm font-extrabold text-slate-900">
                {product?.refund_policy?.payout_time_days || 14} Working Days
              </p>
              <p className="text-[10px] text-slate-500">
                Claim window: within {product?.refund_policy?.claim_window_days || 30} days of outcome
              </p>
            </div>

            <div className="p-2.5 bg-white border border-emerald-200 rounded-lg">
              <p className="text-[10px] uppercase font-bold text-slate-400">Government Fees</p>
              <p className="text-sm font-extrabold text-slate-700 capitalize">
                {(product?.refund_policy?.govt_fees_handling || 'non_refundable').replace('_', ' ')}
              </p>
              <p className="text-[10px] text-slate-500">Official fees paid directly to statutory bodies</p>
            </div>
          </div>

          {/* Guaranteed Triggers & Key Conditions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
            <div className="p-2 bg-emerald-50/70 border border-emerald-200 rounded-lg space-y-1">
              <p className="text-[10px] uppercase font-bold text-emerald-800">Guaranteed Triggers Covered:</p>
              <ul className="text-[11px] text-slate-700 space-y-1">
                {product?.refund_policy?.negative_skills_assessment_guarantee && (
                  <li className="flex items-center gap-1.5 font-medium text-emerald-900">
                    <CheckCircle2 className="h-3 w-3 text-emerald-600 shrink-0" />
                    Negative Skills Assessment from designated authority
                  </li>
                )}
                {product?.refund_policy?.visa_refusal_guarantee && (
                  <li className="flex items-center gap-1.5 font-medium text-emerald-900">
                    <CheckCircle2 className="h-3 w-3 text-emerald-600 shrink-0" />
                    Official immigration department visa refusal
                  </li>
                )}
                {product?.refund_policy?.voluntary_withdrawal_milestones && (
                  <li className="flex items-center gap-1.5 font-medium text-emerald-900">
                    <CheckCircle2 className="h-3 w-3 text-emerald-600 shrink-0" />
                    Tiered voluntary withdrawal milestone credit
                  </li>
                )}
                {Array.isArray(product?.refund_policy?.custom_guaranteed_triggers) &&
                  product.refund_policy.custom_guaranteed_triggers
                    .filter((t) => t.enabled !== false)
                    .map((t, i) => (
                      <li key={i} className="flex items-center gap-1.5 font-medium text-emerald-900">
                        <CheckCircle2 className="h-3 w-3 text-emerald-600 shrink-0" />
                        <span>{t.name} ({t.refund_pct ?? 100}% Refund)</span>
                      </li>
                    ))}
              </ul>
            </div>

            <div className="p-2 bg-slate-50 border border-slate-200 rounded-lg space-y-1">
              <p className="text-[10px] uppercase font-bold text-slate-500">Important Prospect Conditions:</p>
              <ul className="text-[10px] text-slate-600 space-y-0.5">
                {(product?.refund_policy?.conditions || [
                  '100% genuine documentation provided without omissions',
                  'Client responds to case manager queries within 7 working days'
                ]).slice(0, 2).map((c, i) => (
                  <li key={i} className="truncate">• {c}</li>
                ))}
                {Array.isArray(product?.refund_policy?.custom_fee_components) &&
                  product.refund_policy.custom_fee_components.map((f, i) => (
                    <li key={`fee-${i}`} className="text-slate-700 font-medium">
                      • {f.name}: {f.type === 'deduct_flat' ? `Flat ${formatINR(f.value)} deducted` : f.type === 'percentage' ? `${f.value}% refundable` : 'Non-refundable'}
                    </li>
                  ))}
                <li className="text-rose-600 font-semibold">• Excludes fraudulent documents or failure to achieve statutory English score</li>
              </ul>
            </div>
          </div>

          {/* Package-Wise Refund Overrides */}
          {product?.refund_policy?.package_overrides && Object.keys(product.refund_policy.package_overrides).length > 0 && (
            <div className="p-2.5 bg-indigo-50/70 border border-indigo-200 rounded-lg space-y-1.5 text-xs">
              <div className="flex items-center justify-between">
                <p className="text-[10px] uppercase font-bold text-indigo-900 flex items-center gap-1">
                  <Layers className="h-3 w-3 text-indigo-600" />
                  Package Tier Refund Guarantees:
                </p>
                <Badge variant="outline" className="text-[9px] bg-white text-indigo-700 border-indigo-200">
                  {Object.keys(product.refund_policy.package_overrides).length} Package Rules
                </Badge>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {Object.entries(product.refund_policy.package_overrides).map(([k, p]) => (
                  <div key={k} className="p-2 bg-white rounded border border-indigo-100 shadow-xs space-y-0.5">
                    <div className="flex items-center justify-between font-bold text-slate-800">
                      <span className="truncate">{p.name || `${k.charAt(0).toUpperCase() + k.slice(1)} Tier`}</span>
                      <Badge className={p.enabled !== false ? "bg-emerald-100 text-emerald-800 text-[9px]" : "bg-slate-100 text-slate-500 text-[9px]"}>
                        {p.enabled !== false ? `${p.refundable_pct ?? product?.refund_policy?.refundable_service_fee_pct ?? 100}%` : 'Disabled'}
                      </Badge>
                    </div>
                    <p className="text-[10px] text-slate-500">
                      {p.enabled !== false ? `${p.refundable_pct ?? product?.refund_policy?.refundable_service_fee_pct ?? 100}% fee protected on claim` : 'Non-refundable under this tier'}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 2-COLUMN: STATUTORY GOVT COSTS & DOCUMENT CHECKLIST           */}
      {/* ───────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Statutory Government Costs */}
        <Card className="p-4 bg-white border border-slate-200 space-y-2.5">
          <div className="flex items-center justify-between pb-1.5 border-b">
            <h4 className="font-bold text-slate-900 flex items-center gap-1.5 text-xs">
              <DollarSign className="h-4 w-4 text-amber-600" />
              Statutory Government Fee Slabs
            </h4>
            {isEditingPitch ? (
              <Badge className="bg-amber-100 text-amber-800 text-[9px] font-bold">Admin Editable</Badge>
            ) : (
              <Badge variant="outline" className="text-[9px]">Official Govt</Badge>
            )}
          </div>

          {isEditingPitch ? (
            <div className="space-y-2">
              <div className="flex items-center justify-between p-2 bg-slate-50 rounded border text-[11px] gap-2">
                <Label className="text-slate-600 font-bold shrink-0">Fee Currency:</Label>
                <Input
                  value={formGovCosts.currency}
                  onChange={(e) => setFormGovCosts({ ...formGovCosts, currency: e.target.value.toUpperCase() })}
                  placeholder="AUD, USD, CAD..."
                  className="h-7 text-xs font-bold uppercase w-24 text-right"
                />
              </div>

              <div className="flex items-center justify-between p-2 bg-slate-50 rounded border text-[11px] gap-2">
                <Label className="text-slate-600 font-bold shrink-0">Primary Applicant Fee:</Label>
                <div className="flex items-center gap-1">
                  <span className="text-xs font-bold text-slate-500">{formGovCosts.currency}</span>
                  <Input
                    type="number"
                    value={formGovCosts.primary_applicant}
                    onChange={(e) => setFormGovCosts({ ...formGovCosts, primary_applicant: e.target.value })}
                    className="h-7 text-xs font-bold w-32 text-right"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between p-2 bg-slate-50 rounded border text-[11px] gap-2">
                <Label className="text-slate-600 font-bold shrink-0">Spouse / Adult Dependent (18+):</Label>
                <div className="flex items-center gap-1">
                  <span className="text-xs font-bold text-slate-500">{formGovCosts.currency}</span>
                  <Input
                    type="number"
                    value={formGovCosts.secondary_applicant_adult}
                    onChange={(e) => setFormGovCosts({ ...formGovCosts, secondary_applicant_adult: e.target.value })}
                    placeholder="Optional"
                    className="h-7 text-xs font-bold w-32 text-right"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between p-2 bg-slate-50 rounded border text-[11px] gap-2">
                <Label className="text-slate-600 font-bold shrink-0">Child Dependent (Under 18):</Label>
                <div className="flex items-center gap-1">
                  <span className="text-xs font-bold text-slate-500">{formGovCosts.currency}</span>
                  <Input
                    type="number"
                    value={formGovCosts.secondary_applicant_child}
                    onChange={(e) => setFormGovCosts({ ...formGovCosts, secondary_applicant_child: e.target.value })}
                    placeholder="Optional"
                    className="h-7 text-xs font-bold w-32 text-right"
                  />
                </div>
              </div>

              <div className="text-[10px] text-slate-400 pt-1 italic">
                * Government fees configured here will be immediately displayed to sales reps during client consultation.
              </div>
            </div>
          ) : (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between p-2 bg-slate-50 rounded border text-[11px]">
                <span className="text-slate-600 font-medium">Primary Applicant Fee:</span>
                <span className="font-bold text-slate-900">
                  {govCosts.currency || 'AUD'} {Number(govCosts.primary_applicant || 4770).toLocaleString()}
                </span>
              </div>
              {govCosts.secondary_applicant_adult && (
                <div className="flex items-center justify-between p-2 bg-slate-50 rounded border text-[11px]">
                  <span className="text-slate-600 font-medium">Spouse / Adult Dependent (18+):</span>
                  <span className="font-bold text-slate-900">
                    {govCosts.currency || 'AUD'} {Number(govCosts.secondary_applicant_adult).toLocaleString()}
                  </span>
                </div>
              )}
              {govCosts.secondary_applicant_child && (
                <div className="flex items-center justify-between p-2 bg-slate-50 rounded border text-[11px]">
                  <span className="text-slate-600 font-medium">Child Dependent (Under 18):</span>
                  <span className="font-bold text-slate-900">
                    {govCosts.currency || 'AUD'} {Number(govCosts.secondary_applicant_child).toLocaleString()}
                  </span>
                </div>
              )}
              <div className="text-[10px] text-slate-400 pt-1 italic">
                * Official government fees are paid directly to destination immigration department at application lodgement.
              </div>
            </div>
          )}
        </Card>

        {/* Document Checklist for Prospect */}
        <Card className="p-4 bg-white border border-slate-200 space-y-2.5">
          <div className="flex items-center justify-between pb-1.5 border-b">
            <h4 className="font-bold text-slate-900 flex items-center gap-1.5 text-xs">
              <ListChecks className="h-4 w-4 text-purple-600" />
              Documents to Request from Client
            </h4>
            {isEditingPitch ? (
              <Button
                size="sm"
                variant="outline"
                onClick={handleAddChecklistItem}
                className="h-6 text-[10px] gap-1 font-bold text-purple-700 bg-purple-50 border-purple-200 hover:bg-purple-100"
              >
                <Plus className="h-3 w-3" />
                Add Document
              </Button>
            ) : (
              <Badge variant="outline" className="text-[9px]">Checklist</Badge>
            )}
          </div>

          {isEditingPitch ? (
            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {formChecklist.map((item, idx) => (
                <div key={idx} className="p-2 bg-slate-50 rounded border text-[11px] flex items-start gap-1.5">
                  <CheckCircle className="h-3.5 w-3.5 text-emerald-600 shrink-0 mt-1.5" />
                  <div className="flex-1 space-y-1">
                    <Input
                      value={item.document_name}
                      onChange={(e) => handleUpdateChecklistItem(idx, 'document_name', e.target.value)}
                      placeholder="Document name (e.g. Valid Passport, Degree Certificate)..."
                      className="h-7 text-xs font-bold"
                    />
                    <Input
                      value={item.description}
                      onChange={(e) => handleUpdateChecklistItem(idx, 'description', e.target.value)}
                      placeholder="Requirements / specifications (e.g. Color bio-data copy)..."
                      className="h-6 text-[10px] text-slate-600"
                    />
                  </div>
                  <button
                    onClick={() => handleRemoveChecklistItem(idx)}
                    className="p-1 rounded text-rose-500 hover:bg-rose-100 transition mt-1"
                    title="Remove document"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
              {formChecklist.length === 0 && (
                <p className="text-[11px] text-slate-400 italic">No documents added yet. Click "+ Add Document" above.</p>
              )}
            </div>
          ) : (
            <div className="space-y-1.5 max-h-48 overflow-y-auto pr-0.5">
              {(checklist.length > 0 ? checklist : [
                { document_name: 'Valid Passport (Current & Previous)', description: 'Color bio-data copy' },
                { document_name: 'Degree Certificates & Transcripts', description: 'Consolidated semester marks' },
                { document_name: 'Reference Letters & Work Experience', description: 'Roles on company letterhead' },
                { document_name: 'Last 3-6 Months Pay Slips & Form 16 / ITR', description: 'Proof of paid employment' },
                { document_name: 'English Scorecard (IELTS / PTE)', description: 'Valid scorecard' },
              ]).map((item, idx) => (
                <div key={idx} className="flex items-center justify-between p-2 bg-slate-50 rounded border text-[11px]">
                  <div className="flex items-center gap-1.5">
                    <CheckCircle className="h-3 w-3 text-emerald-600 shrink-0" />
                    <span className="font-medium text-slate-800">{item.document_name}</span>
                  </div>
                  {item.description && (
                    <span className="text-[10px] text-slate-400 font-medium">{item.description}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* OBJECTIONS & REBUTTALS LOOKUP                                  */}
      {/* ───────────────────────────────────────────────────────────── */}
      <Card className="p-4 bg-white border border-slate-200 space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-emerald-600" />
            <h3 className="font-extrabold text-slate-900 text-sm">Quick Objection & Rebuttal Lookup</h3>
          </div>
          {isEditingPitch ? (
            <Button
              size="sm"
              variant="outline"
              onClick={handleAddObjection}
              className="h-6 text-[10px] gap-1 font-bold text-emerald-700 bg-emerald-50 border-emerald-200 hover:bg-emerald-100"
            >
              <Plus className="h-3 w-3" />
              Add Objection & Rebuttal
            </Button>
          ) : (
            <Input
              placeholder="Search objection (e.g. fee, time, points)..."
              value={objectionSearch}
              onChange={(e) => setObjectionSearch(e.target.value)}
              className="h-7 text-xs w-64"
            />
          )}
        </div>

        {isEditingPitch ? (
          <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
            {formObjections.map((ob, idx) => (
              <div key={idx} className="p-3 bg-slate-50 border border-slate-300 rounded-lg space-y-2 relative">
                <div className="flex items-center justify-between">
                  <Label className="text-[11px] font-bold text-rose-800">
                    Objection #{idx + 1} (What the client says):
                  </Label>
                  <button
                    onClick={() => handleRemoveObjection(idx)}
                    className="p-1 rounded text-rose-500 hover:bg-rose-100 transition"
                    title="Remove objection"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
                <Input
                  value={ob.objection}
                  onChange={(e) => handleUpdateObjection(idx, 'objection', e.target.value)}
                  placeholder="e.g. Consultancy fee is higher than local agents..."
                  className="h-7 text-xs font-bold text-rose-950 bg-white"
                />
                <div>
                  <Label className="text-[11px] font-bold text-emerald-800">
                    Rebuttal Response (What sales reps should say):
                  </Label>
                  <Textarea
                    rows={2}
                    value={ob.rebuttal}
                    onChange={(e) => handleUpdateObjection(idx, 'rebuttal', e.target.value)}
                    placeholder="e.g. LEAMSS offers statutory-licensed legal representation and guaranteed milestone refunds..."
                    className="mt-1 text-xs font-medium text-emerald-950 bg-white border-emerald-200"
                  />
                </div>
              </div>
            ))}
            {formObjections.length === 0 && (
              <p className="text-[11px] text-slate-400 italic">No objections configured. Click "+ Add Objection & Rebuttal" above.</p>
            )}
          </div>
        ) : (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {filteredObjs.map((ob, idx) => (
              <div key={idx} className="p-2.5 bg-slate-50 border rounded-lg space-y-1">
                <p className="text-xs font-bold text-rose-800">Client: "{ob.objection}"</p>
                <p className="text-[11px] text-emerald-950 font-medium bg-emerald-50/50 p-2 rounded border border-emerald-100">
                  <strong className="text-emerald-700">Say This: </strong>
                  {ob.rebuttal}
                </p>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* CLIENT FAQS                                                   */}
      {/* ───────────────────────────────────────────────────────────── */}
      {(faqs.length > 0 || isEditingPitch) && (
        <Card className="p-4 bg-white border border-slate-200 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b">
            <div className="flex items-center gap-2">
              <HelpCircle className="h-4 w-4 text-indigo-600" />
              <h3 className="font-extrabold text-slate-900 text-sm">Frequently Asked Client Questions</h3>
            </div>
            {isEditingPitch ? (
              <Button
                size="sm"
                variant="outline"
                onClick={handleAddFaq}
                className="h-6 text-[10px] gap-1 font-bold text-indigo-700 bg-indigo-50 border-indigo-200 hover:bg-indigo-100"
              >
                <Plus className="h-3 w-3" />
                Add FAQ
              </Button>
            ) : (
              <Badge variant="outline" className="text-[9px] font-bold">Client Q&A</Badge>
            )}
          </div>

          {isEditingPitch ? (
            <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
              {formFaqs.map((f, idx) => (
                <div key={idx} className="p-3 bg-slate-50 border border-slate-300 rounded-lg space-y-2 relative">
                  <div className="flex items-center justify-between">
                    <Label className="text-[11px] font-bold text-indigo-900">
                      FAQ #{idx + 1} Question:
                    </Label>
                    <button
                      onClick={() => handleRemoveFaq(idx)}
                      className="p-1 rounded text-rose-500 hover:bg-rose-100 transition"
                      title="Remove FAQ"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <Input
                    value={f.question}
                    onChange={(e) => handleUpdateFaq(idx, 'question', e.target.value)}
                    placeholder="Client Question (e.g. Can I bring spouse and dependent children?)..."
                    className="h-7 text-xs font-bold text-slate-900 bg-white"
                  />
                  <div>
                    <Label className="text-[11px] font-bold text-slate-700">
                      Official FAQ Answer:
                    </Label>
                    <Textarea
                      rows={2}
                      value={f.answer}
                      onChange={(e) => handleUpdateFaq(idx, 'answer', e.target.value)}
                      placeholder="Answer script for sales reps to give client..."
                      className="mt-1 text-xs font-medium text-slate-800 bg-white border-indigo-100"
                    />
                  </div>
                </div>
              ))}
              {formFaqs.length === 0 && (
                <p className="text-[11px] text-slate-400 italic">No FAQs added yet. Click "+ Add FAQ" above.</p>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
              {faqs.map((f, idx) => (
                <div key={idx} className="p-2.5 bg-slate-50 border rounded-lg space-y-1">
                  <p className="text-xs font-bold text-slate-900">Q: {f.question}</p>
                  <p className="text-[11px] text-slate-600 leading-relaxed">A: {f.answer}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* ───────────────────────────────────────────────────────────── */}
      {/* STICKY BOTTOM BAR FOR ADMIN WHEN EDITING PITCH                */}
      {/* ───────────────────────────────────────────────────────────── */}
      {isEditingPitch && (
        <div className="sticky bottom-4 z-20 p-3 bg-slate-900 text-white rounded-xl shadow-xl flex items-center justify-between border border-slate-700 animate-in fade-in slide-in-from-bottom-2">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-amber-400" />
            <span className="text-xs font-bold">Unsaved pitch changes for {product?.name}</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setIsEditingPitch(false)}
              disabled={savingPitch}
              className="h-8 text-xs text-slate-300 hover:text-white"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleSaveSalesPitch}
              disabled={savingPitch}
              className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-bold gap-1.5 shadow"
              data-testid="save-sales-pitch-bottom-btn"
            >
              {savingPitch ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-3.5 w-3.5" />
                  Save Pitch Changes
                </>
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
