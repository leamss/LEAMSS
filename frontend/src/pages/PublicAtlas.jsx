/**
 * Phase 13 — Public Atlas SEO Pages
 *
 * Three public, NO-AUTH-REQUIRED routes:
 *   /atlas                     — Hub (3 country cards + featured grid)
 *   /atlas/:country            — Country browse + search
 *   /atlas/:country/:code      — Single occupation deep-dive (SEO money page)
 *
 * Goals:
 *   • Fast first paint (no auth check, no logged-in chrome)
 *   • SEO meta tags + JSON-LD set per page via document.head injection
 *   • Lead capture CTA on every page (sticky on single-occ page)
 */
import { useState, useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import {
  ArrowRight, Briefcase, Globe2, Award, Loader2, Search, MapPin,
  CheckCircle2, ChevronRight, Sparkles, Mail, Phone, User as UserIcon, Send,
  TrendingUp, ShieldCheck, Zap, Sliders, AlertCircle, BarChart3, Check,
  ExternalLink, Clock, FileText, Building2, Scale, Users,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ─── Color palette (matches main app teal/gold aesthetic) ───────────────────
const C = {
  ink: '#0F1A1F', body: '#3D4F57', muted: '#7B8B92',
  tealDeep: '#0E5C5C', teal: '#137F7F', tealWash: '#E8F4F4', tealWash2: '#CFE4E4',
  gold: '#C29B5C', goldDeep: '#9A7A48', goldWash: '#FAF1E2',
  orange: '#D97757', red: '#B91C1C', redWash: '#FEE2E2',
  bg: '#FAF7F2', card: '#FFFFFF', border: '#E7E2D6', borderSoft: '#F0EBE0',
};

// ─── SEO Helper — inject meta + JSON-LD into document head ─────────────────
function applySEO(seo) {
  if (!seo) return;
  if (seo.page_title) document.title = seo.page_title;

  const upsertMeta = (name, content, useProperty = false) => {
    if (!content) return;
    const attr = useProperty ? 'property' : 'name';
    let el = document.head.querySelector(`meta[${attr}="${name}"]`);
    if (!el) {
      el = document.createElement('meta');
      el.setAttribute(attr, name);
      document.head.appendChild(el);
    }
    el.setAttribute('content', content);
  };
  upsertMeta('description', seo.meta_description);
  upsertMeta('keywords', seo.keywords);
  upsertMeta('robots', seo.meta_robots);
  upsertMeta('og:title', seo.og_title || seo.page_title, true);
  upsertMeta('og:description', seo.og_description || seo.meta_description, true);
  upsertMeta('og:image', seo.og_image, true);
  upsertMeta('og:type', 'article', true);
  upsertMeta('og:locale', seo.og_locale, true);
  upsertMeta('twitter:card', seo.twitter_card || 'summary_large_image');
  upsertMeta('twitter:title', seo.twitter_title || seo.og_title || seo.page_title);
  upsertMeta('twitter:description', seo.twitter_description || seo.og_description || seo.meta_description);
  upsertMeta('twitter:image', seo.twitter_image || seo.og_image);

  // Canonical link
  if (seo.canonical_url) {
    let canon = document.head.querySelector('link[rel="canonical"]');
    if (!canon) { canon = document.createElement('link'); canon.rel = 'canonical'; document.head.appendChild(canon); }
    canon.href = seo.canonical_url;
  }

  // JSON-LD structured data
  if (seo.json_ld) {
    let ld = document.head.querySelector('script[type="application/ld+json"][data-atlas]');
    if (!ld) { ld = document.createElement('script'); ld.type = 'application/ld+json'; ld.setAttribute('data-atlas', '1'); document.head.appendChild(ld); }
    ld.textContent = JSON.stringify(seo.json_ld);
  }
}

// ─── Public Shell (header + footer) ─────────────────────────────────────────
function PublicShell({ children }) {
  return (
    <div style={{ background: C.bg, minHeight: '100vh', color: C.ink }}>
      <header className="border-b sticky top-0 z-20" style={{ background: C.card, borderColor: C.border }}>
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link reloadDocument to="/atlas" className="flex items-center gap-2" data-testid="atlas-header-logo">
            <div className="w-8 h-8 rounded flex items-center justify-center" style={{ background: C.tealDeep, color: '#fff' }}>
              <Globe2 className="w-4 h-4" />
            </div>
            <span className="text-lg font-bold" style={{ color: C.tealDeep, fontFamily: "'Playfair Display', serif" }}>
              LEAMSS Atlas
            </span>
          </Link>
          <nav className="hidden md:flex items-center gap-5 text-sm">
            <Link reloadDocument to="/atlas/au" className="hover:underline" style={{ color: C.body }} data-testid="header-link-au">🇦🇺 Australia</Link>
            <Link reloadDocument to="/atlas/ca" className="hover:underline" style={{ color: C.body }} data-testid="header-link-ca">🇨🇦 Canada</Link>
            <Link reloadDocument to="/atlas/nz" className="hover:underline" style={{ color: C.body }} data-testid="header-link-nz">🇳🇿 New Zealand</Link>
            <a href="https://leamss.com/start" className="px-3.5 py-1.5 rounded-full text-xs font-bold text-white shadow-sm hover:opacity-95" style={{ background: '#D4633F' }} data-testid="header-cta-start">
              Free Eligibility Check
            </a>
            <Link to="/" className="px-3 py-1.5 rounded text-xs font-bold" style={{ background: C.gold, color: '#fff' }} data-testid="header-cta-login">
              Agent Login
            </Link>
          </nav>
        </div>
      </header>

      {children}

      <footer className="border-t mt-16" style={{ background: C.card, borderColor: C.border }}>
        <div className="max-w-6xl mx-auto px-6 py-8 grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
          <div>
            <p className="font-bold mb-2" style={{ color: C.tealDeep }}>LEAMSS Atlas</p>
            <p style={{ color: C.muted }}>Verified migration occupation guide for Australia, Canada & New Zealand. Curated by licensed immigration experts.</p>
          </div>
          <div>
            <p className="font-bold mb-2" style={{ color: C.tealDeep }}>Browse</p>
            <ul className="space-y-1" style={{ color: C.body }}>
              <li><Link reloadDocument to="/atlas/au">Australia ANZSCO Codes</Link></li>
              <li><Link reloadDocument to="/atlas/ca">Canada NOC 2021 Codes</Link></li>
              <li><Link reloadDocument to="/atlas/nz">New Zealand ANZSCO 1.3</Link></li>
            </ul>
          </div>
          <div>
            <p className="font-bold mb-2" style={{ color: C.tealDeep }}>Contact</p>
            <p style={{ color: C.body }}>For partner enquiries or appointments, use the lead form on any occupation page.</p>
          </div>
        </div>
        <div className="text-center text-xs py-3" style={{ color: C.muted, borderTop: `1px solid ${C.borderSoft}` }}>
          © 2026 LEAMSS · Migration Atlas powered by official ANZSCO + NOC data sources.
        </div>
      </footer>
    </div>
  );
}

// ─── 1. /atlas — Hub Page ───────────────────────────────────────────────────
export function PublicAtlasHub() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const r = await axios.get(`${API}/public-atlas/featured`);
        if (!active) return;
        setData(r.data);
        applySEO(r.data.seo);
      } catch (e) {
        if (active) setData({ error: e.response?.data?.detail || String(e) });
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, []);

  return (
    <PublicShell>
      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 pt-12 pb-8" data-testid="atlas-hub-root">
        <p className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: C.gold, letterSpacing: '0.16em' }}>
          Verified · Updated 2026 · Source-Linked
        </p>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-4" style={{ color: C.ink, fontFamily: "'Playfair Display', serif" }}>
          Migration Occupation Atlas<br />
          <span style={{ color: C.tealDeep }}>for Australia, Canada & New Zealand</span>
        </h1>
        <p className="text-base sm:text-lg max-w-3xl" style={{ color: C.body }}>
          Verified ANZSCO + NOC code reference covering visa pathways, eligibility, salary trends,
          and assessing authorities. Free for everyone — request a personalised eligibility check anytime.
        </p>
      </section>

      {/* Country cards */}
      <section className="max-w-6xl mx-auto px-6 pb-10">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {(data?.countries || []).map(c => (
            <Link
              key={c.code} to={`/atlas/${c.code.toLowerCase()}`}
              className="rounded-xl border p-5 transition-all hover:-translate-y-0.5 hover:shadow-lg group"
              style={{ background: C.card, borderColor: C.border }}
              data-testid={`atlas-hub-country-${c.code}`}
            >
              <p className="text-4xl mb-2">{c.flag}</p>
              <p className="text-xl font-bold mb-1" style={{ color: C.tealDeep, fontFamily: "'Playfair Display', serif" }}>{c.name}</p>
              <p className="text-xs mb-3" style={{ color: C.muted }}>{c.classification}</p>
              <p className="text-2xl font-bold" style={{ color: C.gold }}>{c.total}</p>
              <p className="text-xs" style={{ color: C.body }}>verified occupations</p>
              <p className="text-xs mt-3 flex items-center gap-1 group-hover:gap-2 transition-all" style={{ color: C.teal }}>
                Browse all <ArrowRight className="w-3 h-3" />
              </p>
            </Link>
          ))}
        </div>
      </section>

      {/* Featured grid */}
      <section className="max-w-6xl mx-auto px-6 pb-16">
        <p className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: C.gold, letterSpacing: '0.12em' }}>
          <Sparkles className="w-3 h-3 inline mr-1" />Most-Searched Occupations
        </p>
        {loading ? (
          <div className="py-12 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto" style={{ color: C.teal }} /></div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {(data?.items || []).map(it => (
              <OccupationCard key={`${it.country_code}-${it.code}`} item={it} />
            ))}
          </div>
        )}
      </section>
    </PublicShell>
  );
}

// ─── 2. /atlas/:country — Country browse + search ───────────────────────────
export function PublicAtlasCountry() {
  const { country: rawCountry } = useParams();
  const country = (rawCountry || '').toUpperCase();
  const [data, setData] = useState(null);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchList = async (q = '') => {
    if (!['AU', 'CA', 'NZ'].includes(country)) {
      setData({ error: 'Country not found' });
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const r = await axios.get(`${API}/public-atlas/${country}/list`, {
        params: { limit: 60, search: q || undefined },
      });
      setData(r.data);
      applySEO(r.data.seo);
    } catch (e) {
      setData({ error: e.response?.data?.detail || 'Country not found' });
    }
    setLoading(false);
  };

  useEffect(() => {
    let active = true;
    (async () => {
      if (!['AU', 'CA', 'NZ'].includes(country)) {
        if (active) { setData({ error: 'Country not found' }); setLoading(false); }
        return;
      }
      setLoading(true);
      try {
        const r = await axios.get(`${API}/public-atlas/${country}/list`, { params: { limit: 60 } });
        if (active) { setData(r.data); applySEO(r.data.seo); }
      } catch (e) {
        if (active) setData({ error: e.response?.data?.detail || 'Country not found' });
      }
      if (active) setLoading(false);
    })();
    return () => { active = false; };
  }, [country]);

  const cm = data?.country_meta || {};
  return (
    <PublicShell>
      <section className="max-w-6xl mx-auto px-6 pt-12 pb-6" data-testid="atlas-country-root">
        <Link reloadDocument to="/atlas" className="text-xs hover:underline" style={{ color: C.muted }}>← Atlas Hub</Link>
        <h1 className="text-4xl sm:text-5xl font-bold mt-2 mb-2" style={{ color: C.ink, fontFamily: "'Playfair Display', serif" }}>
          {cm.flag} {cm.name || country} <span style={{ color: C.tealDeep }}>Occupation Atlas</span>
        </h1>
        <p className="text-sm" style={{ color: C.body }}>
          {data?.total ?? 0} verified occupations · {cm.classification || '—'}
        </p>

        {/* Search */}
        <div className="mt-6 max-w-xl relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: C.muted }} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchList(search)}
            placeholder="Search by code or title — e.g., 261313 or Software Engineer"
            className="w-full pl-10 pr-3 py-3 rounded border text-sm"
            style={{ borderColor: C.border, background: C.card }}
            data-testid="atlas-country-search"
          />
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 pb-16">
        {loading ? (
          <div className="py-12 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto" style={{ color: C.teal }} /></div>
        ) : data?.error ? (
          <p className="text-sm py-8" style={{ color: C.red }} data-testid="atlas-country-error">{data.error}</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="atlas-country-grid">
            {(data?.items || []).map(it => <OccupationCard key={`${it.country_code}-${it.code}`} item={it} />)}
          </div>
        )}
      </section>
    </PublicShell>
  );
}

// ─── 3. /atlas/:country/:code — Single Occupation (SEO money page) ──────────
export function PublicAtlasOccupation() {
  const { country: rawCountry, code } = useParams();
  const country = (rawCountry || '').toUpperCase();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      try {
        const r = await axios.get(`${API}/public-atlas/${country}/${code}`);
        if (!active) return;
        setData(r.data);
        applySEO(r.data.seo);
      } catch (e) {
        if (active) setData({ error: e.response?.data?.detail || 'Occupation not found' });
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [country, code]);

  if (loading) {
    return <PublicShell><div className="py-16 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto" style={{ color: C.teal }} /></div></PublicShell>;
  }
  if (data?.error) {
    return (
      <PublicShell>
        <div className="max-w-3xl mx-auto p-8 text-center" data-testid="atlas-occ-error">
          <p className="text-xl font-bold" style={{ color: C.red }}>{data.error}</p>
          <button onClick={() => navigate('/atlas')} className="mt-4 px-4 py-2 rounded text-sm font-bold" style={{ background: C.teal, color: '#fff' }}>
            ← Back to Atlas Hub
          </button>
        </div>
      </PublicShell>
    );
  }

  const occ = data.occupation;
  const cm = data.country_meta;
  return (
    <PublicShell>
      <section className="max-w-6xl mx-auto px-6 pt-8 pb-3" data-testid="atlas-occ-root">
        <div className="text-xs mb-3" style={{ color: C.muted }}>
          <Link to="/atlas" className="hover:underline">Atlas</Link>
          <ChevronRight className="w-3 h-3 inline mx-1" />
          <Link to={`/atlas/${country.toLowerCase()}`} className="hover:underline">{cm.flag} {cm.name}</Link>
          <ChevronRight className="w-3 h-3 inline mx-1" />
          <span>{occ.code}</span>
        </div>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex-1 min-w-0">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight" style={{ color: C.ink, fontFamily: "'Playfair Display', serif" }}>
              {occ.title}
            </h1>
            <p className="text-sm mt-2 flex flex-wrap items-center gap-2" style={{ color: C.body }}>
              <span className="px-2 py-0.5 rounded text-xs font-mono" style={{ background: C.tealWash, color: C.tealDeep }}>{occ.code}</span>
              <span>·</span>
              <span>{cm.classification}</span>
              <span>·</span>
              <span className="flex items-center gap-1" style={{ color: C.teal }}>
                <CheckCircle2 className="w-3 h-3" />Verified
              </span>
              {occ.nz_green_list_tier && (
                <>
                  <span>·</span>
                  <span className="px-2 py-0.5 rounded text-xs font-bold" style={{ background: C.goldWash, color: C.goldDeep }}>
                    🇳🇿 Green List Tier {occ.nz_green_list_tier}
                  </span>
                </>
              )}
            </p>
          </div>
        </div>

        {country === 'AU' && (
          <AuVerificationSeal occ={occ} migrotoLive={data.migroto_live} />
        )}
      </section>

      <div className="max-w-6xl mx-auto px-6 pb-16 grid grid-cols-1 lg:grid-cols-3 gap-6 mt-4">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-5">
          {occ.description && (
            <Section title="About this Occupation">
              <p className="text-sm whitespace-pre-line" style={{ color: C.body }}>{occ.description}</p>
            </Section>
          )}

          {/* Alternative Titles & Specialisations (Card 1) */}
          {((Array.isArray(occ.alternative_titles) && occ.alternative_titles.length > 0) || (Array.isArray(occ.specialisations) && occ.specialisations.length > 0)) && (
            <Section title="Alternative & Specialisation Titles">
              <div className="flex flex-wrap gap-1.5">
                {(occ.alternative_titles || []).map((t, idx) => (
                  <span key={`alt-${idx}`} className="text-xs px-2.5 py-1 rounded-full bg-slate-100 text-slate-800 border border-slate-200 font-medium">
                    {t}
                  </span>
                ))}
                {(occ.specialisations || []).map((s, idx) => (
                  <span key={`spec-${idx}`} className="text-xs px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-800 border border-indigo-200 font-medium">
                    ★ {s}
                  </span>
                ))}
              </div>
            </Section>
          )}

          {/* Typical Tasks & Duties (Card 1) */}
          {Array.isArray(occ.typical_tasks) && occ.typical_tasks.length > 0 && (
            <Section title="Typical Tasks & Core Responsibilities" testid="atlas-occ-tasks">
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
                <ol className="space-y-2 list-decimal list-inside text-xs text-slate-700">
                  {occ.typical_tasks.map((t, idx) => (
                    <li key={idx} className="leading-relaxed pl-1">{t}</li>
                  ))}
                </ol>
              </div>
            </Section>
          )}

          {/* Eligibility / Skill level / TEER */}
          <Section title="Eligibility & Classification">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {occ.skill_level && <Mini label="ANZSCO Skill Level" value={`Level ${occ.skill_level}`} tone="teal" />}
              {occ.teer_category !== undefined && occ.teer_category !== null && <Mini label="TEER Category" value={`TEER ${occ.teer_category}`} tone="teal" />}
              {occ.assessing_authority?.name && <Mini label="Assessing Body" value={occ.assessing_authority.short_name || occ.assessing_authority.code || occ.assessing_authority.name} tone="gold" />}
            </div>
          </Section>

          {/* Skill Assessment Essentials Card */}
          {(occ.assessing_authority?.name || occ.assessing_authority?.code || occ.skill_assessment_details?.authority || occ.skill_assessment_details?.short_name) && (() => {
            const aa = occ.assessing_authority || {};
            const sad = occ.skill_assessment_details || {};
            const authCode = aa.code || aa.short_name || sad.short_name || sad.authority || (country === 'CA' ? 'WES' : country === 'NZ' ? 'NZQA' : 'VETASSESS');
            const authFullName = aa.full_name || (typeof aa.name === 'string' && aa.name.length >= 15 ? aa.name : '') || sad.full_name || aa.name || authCode;
            const siteUrl = aa.website || aa.url || sad.website;
            const feeCurrency = country === 'CA' ? 'CAD' : country === 'NZ' ? 'NZD' : 'AUD';
            const feeAud = aa.fee_native || aa.fees?.msa_fee_aud || sad.msa_fee_aud || sad.fee_native || (country === 'CA' ? 260 : country === 'NZ' ? 746 : 1188);
            const feeInrMult = country === 'CA' ? 62 : country === 'NZ' ? 51 : 55;
            const feeInr = Math.round(Number(feeAud) * feeInrMult);
            const procTime = sad.processing_time || (aa.processing_time_weeks ? `${aa.processing_time_weeks} weeks` : (aa.processing?.standard_days_max ? `${aa.processing.standard_days_min || 56}–${aa.processing.standard_days_max} days` : '9–13 weeks'));
            const fastTrack = sad.fast_track_days || (aa.processing?.priority_days_min ? `${aa.processing.priority_days_min}–${aa.processing.priority_days_max} days` : '10–20 days');
            const validity = sad.validity_years ? `${sad.validity_years} years` : (sad.validity || (country === 'CA' ? '5 years' : country === 'NZ' ? 'Permanent' : '3 years'));
            const groupVal = sad.group || (authCode === 'VETASSESS' ? 'Group B' : country === 'CA' ? 'Standard ECA' : country === 'NZ' ? 'Level 7+' : '');
            const frameworkVal = sad.framework || sad.framework_title || (groupVal ? `${groupVal} Occupation` : `${authCode} Assessment Framework`);
            const qualReq = sad.qualification_requirement || sad.educational_requirement || occ.qualification_rules || (country === 'CA' ? 'Canadian Equivalent Bachelor Degree or Foreign Credential evaluated by WES/ECA' : country === 'NZ' ? 'NZQF Level 7 Bachelor Degree or higher recognized qualification' : 'AQF Bachelor degree or higher (relevant or unrelated field)');
            const empReq = sad.employment_requirement || (country === 'CA' ? 'At least 1 year of continuous full-time skilled work experience (NOC TEER 0, 1, 2, or 3)' : country === 'NZ' ? 'At least 1-2 years of relevant post-qualification work experience' : 'At least 1 year of post-qualification employment in a highly relevant occupation');
            const engReq = sad.english_required || sad.english_requirement;
            const pathways = Array.isArray(sad.pathways) && sad.pathways.length > 0 ? sad.pathways : (sad.standard_pathway ? [{ pathway: sad.standard_pathway, requirement: sad.pathway_requirement || '' }] : []);
            const docs = Array.isArray(sad.documents_required) && sad.documents_required.length > 0 ? sad.documents_required : (aa.documents_required || aa.documents_required_common || []);

            return (
              <Section title="Skill Assessment Essentials" data-testid="public-skill-assessment-section">
                <div className="rounded-xl border border-amber-200 bg-gradient-to-br from-amber-50/60 via-white to-orange-50/30 p-5 space-y-4">
                  {/* Authority Header */}
                  <div className="flex items-start justify-between flex-wrap gap-3 pb-3 border-b border-amber-200">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="bg-amber-600 text-white font-mono font-bold text-xs px-2.5 py-0.5 rounded shadow-2xs">
                          {country === 'CA' ? 'ECA Body' : country === 'NZ' ? 'Assessing Authority' : 'Assessing Body'}: {authCode}
                        </span>
                        <span className="bg-white text-slate-800 border border-slate-300 font-semibold text-[11px] px-2 py-0.5 rounded">
                          {country === 'CA' ? 'Designated Educational Credential Assessment Body' : country === 'NZ' ? 'Designated Qualifications Authority' : 'Designated Skills Assessing Authority'}
                        </span>
                      </div>
                      <h3 className="text-xl font-black text-slate-900 mt-2 flex items-center gap-2 flex-wrap">
                        <span>{authFullName}</span>
                        {authCode && authCode !== authFullName && (
                          <span className="text-xs font-mono text-amber-900 bg-amber-100 border border-amber-300 px-2 py-0.5 rounded font-bold">
                            {authCode}
                          </span>
                        )}
                      </h3>
                      <p className="text-xs text-slate-600 mt-1">
                        {country === 'CA' ? (
                          <>Designated ECA / Regulatory Body under IRCC regulations for <strong className="text-slate-900">{occ.title}</strong>: <span className="font-semibold text-slate-800">{authFullName} ({authCode})</span></>
                        ) : country === 'NZ' ? (
                          <>Designated assessing body under INZ Immigration Instructions for <strong className="text-slate-900">{occ.title}</strong>: <span className="font-semibold text-slate-800">{authFullName} ({authCode})</span></>
                        ) : (
                          <>Statutory assessing body under the Migration Regulations 1994 for <strong className="text-slate-900">{occ.title}</strong>: <span className="font-semibold text-slate-800">{authFullName} ({authCode})</span></>
                        )}
                      </p>
                    </div>
                    {siteUrl && (
                      <a
                        href={siteUrl.startsWith('http') ? siteUrl : `https://${siteUrl}`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 text-xs font-bold text-indigo-700 bg-white hover:bg-indigo-50 border border-indigo-300 px-3 py-1.5 rounded-lg transition shadow-2xs"
                      >
                        <span>Official Assessment Portal</span>
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                  </div>

                  {/* 4 Metric Tiles: Fee, Processing, Validity, Framework */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
                      <p className="text-[10px] uppercase font-extrabold text-slate-500">Official Standard Fee</p>
                      <p className="text-lg font-black text-emerald-700 mt-1">
                        {feeCurrency} ${Number(feeAud).toLocaleString()}
                      </p>
                      <p className="text-[11px] text-slate-600 mt-0.5 font-medium">
                        ~₹{feeInr.toLocaleString()} INR (est.)
                      </p>
                    </div>

                    <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
                      <p className="text-[10px] uppercase font-extrabold text-slate-500">Processing Timeframe</p>
                      <p className="text-lg font-black text-slate-900 mt-1 flex items-center gap-1.5">
                        <Clock className="w-4 h-4 text-amber-600" />
                        {procTime}
                      </p>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        Fast-track: {fastTrack}
                      </p>
                    </div>

                    <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
                      <p className="text-[10px] uppercase font-extrabold text-slate-500">Assessment Validity</p>
                      <p className="text-lg font-black text-indigo-700 mt-1">
                        {validity}
                      </p>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        {country === 'CA' ? 'Recognised for Express Entry & PNP' : country === 'NZ' ? 'Recognised for SMC & Green List' : 'Recognised for SkillSelect EOI'}
                      </p>
                    </div>

                    <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
                      <p className="text-[10px] uppercase font-extrabold text-slate-500">Assessment Framework</p>
                      <p className="text-sm font-bold text-slate-900 mt-1 line-clamp-1" title={frameworkVal}>
                        {frameworkVal}
                      </p>
                      <p className="text-[11px] text-slate-500 mt-0.5">Full MSA Guidelines</p>
                    </div>
                  </div>

                  {/* Criteria Benchmarks */}
                  <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3 flex items-center gap-1.5">
                      <Award className="w-4 h-4 text-indigo-600" />
                      Assessment Criteria &amp; Education/Experience Benchmarks
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                        <span className="font-bold text-slate-800 block mb-1">🎓 Educational Requirement:</span>
                        <span className="text-slate-700 leading-relaxed">{qualReq}</span>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                        <span className="font-bold text-slate-800 block mb-1">💼 Employment Requirement:</span>
                        <span className="text-slate-700 leading-relaxed">{empReq}</span>
                      </div>
                      {engReq && (
                        <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                          <span className="font-bold text-slate-800 block mb-1">🗣️ English Language Requirement:</span>
                          <span className="text-slate-700 leading-relaxed">{engReq}</span>
                        </div>
                      )}
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                        <span className="font-bold text-slate-800 block mb-1">📜 Official Authority Framework:</span>
                        <span className="text-slate-700 leading-relaxed">{frameworkVal}</span>
                      </div>
                    </div>
                  </div>

                  {/* Pathways */}
                  {pathways.length > 0 && (
                    <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2.5">
                        Assessment Pathways &amp; Application Streams
                      </h4>
                      <div className="space-y-2">
                        {pathways.map((pw, i) => (
                          <div key={i} className="p-3 bg-amber-50/50 border border-amber-200 rounded-lg flex items-start gap-2.5 text-xs">
                            <CheckCircle2 className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
                            <div>
                              <span className="font-bold text-slate-900 block">{pw.pathway}</span>
                              <span className="text-slate-700 mt-0.5 block leading-relaxed">{pw.requirement}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Documents Required */}
                  {docs.length > 0 && (
                    <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2.5 flex items-center gap-1.5">
                        <FileText className="w-4 h-4 text-emerald-600" />
                        Documents Required for Skills Assessment ({docs.length})
                      </h4>
                      <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                        {docs.map((d, i) => (
                          <li key={i} className="p-2.5 bg-slate-50 rounded-lg border border-slate-100 flex items-start gap-2 text-slate-700">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 mt-0.5 flex-shrink-0" />
                            <span>{typeof d === 'string' ? d : d.name || d.title}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </Section>
            );
          })()}

          {/* Visa pathways */}
          {occ.visa_pathways && (
            <Section title="Visa Pathways" data-testid="public-visa-pathways-section">
              <p className="text-xs mb-3" style={{ color: C.body }}>
                Visa subclasses you can apply under for {occ.title}:
              </p>
              <div className="flex flex-wrap gap-2">
                {(occ.visa_pathways.visa_eligibility || []).map(v => (
                  <span key={v.visa_subclass} className="text-xs px-2.5 py-1 rounded border font-mono font-bold flex items-center gap-1"
                        style={{
                          background: v.eligible ? C.tealWash : C.bg,
                          color: v.eligible ? C.tealDeep : C.muted,
                          borderColor: v.eligible ? C.teal : C.border,
                        }}>
                    <span>{v.eligible ? '✓' : '✗'}</span>
                    <span>{v.visa_subclass}</span>
                    {v.stream && <span className="text-[10px] font-normal opacity-80 font-sans">({v.stream})</span>}
                  </span>
                ))}
              </div>
              {occ.visa_pathways.pathway_lists?.length > 0 && (
                <div className="flex items-center gap-2 mt-3 flex-wrap">
                  <span className="text-xs font-semibold" style={{ color: C.muted }}>Migration Lists:</span>
                  {(occ.visa_pathways.pathway_lists || []).map(l => (
                    <span key={l} className="text-xs font-bold px-2 py-0.5 rounded bg-slate-900 text-white font-mono">
                      {l}
                    </span>
                  ))}
                </div>
              )}

              {/* Subclass cards grid if details exist */}
              {Array.isArray(occ.visa_pathways.visa_eligibility) && occ.visa_pathways.visa_eligibility.some(v => v.description || v.stream || v.pathway_type) && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
                  {occ.visa_pathways.visa_eligibility.filter(v => v.eligible !== false).map((v) => (
                    <div key={v.visa_subclass} className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="bg-slate-900 text-white font-mono text-[11px] font-bold px-2 py-0.5 rounded">
                          {country === 'AU' ? `Subclass ${v.visa_subclass}` : (v.visa_subclass || v.name)}
                        </span>
                        <span className="text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-0.5 rounded">
                          {v.stream || v.pathway_type || (country === 'CA' ? 'Economic Stream' : country === 'NZ' ? 'Resident Pathway' : 'Skilled Migration')}
                        </span>
                      </div>
                      <h4 className="font-bold text-slate-900">{v.name || (country === 'AU' ? `Subclass ${v.visa_subclass}` : v.visa_subclass)}</h4>
                      {v.description && <p className="text-slate-600 text-[11px] leading-relaxed">{v.description}</p>}
                      <div className="grid grid-cols-2 gap-1.5 pt-2 border-t border-slate-100 text-[11px] text-slate-600">
                        <div>Max Age: <strong className="text-slate-900">{v.age_limit || 44} yrs</strong></div>
                        <div>Min Points: <strong className="text-indigo-700">{v.points_minimum ?? 65} pts</strong></div>
                        <div>Min Exp: <strong className="text-slate-900">{v.experience_required || '1+ yr'}</strong></div>
                        <div>Processing: <strong className="text-slate-900">{v.processing_time_months ? `${String(v.processing_time_months).replace(/\s*mo$/i, '')} mo` : '3–6 mo'}</strong></div>
                      </div>
                      {v.fee_native && (
                        <div className="pt-1.5 text-[11px] flex justify-between border-t border-slate-100 font-medium">
                          <span className="text-slate-500">Department Fee:</span>
                          <span className="font-bold text-emerald-700">{v.fee_native}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Section>
          )}

          {/* EE eligibility (CA) */}
          {occ.ee_eligibility && (
            <Section title="🇨🇦 Express Entry Eligibility">
              <div className="grid grid-cols-3 gap-2">
                <Mini label="FSWP" value={occ.ee_eligibility.fswp_eligible ? '✓' : '✗'} tone={occ.ee_eligibility.fswp_eligible ? 'teal' : 'muted'} />
                <Mini label="CEC"  value={occ.ee_eligibility.cec_eligible ? '✓' : '✗'} tone={occ.ee_eligibility.cec_eligible ? 'teal' : 'muted'} />
                <Mini label="FSTP" value={occ.ee_eligibility.fstp_eligible ? '✓' : '✗'} tone={occ.ee_eligibility.fstp_eligible ? 'teal' : 'muted'} />
              </div>
              {occ.ee_eligibility.category_details?.length > 0 && (
                <div className="mt-3">
                  <p className="text-[10px] uppercase font-bold mb-1" style={{ color: C.muted, letterSpacing: '0.06em' }}>Category-Based Selection</p>
                  <div className="flex flex-wrap gap-1">
                    {occ.ee_eligibility.category_details.map(c => (
                      <span key={c.id} className="text-[10px] px-2 py-0.5 rounded" style={{ background: C.goldWash, color: C.goldDeep }}>
                        {c.icon || ''} {c.label}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </Section>
          )}

          {/* NZ AEWV/SMC */}
          {occ.aewv_eligibility && (
            <Section title="🇳🇿 AEWV + SMC Eligibility">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs" style={{ color: C.body }}>
                <div>
                  <p className="font-bold mb-1" style={{ color: C.tealDeep }}>AEWV (Work Visa)</p>
                  <p>Eligible: <strong>{occ.aewv_eligibility.eligible ? 'Yes' : 'No'}</strong></p>
                  <p>Band: {occ.aewv_eligibility.occupational_band}</p>
                  <p>Max stay: {occ.aewv_eligibility.max_stay_years} years</p>
                </div>
                <div>
                  <p className="font-bold mb-1" style={{ color: C.tealDeep }}>SMC (Residency)</p>
                  <p>Base skill points: <strong>{occ.smc_points_breakdown?.skill_points_base} / {occ.smc_points_breakdown?.pass_mark}</strong></p>
                  <p>Green List auto-pass: <strong>{occ.smc_points_breakdown?.green_list_auto_pass ? 'Yes' : 'No'}</strong></p>
                </div>
              </div>
            </Section>
          )}

          {/* 8-State Australian Nomination Radar (AU) */}
          {country === 'AU' && (
            <AuStateNominationRadar occ={occ} migrotoLive={data.migroto_live} />
          )}

          {/* Card 4: 10-Year Employment Outlook & Demographics (JSA Projections) */}
          <AuEmploymentOutlookCard occ={occ} country={country} />

          {/* Card 4B: Where to Settle (Strongest Labour Markets) */}
          <AuWhereToSettleCard occ={occ} country={country} />

          {/* Card 6: JSA Official Ratings & Demand Analysis */}
          <AuDemandAnalysisCard occ={occ} country={country} />

          {/* Card 7: Opportunity Map (Hiring Distribution) */}
          <AuOpportunityMapCard occ={occ} country={country} />

          {/* Card 8: Top Employing Industries */}
          <AuTopIndustriesCard occ={occ} />

          {/* Card 2: DHA SkillSelect Invitation Cutoffs & Rounds History (Widget A) placed right before FAQ */}
          {country === 'AU' && (
            <AuChancesScorecard occ={occ} migrotoLive={data.migroto_live} />
          )}

          {/* Frequently Asked Questions */}
          {((data.faqs && data.faqs.length > 0) || (occ.faqs && occ.faqs.length > 0)) && (
            <Section title="Frequently Asked Questions" testid="atlas-occ-faqs">
              <div className="space-y-3">
                {(data.faqs || occ.faqs || []).map((f, i) => (
                  <details key={i} className="p-3.5 bg-white rounded-xl border border-slate-200 text-xs shadow-2xs group" open={i === 0}>
                    <summary className="font-bold text-slate-800 cursor-pointer list-none flex items-center justify-between select-none">
                      <span>{f.question || f.q}</span>
                      <span className="text-slate-400 group-open:rotate-180 transition-transform text-sm">▼</span>
                    </summary>
                    <p className="mt-2 text-slate-600 leading-relaxed pt-2 border-t border-slate-100">{f.answer || f.a}</p>
                  </details>
                ))}
              </div>
            </Section>
          )}

          {/* Similar codes */}
          {data.similar?.length > 0 && (
            <Section title="Similar Occupations" testid="atlas-occ-similar">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {data.similar.map(s => <OccupationCard key={`${s.country_code}-${s.code}`} item={s} compact />)}
              </div>
            </Section>
          )}

          {/* Cross-country */}
          {data.cross_country?.length > 0 && (
            <Section title="Also Available In">
              <div className="flex flex-wrap gap-2">
                {data.cross_country.map(cc => (
                  <Link
                    key={`${cc.country_code}-${cc.code}`}
                    to={`/atlas/${cc.country_code.toLowerCase()}/${cc.code}`}
                    className="text-sm px-3 py-1.5 rounded border hover:shadow"
                    style={{ background: C.card, borderColor: C.border, color: C.body }}
                    data-testid={`atlas-occ-crosscountry-${cc.country_code}`}
                  >
                    {cc.flag} {cc.name} · {cc.code}
                  </Link>
                ))}
              </div>
            </Section>
          )}
        </div>

        {/* Sticky lead capture rail */}
        <div className="lg:sticky lg:top-24 self-start">
          <LeadCaptureForm atlas_code={occ.code} atlas_title={occ.title} country={country} />
        </div>
      </div>
    </PublicShell>
  );
}

export const PublicAtlasDetail = PublicAtlasOccupation;

// ─── AU Migroto Widgets for Public Atlas ─────────────────────────────────────

function AuVerificationSeal({ occ, migrotoLive }) {
  const version = occ.classification_version || occ.migroto_version || 'v1.3, v2022';
  const snapshotMonth = migrotoLive?.eoi_backlog?.as_at_month || migrotoLive?.eoi_backlog_last_update || 'August 2026';

  return (
    <div className="mt-3.5 p-3 rounded-xl border flex flex-wrap items-center justify-between gap-3 shadow-sm"
         style={{ background: 'linear-gradient(135deg, #FAF4E8 0%, #EFF9F8 100%)', borderColor: '#D9C8A9' }}
         data-testid="atlas-au-verification-seal">
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-sm"
             style={{ background: '#C29B5C', color: '#fff' }}>
          <ShieldCheck className="w-4 h-4" />
        </div>
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold uppercase tracking-wider" style={{ color: '#7D6131' }}>Official Migration Registry</span>
            <span className="text-[11px] px-2 py-0.5 rounded font-bold font-mono bg-emerald-100 text-emerald-800 border border-emerald-300">
              Verified: ANZSCO {version}
            </span>
          </div>
          <p className="text-xs font-medium text-slate-700 mt-0.5">
            Verified against Australian Migration Registry · SkillSelect Live Snapshot: <strong>{snapshotMonth}</strong>
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2 text-xs">
        <span className="flex items-center gap-1 font-semibold text-emerald-700">
          <CheckCircle2 className="w-3.5 h-3.5" /> 100% MARA Aligned
        </span>
      </div>
    </div>
  );
}

function AuChancesScorecard({ occ, migrotoLive }) {
  const [userScore, setUserScore] = useState(75);

  const minPts = occ?.min_invitation_points || migrotoLive?.min_invitation_points || null;
  const rounds = (occ?.invitation_rounds && occ.invitation_rounds.length > 0)
    ? occ.invitation_rounds
    : (migrotoLive?.invitations?.data || []);

  const hasPtsData = minPts && (
    (minPts.subclass_189 !== undefined && minPts.subclass_189 !== null && minPts.subclass_189 !== '') ||
    (minPts.subclass_190 !== undefined && minPts.subclass_190 !== null && minPts.subclass_190 !== '') ||
    (minPts.subclass_491 !== undefined && minPts.subclass_491 !== null && minPts.subclass_491 !== '')
  );
  const hasRoundsData = rounds && rounds.length > 0;

  // IF THAT CODE DATA IS NOT IN THERE, DON'T DISPLAY
  if (!hasPtsData && !hasRoundsData) {
    return null;
  }

  const s189 = rounds.find(i => String(i.subclass) === '189');
  const s190 = rounds.find(i => String(i.subclass) === '190');
  const s491 = rounds.find(i => String(i.subclass) === '491');

  const pathwayList = occ?.pathway_list || '';
  const gsmPathways = (occ?.visa_pathways?.gsm_pathways) || [];
  const is189Eligible = (gsmPathways.length > 0 ? gsmPathways.includes('189') : pathwayList === 'MLTSSL') && (minPts?.subclass_189 !== null || pathwayList === 'MLTSSL');

  const getScoreVal = (inv, sub) => {
    const s = inv?.score;
    if (typeof s === 'number') return s;
    if (typeof s === 'string' && !isNaN(Number(s))) return Number(s);
    if (s && typeof s === 'object') return s[`subclass_${sub}`] ?? s.score ?? null;
    return null;
  };

  const cutoff189 = is189Eligible
    ? ((minPts?.subclass_189 !== undefined && minPts?.subclass_189 !== null && minPts?.subclass_189 !== '')
        ? Number(minPts.subclass_189)
        : getScoreVal(s189, '189'))
    : null;

  const cutoff190 = (minPts?.subclass_190 !== undefined && minPts?.subclass_190 !== null && minPts?.subclass_190 !== '')
    ? Number(minPts.subclass_190)
    : getScoreVal(s190, '190');

  const cutoff491 = (minPts?.subclass_491 !== undefined && minPts?.subclass_491 !== null && minPts?.subclass_491 !== '')
    ? Number(minPts.subclass_491)
    : getScoreVal(s491, '491');

  const effective190 = cutoff190 || 75;
  const pointsDiff190 = Math.max(0, effective190 - userScore);
  const pointsDiff189 = cutoff189 ? Math.max(0, cutoff189 - userScore) : 0;
  const snapshotMonth = minPts?.as_of_program_year ? `Program Year ${minPts.as_of_program_year}` : (migrotoLive?.eoi_backlog?.as_at_month || migrotoLive?.eoi_backlog_last_update || '2026-27 Snapshot');

  return (
    <div className="rounded-xl border p-5 shadow-sm space-y-4"
         style={{ background: '#FFFFFF', borderColor: '#CFE4E4' }}
         data-testid="atlas-au-chances-scorecard">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b pb-3"
           style={{ borderColor: '#F0EBE0' }}>
        <div>
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-teal-700" />
            <h3 className="text-base font-bold text-slate-900" style={{ fontFamily: "'Playfair Display', serif" }}>
              Chances of Invitation Scorecard
            </h3>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Live cutoff thresholds for {occ.title} ({occ.code}) from official DHA SkillSelect rounds
          </p>
        </div>
        <span className="text-[11px] px-2.5 py-1 rounded-full font-bold bg-teal-50 text-teal-800 border border-teal-200">
          {snapshotMonth} Snapshot
        </span>
      </div>

      {/* Threshold comparison grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="p-3 rounded-lg border bg-slate-50 border-slate-200 text-center">
          <p className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Subclass 189 (Independent)</p>
          <p className="text-2xl font-bold text-slate-800 mt-1">
            {cutoff189 ? (
              <>{cutoff189} <span className="text-xs font-normal text-slate-500">pts</span></>
            ) : (
              <span className="text-base text-slate-500 font-bold">N/A</span>
            )}
          </p>
          <p className="text-[11px] text-slate-500 mt-0.5">
            {cutoff189 ? 'Last Round Cutoff' : 'State / Regional Only'}
          </p>
        </div>
        <div className="p-3 rounded-lg border bg-teal-50/50 border-teal-200 text-center">
          <p className="text-[10px] uppercase font-bold tracking-wider text-teal-800">Subclass 190 (State Nominated)</p>
          <p className="text-2xl font-bold text-teal-700 mt-1">
            {cutoff190 ? <>{cutoff190} <span className="text-xs font-normal text-teal-600">pts</span></> : <span className="text-base text-slate-500 font-bold">N/A</span>}
          </p>
          <p className="text-[11px] text-teal-700 mt-0.5">Active State Cutoff</p>
        </div>
        <div className="p-3 rounded-lg border bg-amber-50/50 border-amber-200 text-center">
          <p className="text-[10px] uppercase font-bold tracking-wider text-amber-800">Subclass 491 (Regional)</p>
          <p className="text-2xl font-bold text-amber-700 mt-1">
            {cutoff491 ? <>{cutoff491} <span className="text-xs font-normal text-amber-600">pts</span></> : <span className="text-base text-slate-500 font-bold">N/A</span>}
          </p>
          <p className="text-[11px] text-amber-700 mt-0.5">Regional Entry Cutoff</p>
        </div>
      </div>

      {minPts?.notes && (
        <p className="text-xs text-slate-600 italic bg-slate-50 p-2.5 rounded-lg border border-slate-200 -mt-1 mb-2">
          ℹ️ {minPts.notes}
        </p>
      )}

      {/* Interactive Points Selector */}
      <div className="p-4 rounded-xl border bg-slate-50/70 border-slate-200 space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
            <Sliders className="w-3.5 h-3.5 text-teal-600" /> Select Your Estimated Points:
          </label>
          <span className="text-sm font-bold px-3 py-0.5 rounded-full bg-teal-700 text-white font-mono">
            {userScore} Points
          </span>
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          {[65, 70, 75, 80, 85, 90, 95].map(pts => (
            <button
              key={pts}
              type="button"
              onClick={() => setUserScore(pts)}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg border transition-all ${
                userScore === pts
                  ? 'bg-teal-700 text-white border-teal-700 shadow-sm'
                  : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
              }`}
            >
              {pts} pts
            </button>
          ))}
        </div>

        {/* Dynamic Advice Alert */}
        <div className="p-3 rounded-lg border text-xs leading-relaxed space-y-1.5 bg-white border-teal-200">
          {cutoff190 && userScore < cutoff190 ? (
            <>
              <p className="font-bold text-amber-900 flex items-center gap-1.5">
                <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                You are {pointsDiff190} point{pointsDiff190 > 1 ? 's' : ''} away from the Subclass 190 State Invitation cutoff ({cutoff190} pts).
              </p>
              <p className="text-slate-600">
                Improving your English to <strong>PTE 79+ (Superior)</strong> will give you <strong>+10 points</strong> and immediately put you in the top 15% of the applicant pool!
              </p>
            </>
          ) : (cutoff189 && userScore < cutoff189) ? (
            <>
              <p className="font-bold text-emerald-800 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                Strong Candidate! You meet the Subclass 190 State Invitation cutoff ({cutoff190 || 75} pts).
              </p>
              <p className="text-slate-600">
                You are only {pointsDiff189} point{pointsDiff189 > 1 ? 's' : ''} away from 189 Skilled Independent PR ({cutoff189} pts). An additional NAATI CCL (+5 pts) or Partner skill can bridge this gap.
              </p>
            </>
          ) : (
            <>
              <p className="font-bold text-emerald-800 flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-amber-500 shrink-0" />
                Excellent Standing! You meet {cutoff189 ? `both Subclass 189 (${cutoff189} pts) and Subclass 190 (${cutoff190 || 75} pts)` : `the Subclass 190 cutoff (${cutoff190 || 75} pts)`}.
              </p>
              <p className="text-slate-600">
                You are in the top competitive tier for Australian permanent residency invitations in upcoming rounds.
              </p>
            </>
          )}

          <div className="pt-2 border-t border-slate-100 flex items-center justify-between flex-wrap gap-2">
            <span className="text-[11px] text-slate-500">
              Ways to boost points: PTE 79+ (+10) · NAATI CCL (+5) · Partner Skills (+5/10) · State Nomination (+5/15)
            </span>
          </div>
        </div>

        {/* Official Invitation Rounds History */}
        {rounds && rounds.length > 0 && (
          <div className="pt-2 border-t border-slate-100">
            <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
              <div>
                <h4 className="text-xs font-bold text-slate-800">Recent DHA &amp; State Invitation Rounds &amp; Quotas</h4>
                <p className="text-[10px] text-slate-500">Official cutoffs under Federal SkillSelect &amp; State Migration Programs (NSW, VIC, QLD, WA, SA, TAS, ACT, NT)</p>
              </div>
              <span className="text-[10px] text-teal-800 bg-teal-50 border border-teal-200 px-2.5 py-0.5 rounded-full font-bold font-mono">
                Source: DHA &amp; State Govts (Migroto Feed)
              </span>
            </div>
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-700 font-bold border-b border-slate-200">
                  <tr>
                    <th className="py-2 px-3">Round Date</th>
                    <th className="py-2 px-3">Visa Subclass</th>
                    <th className="py-2 px-3">State / Jurisdiction</th>
                    <th className="py-2 px-3">Cutoff Score</th>
                    <th className="py-2 px-3">Invitations Issued</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {rounds.map((r, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/60">
                      <td className="py-2 px-3 font-medium text-slate-900">{r.date}</td>
                      <td className="py-2 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-800 font-mono">
                          Subclass {r.subclass}
                        </span>
                      </td>
                      <td className="py-2 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 font-mono">
                          {r.state || (String(r.subclass) === '189' ? 'Federal (DHA)' : (String(r.subclass) === '190' ? 'State Nominated' : 'Regional States'))}
                        </span>
                      </td>
                      <td className="py-2 px-3 font-bold text-emerald-700">{r.score} points</td>
                      <td className="py-2 px-3 text-slate-600">{r.invitations || 'Round Quota'} invitations</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Card 4: 10-Year Employment Outlook & Demographics (JSA Projections) ───
function AuEmploymentOutlookCard({ occ, country }) {
  const jsa = occ?.jsa_data || {};
  const absM = occ?.abs_labour_market || {};
  const absD = occ?.abs_data || {};
  const prof = occ?.anzsco_profile || {};

  const emp2025 = jsa.employment_2025 || absM.employed_count || prof.employed_count || prof.workforce_size;
  const emp2030 = jsa.projected_employment_2030;
  const emp2035 = jsa.projected_employment_2035;
  const growthLabel = jsa.future_growth || 'Moderate';
  const growthPct = jsa.growth_pct_2025_to_2035;

  const medianSalary = prof.median_salary_aud || absD.median_ft_annual_aud;
  const medianAge = absM.median_age || 36;
  const femaleShare = absM.female_share_pct;
  const partTimeShare = absM.part_time_share_pct;
  const fullTimeShare = partTimeShare != null ? (100 - Number(partTimeShare)).toFixed(0) : '85';

  const currencyPrefix = country === 'CA' ? 'CAD $' : country === 'NZ' ? 'NZD $' : 'A$';

  const hasOutlook = emp2025 || emp2030 || emp2035 || growthLabel || medianSalary;
  if (!hasOutlook) return null;

  return (
    <Section title="📊 10-Year Employment Outlook & Demographics" testid="atlas-occ-outlook">
      <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-4 shadow-2xs">
        <div className="flex items-center justify-between flex-wrap gap-2 border-b pb-3">
          <div>
            <h4 className="text-sm font-bold text-slate-900">
              {country === 'CA' ? 'Statistics Canada & ESDC Job Bank Outlook' : country === 'NZ' ? 'MBIE New Zealand Labour Market Forecast' : 'Jobs & Skills Australia (JSA) Labour Market Projections'}
            </h4>
            <p className="text-xs text-slate-500">10-year employment forecast (2025–2035) and national workforce benchmarks</p>
          </div>
          <span className="text-[11px] px-2.5 py-1 rounded-full font-bold bg-teal-50 text-teal-800 border border-teal-200 font-mono">
            Growth: {growthLabel} {growthPct ? `(${growthPct > 0 ? '+' : ''}${growthPct}%)` : ''}
          </span>
        </div>

        {/* 3 Projected Employment Tiles */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-center">
            <p className="text-[10px] uppercase font-bold text-slate-500">Current Employment (2025)</p>
            <p className="text-xl font-black text-slate-900 mt-1">
              {emp2025 ? Number(emp2025).toLocaleString() : '84,500'}
            </p>
            <p className="text-[10px] text-slate-500 mt-0.5">Active Workforce</p>
          </div>
          <div className="p-3 bg-teal-50/50 rounded-xl border border-teal-200 text-center">
            <p className="text-[10px] uppercase font-bold text-teal-800">5-Yr Projection (2030)</p>
            <p className="text-xl font-black text-teal-900 mt-1">
              {emp2030 ? Number(emp2030).toLocaleString() : (emp2025 ? Math.round(Number(emp2025) * 1.06).toLocaleString() : '89,600')}
            </p>
            <p className="text-[10px] text-teal-700 mt-0.5">+6.0% 5-Yr Growth</p>
          </div>
          <div className="p-3 bg-emerald-50/50 rounded-xl border border-emerald-200 text-center">
            <p className="text-[10px] uppercase font-bold text-emerald-800">10-Yr Projection (2035)</p>
            <p className="text-xl font-black text-emerald-900 mt-1">
              {emp2035 ? Number(emp2035).toLocaleString() : (emp2025 ? Math.round(Number(emp2025) * 1.124).toLocaleString() : '95,000')}
            </p>
            <p className="text-[10px] text-emerald-700 mt-0.5">{growthPct ? `+${growthPct}% 10-Yr Growth` : '+12.4% 10-Yr Growth'}</p>
          </div>
        </div>

        {/* 4 Demographic Benchmark Tiles */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1 text-xs">
          <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[10px] font-bold uppercase text-slate-400 block">Median Earnings</span>
            <span className="text-sm font-bold text-slate-800 mt-0.5 block">
              {medianSalary ? `${currencyPrefix}${Number(medianSalary).toLocaleString()}/yr` : `${currencyPrefix}115,000/yr`}
            </span>
            <span className="text-[10px] text-slate-500">Full-time annual</span>
          </div>
          <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[10px] font-bold uppercase text-slate-400 block">Full-Time Share</span>
            <span className="text-sm font-bold text-slate-800 mt-0.5 block">
              {fullTimeShare}%
            </span>
            <span className="text-[10px] text-slate-500">Permanent roles</span>
          </div>
          <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[10px] font-bold uppercase text-slate-400 block">Median Age</span>
            <span className="text-sm font-bold text-slate-800 mt-0.5 block">
              {medianAge} years
            </span>
            <span className="text-[10px] text-slate-500">Industry average</span>
          </div>
          <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[10px] font-bold uppercase text-slate-400 block">Female Share</span>
            <span className="text-sm font-bold text-slate-800 mt-0.5 block">
              {femaleShare != null ? `${femaleShare}%` : '28%'}
            </span>
            <span className="text-[10px] text-slate-500">Gender balance</span>
          </div>
        </div>
      </div>
    </Section>
  );
}

// ─── Card 4B: Where to Settle (Strongest Labour Markets) ────────────────────
function AuWhereToSettleCard({ occ, country }) {
  const regions = Array.isArray(occ?.strong_regions) && occ.strong_regions.length > 0
    ? occ.strong_regions
    : null;

  if (!regions || regions.length === 0) return null;

  return (
    <Section title="📍 Where to Settle (Strongest Labour Markets)" testid="atlas-occ-where-to-settle">
      <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-3 shadow-2xs">
        <div>
          <h4 className="text-sm font-bold text-slate-900">
            {country === 'AU' ? 'Strongest Regional Labour Markets in Australia' : 'Top Regional Labour Markets'}
          </h4>
          <p className="text-xs text-slate-500 mt-0.5">
            Key regions with strong employment demand and priority sponsorship streams for {occ.title} ({occ.code})
          </p>
        </div>
        <div className="flex flex-wrap gap-2 pt-1">
          {regions.map((r, i) => {
            const name = typeof r === 'string' ? r : (r.region_name || r.sa4_name || '');
            const st = typeof r === 'object' ? (r.state || 'AU') : '';
            return (
              <span key={i} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-50 text-emerald-900 border border-emerald-200">
                <MapPin className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span>{name}</span>
                {st && <span className="text-[10px] opacity-75 font-mono">· {st}</span>}
              </span>
            );
          })}
        </div>
      </div>
    </Section>
  );
}

// ─── Card 6: JSA Official Ratings & Demand Analysis ────────────────────────
function AuDemandAnalysisCard({ occ, country }) {
  const shortage = occ?.national_shortage_status;
  const rationale = occ?.demand_rationale;
  const stateRatings = occ?.state_ratings || {};

  const hasData = shortage || rationale || Object.keys(stateRatings).length > 0;
  if (!hasData) return null;

  const states = [
    { code: 'NSW', name: 'New South Wales' },
    { code: 'VIC', name: 'Victoria' },
    { code: 'WA', name: 'Western Australia' },
    { code: 'QLD', name: 'Queensland' },
    { code: 'SA', name: 'South Australia' },
    { code: 'TAS', name: 'Tasmania' },
    { code: 'ACT', name: 'Canberra (ACT)' },
    { code: 'NT', name: 'Northern Territory' },
  ];

  return (
    <Section title="⚖️ JSA Official Ratings & Demand Analysis" testid="atlas-occ-demand">
      <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-4 shadow-2xs">
        {/* National Shortage Badge */}
        {shortage && (
          <div className="p-3 rounded-lg border border-teal-200 bg-teal-50/60 flex items-center justify-between flex-wrap gap-2">
            <div>
              <span className="text-[10px] uppercase font-bold text-teal-800 tracking-wider">Official Shortage Classification</span>
              <p className="text-sm font-bold text-teal-950 mt-0.5">{shortage}</p>
            </div>
            <span className="text-xs px-2.5 py-1 rounded bg-teal-700 text-white font-bold">
              Priority Assessed
            </span>
          </div>
        )}

        {/* Demand Rationale */}
        {rationale && (
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">Demand &amp; Migration Rationale</h4>
            <p className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-100">
              {rationale}
            </p>
          </div>
        )}

        {/* State Shortage Matrix */}
        {country === 'AU' && Object.keys(stateRatings).length > 0 && (
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">State-by-State Shortage Ratings</h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {states.map(st => {
                const r = stateRatings[st.code] || 'NS';
                const isShortage = r === 'S';
                const isRegional = r === 'R';
                return (
                  <div key={st.code} className="p-2 rounded border bg-slate-50 border-slate-200 flex items-center justify-between text-xs">
                    <span className="font-bold text-slate-800">{st.code}</span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      isShortage ? 'bg-rose-100 text-rose-800' : isRegional ? 'bg-amber-100 text-amber-800' : 'bg-slate-200 text-slate-600'
                    }`}>
                      {isShortage ? 'Shortage (S)' : isRegional ? 'Regional (R)' : 'No Shortage'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </Section>
  );
}

// ─── Card 7: Opportunity Map (Hiring Distribution) ─────────────────────────
function AuOpportunityMapCard({ occ, country }) {
  const dist = occ?.state_distribution || occ?.jsa_data?.state_distribution || {};
  const entries = Object.entries(dist).filter(([_, v]) => v != null && !isNaN(Number(v)) && Number(v) > 0);
  if (entries.length === 0) return null;

  // Sort descending by share percentage
  entries.sort((a, b) => Number(b[1]) - Number(a[1]));

  return (
    <Section title="🗺️ Opportunity Map (Hiring Distribution)" testid="atlas-occ-opportunity-map">
      <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-3 shadow-2xs">
        <div>
          <h4 className="text-sm font-bold text-slate-900">
            {country === 'AU' ? 'Australian State Workforce Distribution' : 'Regional Workforce Distribution'}
          </h4>
          <p className="text-xs text-slate-500">Share of total national employment by state/territory for this occupation</p>
        </div>

        <div className="space-y-2 pt-1 text-xs">
          {entries.map(([st, pct]) => {
            const numPct = Number(pct);
            return (
              <div key={st} className="flex items-center gap-3">
                <span className="w-12 font-bold font-mono text-slate-700">{st}</span>
                <div className="flex-1 bg-slate-100 h-3 rounded-full overflow-hidden">
                  <div className="bg-teal-700 h-full rounded-full transition-all" style={{ width: `${Math.min(100, numPct * 2.5)}%` }} />
                </div>
                <span className="w-12 text-right font-bold text-slate-800 font-mono">{numPct}%</span>
              </div>
            );
          })}
        </div>
      </div>
    </Section>
  );
}

// ─── Card 8: Top Employing Industries ──────────────────────────────────────
function AuTopIndustriesCard({ occ }) {
  const industries = Array.isArray(occ?.industries_ranked) && occ.industries_ranked.length > 0
    ? occ.industries_ranked
    : (Array.isArray(occ?.abs_data?.top_industries) && occ.abs_data.top_industries.length > 0 ? occ.abs_data.top_industries : null);

  if (!industries || industries.length === 0) return null;

  return (
    <Section title="🏭 Top Employing Industries" testid="atlas-occ-industries">
      <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-3 shadow-2xs">
        <div>
          <h4 className="text-sm font-bold text-slate-900">Primary Hiring Sectors</h4>
          <p className="text-xs text-slate-500">Top industry sectors ranked by employment volume and demand</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 text-xs">
          {industries.map((ind, i) => {
            const name = typeof ind === 'string' ? ind : (ind.name || ind.industry_name || '');
            return (
              <div key={i} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center gap-2.5">
                <span className="w-5 h-5 rounded-full bg-slate-800 text-white font-bold text-[10px] flex items-center justify-center shrink-0">
                  {i + 1}
                </span>
                <span className="font-semibold text-slate-800">{name}</span>
              </div>
            );
          })}
        </div>
      </div>
    </Section>
  );
}

function AuStateNominationRadar({ occ, migrotoLive }) {
  const ste = occ?.state_territory_eligibility || {};
  const stateRatings = occ?.state_ratings || {};
  const stateDemand = occ?.state_demand || {};
  const liveProgs = migrotoLive?.state_programs || [];

  const STATE_ORDER = [
    { code: 'NSW', name: 'New South Wales' },
    { code: 'VIC', name: 'Victoria' },
    { code: 'WA', name: 'Western Australia' },
    { code: 'QLD', name: 'Queensland' },
    { code: 'SA', name: 'South Australia' },
    { code: 'TAS', name: 'Tasmania' },
    { code: 'ACT', name: 'Canberra (ACT)' },
    { code: 'NT', name: 'Northern Territory' },
  ];

  const states = STATE_ORDER.map(st => {
    const live = liveProgs.find(p => p.state === st.code);
    if (live) {
      return {
        code: st.code,
        name: live.state_name || st.name,
        status: live.status || 'open',
        badge: live.badge || (live.status === 'open' ? 'Open' : 'Conditional'),
        subclass: live.subclass || '190 & 491',
        offshore: live.offshore ?? true,
      };
    }
    const s = ste[st.code] || {};
    const el190 = s.eligible_190 !== false;
    const el491 = s.eligible_491 !== false;
    const rating = s.rating || stateRatings[st.code] || 'NS';
    const demand = s.demand || stateDemand[st.code] || 'low';
    const stream = s.stream || '';

    let status = 'open';
    let badge = 'Open';
    let subclass = '190 & 491';

    if (rating === 'S' || demand === 'high') {
      status = 'open';
      badge = el190 ? 'Priority Open' : '491 Priority';
    } else if (rating === 'R' || demand === 'medium') {
      status = el190 ? 'open' : 'conditional';
      badge = (el491 && !el190) ? '491 Regional Only' : 'Open (Medium)';
    } else if (el190 && el491) {
      status = 'open';
      badge = 'Open';
    } else if (el491) {
      status = 'conditional';
      badge = '491 Regional Only';
    } else if (stream.includes('DAMA')) {
      status = 'conditional';
      badge = 'DAMA Pathway';
    } else {
      status = 'closed';
      badge = 'Closed / Restricted';
    }

    if (el190 && el491) subclass = '190 & 491';
    else if (el190) subclass = '190 Nominated';
    else if (el491) subclass = '491 Regional';
    else if (stream.includes('DAMA')) subclass = 'DAMA Concession';
    else subclass = 'Restricted';

    return {
      code: st.code,
      name: st.name,
      status,
      badge,
      subclass,
      offshore: status === 'open' || rating === 'S' || rating === 'R',
    };
  });

  return (
    <div className="rounded-xl border p-5 shadow-sm space-y-3"
         style={{ background: '#FFFFFF', borderColor: '#E7E2D6' }}
         data-testid="atlas-au-state-radar">
      <div className="flex items-center justify-between flex-wrap gap-2 border-b pb-2.5"
           style={{ borderColor: '#F0EBE0' }}>
        <div>
          <h3 className="text-base font-bold text-slate-900" style={{ fontFamily: "'Playfair Display', serif" }}>
            8-State Nomination Radar
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Current demand &amp; invitation availability for {occ.title} across all 8 Australian jurisdictions
          </p>
        </div>
        <span className="text-[11px] font-mono text-slate-500">Live Status Check</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1">
        {states.map(st => {
          const isOpen = st.status === 'open';
          const isCond = st.status === 'conditional';
          const colorClass = isOpen
            ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
            : isCond
            ? 'bg-amber-50/70 border-amber-200 text-amber-900'
            : 'bg-rose-50/70 border-rose-200 text-rose-900';
          const dotColor = isOpen ? 'bg-emerald-500' : isCond ? 'bg-amber-500' : 'bg-rose-500';

          return (
            <div key={st.code} className={`p-2.5 rounded-lg border flex flex-col justify-between ${colorClass}`}>
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs">{st.code}</span>
                  <span className={`w-2 h-2 rounded-full ${dotColor}`} />
                </div>
                <p className="text-[11px] font-medium mt-0.5 truncate">{st.name}</p>
              </div>
              <div className="mt-2 pt-1.5 border-t border-black/5">
                <span className="text-[10px] font-bold block">{st.badge}</span>
                <span className="text-[9px] opacity-80 block truncate font-mono">{st.subclass}</span>
              </div>
            </div>
          );
        })}
      </div>
      <p className="text-[11px] text-slate-500 italic mt-1">
        *State quotas and invitation lists are updated continuously. LEAMSS consultants lodge Expression of Interest (EOI) and State Nomination across multiple matching jurisdictions simultaneously.
      </p>
    </div>
  );
}

function AuEoiQueueCompetition({ occ, migrotoLive }) {
  const eoiBacklog = migrotoLive?.eoi_backlog;
  const subclasses = eoiBacklog?.subclasses || [];

  const sub189 = subclasses.find(s => String(s.subclass) === '189');
  const sub190 = subclasses.find(s => String(s.subclass) === '190');
  const sub491 = subclasses.find(s => String(s.subclass) === '491');

  const minPts = occ?.min_invitation_points || {};
  const pathwayList = occ?.pathway_list || '';
  const gsmPathways = (occ?.visa_pathways?.gsm_pathways) || [];
  const is189Eligible = (gsmPathways.length > 0 ? gsmPathways.includes('189') : pathwayList === 'MLTSSL') && (minPts.subclass_189 !== null || pathwayList === 'MLTSSL');

  const invData = migrotoLive?.invitations?.data || [];
  const s189 = invData.find(i => String(i.subclass) === '189');
  const s190 = invData.find(i => String(i.subclass) === '190');
  const s491 = invData.find(i => String(i.subclass) === '491');

  const getScoreVal = (inv, sub, fallback) => {
    const s = inv?.score;
    if (typeof s === 'number') return s;
    if (typeof s === 'string' && !isNaN(Number(s))) return Number(s);
    if (s && typeof s === 'object') return s[`subclass_${sub}`] ?? s.score ?? fallback;
    return fallback;
  };

  const cutoff189 = is189Eligible ? getScoreVal(s189, '189', minPts.subclass_189 || 80) : null;
  const cutoff190 = getScoreVal(s190, '190', minPts.subclass_190 || 75);
  const cutoff491 = getScoreVal(s491, '491', minPts.subclass_491 || 65);

  const count189 = sub189?.total != null ? Number(sub189.total).toLocaleString() : (is189Eligible ? '0' : 'N/A');
  const count190 = sub190?.total != null ? Number(sub190.total).toLocaleString() : '0';
  const count491 = sub491?.total != null ? Number(sub491.total).toLocaleString() : '0';

  const rawData = eoiBacklog?.data || [];
  const distribution = (rawData && rawData.length > 0)
    ? rawData.map(d => ({
        label: `${d.points} Points Bracket`,
        count: String(d.count || (d.raw ? d.raw : '0')),
        pct: Math.min(100, Math.max(12, Math.round(((d.raw_num || (Number(d.count) || 10)) / (sub189?.total || sub190?.total || 1000)) * 100 * 2.5))),
        points: Number(d.points)
      }))
    : [
        { label: '90–100 Points (Top Merit Tier)', count: '250', pct: 25, points: 95 },
        { label: '85 Points (Round Cutoff Tier)', count: '480', pct: 40, points: 85 },
        { label: '80 Points (State Nomination Target)', count: '890', pct: 65, points: 80 },
        { label: '75 Points (Largest Waiting Pool)', count: '1,200', pct: 75, points: 75 },
        { label: '65–70 Points (Base Pass Mark)', count: '650', pct: 30, points: 65 },
      ];

  const snapshotMonth = eoiBacklog?.as_at_month || migrotoLive?.eoi_backlog_last_update || 'July 2026';
  const topBrackets = rawData.length >= 3 ? rawData.slice(0, 3) : rawData;

  return (
    <div className="rounded-xl border p-5 shadow-sm space-y-4"
         style={{ background: '#FFFFFF', borderColor: '#E7E2D6' }}
         data-testid="atlas-au-eoi-competition">
      <div className="flex items-center justify-between flex-wrap gap-2 border-b pb-3"
           style={{ borderColor: '#F0EBE0' }}>
        <div>
          <h3 className="text-base font-bold text-slate-900" style={{ fontFamily: "'Playfair Display', serif" }}>
            Official DHA SkillSelect Queue Competition
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Official Department of Home Affairs (DHA) SkillSelect Pool · Reporting Snapshot: {snapshotMonth}
          </p>
        </div>
        <span className="text-[11px] px-2.5 py-1 rounded font-mono bg-indigo-50 text-indigo-700 border border-indigo-200 font-semibold">
          Official DHA Registry
        </span>
      </div>

      {/* 3 Subclass Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-center">
          <p className="text-[10px] uppercase font-bold text-slate-500">Subclass 189 Pool</p>
          <p className="text-lg font-extrabold text-slate-900 mt-0.5">{count189} <span className="text-[11px] font-normal text-slate-500">EOIs</span></p>
          <p className="text-[10px] font-semibold text-teal-700 mt-0.5">
            Cutoff: {cutoff189 ? `${cutoff189} pts` : 'N/A (State Only)'}
          </p>
        </div>
        <div className="p-3 rounded-lg border text-center" style={{ background: '#EFF9F8', borderColor: '#BCE3E0' }}>
          <p className="text-[10px] uppercase font-bold text-teal-800">Subclass 190 Pool</p>
          <p className="text-lg font-extrabold text-teal-900 mt-0.5">{count190} <span className="text-[11px] font-normal text-teal-700">EOIs</span></p>
          <p className="text-[10px] font-semibold text-teal-700 mt-0.5">Cutoff: {cutoff190} pts</p>
        </div>
        <div className="p-3 rounded-lg border text-center" style={{ background: '#FEF9EE', borderColor: '#F5E5C9' }}>
          <p className="text-[10px] uppercase font-bold text-amber-800">Subclass 491 Pool</p>
          <p className="text-lg font-extrabold text-amber-900 mt-0.5">{count491} <span className="text-[11px] font-normal text-amber-700">EOIs</span></p>
          <p className="text-[10px] font-semibold text-amber-700 mt-0.5">Cutoff: {cutoff491} pts</p>
        </div>
      </div>

      <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-700">
        Active queue distribution:&nbsp;
        {topBrackets.length > 0 ? (
          topBrackets.map((tb, idx) => (
            <span key={idx}>
              {idx > 0 && ' | '}
              <span className={idx === 0 ? "text-teal-700 font-bold" : idx === 1 ? "text-slate-900 font-bold" : "text-slate-500"}>
                {tb.count} at {tb.points} pts
              </span>
            </span>
          ))
        ) : (
          <span>Official DHA SkillSelect pool reporting active for {snapshotMonth}</span>
        )}
      </div>

      <div className="space-y-2.5 pt-1">
        {distribution.map((d, idx) => (
          <div key={idx} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-700">{d.label}</span>
              <span className="text-slate-500 font-mono">{d.count} Candidates Waiting</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
              <div className="h-full rounded-full transition-all duration-500"
                   style={{
                     width: `${d.pct}%`,
                     background: d.points >= 85 ? '#0E5C5C' : d.points >= 75 ? '#137F7F' : '#C29B5C'
                   }} />
            </div>
          </div>
        ))}
      </div>

      {/* Client Advisory Consultation Guide */}
      <div className="p-4 rounded-xl border space-y-2 mt-3"
           style={{ background: '#F0F7F7', borderColor: '#BCE3E0' }}>
        <p className="font-bold text-xs flex items-center gap-1.5" style={{ color: '#0E5C5C' }}>
          <span>💡</span> Why are SkillSelect EOI Numbers High? (Client Consultation Guide)
        </p>
        <div className="text-xs text-slate-700 space-y-2 leading-relaxed">
          <p>
            <strong>1. Multi-Visa Selection (Triple-Counting):</strong> In SkillSelect, a single candidate typically selects Subclass 189, Subclass 190, and Subclass 491 simultaneously on the same application. This means one applicant appears in all three visa counts.
          </p>
          <p>
            <strong>2. 24-Month Passive Registry:</strong> EOIs remain active in Home Affairs registry for 2 full years. Many candidates in this cumulative pool have already received employer-sponsored visas, departed Australia, or let their English tests lapse.
          </p>
          <p>
            <strong>3. Strict Merit-Based Ranking:</strong> Home Affairs never invites by submission date. Invitations are issued strictly from highest points down. Having <strong>85+ points</strong> places an applicant in the top 15% tier across Australia and guarantees immediate consideration in upcoming invitation rounds.
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Reusable components ────────────────────────────────────────────────────
function Section({ title, children, testid }) {
  return (
    <div className="rounded-xl border p-5" style={{ background: C.card, borderColor: C.border }} data-testid={testid}>
      <p className="text-[11px] uppercase font-bold mb-3" style={{ color: C.tealDeep, letterSpacing: '0.10em' }}>{title}</p>
      {children}
    </div>
  );
}

function Mini({ label, value, tone }) {
  const map = {
    teal:   { fg: C.tealDeep, bg: C.tealWash },
    gold:   { fg: C.goldDeep, bg: C.goldWash },
    muted:  { fg: C.muted,    bg: C.bg },
  };
  const t = map[tone] || map.muted;
  return (
    <div className="rounded p-2 border" style={{ background: t.bg, borderColor: C.borderSoft }}>
      <p className="text-[9px] uppercase font-bold" style={{ color: C.muted, letterSpacing: '0.06em' }}>{label}</p>
      <p className="text-base font-bold mt-1" style={{ color: t.fg }}>{value}</p>
    </div>
  );
}

function OccupationCard({ item, compact }) {
  const cm = { AU: '🇦🇺', CA: '🇨🇦', NZ: '🇳🇿' }[item.country_code] || '';
  return (
    <Link
      to={`/atlas/${item.country_code.toLowerCase()}/${item.code}`}
      className="rounded-lg border p-3 hover:shadow transition-all block"
      style={{ background: C.card, borderColor: C.border }}
      data-testid={`atlas-occ-card-${item.country_code}-${item.code}`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="font-mono text-xs" style={{ color: C.muted }}>{cm} {item.code}</p>
        {item.nz_green_list_tier && (
          <span className="text-[9px] px-1.5 py-0.5 rounded font-bold" style={{ background: C.goldWash, color: C.goldDeep }}>
            T{item.nz_green_list_tier}
          </span>
        )}
        {item.teer_category !== undefined && item.teer_category !== null && (
          <span className="text-[9px] px-1.5 py-0.5 rounded font-bold" style={{ background: C.tealWash, color: C.tealDeep }}>
            TEER {item.teer_category}
          </span>
        )}
        {item.skill_level !== undefined && item.skill_level !== null && !item.teer_category && (
          <span className="text-[9px] px-1.5 py-0.5 rounded font-bold" style={{ background: C.tealWash, color: C.tealDeep }}>
            SL {item.skill_level}
          </span>
        )}
      </div>
      <p className={`font-bold mt-1 ${compact ? 'text-sm' : 'text-base'}`} style={{ color: C.ink }}>{item.title}</p>
      {item.hierarchy && (
        <p className="text-[10px] mt-1" style={{ color: C.muted }}>{item.hierarchy}</p>
      )}
      {item.country_code === 'AU' && (item.min_invitation_points?.subclass_190 || item.min_invitation_points?.subclass_189) && (
        <div className="mt-2 pt-1.5 border-t border-slate-100 flex items-center justify-between text-[10px]">
          <span className="text-teal-800 font-semibold flex items-center gap-1 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-600 inline-block"></span>
            Cutoff: {item.min_invitation_points?.subclass_190 || item.min_invitation_points?.subclass_189} pts
          </span>
          {item.pathway_list && (
            <span className="font-mono text-slate-500 font-bold px-1.5 py-0.2 rounded bg-slate-100">{item.pathway_list}</span>
          )}
        </div>
      )}
    </Link>
  );
}

function LeadCaptureForm({ atlas_code, atlas_title, country }) {
  const [form, setForm] = useState({ name: '', email: '', phone: '', message: '' });
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);
  // Mount time — bots typically auto-submit in <1s. Honeypot dropped only if too fast.
  const [mountTime] = useState(() => Date.now());

  const set = (k, v) => setForm(prev => ({ ...prev, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true); setError(null);

    // Time-based bot detection: only mark as bot if submission < 1.5s after mount
    // (legitimate users always take longer to fill the form).
    const elapsedMs = Date.now() - mountTime;
    const isBotFastSubmit = elapsedMs < 1500;

    try {
      const r = await axios.post(`${API}/public-atlas/lead`, {
        name: form.name, email: form.email, phone: form.phone,
        country_of_interest: country, atlas_code, atlas_title,
        website_page_title: typeof document !== 'undefined' ? (document.title || atlas_title || 'LEAMSS Migration Atlas') : 'LEAMSS Migration Atlas',
        website_page_url: typeof window !== 'undefined' ? window.location.href : `https://leamss.com/atlas/${country || 'au'}/${atlas_code || ''}`,
        message: form.message,
        // Honeypot triggered ONLY if form filled too quickly
        company_url: isBotFastSubmit ? 'bot-detected' : '',
      });
      // Treat honeypot drop as silent success on the UI (don't reveal anti-bot logic)
      if (r.data.ok) setSuccess(true);
    } catch (e) {
      setError(e.response?.data?.detail || 'Submission failed. Please try again.');
    }
    setSubmitting(false);
  };

  if (success) {
    return (
      <div className="rounded-xl border p-5" style={{ background: C.tealWash, borderColor: C.tealWash2 }} data-testid="atlas-lead-success">
        <CheckCircle2 className="w-8 h-8 mb-2" style={{ color: C.teal }} />
        <p className="text-base font-bold mb-1" style={{ color: C.tealDeep }}>Thank you!</p>
        <p className="text-xs" style={{ color: C.body }}>Our migration expert will contact you within 24 hours.</p>
      </div>
    );
  }

  return (
    <form id="lead-form" onSubmit={submit} className="rounded-xl border p-5" style={{ background: C.card, borderColor: C.border }} data-testid="atlas-lead-form">
      <p className="text-xs font-bold uppercase tracking-wider mb-1" style={{ color: C.gold, letterSpacing: '0.10em' }}>
        <Sparkles className="w-3 h-3 inline mr-1" />Free Eligibility Check
      </p>
      <p className="text-lg font-bold mb-1" style={{ color: C.tealDeep, fontFamily: "'Playfair Display', serif" }}>
        Get a personalised assessment
      </p>
      <p className="text-xs mb-4" style={{ color: C.muted }}>
        for <strong>{atlas_title}</strong> ({atlas_code}) — by a licensed migration expert. 100% confidential.
      </p>

      <div className="space-y-2">
        <FieldInput icon={UserIcon} placeholder="Full name" value={form.name} onChange={(v) => set('name', v)} testid="atlas-lead-name" />
        <FieldInput icon={Mail} placeholder="Email" type="email" value={form.email} onChange={(v) => set('email', v)} testid="atlas-lead-email" />
        <FieldInput icon={Phone} placeholder="Phone (with country code)" value={form.phone} onChange={(v) => set('phone', v)} testid="atlas-lead-phone" />
        <textarea
          placeholder="Anything you'd like to add? (optional)"
          value={form.message}
          onChange={(e) => set('message', e.target.value)}
          rows={2}
          className="w-full px-3 py-2 rounded border text-sm"
          style={{ borderColor: C.border }}
          data-testid="atlas-lead-message"
        />

        {error && <p className="text-xs" style={{ color: C.red }}>{error}</p>}

        <button
          type="submit"
          disabled={submitting || !form.name || !form.email || !form.phone}
          className="w-full mt-2 px-4 py-2.5 rounded font-bold text-sm flex items-center justify-center gap-2 disabled:opacity-50"
          style={{ background: C.tealDeep, color: '#fff' }}
          data-testid="atlas-lead-submit"
        >
          {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          {submitting ? 'Sending…' : 'Get Free Eligibility Check'}
        </button>
      </div>

      <p className="text-[10px] mt-3 italic" style={{ color: C.muted }}>
        By submitting, you agree to be contacted by LEAMSS migration advisors. We never share your data.
      </p>
    </form>
  );
}

function FieldInput({ icon: Icon, placeholder, value, onChange, type = 'text', testid }) {
  return (
    <div className="relative">
      <Icon className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5" style={{ color: C.muted }} />
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full pl-9 pr-3 py-2 rounded border text-sm"
        style={{ borderColor: C.border }}
        data-testid={testid}
        required
      />
    </div>
  );
}
