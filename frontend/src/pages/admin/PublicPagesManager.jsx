/**
 * Phase 15 — Public Pages Manager (Admin)
 *
 * /admin/public-pages
 *
 * 3 tabs:
 *   1. URLs & Share — browse all public URLs, preview/copy/WhatsApp/QR
 *   2. Content Editor — edit hero, featured, testimonials, FAQs, trust strip
 *   3. Analytics — lead conversion per URL + trends
 */
import { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import {
  ExternalLink, Copy, MessageCircle, Mail, QrCode, Search, X, Plus, Save, RotateCcw,
  TrendingUp, Globe2, FileEdit, Link2, Loader2, CheckCircle2, Star, ArrowUpRight, Trash2, Download,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const C = {
  ink: '#0F1A1F', body: '#3D4F57', muted: '#7B8B92',
  tealDeep: '#1F4D44', teal: '#137F7F', tealWash: '#E8F4F4', tealWash2: '#CFE4E4',
  gold: '#D4633F', goldDeep: '#B85333', goldWash: '#FCEDE2',
  bg: '#FAF7F2', card: '#FFFFFF', border: '#E7E2D6', borderSoft: '#F0EBE0', red: '#B91C1C',
};

// ─── Toast / inline message ────────────────────────────────────────────────
function useFlash() {
  const [msg, setMsg] = useState(null);
  const show = (text, tone = 'success') => {
    setMsg({ text, tone });
    setTimeout(() => setMsg(null), 2500);
  };
  return [msg, show];
}

// ═══════════════════════════════════════════════════════════════════════════
// Main page
// ═══════════════════════════════════════════════════════════════════════════
export default function PublicPagesManager() {
  const [tab, setTab] = useState('urls');
  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };

  return (
    <div style={{ background: C.bg, minHeight: '100vh' }} data-testid="public-pages-manager-root">
      <header className="border-b" style={{ background: C.card, borderColor: C.border }}>
        <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
          <div>
            <p className="text-[10px] uppercase font-bold tracking-[0.18em]" style={{ color: C.gold }}>Admin · Public Site</p>
            <h1 className="font-bold text-2xl mt-1" style={{ color: C.ink, fontFamily: "'Playfair Display', serif" }}>
              Public Pages Manager
            </h1>
            <p className="text-xs mt-1" style={{ color: C.muted }}>
              Browse + share 725+ public URLs · Edit landing-page content · Track lead conversion
            </p>
          </div>
          <Link to="/admin" className="text-xs px-3 py-1.5 rounded border" style={{ color: C.tealDeep, borderColor: C.border }}>
            ← Admin Dashboard
          </Link>
        </div>
      </header>

      <nav className="border-b sticky top-0 z-10" style={{ background: C.card, borderColor: C.border }}>
        <div className="max-w-7xl mx-auto px-6 flex gap-1">
          {[
            { key: 'urls',      label: 'URLs & Share', icon: Link2 },
            { key: 'content',   label: 'Content Editor', icon: FileEdit },
            { key: 'analytics', label: 'Lead Analytics', icon: TrendingUp },
          ].map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className="px-5 py-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors -mb-px"
              style={{
                borderColor: tab === t.key ? C.tealDeep : 'transparent',
                color: tab === t.key ? C.tealDeep : C.muted,
              }}
              data-testid={`tab-${t.key}`}
            >
              <t.icon className="h-4 w-4" />{t.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {tab === 'urls'      && <UrlsTab headers={headers} />}
        {tab === 'content'   && <ContentTab headers={headers} />}
        {tab === 'analytics' && <AnalyticsTab headers={headers} />}
      </main>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Tab 1 — URLs & Share
// ═══════════════════════════════════════════════════════════════════════════
function UrlsTab({ headers }) {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [country, setCountry] = useState('all');
  const [qrTarget, setQrTarget] = useState(null);
  const [flash, showFlash] = useFlash();

  const fetchList = async (override = {}) => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/admin-public-pages/urls`, {
        headers, params: { limit: 100, search: override.search ?? search, country: override.country ?? country },
      });
      setItems(r.data.items);
      setTotal(r.data.total);
    } catch (e) { showFlash('Failed to load URLs', 'error'); }
    setLoading(false);
  };

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      try {
        const r = await axios.get(`${API}/admin-public-pages/urls`, {
          headers, params: { limit: 100, search: '', country: 'all' },
        });
        if (active) { setItems(r.data.items); setTotal(r.data.total); }
      } catch (err) { if (active) showFlash('Failed to load URLs', 'error'); }
      if (active) setLoading(false);
    })();
    return () => { active = false; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const copyLink = (url) => {
    navigator.clipboard.writeText(url);
    showFlash('Link copied!');
  };
  const whatsappShare = (url, title) => {
    const msg = encodeURIComponent(`Check out the ${title} migration guide on LEAMSS Atlas:\n\n${url}`);
    window.open(`https://wa.me/?text=${msg}`, '_blank');
  };
  const emailShare = (url, title) => {
    const subj = encodeURIComponent(`LEAMSS Migration Guide — ${title}`);
    const body = encodeURIComponent(`Hi,\n\nThought you might find this useful — full migration guide for ${title}:\n\n${url}\n\nBest,\nLEAMSS Team`);
    window.location.href = `mailto:?subject=${subj}&body=${body}`;
  };

  return (
    <div className="space-y-4">
      <FlashBanner flash={flash} />
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 p-4 rounded-xl bg-white" style={{ border: `1px solid ${C.border}` }}>
        <div className="relative flex-1 min-w-[260px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: C.muted }} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchList({ search })}
            placeholder="Search 261313, Software Engineer, Carpenter…"
            className="w-full pl-10 pr-3 py-2 rounded border text-sm"
            style={{ borderColor: C.border }}
            data-testid="urls-search-input"
          />
        </div>
        <div className="flex gap-1">
          {['all', 'AU', 'CA', 'NZ'].map(c => (
            <button
              key={c}
              onClick={() => { setCountry(c); fetchList({ country: c }); }}
              className="px-3 py-2 rounded text-xs font-bold border"
              style={{
                background: country === c ? C.tealDeep : C.card,
                color: country === c ? '#fff' : C.body,
                borderColor: country === c ? C.tealDeep : C.border,
              }}
              data-testid={`urls-country-${c}`}
            >
              {c === 'all' ? 'All' : c === 'AU' ? '🇦🇺' : c === 'CA' ? '🇨🇦' : '🇳🇿'}
            </button>
          ))}
        </div>
        <button onClick={() => fetchList()} className="px-3 py-2 rounded text-xs font-bold" style={{ background: C.gold, color: '#fff' }} data-testid="urls-refresh">
          Refresh
        </button>
      </div>

      <p className="text-xs" style={{ color: C.muted }}>{total} URLs · showing {items.length}</p>

      {/* Table */}
      <div className="rounded-xl bg-white overflow-hidden" style={{ border: `1px solid ${C.border}` }}>
        <table className="w-full text-sm" data-testid="urls-table">
          <thead>
            <tr style={{ background: C.tealWash, borderBottom: `2px solid ${C.tealWash2}` }}>
              <th className="text-left px-4 py-3 text-[10px] uppercase font-bold tracking-wider" style={{ color: C.tealDeep }}>Title</th>
              <th className="text-left px-4 py-3 text-[10px] uppercase font-bold tracking-wider" style={{ color: C.tealDeep }}>URL Path</th>
              <th className="text-center px-3 py-3 text-[10px] uppercase font-bold tracking-wider" style={{ color: C.tealDeep }}>Leads (30d)</th>
              <th className="text-right px-4 py-3 text-[10px] uppercase font-bold tracking-wider" style={{ color: C.tealDeep }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={4} className="py-8 text-center"><Loader2 className="w-5 h-5 animate-spin mx-auto" style={{ color: C.teal }} /></td></tr>
            ) : items.length === 0 ? (
              <tr><td colSpan={4} className="py-8 text-center text-xs" style={{ color: C.muted }}>No URLs found</td></tr>
            ) : items.map((r, idx) => (
              <tr key={r.url} style={{ borderBottom: `1px solid ${C.borderSoft}`, background: idx % 2 ? C.bg : C.card }}>
                <td className="px-4 py-2.5">
                  <p className="font-bold text-sm" style={{ color: C.ink }}>{r.title}</p>
                  <div className="flex gap-1 mt-1">
                    <span className="text-[9px] px-1.5 py-0.5 rounded font-bold uppercase" style={{ background: C.goldWash, color: C.goldDeep }}>{r.kind}</span>
                    {r.country_code && <span className="text-[9px] px-1.5 py-0.5 rounded" style={{ background: C.tealWash, color: C.tealDeep }}>{r.country_code} · {r.code}</span>}
                  </div>
                </td>
                <td className="px-4 py-2.5">
                  <code className="text-[11px] font-mono" style={{ color: C.muted }}>{r.path}</code>
                </td>
                <td className="text-center px-3 py-2.5">
                  <span className="font-bold text-lg" style={{ color: r.leads_30d > 0 ? C.tealDeep : C.muted, fontFamily: "'Playfair Display', serif" }}>
                    {r.leads_30d}
                  </span>
                </td>
                <td className="px-4 py-2.5">
                  <div className="flex justify-end gap-1">
                    <IconBtn icon={ExternalLink} title="Preview"      onClick={() => window.open(r.url, '_blank')} testid={`url-preview-${r.path.replace(/\//g, '-')}`} />
                    <IconBtn icon={Copy}         title="Copy link"    onClick={() => copyLink(r.url)} testid={`url-copy-${r.path.replace(/\//g, '-')}`} />
                    <IconBtn icon={MessageCircle} title="WhatsApp"    onClick={() => whatsappShare(r.url, r.title)} testid={`url-wa-${r.path.replace(/\//g, '-')}`} color="#25D366" />
                    <IconBtn icon={Mail}         title="Email"        onClick={() => emailShare(r.url, r.title)} testid={`url-email-${r.path.replace(/\//g, '-')}`} />
                    <IconBtn icon={QrCode}       title="QR Code"      onClick={() => setQrTarget(r)} testid={`url-qr-${r.path.replace(/\//g, '-')}`} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {qrTarget && <QrModal target={qrTarget} headers={headers} onClose={() => setQrTarget(null)} />}
    </div>
  );
}

function IconBtn({ icon: Icon, title, onClick, testid, color }) {
  return (
    <button
      onClick={onClick}
      title={title}
      className="w-7 h-7 rounded flex items-center justify-center hover:bg-white transition-colors border"
      style={{ borderColor: C.border, color: color || C.tealDeep, background: C.card }}
      data-testid={testid}
    >
      <Icon className="w-3.5 h-3.5" />
    </button>
  );
}

function QrModal({ target, headers, onClose }) {
  const [qr, setQr] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const r = await axios.post(`${API}/admin-public-pages/qr`, { url: target.url }, { headers });
        if (active) setQr(r.data.data_url);
      } catch (e) { /* ignore */ }
      if (active) setLoading(false);
    })();
    return () => { active = false; };
  }, [target.url]); // eslint-disable-line react-hooks/exhaustive-deps

  const download = () => {
    if (!qr) return;
    const a = document.createElement('a');
    a.href = qr;
    a.download = `leamss-qr-${target.code || 'page'}.png`;
    a.click();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(15,30,35,0.5)' }} onClick={onClose} data-testid="qr-modal">
      <div className="bg-white rounded-xl p-6 max-w-md w-full" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <p className="font-bold text-base" style={{ color: C.tealDeep, fontFamily: "'Playfair Display', serif" }}>QR Code for {target.title}</p>
          <button onClick={onClose}><X className="w-4 h-4" style={{ color: C.muted }} /></button>
        </div>
        <p className="text-xs mb-4" style={{ color: C.muted }}>Scan to open: <code className="font-mono">{target.path}</code></p>
        {loading ? (
          <div className="py-16 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto" style={{ color: C.teal }} /></div>
        ) : qr ? (
          <>
            <img src={qr} alt="QR" className="w-full max-w-xs mx-auto" data-testid="qr-image" />
            <button onClick={download} className="mt-4 w-full px-4 py-2 rounded font-bold text-sm flex items-center justify-center gap-2" style={{ background: C.tealDeep, color: '#fff' }} data-testid="qr-download">
              <Download className="w-4 h-4" />Download PNG
            </button>
          </>
        ) : <p className="text-xs" style={{ color: C.red }}>Failed to load QR</p>}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Tab 2 — Content Editor
// ═══════════════════════════════════════════════════════════════════════════
function ContentTab({ headers }) {
  const [section, setSection] = useState('hero');
  const sections = [
    { key: 'hero',           label: 'Hero',         icon: Globe2 },
    { key: 'featured_codes', label: 'Featured 12',  icon: Star },
    { key: 'testimonials',   label: 'Testimonials', icon: MessageCircle },
    { key: 'faqs',           label: 'FAQs',         icon: FileEdit },
    { key: 'trust_strip',    label: 'Trust Strip',  icon: TrendingUp },
  ];
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[200px_1fr] gap-5">
      <aside>
        <div className="rounded-xl p-3 bg-white" style={{ border: `1px solid ${C.border}` }}>
          <p className="text-[10px] uppercase font-bold mb-2 tracking-wider" style={{ color: C.muted }}>Sections</p>
          {sections.map(s => (
            <button
              key={s.key}
              onClick={() => setSection(s.key)}
              className="w-full text-left px-3 py-2 rounded text-sm flex items-center gap-2 transition-colors mb-1"
              style={{
                background: section === s.key ? C.tealWash : 'transparent',
                color: section === s.key ? C.tealDeep : C.body,
                fontWeight: section === s.key ? 600 : 400,
              }}
              data-testid={`content-section-${s.key}`}
            >
              <s.icon className="w-4 h-4" />{s.label}
            </button>
          ))}
        </div>
      </aside>
      <div>
        <SectionEditor section={section} headers={headers} key={section} />
      </div>
    </div>
  );
}

function SectionEditor({ section, headers }) {
  const [doc, setDoc] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [flash, showFlash] = useFlash();

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      try {
        const r = await axios.get(`${API}/admin-public-pages/content/${section}`, { headers });
        if (active) { setDoc(r.data); setData(JSON.parse(JSON.stringify(r.data.data))); }
      } catch (e) { /* default content used */ }
      if (active) setLoading(false);
    })();
    return () => { active = false; };
  }, [section]); // eslint-disable-line react-hooks/exhaustive-deps

  const save = async () => {
    setSaving(true);
    try {
      const r = await axios.put(`${API}/admin-public-pages/content/${section}`, { data }, { headers });
      showFlash(`Saved · ${new Date(r.data.updated_at).toLocaleTimeString()}`);
      setDoc({ ...doc, is_default: false, updated_at: r.data.updated_at, updated_by: r.data.updated_by });
    } catch (e) {
      showFlash(e.response?.data?.detail || 'Save failed', 'error');
    }
    setSaving(false);
  };

  const reset = async () => {
    if (!window.confirm('Reset this section to defaults? Your custom edits will be lost.')) return;
    setSaving(true);
    try {
      await axios.post(`${API}/admin-public-pages/content/${section}/reset`, {}, { headers });
      // Reload
      const r = await axios.get(`${API}/admin-public-pages/content/${section}`, { headers });
      setDoc(r.data);
      setData(JSON.parse(JSON.stringify(r.data.data)));
      showFlash('Reset to defaults');
    } catch (e) {
      showFlash('Reset failed', 'error');
    }
    setSaving(false);
  };

  if (loading) return <div className="py-16 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto" style={{ color: C.teal }} /></div>;
  if (!data) return null;

  return (
    <div className="space-y-3" data-testid={`content-editor-${section}`}>
      <FlashBanner flash={flash} />

      {/* Status banner */}
      <div className="rounded-xl p-3 bg-white flex items-center justify-between gap-3" style={{ border: `1px solid ${C.border}` }}>
        <div className="flex items-center gap-2 text-xs" style={{ color: C.body }}>
          {doc.is_default ? (
            <><span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase" style={{ background: C.goldWash, color: C.goldDeep }}>Default</span>Using hardcoded defaults — not yet customized</>
          ) : (
            <><span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase" style={{ background: C.tealWash, color: C.tealDeep }}>Customized</span>
            Last edit: {doc.updated_at && new Date(doc.updated_at).toLocaleString()} by <code>{doc.updated_by}</code></>
          )}
        </div>
        <div className="flex gap-2">
          {!doc.is_default && (
            <button onClick={reset} disabled={saving} className="px-3 py-1.5 rounded text-xs font-bold flex items-center gap-1 border" style={{ color: C.body, borderColor: C.border, background: C.card }} data-testid="reset-btn">
              <RotateCcw className="w-3 h-3" />Reset
            </button>
          )}
          <button onClick={save} disabled={saving} className="px-4 py-1.5 rounded text-xs font-bold flex items-center gap-1" style={{ background: C.gold, color: '#fff' }} data-testid="save-btn">
            {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
            {saving ? 'Saving…' : 'Save Changes'}
          </button>
        </div>
      </div>

      {/* Section-specific editors */}
      <div className="rounded-xl p-5 bg-white" style={{ border: `1px solid ${C.border}` }}>
        {section === 'hero'           && <HeroEditor data={data} onChange={setData} />}
        {section === 'featured_codes' && <FeaturedEditor data={data} onChange={setData} headers={headers} />}
        {section === 'testimonials'   && <ListEditor data={data} onChange={setData} type="testimonials" />}
        {section === 'faqs'           && <ListEditor data={data} onChange={setData} type="faqs" />}
        {section === 'trust_strip'    && <ListEditor data={data} onChange={setData} type="trust_strip" />}
      </div>
    </div>
  );
}

// ── Hero editor ──
function HeroEditor({ data, onChange }) {
  const set = (k, v) => onChange({ ...data, [k]: v });
  return (
    <div className="space-y-3">
      <p className="text-[11px] uppercase font-bold tracking-wider" style={{ color: C.tealDeep, letterSpacing: '0.10em' }}>Hero Section · Mega Landing</p>
      <Field label="Eyebrow (small banner above title)" value={data.eyebrow || ''} onChange={(v) => set('eyebrow', v)} testid="hero-eyebrow" />
      <Field label="Title — Line 1" value={data.title_line1 || ''} onChange={(v) => set('title_line1', v)} testid="hero-line1" />
      <Field label="Title — Line 2 (green accent)" value={data.title_line2 || ''} onChange={(v) => set('title_line2', v)} testid="hero-line2" />
      <Field label="Title — Line 3 (orange italic accent)" value={data.title_line3_accent || ''} onChange={(v) => set('title_line3_accent', v)} testid="hero-line3" />
      <Field label="Subtitle (body paragraph)" value={data.subtitle || ''} onChange={(v) => set('subtitle', v)} multiline testid="hero-subtitle" />
      <div className="grid grid-cols-2 gap-2">
        <Field label="Primary CTA Button text" value={data.cta_primary || ''} onChange={(v) => set('cta_primary', v)} testid="hero-cta1" />
        <Field label="Secondary CTA Button text" value={data.cta_secondary || ''} onChange={(v) => set('cta_secondary', v)} testid="hero-cta2" />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Field label="Star Rating display" value={data.rating || ''} onChange={(v) => set('rating', v)} testid="hero-rating" />
        <Field label="Rating subtitle" value={data.rating_subtitle || ''} onChange={(v) => set('rating_subtitle', v)} testid="hero-rating-sub" />
      </div>
    </div>
  );
}

// ── Featured codes editor ──
function FeaturedEditor({ data, onChange, headers }) {
  const [searchResults, setSearchResults] = useState([]);
  const [searchQ, setSearchQ] = useState('');
  const [searching, setSearching] = useState(false);

  const removeAt = (idx) => onChange(data.filter((_, i) => i !== idx));
  const moveUp = (idx) => {
    if (idx === 0) return;
    const c = [...data]; [c[idx - 1], c[idx]] = [c[idx], c[idx - 1]]; onChange(c);
  };
  const moveDn = (idx) => {
    if (idx === data.length - 1) return;
    const c = [...data]; [c[idx + 1], c[idx]] = [c[idx], c[idx + 1]]; onChange(c);
  };
  const addCode = (item) => {
    if (data.find(d => d.country_code === item.country_code && d.code === item.code)) {
      alert('Already in list');
      return;
    }
    if (data.length >= 16) {
      alert('Max 16 featured codes allowed');
      return;
    }
    onChange([...data, { country_code: item.country_code, code: item.code, title: item.title }]);
    setSearchQ(''); setSearchResults([]);
  };

  const search = async () => {
    if (!searchQ.trim()) return;
    setSearching(true);
    try {
      const r = await axios.get(`${API}/admin-public-pages/urls`, {
        headers, params: { search: searchQ, limit: 20 },
      });
      setSearchResults(r.data.items.filter(x => x.kind === 'occupation').slice(0, 12));
    } catch (e) { /* surface no results */ }
    setSearching(false);
  };

  return (
    <div className="space-y-4">
      <p className="text-[11px] uppercase font-bold tracking-wider" style={{ color: C.tealDeep, letterSpacing: '0.10em' }}>Featured 12 Occupations · Mega Landing + Atlas Hub</p>
      <p className="text-xs" style={{ color: C.muted }}>Drag-equivalent (use ↑ ↓ buttons) to reorder. Max 16. Recommended: 4 AU + 4 CA + 4 NZ.</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {data.map((item, idx) => (
          <div key={`${item.country_code}-${item.code}`} className="rounded p-2.5 flex items-center gap-2" style={{ background: C.bg, border: `1px solid ${C.border}` }} data-testid={`featured-row-${idx}`}>
            <span className="text-xl">{ {AU: '🇦🇺', CA: '🇨🇦', NZ: '🇳🇿'}[item.country_code] }</span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold truncate" style={{ color: C.ink }}>{item.title}</p>
              <p className="text-[10px] font-mono" style={{ color: C.muted }}>{item.country_code} · {item.code}</p>
            </div>
            <div className="flex gap-0.5">
              <button onClick={() => moveUp(idx)} disabled={idx === 0} className="px-1.5 py-0.5 rounded text-xs disabled:opacity-30" style={{ background: C.card, color: C.body }} data-testid={`featured-up-${idx}`}>↑</button>
              <button onClick={() => moveDn(idx)} disabled={idx === data.length - 1} className="px-1.5 py-0.5 rounded text-xs disabled:opacity-30" style={{ background: C.card, color: C.body }} data-testid={`featured-down-${idx}`}>↓</button>
              <button onClick={() => removeAt(idx)} className="px-1.5 py-0.5 rounded text-xs" style={{ background: C.card, color: C.red }} data-testid={`featured-rm-${idx}`}><Trash2 className="w-3 h-3" /></button>
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-xl p-3" style={{ background: C.bg, border: `1px solid ${C.border}` }}>
        <p className="text-xs font-bold mb-2" style={{ color: C.tealDeep }}>Add an occupation</p>
        <div className="flex gap-2">
          <input value={searchQ} onChange={(e) => setSearchQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && search()} placeholder="Search atlas — e.g., 261313 or Civil Engineer" className="flex-1 px-3 py-2 rounded border text-sm" style={{ borderColor: C.border }} data-testid="featured-search-input" />
          <button onClick={search} className="px-4 py-2 rounded text-sm font-bold" style={{ background: C.tealDeep, color: '#fff' }} data-testid="featured-search-btn">
            {searching ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Search'}
          </button>
        </div>
        {searchResults.length > 0 && (
          <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-1.5" data-testid="featured-search-results">
            {searchResults.map(r => (
              <button key={r.url} onClick={() => addCode(r)} className="text-left p-2 rounded text-xs hover:bg-white transition-colors" style={{ background: C.card, border: `1px solid ${C.border}`, color: C.body }} data-testid={`featured-add-${r.country_code}-${r.code}`}>
                <span className="mr-1">{ {AU: '🇦🇺', CA: '🇨🇦', NZ: '🇳🇿'}[r.country_code] }</span>
                <span className="font-mono text-[10px]">{r.code}</span> · <span className="font-bold">{r.title}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── List editor (testimonials, FAQs, trust_strip) ──
function ListEditor({ data, onChange, type }) {
  const blueprint = {
    testimonials: { name: '', city: '', text: '', stars: 5 },
    faqs:         { q: '', a: '' },
    trust_strip:  { num: '', label: '' },
  };
  const titleMap = {
    testimonials: 'Testimonials',
    faqs:         'Frequently Asked Questions',
    trust_strip:  'Trust Strip (marquee numbers)',
  };
  const max = { testimonials: 12, faqs: 30, trust_strip: 12 }[type];

  const addItem = () => {
    if (data.length >= max) { alert(`Max ${max} items`); return; }
    onChange([...data, { ...blueprint[type] }]);
  };
  const removeItem = (idx) => onChange(data.filter((_, i) => i !== idx));
  const updateItem = (idx, patch) => onChange(data.map((it, i) => i === idx ? { ...it, ...patch } : it));
  const moveUp = (idx) => {
    if (idx === 0) return;
    const c = [...data]; [c[idx - 1], c[idx]] = [c[idx], c[idx - 1]]; onChange(c);
  };
  const moveDn = (idx) => {
    if (idx === data.length - 1) return;
    const c = [...data]; [c[idx + 1], c[idx]] = [c[idx], c[idx + 1]]; onChange(c);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-[11px] uppercase font-bold tracking-wider" style={{ color: C.tealDeep, letterSpacing: '0.10em' }}>{titleMap[type]} ({data.length}/{max})</p>
        <button onClick={addItem} className="px-3 py-1.5 rounded text-xs font-bold flex items-center gap-1" style={{ background: C.tealDeep, color: '#fff' }} data-testid={`${type}-add-btn`}>
          <Plus className="w-3 h-3" />Add
        </button>
      </div>

      <div className="space-y-2">
        {data.map((item, idx) => (
          <div key={idx} className="rounded p-3" style={{ background: C.bg, border: `1px solid ${C.border}` }} data-testid={`${type}-row-${idx}`}>
            <div className="flex items-start justify-between mb-2">
              <span className="text-[10px] uppercase font-bold" style={{ color: C.muted }}>#{idx + 1}</span>
              <div className="flex gap-0.5">
                <button onClick={() => moveUp(idx)} disabled={idx === 0} className="px-1.5 py-0.5 rounded text-xs disabled:opacity-30" style={{ background: C.card, color: C.body }}>↑</button>
                <button onClick={() => moveDn(idx)} disabled={idx === data.length - 1} className="px-1.5 py-0.5 rounded text-xs disabled:opacity-30" style={{ background: C.card, color: C.body }}>↓</button>
                <button onClick={() => removeItem(idx)} className="px-1.5 py-0.5 rounded text-xs" style={{ background: C.card, color: C.red }} data-testid={`${type}-rm-${idx}`}><Trash2 className="w-3 h-3" /></button>
              </div>
            </div>
            {type === 'testimonials' && (
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Name" value={item.name || ''} onChange={(v) => updateItem(idx, { name: v })} testid={`${type}-name-${idx}`} />
                  <Field label="City / Migration path" value={item.city || ''} onChange={(v) => updateItem(idx, { city: v })} testid={`${type}-city-${idx}`} />
                </div>
                <Field label="Testimonial text" value={item.text || ''} onChange={(v) => updateItem(idx, { text: v })} multiline testid={`${type}-text-${idx}`} />
                <Field label="Stars (1-5)" value={String(item.stars || 5)} onChange={(v) => updateItem(idx, { stars: Math.max(1, Math.min(5, parseInt(v) || 5)) })} testid={`${type}-stars-${idx}`} />
              </div>
            )}
            {type === 'faqs' && (
              <div className="space-y-2">
                <Field label="Question" value={item.q || ''} onChange={(v) => updateItem(idx, { q: v })} testid={`${type}-q-${idx}`} />
                <Field label="Answer" value={item.a || ''} onChange={(v) => updateItem(idx, { a: v })} multiline testid={`${type}-a-${idx}`} />
              </div>
            )}
            {type === 'trust_strip' && (
              <div className="grid grid-cols-2 gap-2">
                <Field label="Number (e.g., 80k+)" value={item.num || ''} onChange={(v) => updateItem(idx, { num: v })} testid={`${type}-num-${idx}`} />
                <Field label="Label (e.g., Visas Processed)" value={item.label || ''} onChange={(v) => updateItem(idx, { label: v })} testid={`${type}-label-${idx}`} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function Field({ label, value, onChange, multiline, testid }) {
  return (
    <label className="block">
      <span className="text-[10px] uppercase font-bold tracking-wider" style={{ color: C.muted }}>{label}</span>
      {multiline ? (
        <textarea
          value={value} onChange={(e) => onChange(e.target.value)}
          rows={3}
          className="w-full px-3 py-2 rounded border text-sm mt-1 resize-y"
          style={{ borderColor: C.border, fontFamily: 'inherit' }}
          data-testid={testid}
        />
      ) : (
        <input
          value={value} onChange={(e) => onChange(e.target.value)}
          className="w-full px-3 py-2 rounded border text-sm mt-1"
          style={{ borderColor: C.border }}
          data-testid={testid}
        />
      )}
    </label>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Tab 3 — Analytics
// ═══════════════════════════════════════════════════════════════════════════
function AnalyticsTab({ headers }) {
  const [data, setData] = useState(null);
  const [topPages, setTopPages] = useState([]);
  const [days, setDays] = useState(30);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [a, t] = await Promise.all([
          axios.get(`${API}/admin-public-pages/analytics?days=${days}`, { headers }),
          axios.get(`${API}/admin-public-pages/top-pages?limit=10&days=${days}`, { headers }),
        ]);
        if (active) { setData(a.data); setTopPages(t.data.pages); }
      } catch (e) { /* analytics unavailable */ }
    })();
    return () => { active = false; };
  }, [days]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!data) return <div className="py-16 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto" style={{ color: C.teal }} /></div>;

  const maxTrend = Math.max(1, ...data.daily_trend.map(d => d.leads));

  return (
    <div className="space-y-5" data-testid="analytics-tab">
      {/* Window selector */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <p className="text-sm" style={{ color: C.muted }}>Time range:</p>
        <div className="flex gap-1">
          {[7, 30, 90, 365].map(d => (
            <button key={d} onClick={() => setDays(d)} className="px-3 py-1.5 rounded text-xs font-bold border"
              style={{ background: days === d ? C.tealDeep : C.card, color: days === d ? '#fff' : C.body, borderColor: days === d ? C.tealDeep : C.border }}
              data-testid={`analytics-days-${d}`}
            >
              {d === 365 ? '1Y' : `${d}d`}
            </button>
          ))}
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Total Leads" value={data.total_leads} sub={`Last ${days}d`} testid="stat-total" />
        <StatCard label="Top Country" value={Object.entries(data.country_distribution).filter(([k]) => k !== 'unknown').sort(([, a], [, b]) => b - a)[0]?.[0] || '—'}
          sub={`${(Object.entries(data.country_distribution).filter(([k]) => k !== 'unknown').sort(([, a], [, b]) => b - a)[0]?.[1] || 0)} leads`} />
        <StatCard label="Unique Codes" value={data.top_codes.length} sub="receiving leads" />
        <StatCard label="Avg per day" value={(data.total_leads / days).toFixed(1)} sub="leads/day" />
      </div>

      {/* Daily trend chart */}
      <div className="rounded-xl p-5 bg-white" style={{ border: `1px solid ${C.border}` }}>
        <p className="text-[11px] uppercase font-bold mb-4 tracking-wider" style={{ color: C.tealDeep }}>Daily Lead Trend</p>
        {data.daily_trend.length === 0 ? (
          <p className="text-xs text-center py-8" style={{ color: C.muted }}>No leads in this window.</p>
        ) : (
          <div className="flex items-end gap-1 h-32" data-testid="trend-chart">
            {data.daily_trend.map(d => (
              <div key={d.date} className="flex-1 flex flex-col items-center group" title={`${d.date}: ${d.leads} leads`}>
                <div className="w-full rounded-t transition-all hover:opacity-80" style={{ height: `${(d.leads / maxTrend) * 100}%`, background: C.gold, minHeight: 2 }} />
                <span className="text-[8px] mt-1" style={{ color: C.muted }}>{d.date.slice(5)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Top pages */}
      <div className="rounded-xl p-5 bg-white" style={{ border: `1px solid ${C.border}` }}>
        <p className="text-[11px] uppercase font-bold mb-4 tracking-wider" style={{ color: C.tealDeep }}>Top 10 Performing Pages</p>
        <table className="w-full" data-testid="top-pages-table">
          <thead>
            <tr style={{ borderBottom: `1px solid ${C.borderSoft}` }}>
              <th className="text-left text-[10px] uppercase font-bold py-2" style={{ color: C.muted }}>#</th>
              <th className="text-left text-[10px] uppercase font-bold py-2" style={{ color: C.muted }}>Title</th>
              <th className="text-left text-[10px] uppercase font-bold py-2" style={{ color: C.muted }}>Country / Code</th>
              <th className="text-right text-[10px] uppercase font-bold py-2" style={{ color: C.muted }}>Leads</th>
              <th className="text-right text-[10px] uppercase font-bold py-2" style={{ color: C.muted }}></th>
            </tr>
          </thead>
          <tbody>
            {topPages.length === 0 ? (
              <tr><td colSpan={5} className="py-6 text-center text-xs" style={{ color: C.muted }}>No data yet</td></tr>
            ) : topPages.map((p, i) => (
              <tr key={`${p.country}-${p.atlas_code}`} style={{ borderBottom: `1px solid ${C.borderSoft}` }}>
                <td className="py-2.5 text-xs font-bold" style={{ color: C.muted }}>{i + 1}</td>
                <td className="py-2.5 text-sm font-bold" style={{ color: C.ink }}>{p.atlas_title}</td>
                <td className="py-2.5 text-xs font-mono" style={{ color: C.body }}>{p.country} · {p.atlas_code}</td>
                <td className="py-2.5 text-right">
                  <span className="font-bold text-base" style={{ color: C.tealDeep, fontFamily: "'Playfair Display', serif" }}>{p.leads}</span>
                </td>
                <td className="py-2.5 text-right">
                  <a href={p.url} target="_blank" rel="noreferrer" className="text-xs underline" style={{ color: C.gold }} data-testid={`top-page-link-${i}`}>
                    Open <ArrowUpRight className="w-3 h-3 inline" />
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatCard({ label, value, sub, testid }) {
  return (
    <div className="rounded-xl p-4 bg-white" style={{ border: `1px solid ${C.border}` }} data-testid={testid}>
      <p className="text-[10px] uppercase font-bold tracking-wider" style={{ color: C.muted }}>{label}</p>
      <p className="text-3xl font-bold mt-1" style={{ color: C.tealDeep, fontFamily: "'Playfair Display', serif" }}>{value}</p>
      <p className="text-[10px] mt-1" style={{ color: C.muted }}>{sub}</p>
    </div>
  );
}

function FlashBanner({ flash }) {
  if (!flash) return null;
  const bg = flash.tone === 'error' ? '#FEE2E2' : C.tealWash;
  const fg = flash.tone === 'error' ? C.red : C.tealDeep;
  return (
    <div className="rounded p-2 flex items-center gap-2 text-sm" style={{ background: bg, color: fg }} data-testid="flash-banner">
      {flash.tone === 'error' ? <X className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}{flash.text}
    </div>
  );
}
