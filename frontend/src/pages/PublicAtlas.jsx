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
  CheckCircle2, ChevronRight, Sparkles, Mail, Phone, User as UserIcon, Send, X,
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
  upsertMeta('og:title', seo.og_title || seo.page_title, true);
  upsertMeta('og:description', seo.og_description || seo.meta_description, true);
  upsertMeta('og:image', seo.og_image, true);
  upsertMeta('og:type', 'article', true);

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
            <Link reloadDocument
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
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  const fetchList = async (targetPage = 1, q = '') => {
    setShowSuggestions(false);
    if (!['AU', 'CA', 'NZ'].includes(country)) {
      setData({ error: 'Country not found' });
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const r = await axios.get(`${API}/public-atlas/${country}/list`, {
        params: { limit: 50, offset: (targetPage - 1) * 50, search: q.trim() || undefined },
      });
      setData(r.data);
      applySEO(r.data.seo);
    } catch (e) {
      setData({ error: e.response?.data?.detail || 'Country not found' });
    }
    setLoading(false);
  };

  useEffect(() => {
    setPage(1);
    setSearch('');
    fetchList(1, '');
  }, [country]);

  // Typeahead suggestions
  useEffect(() => {
    if (search.trim().length < 2 || !showSuggestions) {
      setSuggestions([]);
      return;
    }
    const t = setTimeout(() => {
      axios.get(`${API}/public-atlas/${country}/typeahead`, { params: { q: search.trim(), limit: 6 } })
        .then(r => setSuggestions(r.data.items || []))
        .catch(() => setSuggestions([]));
    }, 180);
    return () => clearTimeout(t);
  }, [search, country, showSuggestions]);

  const cm = data?.country_meta || {};
  const total = data?.total || 0;
  const pageSize = 50;
  const totalPages = Math.ceil(total / pageSize);

  const getPageNumbers = () => {
    if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1);
    const pages = [1];
    let start = Math.max(2, page - 1);
    let end = Math.min(totalPages - 1, page + 1);
    if (page <= 3) end = 4;
    else if (page >= totalPages - 2) start = totalPages - 3;
    if (start > 2) pages.push('...');
    for (let p = start; p <= end; p++) pages.push(p);
    if (end < totalPages - 1) pages.push('...');
    pages.push(totalPages);
    return pages;
  };

  return (
    <PublicShell>
      <section className="max-w-6xl mx-auto px-6 pt-12 pb-6" data-testid="atlas-country-root">
        <Link reloadDocument to="/atlas" className="text-xs hover:underline" style={{ color: C.muted }}>← Atlas Hub</Link>
        <h1 className="text-4xl sm:text-5xl font-bold mt-2 mb-2" style={{ color: C.ink, fontFamily: "'Playfair Display', serif" }}>
          {cm.flag} {cm.name || country} <span style={{ color: C.tealDeep }}>Occupation Atlas</span>
        </h1>
        <p className="text-sm" style={{ color: C.body }}>
          {total} verified occupations · {cm.classification || '—'}
        </p>

        {/* Search */}
        <div className="mt-6 max-w-xl relative">
          <div className="relative flex items-center">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: C.muted }} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  setPage(1);
                  fetchList(1, search);
                } else if (e.key === 'Escape') {
                  setShowSuggestions(false);
                }
              }}
              placeholder="Search by code, title, alternative title, or industry — e.g., 'marketing', 'software engineer', '225113', 'operations head'…"
              className="w-full pl-10 pr-10 py-3 rounded border text-sm"
              style={{ borderColor: C.border, background: C.card }}
              data-testid="atlas-country-search"
            />
            {search && (
              <button
                type="button"
                onClick={() => { setSearch(''); setPage(1); fetchList(1, ''); }}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                aria-label="Clear search"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Typeahead dropdown */}
          {showSuggestions && suggestions.length > 0 && search.trim().length >= 2 && (
            <div
              className="absolute left-0 right-0 top-full mt-1.5 z-40 bg-white border rounded-xl shadow-xl max-h-80 overflow-y-auto"
              style={{ borderColor: C.border }}
              data-testid="typeahead-dropdown"
            >
              {suggestions.map((s) => (
                <Link
                  key={`${s.country_code}-${s.code}`}
                  reloadDocument
                  to={`/atlas/${(s.country_code || country).toLowerCase()}/${s.code}`}
                  onMouseDown={(e) => e.preventDefault()}
                  className="w-full text-left px-4 py-3 hover:bg-slate-50 border-b last:border-b-0 flex items-center gap-3 transition-colors block"
                >
                  <span className="text-xs font-bold px-2 py-1 rounded shrink-0 font-mono" style={{ background: C.tealWash, color: C.tealDeep }}>
                    {s.country_code || country}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold truncate text-slate-800">
                      {s.code} · {s.title}
                    </p>
                    <p className="text-xs text-slate-500 truncate mt-0.5">
                      {[s.assessing_body, s.pathway].filter(Boolean).join(' · ') || `${cm.classification || ''} ${s.code}`}
                    </p>
                  </div>
                  <span className="text-[11px] font-bold px-2.5 py-1 rounded-full shrink-0 bg-slate-900 text-white">
                    {s.score || 90}%
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 pb-16">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <h2 className="text-lg font-bold" style={{ color: C.ink }}>Browse occupations</h2>
          <span className="text-xs" style={{ color: C.muted }}>
            Showing {total > 0 ? (page - 1) * pageSize + 1 : 0}–{Math.min(page * pageSize, total)} of {total} verified · sorted by code
          </span>
        </div>

        {loading ? (
          <div className="py-12 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto" style={{ color: C.teal }} /></div>
        ) : data?.error ? (
          <p className="text-sm py-8" style={{ color: C.red }} data-testid="atlas-country-error">{data.error}</p>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="atlas-country-grid">
              {(data?.items || []).map(it => <OccupationCard key={`${it.country_code}-${it.code}`} item={it} />)}
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-1.5 mt-10 flex-wrap" data-testid="atlas-pagination">
                <button
                  onClick={() => { const prev = Math.max(1, page - 1); setPage(prev); fetchList(prev, search); window.scrollTo({ top: 300, behavior: 'smooth' }); }}
                  disabled={page === 1}
                  className="px-3 py-1.5 rounded border text-xs font-bold bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition"
                  style={{ borderColor: C.border }}
                >
                  ← Prev
                </button>
                {getPageNumbers().map((num, idx) => (
                  num === '...' ? (
                    <span key={`ellipsis-${idx}`} className="w-8 text-center text-xs font-bold text-slate-400">…</span>
                  ) : (
                    <button
                      key={num}
                      onClick={() => { setPage(num); fetchList(num, search); window.scrollTo({ top: 300, behavior: 'smooth' }); }}
                      className="min-w-[36px] h-9 px-2 rounded text-xs font-bold transition flex items-center justify-center"
                      style={{
                        background: page === num ? C.tealDeep : '#fff',
                        color: page === num ? '#fff' : C.ink,
                        border: `1.5px solid ${page === num ? C.tealDeep : C.border}`,
                      }}
                    >
                      {num}
                    </button>
                  )
                ))}
                <button
                  onClick={() => { const next = Math.min(totalPages, page + 1); setPage(next); fetchList(next, search); window.scrollTo({ top: 300, behavior: 'smooth' }); }}
                  disabled={page === totalPages}
                  className="px-3 py-1.5 rounded border text-xs font-bold bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition"
                  style={{ borderColor: C.border }}
                >
                  Next →
                </button>
              </div>
            )}
          </>
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
          <Link reloadDocument to="/atlas" className="hover:underline">Atlas</Link>
          <ChevronRight className="w-3 h-3 inline mx-1" />
          <Link reloadDocument to={`/atlas/${country.toLowerCase()}`} className="hover:underline">{cm.flag} {cm.name}</Link>
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
      </section>

      <div className="max-w-6xl mx-auto px-6 pb-16 grid grid-cols-1 lg:grid-cols-3 gap-6 mt-4">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-5">
          {occ.description && (
            <Section title="About this Occupation">
              <p className="text-sm whitespace-pre-line" style={{ color: C.body }}>{occ.description}</p>
            </Section>
          )}

          {/* Eligibility / Skill level / TEER */}
          <Section title="Eligibility & Classification">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {occ.skill_level && <Mini label="ANZSCO Skill Level" value={`Level ${occ.skill_level}`} tone="teal" />}
              {occ.teer_category !== undefined && occ.teer_category !== null && <Mini label="TEER Category" value={`TEER ${occ.teer_category}`} tone="teal" />}
              {occ.assessing_authority?.name && <Mini label="Assessing Body" value={occ.assessing_authority.name} tone="gold" />}
            </div>
            {occ.assessing_authority?.full_name && (
              <p className="text-xs mt-3 italic" style={{ color: C.muted }}>
                Full assessing body: {occ.assessing_authority.full_name}
                {occ.assessing_authority.website && (
                  <> · <a href={occ.assessing_authority.website} target="_blank" rel="noreferrer" className="underline" style={{ color: C.teal }}>Official site</a></>
                )}
              </p>
            )}
          </Section>

          {/* Visa pathways */}
          {occ.visa_pathways && (
            <Section title="Visa Pathways">
              <div className="flex flex-wrap gap-2">
                {(occ.visa_pathways.visa_eligibility || []).map(v => (
                  <span key={v.visa_subclass} className="text-xs px-2 py-1 rounded border font-mono"
                        style={{
                          background: v.eligible ? C.tealWash : C.bg,
                          color: v.eligible ? C.tealDeep : C.muted,
                          borderColor: v.eligible ? C.teal : C.border,
                        }}>
                    {v.eligible ? '✓' : '✗'} {v.visa_subclass}
                  </span>
                ))}
              </div>
              {occ.visa_pathways.pathway_lists?.length > 0 && (
                <p className="text-xs mt-3" style={{ color: C.muted }}>
                  Lists: {(occ.visa_pathways.pathway_lists || []).join(' · ')}
                </p>
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

          {/* Salary band (AU) */}
          {occ.anzsco_profile && (
            <Section title="🇦🇺 Salary & Workforce Data">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs" style={{ color: C.body }}>
                {occ.anzsco_profile.median_salary_aud && (
                  <Mini label="Median Salary" value={`A$${(occ.anzsco_profile.median_salary_aud / 1000).toFixed(0)}k`} tone="gold" />
                )}
                {occ.anzsco_profile.workforce_size && (
                  <Mini label="Workforce" value={Number(occ.anzsco_profile.workforce_size).toLocaleString()} tone="teal" />
                )}
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
                  <Link reloadDocument
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
    <Link reloadDocument
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
    <form onSubmit={submit} className="rounded-xl border p-5" style={{ background: C.card, borderColor: C.border }} data-testid="atlas-lead-form">
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
