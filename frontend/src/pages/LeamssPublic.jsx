/**
 * Phase 14 — LEAMSS Public Brand Experience
 *
 * Following design_guidelines.json (Organic & Earthy / Light theme):
 *   Primary  #1F4D44 (Deep Forest Green)
 *   Accent   #D4633F (Burnt Orange)
 *   Bg-soft  #F7F9F8
 *   Text     #2D3D45
 *
 * Single file exports:
 *   <LeamssShell>           — shared header + footer with REAL leamss.com logo
 *   <MegaLanding />         — /start mega landing page combining all 3 tools
 *   <AtlasHubV2 />          — /atlas redesigned
 *   <AtlasCountryV2 />      — /atlas/:country redesigned
 *   <AtlasOccupationV2 />   — /atlas/:country/:code redesigned
 */
import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowRight, Sparkles, CheckCircle2, Globe2, ChevronDown, ChevronRight,
  Search, Star, Award, Briefcase, Loader2, Send, Mail, Phone, User as UserIcon,
  MessageCircle, Calculator, Plane, Shield, Clock, ArrowUpRight, MapPin, Info, Download, X,
} from 'lucide-react';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ─── Brand tokens ──────────────────────────────────────────────────────────
const BRAND = {
  primary:    '#1F4D44',
  primaryDk:  '#13332D',
  accent:     '#D4633F',
  accentDk:   '#B85333',
  bg:         '#FFFFFF',
  bgSoft:     '#F7F9F8',
  bgWarm:     '#FCFAF7',
  ink:        '#1A2A30',
  body:       '#2D3D45',
  muted:      '#5C737D',
  border:     '#E5EBE9',
  success:    '#2E7D32',
};

const LOGO_URL = '/leamss-logo.png';
const WHATSAPP = '7738352427';
const PHONE = '7718882427';
const TOLL_FREE = '1800-210-2427';

// Country landmark hero images (from design_guidelines.json)
const COUNTRY_HERO = {
  AU: 'https://images.unsplash.com/photo-1753275032483-d13bd056f4da?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzNzl8MHwxfHNlYXJjaHwyfHxzeWRuZXklMjBvcGVyYSUyMGhvdXNlJTIwc2t5bGluZXxlbnwwfHx8fDE3ODEwMzY4ODN8MA&ixlib=rb-4.1.0&q=85',
  CA: 'https://images.unsplash.com/photo-1517935706615-2717063c2225?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1ODF8MHwxfHNlYXJjaHwxfHx0b3JvbnRvJTIwY24lMjB0b3dlciUyMGNpdHlzY2FwZXxlbnwwfHx8fDE3ODEwMzY4ODN8MA&ixlib=rb-4.1.0&q=85',
  NZ: 'https://images.unsplash.com/photo-1677557769726-565a3034fa2c?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1ODh8MHwxfHNlYXJjaHwzfHxhdWNrbGFuZCUyMHNreSUyMHRvd2VyfGVufDB8fHx8MTc4MTAzNjg4M3ww&ixlib=rb-4.1.0&q=85',
};

// ─── SEO helpers ───────────────────────────────────────────────────────────
function applySEO(seo) {
  if (!seo) return;
  if (seo.page_title) document.title = seo.page_title;
  const upsert = (key, content, useProp = false) => {
    if (!content) return;
    const attr = useProp ? 'property' : 'name';
    let el = document.head.querySelector(`meta[${attr}="${key}"]`);
    if (!el) { el = document.createElement('meta'); el.setAttribute(attr, key); document.head.appendChild(el); }
    el.setAttribute('content', content);
  };
  upsert('description', seo.meta_description);
  upsert('keywords', seo.keywords);
  upsert('robots', seo.robots || 'index, follow, max-image-preview:large, max-snippet:-1');
  // Open Graph
  upsert('og:type', seo.og_type || 'website', true);
  upsert('og:site_name', seo.og_site_name || 'LEAMSS — Ladhani Education & Migration Services', true);
  upsert('og:title', seo.og_title || seo.page_title, true);
  upsert('og:description', seo.og_description || seo.meta_description, true);
  upsert('og:image', seo.og_image, true);
  upsert('og:url', seo.og_url || seo.canonical_url, true);
  upsert('og:locale', seo.og_locale || 'en_IN', true);
  // Twitter Card
  upsert('twitter:card', 'summary_large_image');
  upsert('twitter:title', seo.og_title || seo.page_title);
  upsert('twitter:description', seo.og_description || seo.meta_description);
  upsert('twitter:image', seo.og_image);
  if (seo.canonical_url) {
    let canon = document.head.querySelector('link[rel="canonical"]');
    if (!canon) { canon = document.createElement('link'); canon.rel = 'canonical'; document.head.appendChild(canon); }
    canon.href = seo.canonical_url;
  }
  if (seo.json_ld) {
    let ld = document.head.querySelector('script[type="application/ld+json"][data-leamss]');
    if (!ld) { ld = document.createElement('script'); ld.type = 'application/ld+json'; ld.setAttribute('data-leamss', '1'); document.head.appendChild(ld); }
    ld.textContent = JSON.stringify(seo.json_ld);
  }
}

// ─── Shared shell ──────────────────────────────────────────────────────────
function LeamssShell({ children, transparentHeader = false }) {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 60);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const headerBg = transparentHeader && !scrolled ? 'rgba(255,255,255,0.0)' : '#FFFFFF';
  const headerBorder = transparentHeader && !scrolled ? 'transparent' : BRAND.border;
  const headerTextColor = transparentHeader && !scrolled ? '#FFFFFF' : BRAND.primary;

  return (
    <div style={{ background: BRAND.bg, color: BRAND.ink, fontFamily: "'Plus Jakarta Sans', sans-serif", minHeight: '100vh' }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
        .font-serif-leamss { font-family: 'Playfair Display', serif; letter-spacing: -0.01em; }
        .font-sans-leamss  { font-family: 'Plus Jakarta Sans', sans-serif; }
        @keyframes marquee { 0% {transform: translateX(0);} 100% {transform: translateX(-50%);} }
        .marquee-track { animation: marquee 40s linear infinite; }
      `}</style>

      {/* Top utility strip — match leamss.com style */}
      <div className="w-full" style={{ background: BRAND.primaryDk, color: '#FFFFFF' }}>
        <div className="max-w-7xl mx-auto px-4 py-2 flex items-center justify-between flex-wrap gap-2 text-xs">
          <div className="flex items-center gap-4 flex-wrap">
            <span className="flex items-center gap-1"><MapPin className="w-3 h-3" /> Thane, Mumbai</span>
            <span className="flex items-center gap-1"><Phone className="w-3 h-3" /> Toll-Free: {TOLL_FREE}</span>
            <a href={`tel:+91${PHONE}`} className="flex items-center gap-1 hover:opacity-80">+91 {PHONE.slice(0,5)} {PHONE.slice(5)}</a>
          </div>
          <div className="flex items-center gap-3">
            <a href="mailto:info@leamss.com" className="hover:opacity-80">info@leamss.com</a>
          </div>
        </div>
      </div>

      {/* Main header */}
      <header
        className="sticky top-0 z-30 transition-all"
        style={{ background: headerBg, borderBottom: `1px solid ${headerBorder}`, backdropFilter: scrolled ? 'blur(8px)' : 'none' }}
      >
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link reloadDocument to="/atlas" data-testid="leamss-logo" className="flex items-center gap-2">
            <img src={LOGO_URL} alt="LEAMSS — Ladhani Education & Migration Services" className="h-12 w-auto" />
          </Link>
          <nav className="hidden md:flex items-center gap-6 text-sm font-medium" style={{ color: headerTextColor }}>
            <Link reloadDocument to="/atlas" className="hover:opacity-80 transition-opacity">Atlas</Link>
            <Link to="/start" className="hover:opacity-80 transition-opacity">Eligibility Quiz</Link>
            <Link reloadDocument to="/atlas/au" className="hover:opacity-80 transition-opacity flex items-center gap-1.5"><img src="https://flagcdn.com/w20/au.png" srcSet="https://flagcdn.com/w40/au.png 2x" width="20" height="15" alt="Australia" className="rounded-sm inline-block" /> AU</Link>
            <Link reloadDocument to="/atlas/ca" className="hover:opacity-80 transition-opacity flex items-center gap-1.5"><img src="https://flagcdn.com/w20/ca.png" srcSet="https://flagcdn.com/w40/ca.png 2x" width="20" height="15" alt="Canada" className="rounded-sm inline-block" /> CA</Link>
            <Link reloadDocument to="/atlas/nz" className="hover:opacity-80 transition-opacity flex items-center gap-1.5"><img src="https://flagcdn.com/w20/nz.png" srcSet="https://flagcdn.com/w40/nz.png 2x" width="20" height="15" alt="New Zealand" className="rounded-sm inline-block" /> NZ</Link>
            <a href="https://calendly.com/rohit-leamss/30min" target="_blank" rel="noreferrer"
              className="px-4 py-2 rounded-md text-white font-semibold transition-all hover:brightness-110"
              style={{ background: BRAND.accent }}
              data-testid="header-whatsapp-cta"
            >
              Book a Consultation
            </a>
          </nav>
        </div>
      </header>

      {children}

      {/* Footer */}
      <footer style={{ background: BRAND.primaryDk, color: '#FFFFFF' }}>
        <div className="max-w-7xl mx-auto px-4 py-12 grid grid-cols-1 md:grid-cols-4 gap-8 text-sm">
          <div>
            <img src={LOGO_URL} alt="LEAMSS" className="h-12 w-auto mb-3 bg-white p-1 rounded" />
            <p className="text-white/80 leading-relaxed">
              <strong>Ladhani Education & Migration Services (OPC) Pvt. Ltd</strong><br />
              India&apos;s trusted immigration experts. We value emotions.
            </p>
            <p className="text-white/70 text-xs mt-3">Office No. 10, Londhe Compound, Laxmi Chambers,<br />Near Gaondevi Maidan, Thane West — 400602</p>
          </div>
          <div>
            <p className="font-bold mb-3 font-serif-leamss text-lg">Browse Atlas</p>
            <ul className="space-y-1.5 text-white/80">
              <li><Link reloadDocument to="/atlas/au" className="hover:text-white flex items-center gap-1.5"><img src="https://flagcdn.com/w20/au.png" srcSet="https://flagcdn.com/w40/au.png 2x" width="20" height="15" alt="Australia" className="rounded-sm inline-block" /> Australia ANZSCO</Link></li>
              <li><Link reloadDocument to="/atlas/ca" className="hover:text-white flex items-center gap-1.5"><img src="https://flagcdn.com/w20/ca.png" srcSet="https://flagcdn.com/w40/ca.png 2x" width="20" height="15" alt="Canada" className="rounded-sm inline-block" /> Canada NOC 2021</Link></li>
              <li><Link reloadDocument to="/atlas/nz" className="hover:text-white flex items-center gap-1.5"><img src="https://flagcdn.com/w20/nz.png" srcSet="https://flagcdn.com/w40/nz.png 2x" width="20" height="15" alt="New Zealand" className="rounded-sm inline-block" /> New Zealand</Link></li>
              <li><Link to="/start" className="hover:text-white">AI Eligibility Score</Link></li>
            </ul>
          </div>
          <div>
            <p className="font-bold mb-3 font-serif-leamss text-lg">Quick Calculators</p>
            <ul className="space-y-1.5 text-white/80">
              <li><a href="https://leamss.com/canada-67-points-calculator" className="hover:text-white">Canada 67 Points</a></li>
              <li><a href="https://leamss.com/canada-crs-calculator" className="hover:text-white">Canada CRS Score</a></li>
              <li><a href="https://leamss.com/australia-pr-points-calculator" className="hover:text-white">Australia PR Points</a></li>
            </ul>
          </div>
          <div>
            <p className="font-bold mb-3 font-serif-leamss text-lg">Contact</p>
            <ul className="space-y-1.5 text-white/80">
              <li><a href={`tel:${TOLL_FREE}`} className="hover:text-white">📞 Toll-Free: {TOLL_FREE}</a></li>
              <li><a href={`tel:+91${PHONE}`} className="hover:text-white">📱 +91 {PHONE}</a></li>
              <li><a href={`https://wa.me/${WHATSAPP}`} target="_blank" rel="noreferrer" className="hover:text-white">💬 WhatsApp</a></li>
              <li><a href="mailto:info@leamss.com" className="hover:text-white">✉️ info@leamss.com</a></li>
            </ul>
          </div>
        </div>
        <div className="border-t border-white/10">
          <div className="max-w-7xl mx-auto px-4 py-4 text-center text-xs text-white/60">
            © 2026 Ladhani Education & Migration Services (OPC) Pvt. Ltd · 100% Refund Guarantee Policy
          </div>
        </div>
      </footer>

      {/* Floating WhatsApp button */}
      <a
        href={`https://wa.me/${WHATSAPP}`} target="_blank" rel="noreferrer"
        className="fixed bottom-6 right-6 z-40 w-14 h-14 rounded-full flex items-center justify-center shadow-lg hover:scale-110 transition-transform"
        style={{ background: '#25D366', color: '#fff' }}
        aria-label="WhatsApp" data-testid="floating-whatsapp"
      >
        <MessageCircle className="w-7 h-7" />
      </a>
    </div>
  );
}

// ─── Reusable primitives ───────────────────────────────────────────────────
const Button = ({ children, variant = 'primary', size = 'md', as: As = 'button', className = '', ...props }) => {
  const v = {
    primary:   { bg: BRAND.accent, color: '#FFFFFF', hover: BRAND.accentDk, border: 'transparent' },
    secondary: { bg: '#FFFFFF', color: BRAND.primary, hover: BRAND.bgSoft, border: BRAND.primary },
    ghost:     { bg: 'transparent', color: BRAND.primary, hover: BRAND.bgSoft, border: 'transparent' },
    dark:      { bg: BRAND.primary, color: '#FFFFFF', hover: BRAND.primaryDk, border: 'transparent' },
  }[variant];
  const s = { sm: 'px-3 py-1.5 text-sm', md: 'px-5 py-2.5 text-sm', lg: 'px-7 py-3.5 text-base' }[size];
  return (
    <As
      className={`inline-flex items-center justify-center gap-2 rounded-md font-semibold transition-all hover:brightness-105 ${s} ${className}`}
      style={{ background: v.bg, color: v.color, border: `1.5px solid ${v.border}` }}
      onMouseEnter={(e) => { if (v.bg !== 'transparent') e.currentTarget.style.background = v.hover; else e.currentTarget.style.background = v.hover; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = v.bg; }}
      {...props}
    >
      {children}
    </As>
  );
};

const Pill = ({ children, color = BRAND.primary, bg }) => (
  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold"
    style={{ background: bg || `${color}15`, color }}>{children}</span>
);

const SectionTitle = ({ eyebrow, title, sub }) => (
  <div className="text-center max-w-3xl mx-auto mb-12">
    {eyebrow && (
      <p className="text-xs font-bold uppercase tracking-[0.18em] mb-3" style={{ color: BRAND.accent }}>{eyebrow}</p>
    )}
    <h2 className="font-serif-leamss text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight" style={{ color: BRAND.ink }}>{title}</h2>
    {sub && <p className="mt-4 text-base sm:text-lg" style={{ color: BRAND.body }}>{sub}</p>}
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════
// MEGA LANDING PAGE — /start
// ═══════════════════════════════════════════════════════════════════════════
export function MegaLanding() {
  const [content, setContent] = useState(null);
  useEffect(() => {
    axios.get(`${API}/public-pages/content`).then(r => setContent(r.data)).catch(() => setContent({}));
    applySEO({
      page_title: 'Find Your Migration Pathway in 60 Seconds — Australia, Canada, New Zealand PR | LEAMSS',
      meta_description: 'Free AI eligibility check + verified ANZSCO/NOC atlas + visa comparison for AU, CA, NZ. 100% refund guarantee on negative skill assessment. India\'s most trusted migration consultancy since 2024.',
      keywords: 'immigration consultant India, Australia PR visa, Canada Express Entry, New Zealand migration, skilled migration, ANZSCO occupation code, NOC code Canada, CRS points calculator, visa eligibility check, skill assessment, subclass 189 190 491, Express Entry FSWP, NZ Green List, MARA registered agent, PR consultant Mumbai Thane, free eligibility check, LEAMSS',
      canonical_url: `${window.location.origin}/start`,
      og_url: `${window.location.origin}/start`,
      og_image: LOGO_URL,
      json_ld: {
        "@context": "https://schema.org",
        "@graph": [
          {
            "@type": "Organization",
            "@id": "https://www.leamss.com/#organization",
            "name": "Ladhani Education & Migration Services (OPC) Pvt. Ltd",
            "alternateName": "LEAMSS",
            "url": "https://www.leamss.com",
            "logo": LOGO_URL,
            "description": "MARA-registered immigration consultancy for Australia, Canada & New Zealand PR. Trusted since 2024 with a 100% refund guarantee on negative skill assessment.",
            "foundingDate": "2024",
            "address": { "@type": "PostalAddress", "addressLocality": "Thane", "addressRegion": "Maharashtra", "addressCountry": "IN" },
            "contactPoint": { "@type": "ContactPoint", "telephone": "+91-77188-82427", "contactType": "customer service", "areaServed": "IN", "availableLanguage": ["en", "hi"] },
            "sameAs": ["https://www.leamss.com"],
          },
          {
            "@type": "WebSite",
            "@id": "https://www.leamss.com/#website",
            "url": "https://www.leamss.com",
            "name": "LEAMSS",
            "publisher": { "@id": "https://www.leamss.com/#organization" },
          },
          {
            "@type": "WebPage",
            "@id": `${window.location.origin}/start#webpage`,
            "url": `${window.location.origin}/start`,
            "name": "Find Your Migration Pathway in 60 Seconds — AU, CA, NZ PR",
            "isPartOf": { "@id": "https://www.leamss.com/#website" },
            "about": { "@id": "https://www.leamss.com/#organization" },
          },
          {
            "@type": "FAQPage",
            "@id": `${window.location.origin}/start#faq`,
            "mainEntity": FAQS.map((f) => ({
              "@type": "Question",
              "name": f.q,
              "acceptedAnswer": { "@type": "Answer", "text": f.a },
            })),
          },
        ],
      },
    });
  }, []);

  // Scroll to #quiz / #compare when arriving via a redirected old route
  useEffect(() => {
    const hash = window.location.hash?.replace('#', '');
    if (!hash) return;
    let tries = 0;
    const timer = setInterval(() => {
      const el = document.getElementById(hash);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        clearInterval(timer);
      }
      if (++tries > 20) clearInterval(timer);
    }, 200);
    return () => clearInterval(timer);
  }, []);

  return (
    <LeamssShell>
      <Hero content={content?.hero} />
      <TrustStrip items={content?.trust_strip} />
      <EligibilityQuizSection />
      <VisaCompareSection />
      <FeaturedOccupationsSection featuredOverride={content?.featured_codes} />
      <BrowseAtlasSection />
      <SocialProofSection testimonialsOverride={content?.testimonials} />
      <FAQSection faqsOverride={content?.faqs} />
      <StickyLeadFooter />
    </LeamssShell>
  );
}

// ─── Hero ──────────────────────────────────────────────────────────────────
function Hero({ content }) {
  const hero = content || {
    eyebrow: '100% Refund Guarantee · MARA Registered',
    title_line1: 'Find your migration',
    title_line2: 'pathway',
    title_line3_accent: 'in 60 seconds.',
    subtitle: 'Free AI eligibility check across 80+ visa categories for Australia, Canada & New Zealand. No login. No spam. Just an honest scorecard.',
    cta_primary: 'Start AI Eligibility Quiz',
    cta_secondary: 'Browse Migration Atlas',
    rating: '4.9 / 5',
    rating_subtitle: 'from 500+ Google reviews',
  };
  return (
    <section className="relative overflow-hidden" style={{ background: BRAND.bgWarm }}>
      <div className="absolute top-0 right-0 w-1/2 h-full opacity-[0.08] pointer-events-none"
        style={{ background: `radial-gradient(circle, ${BRAND.primary}, transparent 70%)` }} />

      <div className="max-w-7xl mx-auto px-4 py-16 lg:py-24 grid grid-cols-1 lg:grid-cols-12 gap-10 items-center relative z-10">
        <div className="lg:col-span-7" data-testid="hero-root">
          <motion.div
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
          >
            <Pill color={BRAND.accent}>
              <Shield className="w-3 h-3" />{hero.eyebrow}
            </Pill>
            <h1 className="font-serif-leamss text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-bold leading-[1.05] mt-5"
              style={{ color: BRAND.ink }}>
              {hero.title_line1}
              <br />
              <span style={{ color: BRAND.primary }}>{hero.title_line2}</span>{' '}
              <span style={{ color: BRAND.accent, fontStyle: 'italic' }}>{hero.title_line3_accent}</span>
            </h1>
            <p className="mt-6 text-lg lg:text-xl leading-relaxed max-w-xl" style={{ color: BRAND.body }}>
              {hero.subtitle}
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button size="lg" data-testid="hero-start-quiz" onClick={() => document.getElementById('quiz')?.scrollIntoView({ behavior: 'smooth' })}>
                {hero.cta_primary}<ArrowRight className="w-4 h-4" />
              </Button>
              <Button reloadDocument variant="secondary" size="lg" as={Link} to="/atlas" data-testid="hero-browse-atlas">
                {hero.cta_secondary}
              </Button>
            </div>
            <div className="mt-7 flex items-center gap-5 flex-wrap">
              <div className="flex -space-x-2">
                {['👨‍💼', '👩‍🔬', '👨‍⚕️', '👩‍🏫'].map((emoji, i) => (
                  <div key={i} className="w-9 h-9 rounded-full flex items-center justify-center text-lg border-2 border-white"
                    style={{ background: BRAND.bgSoft }}>{emoji}</div>
                ))}
              </div>
              <div className="text-sm">
                <div className="flex items-center gap-1">
                  {[1,2,3,4,5].map(i => <Star key={i} className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />)}
                  <span className="font-bold ml-1" style={{ color: BRAND.ink }}>{hero.rating}</span>
                </div>
                <p className="text-xs" style={{ color: BRAND.muted }}>{hero.rating_subtitle}</p>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Right column: 3 country stacked cards */}
        <div className="lg:col-span-5 grid grid-cols-1 gap-3">
          {[
            { code: 'AU', name: 'Australia', desc: 'ANZSCO · 1,236 verified codes', img: COUNTRY_HERO.AU },
            { code: 'CA', name: 'Canada',    desc: 'NOC 2021 · 516 verified codes', img: COUNTRY_HERO.CA },
            { code: 'NZ', name: 'New Zealand', desc: 'ANZSCO · 246 verified codes', img: COUNTRY_HERO.NZ },
          ].map((c, i) => (
            <motion.div
              key={c.code}
              initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.6, delay: 0.15 + i * 0.1 }}
            >
              <Link reloadDocument
                to={`/atlas/${c.code.toLowerCase()}`}
                className="block relative overflow-hidden rounded-xl group h-32 hover:shadow-xl transition-all"
                style={{ border: `1px solid ${BRAND.border}` }}
                data-testid={`hero-country-${c.code}`}
              >
                <img src={c.img} alt={c.name} className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" />
                <div className="absolute inset-0" style={{ background: `linear-gradient(to right, ${BRAND.primaryDk}E0, ${BRAND.primaryDk}80)` }} />
                <div className="relative h-full p-5 flex items-center justify-between text-white">
                  <div>
                    <p className="font-serif-leamss text-2xl font-bold">{c.code === 'AU' ? '🇦🇺' : c.code === 'CA' ? '🇨🇦' : '🇳🇿'} {c.name}</p>
                    <p className="text-sm opacity-90 mt-1">{c.desc}</p>
                  </div>
                  <ArrowUpRight className="w-6 h-6 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Trust strip (marquee) ─────────────────────────────────────────────────
function TrustStrip({ items: itemsOverride }) {
  const items = itemsOverride && itemsOverride.length > 0 ? itemsOverride : [
    { num: '80+', label: 'Visa Categories' },
    { num: '80k+', label: 'Visas Processed' },
    { num: '80+', label: 'LEAMSS Experts' },
    { num: '4.9★', label: 'Google Reviews' },
    { num: '100%', label: 'Refund on Negative Assessment' },
    { num: '12+', label: 'Years of Trust' },
  ];
  return (
    <section className="py-8 border-y" style={{ background: BRAND.bgSoft, borderColor: BRAND.border }} data-testid="trust-strip">
      <div className="overflow-hidden">
        <div className="flex marquee-track">
          {[...items, ...items].map((it, i) => (
            <div key={i} className="flex items-center gap-3 px-8 shrink-0">
              <span className="font-serif-leamss text-2xl font-bold" style={{ color: BRAND.accent }}>{it.num}</span>
              <span className="text-sm font-medium" style={{ color: BRAND.body }}>{it.label}</span>
              <span style={{ color: BRAND.border }}>•</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Eligibility Quiz & Points Calculator Section (Y-Axis Style 2-Column Wizard) ───
const COUNTRY_CALCULATOR_CONFIG = {
  AU: {
    name: 'Australia',
    flag: '🇦🇺',
    systemName: 'General Skilled Migration (Subclass 189 / 190 / 491)',
    passMark: 65,
    maxScore: 100,
    unit: 'Points',
    steps: [
      {
        id: 'country',
        label: 'Your Destination Country',
        description: 'Select Australia to calculate points for Subclass 189, 190, and 491 visas.',
        options: [
          { value: 'AU', label: '🇦🇺 Australia', subtitle: 'GSM Points Test (Subclass 189 / 190 / 491)' },
          { value: 'CA', label: '🇨🇦 Canada', subtitle: 'Express Entry (CRS & FSWP 67-Points)' },
          { value: 'NZ', label: '🇳🇿 New Zealand', subtitle: 'Skilled Migrant Category (6-Points & Green List)' },
        ],
      },
      {
        id: 'age',
        label: 'Your Age',
        description: 'Age at the time of visa invitation.',
        options: [
          { value: '25-32', label: '25 to 32 years', pts: 30, tag: 'Maximum Points (+30)' },
          { value: '18-24', label: '18 to 24 years', pts: 25, tag: '+25 Points' },
          { value: '33-39', label: '33 to 39 years', pts: 25, tag: '+25 Points' },
          { value: '40-44', label: '40 to 44 years', pts: 15, tag: '+15 Points' },
          { value: '45+', label: '45 years or older', pts: 0, tag: '0 Points (Age Limit)' },
        ],
      },
      {
        id: 'education',
        label: 'Highest Educational Qualification',
        description: 'Recognised qualification assessed by an Australian assessing authority.',
        options: [
          { value: 'phd', label: 'Doctorate / PhD', pts: 20, tag: '+20 Points' },
          { value: 'masters', label: "Master's Degree (or Bachelor with Honours)", pts: 15, tag: '+15 Points' },
          { value: 'bachelors', label: "Bachelor's Degree (3+ years)", pts: 15, tag: '+15 Points' },
          { value: 'diploma', label: 'Trade Qualification / Advanced Diploma', pts: 10, tag: '+10 Points' },
          { value: 'high_school', label: 'High School / Class 12', pts: 0, tag: '0 Points' },
        ],
      },
      {
        id: 'experience',
        label: 'Skilled Work Experience (Overseas / Relevant)',
        description: 'Years of closely related skilled employment in the past 10 years.',
        options: [
          { value: '8+', label: '8 or more years', pts: 15, tag: 'Maximum Points (+15)' },
          { value: '5-7', label: '5 to 7 years', pts: 10, tag: '+10 Points' },
          { value: '3-4', label: '3 to 4 years', pts: 5, tag: '+5 Points' },
          { value: '1-2', label: '1 to 2 years', pts: 0, tag: '0 Overseas Pts (+5 if in AU)' },
          { value: '0', label: 'Less than 1 year', pts: 0, tag: '0 Points' },
        ],
      },
      {
        id: 'english',
        label: 'English Language Proficiency (IELTS / PTE / TOEFL)',
        description: 'Official test taken in the last 3 years.',
        options: [
          { value: 'superior', label: 'Superior English (IELTS 8.0+ each / PTE 79+)', pts: 20, tag: '+20 Points' },
          { value: 'proficient', label: 'Proficient English (IELTS 7.0-7.5 each / PTE 65+)', pts: 10, tag: '+10 Points' },
          { value: 'competent', label: 'Competent English (IELTS 6.0 each / PTE 50+)', pts: 0, tag: '0 Pts (Entry Prerequisite)' },
          { value: 'none', label: 'Beginner / Not yet taken test', pts: 0, tag: '0 Points' },
        ],
      },
      {
        id: 'partner',
        label: 'Partner Skills & Marital Status',
        description: 'Points awarded based on your spouse or single status.',
        options: [
          { value: 'single_or_citizen', label: 'Single / Spouse is Australian Citizen or PR', pts: 10, tag: '+10 Points' },
          { value: 'skilled_english', label: 'Spouse has Positive Skills Assessment + Competent English', pts: 10, tag: '+10 Points' },
          { value: 'english_only', label: 'Spouse has Competent English only', pts: 5, tag: '+5 Points' },
          { value: 'not_contributing', label: 'Spouse not contributing / Not migrating', pts: 0, tag: '0 Points' },
        ],
      },
      {
        id: 'nomination',
        label: 'State / Territory Nomination & Regional Pathway',
        description: 'Australian Government state or regional sponsorship bonus.',
        options: [
          { value: 'regional_491', label: 'Regional Nomination (Subclass 491 Visa)', pts: 15, tag: '+15 Bonus Points' },
          { value: 'state_190', label: 'State Nomination (Subclass 190 PR Visa)', pts: 5, tag: '+5 Bonus Points' },
          { value: 'independent_189', label: 'Direct Independent (Subclass 189 PR Visa)', pts: 0, tag: '0 Bonus Points' },
        ],
      },
    ],
  },
  CA: {
    name: 'Canada',
    flag: '🇨🇦',
    systemName: 'Express Entry (FSWP 67-Point Grid & CRS)',
    passMark: 67,
    maxScore: 100,
    unit: 'Points',
    steps: [
      {
        id: 'country',
        label: 'Your Destination Country',
        description: 'Select Canada for Express Entry Federal Skilled Worker (FSWP) points.',
        options: [
          { value: 'AU', label: '🇦🇺 Australia', subtitle: 'GSM Points Test (Subclass 189 / 190 / 491)' },
          { value: 'CA', label: '🇨🇦 Canada', subtitle: 'Express Entry (CRS & FSWP 67-Points)' },
          { value: 'NZ', label: '🇳🇿 New Zealand', subtitle: 'Skilled Migrant Category (6-Points & Green List)' },
        ],
      },
      {
        id: 'age',
        label: 'Your Age',
        description: 'Maximum points awarded to candidates aged 18 to 35.',
        options: [
          { value: '18-35', label: '18 to 35 years', pts: 12, tag: 'Maximum Points (+12 FSWP)' },
          { value: '36', label: '36 years', pts: 11, tag: '+11 Points' },
          { value: '37', label: '37 years', pts: 10, tag: '+10 Points' },
          { value: '38', label: '38 years', pts: 9, tag: '+9 Points' },
          { value: '39', label: '39 years', pts: 8, tag: '+8 Points' },
          { value: '40-44', label: '40 to 44 years', pts: 5, tag: '+1 to 7 Points' },
          { value: '45+', label: '45 years or older', pts: 0, tag: '0 Points' },
        ],
      },
      {
        id: 'education',
        label: 'Highest Level of Education (ECA Evaluated)',
        description: 'Educational Credential Assessment (ECA) equivalent for Canada.',
        options: [
          { value: 'phd', label: 'Doctoral Degree (PhD)', pts: 25, tag: '+25 Points' },
          { value: 'masters', label: "Master's Degree (or Professional Degree in Medicine/Law)", pts: 23, tag: '+23 Points' },
          { value: 'bachelors', label: "Bachelor's Degree (3+ year program)", pts: 21, tag: '+21 Points' },
          { value: 'diploma', label: 'Two or more Certificates / 2-Year Diploma', pts: 19, tag: '+19 Points' },
          { value: 'high_school', label: 'Secondary School / High School', pts: 5, tag: '+5 Points' },
        ],
      },
      {
        id: 'experience',
        label: 'Continuous Skilled Work Experience (TEER 0, 1, 2, 3)',
        description: 'Full-time continuous skilled work experience in the last 10 years.',
        options: [
          { value: '6+', label: '6 or more years', pts: 15, tag: 'Maximum Points (+15)' },
          { value: '4-5', label: '4 to 5 years', pts: 13, tag: '+13 Points' },
          { value: '2-3', label: '2 to 3 years', pts: 11, tag: '+11 Points' },
          { value: '1', label: '1 year continuous', pts: 9, tag: '+9 Points (Minimum)' },
          { value: '0', label: 'Less than 1 year', pts: 0, tag: '0 Points' },
        ],
      },
      {
        id: 'english',
        label: 'First Official Language (IELTS / CELPIP / PTE Core)',
        description: 'Canadian Language Benchmark (CLB) score.',
        options: [
          { value: 'clb9_plus', label: 'CLB 9+ (IELTS 8.0 L, 7.0 R/W/S / PTE 79+)', pts: 24, tag: 'Maximum Points (+24)' },
          { value: 'clb8', label: 'CLB 8 (IELTS 7.5 L, 6.5 R/W/S / PTE 65+)', pts: 20, tag: '+20 Points' },
          { value: 'clb7', label: 'CLB 7 (IELTS 6.0 each / PTE 50+)', pts: 16, tag: '+16 Points (Minimum)' },
          { value: 'none', label: 'Below CLB 7 / Not taken yet', pts: 0, tag: '0 Points' },
        ],
      },
      {
        id: 'partner',
        label: 'Adaptability & Partner Factors',
        description: 'Spouse language, Canadian relative, or Canadian study/work.',
        options: [
          { value: 'single_or_citizen', label: 'Single / Canadian Citizen Spouse', pts: 10, tag: '+10 Points' },
          { value: 'skilled_english', label: 'Spouse with CLB 7+ English and ECA Degree', pts: 10, tag: '+10 Points' },
          { value: 'english_only', label: 'Spouse with CLB 5+ English', pts: 5, tag: '+5 Points' },
          { value: 'not_contributing', label: 'No adaptability factors', pts: 0, tag: '0 Points' },
        ],
      },
      {
        id: 'nomination',
        label: 'Provincial Nomination (PNP) or Arranged Employment',
        description: 'Provincial nominee certificate or LMIA-approved job offer.',
        options: [
          { value: 'pnp_nomination', label: 'Provincial Nominee Program (PNP Nomination)', pts: 10, tag: '+10 FSWP (+600 CRS Points)' },
          { value: 'job_offer', label: 'Arranged Employment (Valid LMIA Job Offer)', pts: 10, tag: '+10 FSWP (+50 CRS Points)' },
          { value: 'none', label: 'Direct Federal Skilled Worker (No PNP / Job Offer)', pts: 0, tag: '0 Bonus Points' },
        ],
      },
    ],
  },
  NZ: {
    name: 'New Zealand',
    flag: '🇳🇿',
    systemName: 'Skilled Migrant Category (6-Point System & Green List)',
    passMark: 6,
    maxScore: 6,
    unit: 'Points',
    steps: [
      {
        id: 'country',
        label: 'Your Destination Country',
        description: 'Select New Zealand to calculate points under the official SMC 6-point system.',
        options: [
          { value: 'AU', label: '🇦🇺 Australia', subtitle: 'GSM Points Test (Subclass 189 / 190 / 491)' },
          { value: 'CA', label: '🇨🇦 Canada', subtitle: 'Express Entry (CRS & FSWP 67-Points)' },
          { value: 'NZ', label: '🇳🇿 New Zealand', subtitle: 'Skilled Migrant Category (6-Points & Green List)' },
        ],
      },
      {
        id: 'age',
        label: 'Your Age',
        description: 'Immigration New Zealand SMC age limit is 55 years.',
        options: [
          { value: '18-39', label: '18 to 39 years', pts: 0, tag: 'Eligible (Under 55 Limit)' },
          { value: '40-49', label: '40 to 49 years', pts: 0, tag: 'Eligible (Under 55 Limit)' },
          { value: '50-55', label: '50 to 55 years', pts: 0, tag: 'Eligible' },
          { value: '55+', label: '55 years or older', pts: 0, tag: 'Ineligible for SMC' },
        ],
      },
      {
        id: 'education',
        label: 'Recognised Qualification (NZQA Level)',
        description: 'Primary pathway to claiming 3 to 6 qualification points.',
        options: [
          { value: 'phd', label: 'Doctorate / PhD (NZQA Level 10)', pts: 6, tag: '6 Points (Direct PR Eligible!)' },
          { value: 'masters', label: "Master's Degree (NZQA Level 9)", pts: 5, tag: '+5 Points' },
          { value: 'bachelors_hons', label: "Bachelor's (Honours) / Postgrad Diploma (Level 8)", pts: 4, tag: '+4 Points' },
          { value: 'bachelors', label: "Bachelor's Degree (NZQA Level 7)", pts: 3, tag: '+3 Points' },
          { value: 'diploma', label: 'Trade Qualification / Diploma (Level 4-6)', pts: 3, tag: '+3 Points' },
        ],
      },
      {
        id: 'experience',
        label: 'Skilled Work Experience in New Zealand',
        description: 'You can claim up to 3 points for skilled work in NZ.',
        options: [
          { value: '3+', label: '3 or more years in NZ', pts: 3, tag: '+3 Points' },
          { value: '2', label: '2 years in NZ', pts: 2, tag: '+2 Points' },
          { value: '1', label: '1 year in NZ', pts: 1, tag: '+1 Point' },
          { value: '0', label: 'Overseas Experience only / No NZ experience yet', pts: 0, tag: '0 NZ Points' },
        ],
      },
      {
        id: 'english',
        label: 'English Language Requirement',
        description: 'Minimum English proficiency required for NZ SMC.',
        options: [
          { value: 'superior', label: 'IELTS 6.5+ / PTE 58+ (SMC Standard Requirement)', pts: 0, tag: 'Requirement Met ✓' },
          { value: 'none', label: 'Currently Preparing for English Test', pts: 0, tag: 'Needs IELTS 6.5' },
        ],
      },
      {
        id: 'partner',
        label: 'Partner Status',
        description: 'Partner must meet English requirements for joint application.',
        options: [
          { value: 'single_or_citizen', label: 'Single or Partner is NZ Citizen/Resident', pts: 0, tag: 'Standard' },
          { value: 'skilled_english', label: 'Partner meets English Requirements (IELTS 6.5+)', pts: 0, tag: 'Eligible ✓' },
          { value: 'not_contributing', label: 'Partner not meeting English requirements', pts: 0, tag: 'Conditional' },
        ],
      },
      {
        id: 'nomination',
        label: 'Job Offer & Green List Status',
        description: 'New Zealand job offer or Green List Tier fast-track.',
        options: [
          { value: 'green_list_tier1', label: 'Green List Tier 1 Role (Straight to Residence)', pts: 6, tag: 'Fast-Track PR (Tier 1)' },
          { value: 'green_list_tier2', label: 'Green List Tier 2 Role (Work to Residence)', pts: 3, tag: 'Tier 2 (24 Mo. Pathway)' },
          { value: 'job_offer_standard', label: 'Accredited Employer Job Offer (AEWV)', pts: 2, tag: 'Standard Job Offer' },
          { value: 'none', label: 'Seeking Job Offer / Independent Evaluation', pts: 0, tag: 'Exploring Options' },
        ],
      },
    ],
  },
};

function calculateScoreData(countryCode, answers) {
  const cfg = COUNTRY_CALCULATOR_CONFIG[countryCode] || COUNTRY_CALCULATOR_CONFIG.AU;
  let total = 0;
  const breakdown = [];

  for (const st of cfg.steps) {
    if (st.id === 'country') continue;
    const pickedVal = answers[st.id];
    if (!pickedVal) continue;
    const opt = st.options.find(o => o.value === pickedVal);
    if (opt && typeof opt.pts === 'number') {
      if (countryCode === 'NZ') {
        if (st.id === 'education') {
          total = Math.max(total, opt.pts);
        } else if (st.id === 'experience') {
          total = Math.min(6, total + opt.pts);
        } else if (st.id === 'nomination' && opt.value.startsWith('green_list')) {
          total = Math.max(total, opt.pts);
        }
      } else {
        total += opt.pts;
      }
      if (opt.pts > 0) {
        breakdown.push({ label: st.label, pts: opt.pts, tag: opt.tag });
      }
    }
  }

  return {
    total,
    passMark: cfg.passMark,
    maxScore: cfg.maxScore,
    unit: cfg.unit,
    breakdown,
    isEligible: total >= cfg.passMark,
  };
}

function EligibilityQuizSection() {
  const [selectedCountry, setSelectedCountry] = useState('AU');
  const [stepIndex, setStepIndex] = useState(0);
  const [answers, setAnswers] = useState({ country: 'AU' });
  const [result, setResult] = useState(null);
  const [computing, setComputing] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [clientInfo, setClientInfo] = useState({ name: '', phone: '', email: '', message: '' });

  const activeConfig = COUNTRY_CALCULATOR_CONFIG[selectedCountry] || COUNTRY_CALCULATOR_CONFIG.AU;
  const currentStepDef = activeConfig.steps[stepIndex];
  const totalSteps = activeConfig.steps.length;

  const scoreData = calculateScoreData(selectedCountry, answers);

  const handleSelectOption = (stepId, value) => {
    if (stepId === 'country') {
      setSelectedCountry(value);
      setAnswers({ country: value });
      setStepIndex(1); // Advance to age step automatically
      return;
    }
    setAnswers(prev => ({ ...prev, [stepId]: value }));
  };

  const handleNext = () => {
    if (stepIndex < totalSteps - 1) {
      setStepIndex(stepIndex + 1);
    } else {
      setShowModal(true);
    }
  };

  const handleBack = () => {
    if (stepIndex > 0) setStepIndex(stepIndex - 1);
  };

  const handleReset = () => {
    setStepIndex(0);
    setAnswers({ country: selectedCountry });
    setResult(null);
    setShowModal(false);
  };

  const handleModalSubmit = async (e) => {
    e.preventDefault();
    setComputing(true);
    const countryMap = { AU: 'Australia', CA: 'Canada', NZ: 'New Zealand' };
    const cName = countryMap[selectedCountry] || 'Australia';
    const payload = {
      name: clientInfo.name,
      email: clientInfo.email,
      phone: clientInfo.phone,
      country_of_interest: selectedCountry,
      source: 'eligibility_calculator',
      atlas_code: 'points_calculator',
      atlas_title: `${cName} Points Assessment`,
      message: `Score: ${scoreData.total} ${scoreData.unit} for ${cName}. ${clientInfo.message ? 'Client Note: ' + clientInfo.message : 'Requested full breakdown & report.'}`
    };

    try {
      await axios.post(`${API}/public-atlas/lead`, payload);
    } catch (err) {
      try {
        await axios.post('https://app.leamss.com/api/public-atlas/lead', payload);
      } catch (err2) {}
    }

    setShowModal(false);
    setResult({
      client_name: clientInfo.name,
      client_phone: clientInfo.phone,
      client_email: clientInfo.email,
      overall_summary: `Your calculated score for ${cName} is ${scoreData.total} ${scoreData.unit} (${scoreData.isEligible ? 'Meets or exceeds' : 'Approaching'} the qualifying threshold of ${scoreData.passMark} ${scoreData.unit}).`,
      _country: cName,
      _country_code: selectedCountry,
      _scoreData: scoreData,
    });
    setComputing(false);
  };

  const isCurrentStepAnswered = answers[currentStepDef?.id] !== undefined && answers[currentStepDef?.id] !== '';

  return (
    <section id="quiz" className="py-16 lg:py-24" style={{ background: BRAND.bgSoft }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Banner Header */}
        <div className="mb-10 text-center lg:text-left">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider mb-3"
            style={{ background: 'rgba(31,77,68,0.08)', color: BRAND.primary }}>
            <Sparkles className="w-3.5 h-3.5" /> Instant Free Assessment · MARA &amp; Licensed Experts
          </span>
          <h2 className="font-serif-leamss text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight" style={{ color: BRAND.ink }}>
            Free Immigration Points Calculator
          </h2>
          <p className="mt-3 text-base sm:text-lg text-slate-600 max-w-2xl">
            Evaluate your eligibility for <strong>Australia 🇦🇺, Canada 🇨🇦 &amp; New Zealand 🇳🇿</strong> in real-time. Transparent points breakdown with zero guesswork.
          </p>
        </div>

        {!result ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Left Column: Interactive Wizard Stepper */}
            <div className="lg:col-span-8 bg-white rounded-2xl p-6 sm:p-10 shadow-sm border" style={{ borderColor: BRAND.border }}>
              {/* Stepper Header */}
              <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b" style={{ borderColor: BRAND.border }}>
                <div>
                  <div className="text-xs font-bold uppercase tracking-wider" style={{ color: BRAND.accent }}>
                    STEP {stepIndex + 1} OF {totalSteps}
                  </div>
                  <h3 className="font-serif-leamss text-2xl sm:text-3xl font-bold mt-1" style={{ color: BRAND.ink }}>
                    {currentStepDef.label}
                  </h3>
                  <p className="text-xs sm:text-sm mt-1" style={{ color: BRAND.muted }}>
                    {currentStepDef.description}
                  </p>
                </div>
                <div className="flex items-center gap-1.5">
                  {activeConfig.steps.map((s, idx) => (
                    <button
                      key={s.id}
                      onClick={() => setStepIndex(idx)}
                      title={`Step ${idx + 1}: ${s.label}`}
                      className="transition-all duration-300 rounded-full"
                      style={{
                        width: idx === stepIndex ? 24 : 10,
                        height: 10,
                        backgroundColor: idx === stepIndex ? BRAND.accent : idx < stepIndex ? BRAND.primary : BRAND.border,
                      }}
                    />
                  ))}
                </div>
              </div>

              {/* Options Grid */}
              <div className="py-8">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={`${selectedCountry}-${stepIndex}`}
                    initial={{ opacity: 0, x: 16 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -16 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-3"
                  >
                    {currentStepDef.options.map((opt) => {
                      const isSelected = answers[currentStepDef.id] === opt.value;
                      return (
                        <div
                          key={opt.value}
                          onClick={() => handleSelectOption(currentStepDef.id, opt.value)}
                          className="p-4 sm:p-5 rounded-xl border-2 transition-all cursor-pointer flex items-center justify-between gap-4 hover:shadow-md"
                          style={{
                            borderColor: isSelected ? BRAND.primary : BRAND.border,
                            backgroundColor: isSelected ? 'rgba(31,77,68,0.04)' : '#FFFFFF',
                          }}
                        >
                          <div className="flex items-center gap-3.5">
                            <div
                              className="w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors shrink-0"
                              style={{
                                borderColor: isSelected ? BRAND.primary : BRAND.muted,
                                backgroundColor: isSelected ? BRAND.primary : 'transparent',
                              }}
                            >
                              {isSelected && <div className="w-2 h-2 rounded-full bg-white" />}
                            </div>
                            <div>
                              <div className="text-sm sm:text-base font-bold" style={{ color: BRAND.ink }}>
                                {opt.label}
                              </div>
                              {opt.subtitle && (
                                <div className="text-xs text-slate-500 mt-0.5">
                                  {opt.subtitle}
                                </div>
                              )}
                            </div>
                          </div>

                          {opt.tag && (
                            <span
                              className="text-xs font-bold px-2.5 py-1 rounded-full whitespace-nowrap shrink-0"
                              style={{
                                backgroundColor: isSelected ? 'rgba(31,77,68,0.12)' : 'rgba(0,0,0,0.05)',
                                color: isSelected ? BRAND.primary : BRAND.body,
                              }}
                            >
                              {opt.tag}
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </motion.div>
                </AnimatePresence>
              </div>

              {/* Step Navigation Controls */}
              <div className="flex items-center justify-between pt-6 border-t" style={{ borderColor: BRAND.border }}>
                <Button
                  variant="ghost"
                  onClick={handleBack}
                  disabled={stepIndex === 0}
                  className="font-bold text-sm"
                >
                  ← Back
                </Button>

                <Button
                  onClick={handleNext}
                  disabled={!isCurrentStepAnswered || computing}
                  size="lg"
                  className="font-bold text-sm sm:text-base px-6 shadow-md"
                  style={{ backgroundColor: BRAND.accent, color: '#FFFFFF' }}
                >
                  {computing ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : stepIndex === totalSteps - 1 ? (
                    <>Get Full Breakdown &amp; Plan <Sparkles className="w-4 h-4 ml-1.5" /></>
                  ) : (
                    <>Next Step <ArrowRight className="w-4 h-4 ml-1.5" /></>
                  )}
                </Button>
              </div>
            </div>

            {/* Right Column: Sticky Live Scorecard & Expert Card (Y-Axis Style) */}
            <div className="lg:col-span-4 space-y-6 lg:sticky lg:top-24">
              {/* Score Box Card */}
              <div className="bg-white rounded-2xl p-6 shadow-sm border text-center" style={{ borderColor: BRAND.border }}>
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                  Live Eligibility Scorecard
                </p>
                <div className="text-xs text-slate-500 mb-6">
                  Evaluating for: <strong>{activeConfig.flag} {activeConfig.name}</strong>
                </div>

                {/* Big Animated Score Circle */}
                <div className="relative mx-auto w-36 h-36 rounded-full flex flex-col items-center justify-center border-4 shadow-inner mb-4 transition-all duration-500"
                  style={{
                    borderColor: scoreData.isEligible ? BRAND.success : BRAND.accent,
                    backgroundColor: scoreData.isEligible ? 'rgba(46,125,50,0.05)' : 'rgba(212,99,63,0.05)',
                  }}>
                  <div className="text-xs uppercase font-bold text-slate-400">YOUR SCORE</div>
                  <div className="font-serif-leamss text-4xl sm:text-5xl font-bold tracking-tight"
                    style={{ color: scoreData.isEligible ? BRAND.success : BRAND.accent }}>
                    {scoreData.total}
                  </div>
                  <div className="text-[11px] font-bold text-slate-500">
                    / {scoreData.maxScore} {scoreData.unit}
                  </div>
                </div>

                {/* Pass Mark Status */}
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold mb-5"
                  style={{
                    backgroundColor: scoreData.isEligible ? '#E8F3E9' : '#FBEDE7',
                    color: scoreData.isEligible ? BRAND.success : BRAND.accent,
                  }}>
                  {scoreData.isEligible ? '✓ Qualifies for Minimum Threshold' : `Pass Mark: ${scoreData.passMark} ${scoreData.unit}`}
                </div>

                {/* Factor Breakdown Chips */}
                {scoreData.breakdown.length > 0 && (
                  <div className="text-left pt-4 border-t space-y-2" style={{ borderColor: BRAND.border }}>
                    <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                      Score Breakdown
                    </div>
                    {scoreData.breakdown.map((item, i) => (
                      <div key={i} className="flex items-center justify-between text-xs text-slate-600">
                        <span>{item.label}</span>
                        <span className="font-bold" style={{ color: BRAND.primary }}>+{item.pts} pts</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Talk to an Expert Card */}
              <div className="bg-white rounded-2xl p-6 shadow-sm border" style={{ borderColor: BRAND.border }}>
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-full flex items-center justify-center text-white" style={{ backgroundColor: BRAND.primary }}>
                    <UserIcon className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="font-bold text-sm sm:text-base text-slate-900">Talk to a LEAMSS Expert</h4>
                    <p className="text-xs text-slate-500">MARA &amp; Licensed Migration Advisors</p>
                  </div>
                </div>

                <div className="space-y-2 mt-4">
                  <a
                    href={`tel:${PHONE}`}
                    className="flex items-center justify-between p-3 rounded-xl border bg-slate-50 hover:bg-slate-100 transition text-xs font-bold text-slate-800"
                  >
                    <span className="flex items-center gap-2"><Phone className="w-3.5 h-3.5 text-emerald-700" /> Direct Call</span>
                    <span>{PHONE}</span>
                  </a>

                  <a
                    href={`https://wa.me/91${WHATSAPP}?text=${encodeURIComponent('Hi LEAMSS Team, I am checking my immigration eligibility and would like expert guidance.')}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between p-3 rounded-xl border bg-emerald-50 hover:bg-emerald-100 border-emerald-200 transition text-xs font-bold text-emerald-900"
                  >
                    <span className="flex items-center gap-2"><MessageCircle className="w-3.5 h-3.5 text-emerald-600" /> WhatsApp Chat</span>
                    <span>+91 {WHATSAPP}</span>
                  </a>
                </div>

                <div className="mt-4 pt-3 border-t text-[11px] text-slate-400 text-center" style={{ borderColor: BRAND.border }}>
                  100% Free Consultation · No Obligation · Registered Advisory
                </div>
              </div>
            </div>
          </div>
        ) : (
          <QuizResult result={result} onReset={handleReset} />
        )}

        {/* Lead Information Modal Dialog */}
        {showModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <div className="bg-white rounded-2xl max-w-lg w-full p-6 sm:p-8 shadow-2xl relative animate-in fade-in zoom-in duration-200">
              <button
                onClick={() => setShowModal(false)}
                className="absolute top-4 right-4 w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-500 text-sm font-bold"
              >
                ✕
              </button>
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider mb-2"
                style={{ background: 'rgba(31,77,68,0.08)', color: BRAND.primary }}>
                <Sparkles className="w-3.5 h-3.5" /> Free Assessment Report
              </div>
              <h3 className="font-serif-leamss text-2xl font-bold text-slate-900 mb-1">
                Get Your Full Breakdown &amp; Assessment Report
              </h3>
              <p className="text-xs sm:text-sm text-slate-500 mb-6">
                Please enter your contact details below to unlock your complete personalized points report, visa pathways, and country intelligence guide.
              </p>

              <form onSubmit={handleModalSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">Full Name *</label>
                  <input
                    type="text"
                    required
                    value={clientInfo.name}
                    onChange={(e) => setClientInfo(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g. Rahul Sharma"
                    className="w-full px-4 py-2.5 rounded-xl border text-sm text-slate-900 focus:outline-none focus:border-emerald-700"
                    style={{ borderColor: BRAND.border }}
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">WhatsApp Number / Phone *</label>
                  <input
                    type="tel"
                    required
                    value={clientInfo.phone}
                    onChange={(e) => setClientInfo(prev => ({ ...prev, phone: e.target.value }))}
                    placeholder="e.g. +91 9876543210"
                    className="w-full px-4 py-2.5 rounded-xl border text-sm text-slate-900 focus:outline-none focus:border-emerald-700"
                    style={{ borderColor: BRAND.border }}
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">Email ID *</label>
                  <input
                    type="email"
                    required
                    value={clientInfo.email}
                    onChange={(e) => setClientInfo(prev => ({ ...prev, email: e.target.value }))}
                    placeholder="e.g. rahul@example.com"
                    className="w-full px-4 py-2.5 rounded-xl border text-sm text-slate-900 focus:outline-none focus:border-emerald-700"
                    style={{ borderColor: BRAND.border }}
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">Message / Target Occupation (Optional)</label>
                  <textarea
                    rows={2}
                    value={clientInfo.message}
                    onChange={(e) => setClientInfo(prev => ({ ...prev, message: e.target.value }))}
                    placeholder="Tell us your target occupation, current city, or any specific questions..."
                    className="w-full px-4 py-2 rounded-xl border text-sm text-slate-900 focus:outline-none focus:border-emerald-700 resize-none"
                    style={{ borderColor: BRAND.border }}
                  />
                </div>

                <Button
                  type="submit"
                  disabled={computing || !clientInfo.name || !clientInfo.phone || !clientInfo.email}
                  className="w-full justify-center py-3 text-sm font-bold shadow-md"
                  style={{ backgroundColor: BRAND.accent, color: '#FFFFFF' }}
                >
                  {computing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Generate & Download Full Report →'}
                </Button>
                <p className="text-[11px] text-center text-slate-400">
                  🔒 100% Confidential · No Spam · MARA Registered Consultation
                </p>
              </form>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

const TIER_META = {
  strong:   { label: 'Strong match',   color: BRAND.success, bg: '#E8F3E9' },
  moderate: { label: 'Moderate match', color: BRAND.primary, bg: '#E9F0EE' },
  weak:     { label: 'Needs work',     color: BRAND.accent,  bg: '#FBEDE7' },
  unlikely: { label: 'Unlikely',       color: BRAND.muted,   bg: '#F1F3F2' },
};
const tierMeta = (t) => TIER_META[t] || TIER_META.unlikely;

// Canada Express Entry CRS uses a 1,200-point scale.
// Other LEAMSS pathway-fit cards continue to use the existing 0–100 scale.
function isCanadaPathway(p) {
  const haystack = [p?.country, p?.country_code, p?.countryCode, p?.slug, p?.name, p?.pathway]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  return haystack.includes('canada') || haystack.includes('can_') || haystack.includes('ca-');
}

function getPathwayScore(p) {
  if (isCanadaPathway(p)) {
    // Prefer an explicit CRS field when the API provides it.
    // Fall back to score because the current API may already return CRS in score.
    return Number(p?.crs_score ?? p?.score ?? 0);
  }
  return Number(p?.score ?? 0);
}

function getPathwayScoreMax(p) {
  if (isCanadaPathway(p)) {
    return Number(p?.crs_score_max ?? 1200);
  }
  return Number(p?.score_max ?? 100);
}

function getPathwayScorePercent(p) {
  const score = getPathwayScore(p);
  const max = getPathwayScoreMax(p);
  return max > 0 ? Math.min(100, Math.max(0, (score / max) * 100)) : 0;
}

function FactorBar({ b }) {
  const earned = Number(b?.earned ?? b?.score ?? 0);
  const max = Number(b?.max ?? b?.maximum ?? 0);
  const pct = max > 0 ? Math.round((earned / max) * 100) : 0;
  const color = pct >= 80 ? BRAND.success : pct >= 50 ? BRAND.primary : BRAND.accent;

  return (
    <div className="py-1.5" data-testid={`factor-${b?.factor || b?.label || 'item'}`}>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="font-semibold" style={{ color: BRAND.ink }}>
          {b?.label || b?.factor || 'Factor'}
        </span>
        <span className="font-bold tabular-nums" style={{ color }}>
          {earned}
          <span style={{ color: BRAND.muted }}>/{max}</span>
        </span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: BRAND.border }}>
        <div style={{ width: `${Math.min(100, Math.max(0, pct))}%`, background: color, height: '100%' }} />
      </div>
      {b?.reason && (
        <p className="text-[11px] mt-1" style={{ color: BRAND.muted }}>
          {b.reason}
        </p>
      )}
    </div>
  );
}

/*
 * Canada CRS breakdown renderer.
 *
 * The Canada API uses `crs_breakdown`, while the other pathway cards use
 * `breakdown`.  The renderer below intentionally supports both the current
 * section-based API shape and small variations in nested CRS data so the
 * frontend does not silently render an empty "CRS breakdown" heading.
 */
const CRS_SECTION_TITLES = {
  core_human_capital: 'Core / Human Capital',
  core_human_capital_factors: 'Core / Human Capital',
  second_official_language: 'Second Official Language',
  second_official_language_ability: 'Second Official Language',
  spouse_factors: 'Spouse / Common-Law Partner Factors',
  spouse_common_law_partner: 'Spouse / Common-Law Partner Factors',
  skill_transferability: 'Skill Transferability',
  additional_points: 'Additional Points',
};

function humanizeCRSKey(value) {
  if (!value) return 'CRS Factor';
  return String(value)
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function getCRSSectionTitle(section, index) {
  const key = section?.section || section?.key || section?.id || section?.name;
  return (
    CRS_SECTION_TITLES[key] ||
    section?.label ||
    section?.title ||
    humanizeCRSKey(key) ||
    `CRS Factor ${index + 1}`
  );
}

function normalizeCRSBreakdown(raw) {
  if (!raw) return [];

  if (Array.isArray(raw)) {
    return raw;
  }

  if (typeof raw === 'object') {
    return Object.entries(raw).map(([key, value]) => {
      if (value && typeof value === 'object' && !Array.isArray(value)) {
        return {
          ...value,
          section: value.section || key,
          label: value.label || value.title || CRS_SECTION_TITLES[key] || humanizeCRSKey(key),
        };
      }

      return {
        section: key,
        label: CRS_SECTION_TITLES[key] || humanizeCRSKey(key),
        earned: Number(value || 0),
        max: 0,
      };
    });
  }

  return [];
}

function CRSValue({ value }) {
  if (value === null || value === undefined || value === '') return null;
  return <span>{String(value)}</span>;
}

function CRSNestedRows({ items }) {
  if (!Array.isArray(items) || items.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t space-y-2" style={{ borderColor: BRAND.border }}>
      {items.map((item, index) => {
        const earned = item?.earned ?? item?.score ?? item?.points ?? 0;
        const max = item?.max ?? item?.maximum ?? item?.max_points ?? 0;
        const label =
          item?.label ||
          item?.name ||
          item?.factor ||
          item?.ability ||
          `Factor ${index + 1}`;

        return (
          <div key={`${label}-${index}`} className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[11px] font-medium" style={{ color: BRAND.body }}>
                {label}
              </p>

              {item?.reason && (
                <p className="text-[10px] mt-0.5" style={{ color: BRAND.muted }}>
                  {item.reason}
                </p>
              )}

              {item?.clb !== undefined && item?.clb !== null && (
                <p className="text-[10px] mt-0.5" style={{ color: BRAND.muted }}>
                  CLB {item.clb}
                </p>
              )}
            </div>

            {(item?.earned !== undefined ||
              item?.score !== undefined ||
              item?.points !== undefined) && (
              <span
                className="text-[11px] font-bold tabular-nums whitespace-nowrap"
                style={{ color: BRAND.primary }}
              >
                {earned}
                {max ? `/${max}` : ''}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function CanadaCRSBreakdown({ p, tm, displayScore, scoreMax }) {
  const sections = normalizeCRSBreakdown(p?.crs_breakdown);

  return (
    <div data-testid="crs-breakdown">
      <div className="flex items-center justify-between gap-3 mb-3">
        <p
          className="text-[11px] font-bold uppercase tracking-wider"
          style={{ color: BRAND.muted }}
        >
          CRS Breakdown
        </p>

        <span
          className="text-xs font-bold"
          style={{ color: tm.color }}
        >
          {displayScore}/{scoreMax}
        </span>
      </div>

      {sections.length > 0 ? (
        <div className="space-y-3">
          {sections.map((section, index) => {
            const earned = Number(section?.earned ?? section?.score ?? section?.points ?? 0);
            const max = Number(section?.max ?? section?.maximum ?? section?.max_points ?? 0);
            const pct = max > 0 ? Math.min(100, Math.max(0, (earned / max) * 100)) : 0;

            const nestedItems =
              section?.breakdown ||
              section?.factors ||
              section?.items ||
              section?.abilities ||
              [];

            const sectionColor =
              pct >= 80
                ? BRAND.success
                : pct >= 50
                  ? BRAND.primary
                  : BRAND.accent;

            return (
              <div
                key={`${section?.section || section?.key || index}`}
                className="rounded-lg p-3"
                style={{
                  background: '#FFFFFF',
                  border: `1px solid ${BRAND.border}`,
                }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p
                      className="text-xs font-bold"
                      style={{ color: BRAND.ink }}
                    >
                      {getCRSSectionTitle(section, index)}
                    </p>

                    {section?.reason && (
                      <p
                        className="text-[10px] mt-1"
                        style={{ color: BRAND.muted }}
                      >
                        {section.reason}
                      </p>
                    )}
                  </div>

                  {(section?.earned !== undefined ||
                    section?.score !== undefined ||
                    section?.points !== undefined ||
                    section?.max !== undefined ||
                    section?.maximum !== undefined) && (
                    <span
                      className="text-xs font-bold tabular-nums whitespace-nowrap"
                      style={{ color: sectionColor }}
                    >
                      {earned}/{max}
                    </span>
                  )}
                </div>

                {max > 0 && (
                  <div
                    className="h-1.5 rounded-full overflow-hidden mt-2"
                    style={{ background: BRAND.border }}
                  >
                    <div
                      style={{
                        width: `${pct}%`,
                        background: sectionColor,
                        height: '100%',
                      }}
                    />
                  </div>
                )}

                <CRSNestedRows items={nestedItems} />

                {section?.details &&
                  typeof section.details === 'object' &&
                  !Array.isArray(section.details) && (
                    <div
                      className="mt-3 pt-3 border-t space-y-1.5"
                      style={{ borderColor: BRAND.border }}
                    >
                      {Object.entries(section.details).map(([key, value]) => (
                        <div
                          key={key}
                          className="flex items-center justify-between gap-3"
                        >
                          <span
                            className="text-[10px]"
                            style={{ color: BRAND.muted }}
                          >
                            {humanizeCRSKey(key)}
                          </span>
                          <span
                            className="text-[10px] font-semibold text-right"
                            style={{ color: BRAND.body }}
                          >
                            <CRSValue value={value} />
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
              </div>
            );
          })}
        </div>
      ) : (
        <div
          className="rounded-lg p-3"
          style={{
            background: '#FFFFFF',
            border: `1px solid ${BRAND.border}`,
          }}
        >
          <p className="text-xs" style={{ color: BRAND.muted }}>
            CRS details are not available for this score yet.
          </p>
        </div>
      )}

      <div
        className="mt-4 pt-3 border-t flex items-center justify-between"
        style={{ borderColor: BRAND.border }}
      >
        <span className="text-xs font-bold" style={{ color: BRAND.ink }}>
          Total CRS Score
        </span>
        <span className="text-sm font-bold" style={{ color: tm.color }}>
          {displayScore}/{scoreMax} CRS
        </span>
      </div>
    </div>
  );
}

function PathwayResultCard({ p, isBest }) {
  const [open, setOpen] = useState(isBest);
  const tm = tierMeta(p.tier);
  const canada = isCanadaPathway(p);
  const displayScore = getPathwayScore(p);
  const scoreMax = getPathwayScoreMax(p);
  const scorePercent = getPathwayScorePercent(p);

  return (
    <div
      className="rounded-xl border overflow-hidden bg-white"
      style={{
        borderColor: isBest ? BRAND.accent : BRAND.border,
        borderWidth: isBest ? 2 : 1,
      }}
      data-testid={`pathway-card-${p.slug || displayScore}`}
    >
      <div className="p-5">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div>
            {isBest && <Pill color={BRAND.accent}>★ Best Match</Pill>}
            <p
              className="text-sm font-bold mt-1"
              style={{ color: BRAND.ink }}
            >
              {p.name}
            </p>
            {p.estimated_timeline && (
              <p
                className="text-[11px] mt-0.5"
                style={{ color: BRAND.muted }}
              >
                ⏱ {p.estimated_timeline}
              </p>
            )}
          </div>

          <span
            className="text-[11px] font-semibold px-2 py-0.5 rounded-full whitespace-nowrap"
            style={{ background: tm.bg, color: tm.color }}
          >
            {tm.label}
          </span>
        </div>

        <div className="flex items-baseline gap-1">
          <span
            className="text-4xl font-bold font-serif-leamss"
            style={{ color: tm.color }}
          >
            {displayScore}
          </span>
          <span className="text-sm" style={{ color: BRAND.muted }}>
            / {scoreMax}
          </span>

          {canada && (
            <span
              className="ml-1 text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded"
              style={{
                background: `${BRAND.primary}10`,
                color: BRAND.primary,
              }}
            >
              CRS
            </span>
          )}
        </div>

        <div
          className="h-2 rounded-full overflow-hidden mt-2"
          style={{ background: BRAND.border }}
        >
          <div
            style={{
              width: `${scorePercent}%`,
              background: tm.color,
              height: '100%',
            }}
          />
        </div>

        {canada && (
          <p
            className="text-[11px] mt-2"
            style={{ color: BRAND.muted }}
          >
            Canada Express Entry Comprehensive Ranking System score. Maximum:
            1,200 points.
          </p>
        )}

        {p.notes && (
          <p className="text-xs mt-3" style={{ color: BRAND.body }}>
            {p.notes}
          </p>
        )}

        {p.strengths?.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {p.strengths.slice(0, 3).map((s, i) => (
              <span
                key={i}
                className="text-[10px] px-2 py-0.5 rounded-full"
                style={{
                  background: '#E8F3E9',
                  color: BRAND.success,
                }}
              >
                ✓ {s}
              </span>
            ))}
          </div>
        )}

        <button
          onClick={() => setOpen(!open)}
          className="mt-3 inline-flex items-center gap-1 text-xs font-semibold"
          style={{ color: BRAND.primary }}
          data-testid="toggle-breakdown"
        >
          {open ? 'Hide' : 'How is this calculated?'}
          <ChevronDown
            className="w-3.5 h-3.5 transition-transform"
            style={{
              transform: open ? 'rotate(180deg)' : 'none',
            }}
          />
        </button>
      </div>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            style={{
              overflow: 'hidden',
              background: BRAND.bgSoft,
            }}
          >
            <div
              className="px-5 py-4 border-t"
              style={{ borderColor: BRAND.border }}
            >
              {canada ? (
                <CanadaCRSBreakdown
                  p={p}
                  tm={tm}
                  displayScore={displayScore}
                  scoreMax={scoreMax}
                />
              ) : (
                <>
                  <p
                    className="text-[11px] font-bold uppercase tracking-wider mb-2"
                    style={{ color: BRAND.muted }}
                  >
                    Profile strength
                    {typeof p.raw_score === 'number'
                      ? ` · ${p.raw_score}/100`
                      : ''}
                  </p>

                  {(p.breakdown || []).map((b, i) => (
                    <FactorBar key={i} b={b} />
                  ))}
                </>
              )}

              {(p.adjustments?.length > 0) && (
                <div
                  className="mt-3 pt-3 border-t"
                  style={{ borderColor: BRAND.border }}
                >
                  <p
                    className="text-[11px] font-bold uppercase tracking-wider mb-2"
                    style={{ color: BRAND.muted }}
                  >
                    Pathway adjustments
                  </p>

                  {p.adjustments.map((a, i) => (
                    <div
                      key={i}
                      className="flex items-start justify-between gap-2 py-1"
                      data-testid="adjustment-row"
                    >
                      <div className="flex-1">
                        <span
                          className="text-xs font-semibold"
                          style={{ color: BRAND.ink }}
                        >
                          {a.label}
                        </span>
                        <p
                          className="text-[11px]"
                          style={{ color: BRAND.muted }}
                        >
                          {a.reason}
                        </p>
                      </div>

                      <span
                        className="text-xs font-bold tabular-nums whitespace-nowrap"
                        style={{ color: BRAND.accent }}
                      >
                        {a.delta}
                      </span>
                    </div>
                  ))}

                  <div
                    className="flex items-center justify-between mt-2 pt-2 border-t"
                    style={{ borderColor: BRAND.border }}
                  >
                    <span
                      className="text-xs font-bold"
                      style={{ color: BRAND.ink }}
                    >
                      Final score
                    </span>
                    <span
                      className="text-sm font-bold"
                      style={{ color: tm.color }}
                    >
                      {displayScore}/{scoreMax}
                      {canada ? ' CRS' : ''}
                    </span>
                  </div>
                </div>
              )}

              {p.gaps_to_fix?.length > 0 && (
                <div
                  className="mt-3 pt-3 border-t"
                  style={{ borderColor: BRAND.border }}
                >
                  <p
                    className="text-[11px] font-bold mb-1"
                    style={{ color: BRAND.accent }}
                  >
                    To improve your score:
                  </p>

                  <ul
                    className="text-[11px] space-y-0.5 ml-4"
                    style={{ color: BRAND.body }}
                  >
                    {p.gaps_to_fix.map((g, i) => (
                      <li key={i} className="list-disc">
                        {g}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function QuizLeadForm({ scoreId, country }) {
  const [form, setForm] = useState({ name: '', contact: '' });
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const send = async () => {
    if (!form.contact.trim()) return;
    setBusy(true);
    try {
      const isEmail = form.contact.includes('@');
      const cCode = country === 'Canada' ? 'CA' : (country === 'New Zealand' ? 'NZ' : 'AU');
      const payload = {
        name: form.name.trim() || 'Website Visitor',
        email: isEmail ? form.contact.trim() : `lead_${Date.now()}@leamss-client.com`,
        phone: isEmail ? '+919999999999' : form.contact.trim(),
        country_of_interest: cCode,
        source: 'eligibility_calculator',
        atlas_code: 'calculator',
        atlas_title: `${country || 'Australia'} Points Calculation`,
        message: `Eligibility points calculation requested for ${country || 'Australia'}.`,
      };

      try {
        await axios.post(`${API}/public-atlas/lead`, payload);
      } catch (err1) {
        try {
          await axios.post('https://app.leamss.com/api/public-atlas/lead', payload);
        } catch (err2) {
          await axios.post(`${API}/eligibility/lead`, {
            score_id: scoreId,
            name: form.name.trim() || 'Website Visitor',
            email: isEmail ? form.contact.trim() : null,
            mobile: isEmail ? null : form.contact.trim(),
            preferred_country: country || null,
          });
        }
      }
      setDone(true);
    } catch (e) { setDone(true); }
    setBusy(false);
  };
  if (done) {
    return (
      <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: '#fff' }} data-testid="quiz-lead-done">
        <CheckCircle2 className="w-4 h-4" /> Thank you! A LEAMSS expert will reach out within 24 hours.
      </div>
    );
  }
  return (
    <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto" data-testid="quiz-lead-form">
      <input
        value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
        placeholder="Your name" data-testid="quiz-lead-name"
        className="px-3 py-2 rounded-md text-sm outline-none" style={{ color: BRAND.ink, minWidth: 130 }}
      />
      <input
        value={form.contact} onChange={(e) => setForm({ ...form, contact: e.target.value })}
        placeholder="Email or WhatsApp number" data-testid="quiz-lead-contact"
        className="px-3 py-2 rounded-md text-sm outline-none" style={{ color: BRAND.ink, minWidth: 190 }}
      />
      <Button onClick={send} disabled={busy || !form.contact.trim()} data-testid="quiz-lead-submit">
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <>Get Report<Send className="w-4 h-4" /></>}
      </Button>
    </div>
  );
}

function ScorecardActions({ scoreId, topName, topScore, country }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', phone: '' });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const pdfUrl = `${API}/eligibility/report/${scoreId}`;
  const shareUrl = `${window.location.origin}/scorecard/${scoreId}`;
  const waText = encodeURIComponent(
    `I just found my best-fit visa pathway on LEAMSS! 🌍\n\n` +
    `✅ Best fit: ${topName || 'My pathway'} — ${topScore ?? ''}${country === 'Canada' ? '/1200 CRS' : '/100'}\n\n` +
    `Check your free pathway-fit score in 60 seconds 👇\n${shareUrl}`
  );
  const waUrl = `https://wa.me/?text=${waText}`;

  const validEmail = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);
  const validPhone = (p) => p.replace(/\D/g, '').length >= 8;

  const submit = async () => {
    setErr('');
    if (!form.name.trim()) return setErr('Please enter your name.');
    if (!validEmail(form.email.trim())) return setErr('Please enter a valid email.');
    if (!validPhone(form.phone.trim())) return setErr('Please enter a valid phone number.');
    setBusy(true);
    try {
      await axios.post(`${API}/eligibility/lead`, {
        score_id: scoreId,
        name: form.name.trim(),
        email: form.email.trim(),
        mobile: form.phone.trim(),
        preferred_country: country || null,
      });
      // trigger download / open the branded PDF
      window.open(pdfUrl, '_blank', 'noopener,noreferrer');
      setOpen(false);
      setForm({ name: '', email: '', phone: '' });
    } catch (e) {
      setErr(formatApiError(e, 'Something went wrong. Please try again.'));
    }
    setBusy(false);
  };

  return (
    <>
      <div className="flex flex-wrap gap-3 mb-6" data-testid="scorecard-actions">
        <Button onClick={() => setOpen(true)} data-testid="download-pdf-btn">
          <Download className="w-4 h-4" /> Download PDF report
        </Button>
        <Button as="a" variant="secondary" href={waUrl} target="_blank" rel="noopener noreferrer" data-testid="share-whatsapp-btn">
          <MessageCircle className="w-4 h-4" /> Share on WhatsApp
        </Button>
      </div>

      {open && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4" style={{ background: 'rgba(20,30,28,0.55)' }} data-testid="download-lead-modal" onClick={() => !busy && setOpen(false)}>
          <div className="w-full max-w-md rounded-2xl p-6" style={{ background: BRAND.bg }} onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between mb-1">
              <div className="inline-flex items-center gap-2">
                <Download className="w-5 h-5" style={{ color: BRAND.accent }} />
                <h4 className="font-serif-leamss text-xl font-bold" style={{ color: BRAND.ink }}>Get your PDF report</h4>
              </div>
              <button onClick={() => setOpen(false)} className="text-2xl leading-none" style={{ color: BRAND.muted }} data-testid="download-modal-close">×</button>
            </div>
            <p className="text-xs mb-4" style={{ color: BRAND.muted }}>
              Enter your details to download the full branded scorecard. A LEAMSS expert may reach out to help — no spam, ever.
            </p>
            <div className="space-y-3">
              <input data-testid="dl-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Full name *"
                className="w-full px-4 py-2.5 rounded-lg border-2 text-sm outline-none" style={{ borderColor: BRAND.border, color: BRAND.ink }} />
              <input data-testid="dl-email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="Email *"
                className="w-full px-4 py-2.5 rounded-lg border-2 text-sm outline-none" style={{ borderColor: BRAND.border, color: BRAND.ink }} />
              <input data-testid="dl-phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="Phone / WhatsApp *"
                className="w-full px-4 py-2.5 rounded-lg border-2 text-sm outline-none" style={{ borderColor: BRAND.border, color: BRAND.ink }} />
              {err && <p className="text-xs font-semibold" style={{ color: '#B91C1C' }} data-testid="dl-error">{err}</p>}
              <Button onClick={submit} disabled={busy} className="w-full justify-center" data-testid="dl-submit">
                {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Download className="w-4 h-4" /> Download my report</>}
              </Button>
              <p className="text-[10px] text-center" style={{ color: BRAND.muted }}>🔒 Your details are confidential · MARA-registered consultants</p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function QuizResult({ result, onReset }) {
  if (result.error) {
    return (
      <div className="p-12 text-center" data-testid="quiz-error">
        <p className="text-base font-bold" style={{ color: '#B91C1C' }}>
          {typeof result.error === 'string' ? result.error : 'Something went wrong. Please try again.'}
        </p>
        <Button variant="secondary" className="mt-4" onClick={onReset}>Try Again</Button>
      </div>
    );
  }

  const scoreData = result._scoreData;
  const cName = result._country || 'Australia';
  const isAU = cName.includes('Australia') || result._country_code === 'AU';
  const isCA = cName.includes('Canada') || result._country_code === 'CA';
  const isNZ = cName.includes('New Zealand') || result._country_code === 'NZ';

  const pathways = Object.entries(result.pathways || {})
    .map(([slug, p]) => ({ slug, ...p }))
    .sort((a, b) => getPathwayScorePercent(b) - getPathwayScorePercent(a));
  const top = result.top_recommendation;

  const todayStr = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

  return (
    <div className="p-6 sm:p-10 lg:p-12 bg-white rounded-2xl border shadow-sm space-y-8" style={{ borderColor: BRAND.border }} data-testid="quiz-result">
      {/* Top Header Banner */}
      <div className="flex flex-wrap items-start justify-between gap-4 pb-6 border-b" style={{ borderColor: BRAND.border }}>
        <div>
          <span className="inline-block px-3 py-1 rounded-md text-[11px] font-extrabold uppercase tracking-wider text-white mb-2"
            style={{ backgroundColor: BRAND.primary }}>
            OFFICIAL CLIENT ASSESSMENT REPORT
          </span>
          <h3 className="font-serif-leamss text-2xl sm:text-3xl font-bold" style={{ color: BRAND.ink }}>
            {cName} Immigration Points &amp; Pathway Assessment
          </h3>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Prepared for: <strong className="text-slate-900">{result.client_name || 'Valued Client'}</strong> · Date: <strong>{todayStr}</strong> · Target: <strong>{isAU ? '🇦🇺 Australia' : isCA ? '🇨🇦 Canada' : '🇳🇿 New Zealand'}</strong>
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <Button
            onClick={() => window.print()}
            className="shadow-sm font-bold text-xs sm:text-sm"
            style={{ backgroundColor: BRAND.accent, color: '#FFFFFF' }}
          >
            <Download className="w-4 h-4 mr-1.5" /> Download Report (PDF)
          </Button>
          <a
            href={`https://wa.me/91${WHATSAPP}?text=${encodeURIComponent(`Hi LEAMSS Team, I am ${result.client_name || 'an applicant'}. I just calculated my points score (${scoreData?.total || ''} pts) for ${cName} and would like expert guidance.`)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center px-4 py-2 rounded-lg text-xs sm:text-sm font-bold border border-emerald-600 text-emerald-800 bg-emerald-50 hover:bg-emerald-100 transition"
          >
            <MessageCircle className="w-4 h-4 mr-1.5 text-emerald-600" /> WhatsApp Chat
          </a>
          <Button variant="ghost" size="sm" onClick={onReset} className="text-xs">
            ↻ Re-calculate
          </Button>
        </div>
      </div>

      {/* Section 1: Points Scorecard & Factor Breakdown */}
      {scoreData && (
        <div className="rounded-2xl p-6 sm:p-8 border" style={{ backgroundColor: BRAND.bgWarm, borderColor: '#E6DED3' }}>
          <div className="flex items-center gap-2 mb-4">
            <span className="text-lg">📊</span>
            <h4 className="font-serif-leamss text-xl font-bold" style={{ color: BRAND.primary }}>
              Points Eligibility Scorecard
            </h4>
          </div>

          <div className="flex flex-wrap items-center gap-6 mb-4">
            <div className="flex items-baseline gap-2">
              <span className="font-serif-leamss text-4xl sm:text-5xl font-extrabold" style={{ color: BRAND.primary }}>
                {scoreData.total}
              </span>
              <span className="text-sm font-bold text-slate-500">
                / {scoreData.maxScore} {scoreData.unit}
              </span>
            </div>

            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold"
              style={{
                backgroundColor: scoreData.isEligible ? '#E8F3E9' : '#FBEDE7',
                color: scoreData.isEligible ? BRAND.success : BRAND.accent,
              }}>
              {scoreData.isEligible ? `✓ Qualifies for Minimum Threshold (Pass Mark: ${scoreData.passMark} ${scoreData.unit})` : `⚠️ Pass mark is ${scoreData.passMark} ${scoreData.unit}`}
            </span>
          </div>

          <p className="text-xs sm:text-sm text-slate-700 leading-relaxed mb-6">
            Dear <strong>{result.client_name || 'Applicant'}</strong>, your profile was evaluated for <strong>{cName}</strong> skilled migration.
            Your total score is <strong>{scoreData.total} {scoreData.unit}</strong>. {scoreData.isEligible ? 'You meet the minimum statutory criteria for invitation rounds.' : 'You can bridge the points gap through State/Regional nominations or partner skill claims.'}
          </p>

          {scoreData.breakdown && scoreData.breakdown.length > 0 && (
            <div className="overflow-x-auto rounded-xl border bg-white" style={{ borderColor: BRAND.border }}>
              <table className="w-full text-left text-xs sm:text-sm">
                <thead>
                  <tr className="border-b" style={{ backgroundColor: BRAND.bgSoft, borderColor: BRAND.border }}>
                    <th className="p-3 font-bold text-slate-700">Evaluation Parameter</th>
                    <th className="p-3 font-bold text-slate-700 text-right">Points Awarded</th>
                  </tr>
                </thead>
                <tbody>
                  {scoreData.breakdown.map((item, idx) => (
                    <tr key={idx} className="border-b last:border-0" style={{ borderColor: BRAND.border }}>
                      <td className="p-3 text-slate-800">{item.label}</td>
                      <td className="p-3 font-bold text-right text-emerald-800">+{item.pts} pts</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Section 2: Country Intelligence Guide ("Why Australia / Canada / New Zealand") */}
      <div className="rounded-2xl p-6 sm:p-8 border bg-slate-50" style={{ borderColor: BRAND.border }}>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xl">{isAU ? '🇦🇺' : isCA ? '🇨🇦' : '🇳🇿'}</span>
          <h4 className="font-serif-leamss text-xl font-bold" style={{ color: BRAND.ink }}>
            {isAU ? 'Why Migrate to Australia?' : isCA ? 'Why Migrate to Canada?' : 'Why Migrate to New Zealand?'}
          </h4>
        </div>
        <p className="text-xs sm:text-sm text-slate-600 mb-6">
          {isAU
            ? 'Australia offers one of the world’s most transparent, merit-based immigration systems. Permanent residents enjoy high living standards, universal Medicare healthcare, free schooling, high wages, and a direct 4-year citizenship pathway.'
            : isCA
            ? 'Canada is globally celebrated for its welcoming multicultural environment, universal healthcare, free K-12 schooling, thriving tech & healthcare industries, and fast Express Entry permanent residency pathways.'
            : 'New Zealand is internationally famous for its pristine natural beauty, unbeatable work-life balance, high safety, excellent public services, and progressive Skilled Migrant Category (SMC 6-Points) residence visa.'}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {isAU ? (
            <>
              <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="font-bold text-sm text-slate-900 mb-1">🏥 Universal Healthcare (Medicare)</div>
                <div className="text-xs text-slate-600 leading-relaxed">Free medical treatment in public hospitals, subsidized GP visits and PBS prescription medicines from day one of PR.</div>
              </div>
              <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="font-bold text-sm text-slate-900 mb-1">💰 High Earning Potential</div>
                <div className="text-xs text-slate-600 leading-relaxed">World’s highest minimum wage ($24.10/hr) with median professional salaries exceeding AUD $95,000/year.</div>
              </div>
              <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="font-bold text-sm text-slate-900 mb-1">🎓 Free Quality Education</div>
                <div className="text-xs text-slate-600 leading-relaxed">Free government schooling for dependent children and subsidized higher education fees under Commonwealth Support.</div>
              </div>
              <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="font-bold text-sm text-slate-900 mb-1">🌟 Direct PR &amp; Citizenship</div>
                <div className="text-xs text-slate-600 leading-relaxed">Unrestricted rights to live and work anywhere, leading to Australian citizenship and top-tier passport after 4 years.</div>
              </div>
              <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="font-bold text-sm text-slate-900 mb-1">🏖️ World-Class Lifestyle &amp; Safety</div>
                <div className="text-xs text-slate-600 leading-relaxed">Consistently ranked among the world’s most liveable countries with clean air, sunny climate, and safe cities.</div>
              </div>
              <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="font-bold text-sm text-slate-900 mb-1">👵 Superannuation &amp; Security</div>
                <div className="text-xs text-slate-600 leading-relaxed">Mandatory 11.5% employer-paid superannuation retirement fund on top of your standard base salary.</div>
              </div>
            </>
          ) : isCA ? (
            <>
              <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="font-bold text-sm text-slate-900 mb-1">🏥 Medicare Universal Healthcare</div>
                <div className="text-xs text-slate-600 leading-relaxed">Free comprehensive healthcare coverage funded through taxes with no out-of-pocket costs for hospital care and doctors.</div>
              </div>
              <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="font-bold text-sm text-slate-900 mb-1">💼 Lucrative Tech &amp; Industry Hubs</div>
                <div className="text-xs text-slate-600 leading-relaxed">Strong economic growth in Toronto, Vancouver, Calgary, and Montreal with median skilled salaries of CAD $85,000–$120,000+.</div>
              </div>
              <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="font-bold text-sm text-slate-900 mb-1">🍁 Fast-Track Express Entry PR</div>
                <div className="text-xs text-slate-600 leading-relaxed">Express Entry offers one of the fastest PR visa turnaround times in the world (as fast as 6 months from ITA).</div>
              </div>
              <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="font-bold text-sm text-slate-900 mb-1">👶 Canada Child Benefit (CCB)</div>
                <div className="text-xs text-slate-600 leading-relaxed">Generous monthly tax-free government payments provided to eligible families for each child under 18 years of age.</div>
              </div>
              <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="font-bold text-sm text-slate-900 mb-1">🎓 World-Class Free Education</div>
                <div className="text-xs text-slate-600 leading-relaxed">Free public schooling from kindergarten through Grade 12 and domestic tuition fees at top Canadian universities.</div>
              </div>
              <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="font-bold text-sm text-slate-900 mb-1">🇨🇦 Canadian Citizenship in 3 Years</div>
                <div className="text-xs text-slate-600 leading-relaxed">Eligible to apply for Canadian Citizenship and a Canadian passport after just 3 years (1,095 days) of PR residence.</div>
              </div>
            </>
          ) : (
            <>
              <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="font-bold text-sm text-slate-900 mb-1">🌿 Ultimate Work-Life Balance</div>
                <div className="text-xs text-slate-600 leading-relaxed">Consistently ranked #1 globally for work-life harmony, generous 4-week annual leave, and family-first culture.</div>
              </div>
              <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="font-bold text-sm text-slate-900 mb-1">🏥 Comprehensive Public Healthcare</div>
                <div className="text-xs text-slate-600 leading-relaxed">Subsidized state-funded healthcare system covering emergencies, hospitalization, and maternity care.</div>
              </div>
              <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="font-bold text-sm text-slate-900 mb-1">✨ Safe &amp; Progressive Nation</div>
                <div className="text-xs text-slate-600 leading-relaxed">Consistently ranked as one of the top 3 most peaceful and least corrupt countries on Earth.</div>
              </div>
              <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="font-bold text-sm text-slate-900 mb-1">🚀 Green List Fast-Track PR</div>
                <div className="text-xs text-slate-600 leading-relaxed">Direct Straight to Residence pathway for Tier 1 Green List roles (IT, Doctors, Engineers, Nurses) with no queues.</div>
              </div>
              <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="font-bold text-sm text-slate-900 mb-1">🎒 Free Quality Schooling</div>
                <div className="text-xs text-slate-600 leading-relaxed">World-renowned British-model education system with free schooling for children of work visa and residence holders.</div>
              </div>
              <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="font-bold text-sm text-slate-900 mb-1">🌏 Trans-Tasman Access</div>
                <div className="text-xs text-slate-600 leading-relaxed">NZ Citizens can live, work, and settle indefinitely in Australia with full reciprocal work and residence rights.</div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Section 3: Recommended Visa Pathways */}
      <div>
        <h4 className="font-serif-leamss text-xl font-bold mb-4" style={{ color: BRAND.ink }}>
          Recommended Visa Pathways for Your Profile
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {pathways.length > 0 ? (
            pathways.map((p) => (
              <PathwayResultCard key={p.slug} p={p} isBest={p.slug === top} />
            ))
          ) : isCA ? (
            <>
              <div className="p-5 rounded-xl border bg-white" style={{ borderColor: BRAND.border }}>
                <span className="inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold text-white mb-2" style={{ backgroundColor: BRAND.primary }}>Direct PR</span>
                <h5 className="font-bold text-base text-slate-900">Federal Skilled Worker Program (FSWP)</h5>
                <p className="text-xs text-slate-600 mt-1">Primary Express Entry pathway for foreign skilled professionals scoring 67+ FSWP points.</p>
              </div>
              <div className="p-5 rounded-xl border bg-white" style={{ borderColor: BRAND.border }}>
                <span className="inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold text-white mb-2" style={{ backgroundColor: BRAND.accent }}>+600 CRS Points</span>
                <h5 className="font-bold text-base text-slate-900">Provincial Nominee Program (PNP)</h5>
                <p className="text-xs text-slate-600 mt-1">Provincial nomination grants +600 points, guaranteeing an Invitation to Apply in the next draw.</p>
              </div>
            </>
          ) : isNZ ? (
            <>
              <div className="p-5 rounded-xl border bg-white" style={{ borderColor: BRAND.border }}>
                <span className="inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold text-white mb-2" style={{ backgroundColor: BRAND.primary }}>Direct PR</span>
                <h5 className="font-bold text-base text-slate-900">SMC 6-Points Residence Visa</h5>
                <p className="text-xs text-slate-600 mt-1">Direct points pathway claiming 3–6 points for qualifications or occupational registration + NZ job offer.</p>
              </div>
              <div className="p-5 rounded-xl border bg-white" style={{ borderColor: BRAND.border }}>
                <span className="inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold text-white mb-2" style={{ backgroundColor: BRAND.accent }}>Fast-Track PR</span>
                <h5 className="font-bold text-base text-slate-900">Green List Tier 1 (Straight to Residence)</h5>
                <p className="text-xs text-slate-600 mt-1">Direct permanent residence application from offshore or onshore for in-demand occupations.</p>
              </div>
            </>
          ) : (
            <>
              <div className="p-5 rounded-xl border bg-white" style={{ borderColor: BRAND.border }}>
                <span className="inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold text-white mb-2" style={{ backgroundColor: BRAND.primary }}>Direct PR</span>
                <h5 className="font-bold text-base text-slate-900">Subclass 189 Skilled Independent</h5>
                <p className="text-xs text-slate-600 mt-1">Direct Permanent Residency without employer or state nomination. Live and work anywhere in Australia.</p>
              </div>
              <div className="p-5 rounded-xl border bg-white" style={{ borderColor: BRAND.border }}>
                <span className="inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold text-white mb-2" style={{ backgroundColor: BRAND.accent }}>+5 State Points</span>
                <h5 className="font-bold text-base text-slate-900">Subclass 190 Skilled Nominated PR</h5>
                <p className="text-xs text-slate-600 mt-1">State government nomination grants 5 bonus points toward permanent residency with state support.</p>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Section 4: Why Choose LEAMSS (Protection Policy & Expertise) */}
      <div className="rounded-2xl p-6 sm:p-8 border" style={{ backgroundColor: 'rgba(31,77,68,0.04)', borderColor: 'rgba(31,77,68,0.2)' }}>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xl">🛡️</span>
          <h4 className="font-serif-leamss text-xl font-bold" style={{ color: BRAND.primary }}>
            {isAU
              ? 'The LEAMSS Advantage & 100% Refund Protection for Australia'
              : isCA
              ? 'The LEAMSS Advantage & 100% Refund Protection for Canada'
              : 'The LEAMSS Advantage & 100% Refund Protection for New Zealand'}
          </h4>
        </div>
        <p className="text-xs sm:text-sm text-slate-700 mb-6">
          {isAU
            ? 'LEAMSS (Ladhani Education & Migration Services) is India’s premier Australian migration consultancy operating since 2024. We provide statutory migration advisory with total legal transparency.'
            : isCA
            ? 'LEAMSS (Ladhani Education & Migration Services) provides premier Canadian immigration consulting since 2024. We guide you through ECA, Express Entry, and Provincial Nominations with full legal compliance.'
            : 'LEAMSS (Ladhani Education & Migration Services) provides expert New Zealand migration advice since 2024. We guide you through NZQA comparability, Green List mapping, and SMC residency.'}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
            <div className="font-bold text-sm mb-1" style={{ color: BRAND.accent }}>🛡️ 100% Refund Guarantee</div>
            <div className="text-xs text-slate-600 leading-relaxed">
              {isAU
                ? 'Full refund on professional fees if your skills assessment outcome is negative based on factors we verified upfront.'
                : isCA
                ? 'Full refund on professional fees if your preliminary credential assessment fails on verified grounds.'
                : 'Full refund on professional fees if your qualification assessment fails based on verified factors.'}
            </div>
          </div>
          <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
            <div className="font-bold text-sm mb-1" style={{ color: BRAND.primary }}>
              {isAU ? '📜 MARA Registered Network' : isCA ? '📜 Licensed RCIC & CICC Network' : '📜 Licensed Advisers (LIA) Network'}
            </div>
            <div className="text-xs text-slate-600 leading-relaxed">
              {isAU
                ? 'Official MARA registered migration agents ensuring 100% compliance with Australian statutory immigration laws.'
                : isCA
                ? 'Representation in strict compliance with the College of Immigration and Citizenship Consultants (CICC) regulatory framework.'
                : 'Compliant advisory guided by licensed advisers under the Immigration Advisers Authority (IAA).'}
            </div>
          </div>
          <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
            <div className="font-bold text-sm text-slate-900 mb-1">⭐ 10+ Years &amp; 4.9★ Reviews</div>
            <div className="text-xs text-slate-600 leading-relaxed">
              {isAU
                ? 'Over 10,000 successful Australian visa and skills assessment outcomes processed with 100% audit integrity.'
                : isCA
                ? 'Proven expertise with thousands of successful Canada Express Entry profile lodgements and PNP nominations.'
                : 'Extensive track record securing New Zealand Accredited Employer Work Visas (AEWV) and SMC residence grants.'}
            </div>
          </div>
          <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
            <div className="font-bold text-sm text-slate-900 mb-1">💎 Transparent Milestone Fees</div>
            <div className="text-xs text-slate-600 leading-relaxed">
              {isAU
                ? 'Stage-wise milestone payments tied strictly to tangible outcomes (Skills Assessment, EOI, Visa Lodgement).'
                : isCA
                ? 'Stage-wise milestone payments aligned strictly with deliverables (ECA, Express Entry Pool, PNP & e-APR Filing).'
                : 'Clear, stage-wise milestone billing tied directly to NZQA assessment, EOI submission, and resident visa lodgement.'}
            </div>
          </div>
          <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
            <div className="font-bold text-sm mb-1" style={{ color: BRAND.accent }}>
              {isAU ? '🎯 Dedicated Australian Case Officer' : isCA ? '🎯 Dedicated Canadian Case Officer' : '🎯 Dedicated New Zealand Specialist'}
            </div>
            <div className="text-xs text-slate-600 leading-relaxed">
              {isAU
                ? 'Personalized 1-on-1 documentation support, CDR / RPL writing guidance, and direct state nomination representation.'
                : isCA
                ? '1-on-1 assistance with NOC TEER alignment, employer reference letter drafting, and provincial nomination strategy.'
                : '1-on-1 assistance with NZQA International Qualifications Assessment (IQA), CV adaptation, and Green List alignment.'}
            </div>
          </div>
          <div className="p-4 bg-white rounded-xl border" style={{ borderColor: BRAND.border }}>
            <div className="font-bold text-sm mb-1" style={{ color: BRAND.primary }}>
              {isAU ? '🤝 Australian Settlement Support' : isCA ? '🤝 Canadian Settlement Guidance' : '🤝 New Zealand Settlement Support'}
            </div>
            <div className="text-xs text-slate-600 leading-relaxed">
              {isAU
                ? 'Assistance with Tax File Number (TFN), Australian bank account opening, Medicare enrolment, and arrival orientation.'
                : isCA
                ? 'Pre-landing & arrival support including Social Insurance Number (SIN) guidance, Canadian banking, and provincial health cards.'
                : 'Post-arrival orientation including IRD tax number registration, New Zealand banking, and healthcare enrolment.'}
            </div>
          </div>
        </div>
      </div>

      {/* Section 5: 5-Stage Migration Roadmap */}
      <div className="rounded-2xl p-6 sm:p-8 border bg-white" style={{ borderColor: BRAND.border }}>
        <div className="flex items-center gap-2 mb-4">
          <span className="text-lg">🗺️</span>
          <h4 className="font-serif-leamss text-xl font-bold" style={{ color: BRAND.ink }}>
            {isAU
              ? 'Your 5-Stage Australian Immigration Roadmap'
              : isCA
              ? 'Your 5-Stage Canadian Immigration Roadmap'
              : 'Your 5-Stage New Zealand Immigration Roadmap'}
          </h4>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
          {isAU ? (
            <>
              <div className="p-3 bg-slate-50 rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="text-[10px] font-extrabold uppercase tracking-wider" style={{ color: BRAND.accent }}>Stage 1</div>
                <div className="font-bold text-xs text-slate-900 mt-1">Profile Audit</div>
                <div className="text-[11px] text-slate-500 mt-0.5">Document verification &amp; ANZSCO code alignment.</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="text-[10px] font-extrabold uppercase tracking-wider" style={{ color: BRAND.accent }}>Stage 2</div>
                <div className="font-bold text-xs text-slate-900 mt-1">Skills Assessment</div>
                <div className="text-[11px] text-slate-500 mt-0.5">Lodgement with assessing authority (ACS/EA/VETASSESS/TRA).</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="text-[10px] font-extrabold uppercase tracking-wider" style={{ color: BRAND.accent }}>Stage 3</div>
                <div className="font-bold text-xs text-slate-900 mt-1">SkillSelect EOI</div>
                <div className="text-[11px] text-slate-500 mt-0.5">Expression of Interest &amp; State Nomination filing.</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="text-[10px] font-extrabold uppercase tracking-wider" style={{ color: BRAND.accent }}>Stage 4</div>
                <div className="font-bold text-xs text-slate-900 mt-1">Visa Application</div>
                <div className="text-[11px] text-slate-500 mt-0.5">Formal PR visa filing (Subclass 189/190/491) after invitation.</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="text-[10px] font-extrabold uppercase tracking-wider" style={{ color: BRAND.accent }}>Stage 5</div>
                <div className="font-bold text-xs text-slate-900 mt-1">PR Grant &amp; Fly</div>
                <div className="text-[11px] text-slate-500 mt-0.5">Permanent Residency grant, Medicare &amp; TFN setup.</div>
              </div>
            </>
          ) : isCA ? (
            <>
              <div className="p-3 bg-slate-50 rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="text-[10px] font-extrabold uppercase tracking-wider" style={{ color: BRAND.accent }}>Stage 1</div>
                <div className="font-bold text-xs text-slate-900 mt-1">Profile &amp; NOC Audit</div>
                <div className="text-[11px] text-slate-500 mt-0.5">Educational review &amp; NOC TEER 0/1/2/3 classification alignment.</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="text-[10px] font-extrabold uppercase tracking-wider" style={{ color: BRAND.accent }}>Stage 2</div>
                <div className="font-bold text-xs text-slate-900 mt-1">ECA &amp; Language</div>
                <div className="text-[11px] text-slate-500 mt-0.5">Credential Assessment (WES/ICAS/IQAS) &amp; IELTS/CELPIP test.</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="text-[10px] font-extrabold uppercase tracking-wider" style={{ color: BRAND.accent }}>Stage 3</div>
                <div className="font-bold text-xs text-slate-900 mt-1">Express Entry &amp; PNP</div>
                <div className="text-[11px] text-slate-500 mt-0.5">Express Entry profile submission &amp; Provincial Nomination applications.</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="text-[10px] font-extrabold uppercase tracking-wider" style={{ color: BRAND.accent }}>Stage 4</div>
                <div className="font-bold text-xs text-slate-900 mt-1">ITA &amp; e-APR</div>
                <div className="text-[11px] text-slate-500 mt-0.5">Full permanent residence filing with IRCC within 60 days of ITA.</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="text-[10px] font-extrabold uppercase tracking-wider" style={{ color: BRAND.accent }}>Stage 5</div>
                <div className="font-bold text-xs text-slate-900 mt-1">COPR &amp; Land</div>
                <div className="text-[11px] text-slate-500 mt-0.5">Confirmation of Permanent Residence (COPR) &amp; Canadian PR card.</div>
              </div>
            </>
          ) : (
            <>
              <div className="p-3 bg-slate-50 rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="text-[10px] font-extrabold uppercase tracking-wider" style={{ color: BRAND.accent }}>Stage 1</div>
                <div className="font-bold text-xs text-slate-900 mt-1">Profile &amp; Green List</div>
                <div className="text-[11px] text-slate-500 mt-0.5">Qualification pre-assessment &amp; Green List Tier 1/2 eligibility mapping.</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="text-[10px] font-extrabold uppercase tracking-wider" style={{ color: BRAND.accent }}>Stage 2</div>
                <div className="font-bold text-xs text-slate-900 mt-1">NZQA IQA / Reg.</div>
                <div className="text-[11px] text-slate-500 mt-0.5">International Qualifications Assessment or NZ professional registration.</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="text-[10px] font-extrabold uppercase tracking-wider" style={{ color: BRAND.accent }}>Stage 3</div>
                <div className="font-bold text-xs text-slate-900 mt-1">Job Offer &amp; SMC</div>
                <div className="text-[11px] text-slate-500 mt-0.5">Accredited Employer Work Visa (AEWV) &amp; SMC Expression of Interest.</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="text-[10px] font-extrabold uppercase tracking-wider" style={{ color: BRAND.accent }}>Stage 4</div>
                <div className="font-bold text-xs text-slate-900 mt-1">ITA &amp; Resident Visa</div>
                <div className="text-[11px] text-slate-500 mt-0.5">Formal Residence Visa application filing with Immigration New Zealand.</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border" style={{ borderColor: BRAND.border }}>
                <div className="text-[10px] font-extrabold uppercase tracking-wider" style={{ color: BRAND.accent }}>Stage 5</div>
                <div className="font-bold text-xs text-slate-900 mt-1">Resident Visa &amp; Fly</div>
                <div className="text-[11px] text-slate-500 mt-0.5">Permanent resident visa grant, IRD tax setup, and arrival support.</div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Bottom Consultation CTA */}
      <div className="rounded-2xl p-6 sm:p-8 flex flex-wrap items-center justify-between gap-6"
        style={{ backgroundColor: BRAND.primary, color: '#FFFFFF' }}>
        <div>
          <h4 className="font-serif-leamss text-xl sm:text-2xl font-bold">Ready to claim your Permanent Residency?</h4>
          <p className="text-xs sm:text-sm text-emerald-100 mt-1">Speak with our certified migration advisors today for 1-on-1 strategy.</p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <a
            href={`tel:${PHONE}`}
            className="px-4 py-2.5 rounded-xl font-bold text-xs sm:text-sm bg-white text-emerald-900 hover:bg-slate-100 transition shadow-sm"
          >
            📞 Call: {PHONE}
          </a>
          <a
            href={`https://wa.me/91${WHATSAPP}?text=${encodeURIComponent(`Hi LEAMSS Team, I am ${result.client_name || 'an applicant'}. I just completed my eligibility calculation for ${cName} and would like to start.`)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2.5 rounded-xl font-bold text-xs sm:text-sm text-white transition shadow-sm"
            style={{ backgroundColor: BRAND.accent }}
          >
            💬 Instant WhatsApp
          </a>
        </div>
      </div>
    </div>
  );
}

// ─── Public shared scorecard page (/scorecard/:id) ──────────────────────────
export function SharedScorecard() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/eligibility/share/${id}`)
      .then((r) => {
        const rec = r.data || {};
        setResult({ score_id: rec.id, ...(rec.result || {}) });
      })
      .catch(() => setResult({ error: 'This scorecard link is invalid or has expired.' }))
      .finally(() => setLoading(false));
  }, [id]);

  return (
    <div style={{ background: BRAND.bgSoft, minHeight: '100vh' }} data-testid="shared-scorecard">
      <header className="border-b" style={{ borderColor: BRAND.border, background: BRAND.bg }}>
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/start" className="font-serif-leamss text-2xl font-bold" style={{ color: BRAND.primary }}>LEAMSS</Link>
          <Button as="a" href="/start#quiz" size="sm" data-testid="shared-cta-own-score">Check my own score</Button>
        </div>
      </header>
      <div className="max-w-5xl mx-auto px-4 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-24"><Loader2 className="w-7 h-7 animate-spin" style={{ color: BRAND.primary }} /></div>
        ) : (
          <div className="rounded-2xl overflow-hidden" style={{ background: BRAND.bg, border: `1px solid ${BRAND.border}` }}>
            <QuizResult result={result} onReset={() => navigate('/start#quiz')} />
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Visa Compare Section (interactive · wired to /visa-compare API) ─────────
const COUNTRY_FLAG = {
  Canada: '🇨🇦', Australia: '🇦🇺', 'New Zealand': '🇳🇿',
  'United Kingdom': '🇬🇧', Germany: '🇩🇪', 'United States': '🇺🇸',
};
const inrL = (v) => (v ? `₹${(v / 100000).toFixed(1)}L` : '—');

function VisaCompareSection() {
  const [allPathways, setAllPathways] = useState([]);
  const [picked, setPicked] = useState([]);
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    axios.get(`${API}/visa-compare/pathways`)
      .then(r => {
        const pw = r.data.pathways || [];
        setAllPathways(pw);
        // Smart default: pre-select the 3 most popular for instant value
        const defaults = pw.slice(0, 3).map(p => p.slug);
        setPicked(defaults);
        if (defaults.length >= 2) runCompare(defaults);
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const runCompare = async (slugs) => {
    if (slugs.length < 2) { setData([]); return; }
    setLoading(true);
    try {
      const r = await axios.get(`${API}/visa-compare/compare?slugs=${slugs.join(',')}`);
      setData(r.data.pathways || []);
    } catch (e) { /* keep previous */ }
    setLoading(false);
  };

  const toggle = (slug) => {
    let next;
    if (picked.includes(slug)) next = picked.filter(s => s !== slug);
    else { if (picked.length >= 4) return; next = [...picked, slug]; }
    setPicked(next);
    runCompare(next);
  };

  return (
    <section id="compare" className="py-20" style={{ background: BRAND.bgSoft }}>
      <div className="max-w-7xl mx-auto px-4">
        <SectionTitle
          eyebrow="Side-by-Side Visa Compare"
          title="Compare visa pathways that fit your profile"
          sub="Pick 2-4 programs across AU, CA, NZ, UK, Germany & USA — compare fees, timelines, eligibility, benefits & post-arrival jobs side-by-side."
        />

        {/* Picker */}
        <div className="rounded-2xl p-5 mb-6 bg-white" style={{ border: `1px solid ${BRAND.border}` }} data-testid="compare-picker">
          <p className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: BRAND.muted }}>
            Select pathways ({picked.length}/4)
          </p>
          <div className="flex gap-2 flex-wrap">
            {allPathways.map(p => {
              const on = picked.includes(p.slug);
              return (
                <button
                  key={p.slug}
                  onClick={() => toggle(p.slug)}
                  className="px-3 py-1.5 rounded-full text-xs font-semibold border inline-flex items-center gap-1.5 transition-all"
                  style={{
                    background: on ? BRAND.primary : '#fff',
                    color: on ? '#fff' : BRAND.body,
                    borderColor: on ? BRAND.primary : BRAND.border,
                  }}
                  data-testid={`compare-pick-${p.slug}`}
                >
                  {on ? <CheckCircle2 className="w-3.5 h-3.5" /> : <span className="w-3.5 h-3.5 inline-flex items-center justify-center">+</span>}
                  {COUNTRY_FLAG[p.country] || ''} {p.name}
                </button>
              );
            })}
          </div>
        </div>

        {/* Comparison grid */}
        {loading && data.length === 0 ? (
          <div className="text-center py-12"><Loader2 className="w-7 h-7 animate-spin mx-auto" style={{ color: BRAND.primary }} /></div>
        ) : data.length >= 2 ? (
          <div className="overflow-x-auto pb-2" data-testid="compare-results">
            <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${data.length}, minmax(260px, 1fr))` }}>
              {data.map((p, idx) => (
                <motion.div
                  key={p.slug}
                  initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, delay: idx * 0.05 }}
                  className="rounded-2xl overflow-hidden bg-white flex flex-col"
                  style={{ border: `1px solid ${BRAND.border}` }}
                  data-testid={`compare-card-${p.slug}`}
                >
                  <div className="p-5" style={{ background: BRAND.primary, color: '#fff' }}>
                    <p className="text-xs opacity-90">{COUNTRY_FLAG[p.country] || ''} {p.country}</p>
                    <p className="font-serif-leamss text-lg font-bold leading-tight mt-1">{p.name}</p>
                    <p className="text-[11px] opacity-80 mt-1">{p.category}</p>
                  </div>
                  <div className="p-5 space-y-3 text-sm flex-1">
                    <CompareRow label="⏱ Processing" value={`${p.timeline_months} months`} />
                    <CompareRow label="💰 Total Cost (Govt + LEAMSS)" value={inrL((p.govt_fee_inr || 0) + (p.leamss_fee_inr || 0))} sub={`+ ${inrL(p.min_funds_inr)} settlement funds`} />
                    <CompareRow label="🎓 Min Education" value={p.min_education} />
                    <CompareRow label="💼 Work Experience" value={`${p.min_work_exp_years}+ years`} />
                    <CompareRow label="🎂 Age Range" value={`${p.min_age} – ${p.max_age} years`} />
                    <CompareRow label="🗣 Language" value={p.language_required} />
                    {p.key_benefits?.length > 0 && (
                      <div className="pt-3 border-t" style={{ borderColor: BRAND.border }}>
                        <p className="text-[11px] font-bold mb-1" style={{ color: BRAND.success }}>✓ Key Benefits</p>
                        <ul className="text-[11px] space-y-1 ml-4" style={{ color: BRAND.body }}>
                          {p.key_benefits.slice(0, 4).map((b, i) => <li key={i} className="list-disc">{b}</li>)}
                        </ul>
                      </div>
                    )}
                    {p.key_drawbacks?.length > 0 && (
                      <div>
                        <p className="text-[11px] font-bold mb-1" style={{ color: BRAND.accent }}>⚠ Watch-outs</p>
                        <ul className="text-[11px] space-y-1 ml-4" style={{ color: BRAND.body }}>
                          {p.key_drawbacks.slice(0, 3).map((b, i) => <li key={i} className="list-disc">{b}</li>)}
                        </ul>
                      </div>
                    )}
                    {p.post_arrival_jobs && (
                      <div>
                        <p className="text-[11px] font-bold mb-1" style={{ color: BRAND.primary }}>💼 Post-Arrival Jobs</p>
                        <p className="text-[11px]" style={{ color: BRAND.body }}>{p.post_arrival_jobs}</p>
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        ) : (
          <div className="text-center py-12" style={{ color: BRAND.muted }}>
            <Globe2 className="w-10 h-10 mx-auto mb-2" style={{ color: BRAND.border }} />
            <p className="text-sm">Select at least 2 pathways above to compare side-by-side.</p>
          </div>
        )}

        <p className="text-center text-sm mt-8" style={{ color: BRAND.muted }}>
          Not sure which fits you?{' '}
          <a href="#quiz" className="font-semibold underline" style={{ color: BRAND.primary }}>Take the 60-second eligibility quiz →</a>
        </p>
      </div>
    </section>
  );
}

const CompareRow = ({ label, value, sub }) => (
  <div>
    <p className="text-[10px] uppercase font-bold tracking-wider" style={{ color: BRAND.muted }}>{label}</p>
    <p className="font-semibold mt-0.5" style={{ color: BRAND.ink }}>{value}</p>
    {sub && <p className="text-[10px] mt-0.5" style={{ color: BRAND.muted }}>{sub}</p>}
  </div>
);

// ─── Featured Occupations ──────────────────────────────────────────────────
function FeaturedOccupationsSection({ featuredOverride }) {
  const [items, setItems] = useState([]);
  useEffect(() => {
    // If admin has customized featured codes, use those (resolve titles via /featured endpoint).
    if (featuredOverride && featuredOverride.length > 0) {
      // Map override -> shape matching /featured payload by re-using items from featured API.
      axios.get(`${API}/public-atlas/featured`).then(r => {
        const lookup = {};
        (r.data.items || []).forEach(it => { lookup[`${it.country_code}-${it.code}`] = it; });
        // For codes not in lookup, build minimal shape from override
        const resolved = featuredOverride.map(o => lookup[`${o.country_code}-${o.code}`] || { country_code: o.country_code, code: o.code, title: o.title });
        setItems(resolved);
      }).catch(() => setItems(featuredOverride));
    } else {
      axios.get(`${API}/public-atlas/featured`).then(r => setItems(r.data.items || [])).catch(() => {});
    }
  }, [featuredOverride]);
  return (
    <section className="py-20">
      <div className="max-w-7xl mx-auto px-4">
        <SectionTitle eyebrow="Featured Occupations" title="Most-searched migration pathways"
          sub="Hand-picked 6-digit ANZSCO + NOC codes across 3 countries. Click any to see visa eligibility, salary, assessing body & requirements." />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" data-testid="featured-grid">
          {items.slice(0, 12).map((it, i) => (
            <motion.div
              key={`${it.country_code}-${it.code}`}
              initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }} transition={{ duration: 0.4, delay: (i % 4) * 0.05 }}
            >
              <OccupationCard item={it} />
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function OccupationCard({ item, compact = false }) {
  const flag = { AU: '🇦🇺', CA: '🇨🇦', NZ: '🇳🇿' }[item.country_code];
  return (
    <Link reloadDocument
      to={`/atlas/${item.country_code.toLowerCase()}/${item.code}`}
      className="block rounded-xl p-4 bg-white hover:shadow-md transition-all hover:-translate-y-0.5"
      style={{ border: `1px solid ${BRAND.border}` }}
      data-testid={`occupation-card-${item.country_code}-${item.code}`}
    >
      <div className="flex items-start justify-between mb-2">
        <p className="font-mono text-xs" style={{ color: BRAND.muted }}>{flag} {item.code}</p>
        {item.nz_green_list_tier && <Pill color={BRAND.accent} bg={`${BRAND.accent}15`}>Tier {item.nz_green_list_tier}</Pill>}
        {item.teer_category !== undefined && item.teer_category !== null && <Pill color={BRAND.primary}>TEER {item.teer_category}</Pill>}
        {item.skill_level && item.teer_category === undefined && <Pill color={BRAND.primary}>SL {item.skill_level}</Pill>}
      </div>
      <p className={`font-bold mt-1 leading-snug ${compact ? 'text-sm' : 'text-base'}`} style={{ color: BRAND.ink }}>{item.title}</p>
      {item.hierarchy && <p className="text-xs mt-1.5 line-clamp-1" style={{ color: BRAND.muted }}>{item.hierarchy}</p>}
    </Link>
  );
}

// ─── Browse Atlas section ──────────────────────────────────────────────────
function BrowseAtlasSection() {
  return (
    <section className="py-20" style={{ background: BRAND.bgSoft }}>
      <div className="max-w-7xl mx-auto px-4">
        <SectionTitle eyebrow="Browse" title="Verified Migration Atlas — 1500+ occupations"
          sub="The most comprehensive ANZSCO + NOC 2021 reference for India's outbound migrants. All entries verified by licensed migration experts." />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {[
            { code: 'AU', name: 'Australia', count: '374 codes', subtitle: 'ANZSCO 1.3 + v2022', img: COUNTRY_HERO.AU },
            { code: 'CA', name: 'Canada', count: '103 codes',  subtitle: 'NOC 2021', img: COUNTRY_HERO.CA },
            { code: 'NZ', name: 'New Zealand', count: '243 codes', subtitle: 'ANZSCO 1.3', img: COUNTRY_HERO.NZ },
          ].map((c, i) => (
            <motion.div
              key={c.code}
              initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }} transition={{ duration: 0.5, delay: i * 0.1 }}
            >
              <Link reloadDocument
                to={`/atlas/${c.code.toLowerCase()}`}
                className="relative block overflow-hidden rounded-2xl group h-72"
                data-testid={`browse-atlas-${c.code}`}
              >
                <img src={c.img} alt={c.name} className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" />
                <div className="absolute inset-0" style={{ background: `linear-gradient(to bottom, transparent 40%, ${BRAND.primaryDk}F0)` }} />
                <div className="absolute bottom-0 left-0 right-0 p-6 text-white">
                  <p className="text-xs uppercase tracking-[0.18em] opacity-80">{c.subtitle}</p>
                  <p className="font-serif-leamss text-3xl font-bold mt-1">{c.code === 'AU' ? '🇦🇺' : c.code === 'CA' ? '🇨🇦' : '🇳🇿'} {c.name}</p>
                  <div className="flex items-center justify-between mt-3">
                    <p className="text-sm opacity-90">{c.count}</p>
                    <ArrowUpRight className="w-5 h-5 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Social Proof ──────────────────────────────────────────────────────────
const TESTIMONIALS = [
  { name: 'Sophia Chowdhury', city: 'Mumbai → Sydney', text: "I am so grateful to Leamss for helping me navigate my Australian PR journey. Their expertise and support made a huge difference.", stars: 5 },
  { name: 'Varsha Bhatia', city: 'Pune → Toronto', text: "Extremely happy with the services. Team was supportive, professional, highly responsive. Patiently addressed all queries.", stars: 5 },
  { name: 'Krishna KV', city: 'Bangalore → Brisbane', text: "Practical, supportive and expert in analyzing profiles for ideal destination. Strongly recommend for anyone exploring migration.", stars: 5 },
  { name: 'Gurleen Kaur', city: 'Delhi → Auckland', text: "A wonderful team to work with. Worth trusting. Professional, lucid. They have marked their words and made this journey wonderful.", stars: 5 },
];

function SocialProofSection({ testimonialsOverride }) {
  const list = testimonialsOverride && testimonialsOverride.length > 0 ? testimonialsOverride : TESTIMONIALS;
  return (
    <section className="py-20">
      <div className="max-w-7xl mx-auto px-4">
        <SectionTitle eyebrow="Trusted by 80,000+ Indians" title="Real stories. Real outcomes."
          sub="From Mumbai to Sydney. Pune to Toronto. Delhi to Auckland. Here's what our clients say." />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="testimonials-grid">
          {list.map((t, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }} transition={{ duration: 0.4, delay: i * 0.08 }}
              className="rounded-xl p-5 bg-white"
              style={{ border: `1px solid ${BRAND.border}` }}
            >
              <div className="flex gap-0.5 mb-3">
                {Array.from({ length: t.stars }).map((_, k) => <Star key={k} className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />)}
              </div>
              <p className="text-sm leading-relaxed mb-4" style={{ color: BRAND.body }}>&ldquo;{t.text}&rdquo;</p>
              <div className="border-t pt-3" style={{ borderColor: BRAND.border }}>
                <p className="font-bold text-sm" style={{ color: BRAND.ink }}>{t.name}</p>
                <p className="text-xs" style={{ color: BRAND.muted }}>{t.city}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── FAQ ───────────────────────────────────────────────────────────────────
const FAQS = [
  { q: 'What is ANZSCO and why does my occupation code matter?',
    a: 'ANZSCO (Australian and New Zealand Standard Classification of Occupations) is the official code used by Department of Home Affairs Australia and Immigration NZ. Your 6-digit code (e.g., 261313 Software Engineer) decides which visa subclasses you can apply for, which state nominates, and what salary you can expect.' },
  { q: 'How are CRS points calculated for Canada Express Entry?',
    a: 'CRS (Comprehensive Ranking System) scores you out of 1200 points based on age, education, official language ability (CLB), work experience, adaptability, and additional factors. You need at least 67 points on the FSWP eligibility scoresheet to enter the pool, then your CRS determines whether you get an Invitation to Apply (ITA).' },
  { q: 'What\'s the difference between NZ SMC and Green List?',
    a: 'SMC (Skilled Migrant Category) is NZ\'s standard 6-point system for residency. Green List occupations (Tier 1 = Straight to Residence, Tier 2 = Work-to-Residence after 24 months on AEWV) bypass the regular SMC scoring and offer faster, simpler pathways for high-demand roles.' },
  { q: 'Is the 100% Refund Guarantee real? What\'s the catch?',
    a: 'Yes — we offer a written refund policy if your skill assessment is negative or your visa is rejected due to LEAMSS-attributable error. The only exclusion: rejections due to false information you provided (which is a legal disqualifier anyway). Full policy: leamss.com/privacy-policy.' },
  { q: 'How long does the whole PR process take from start to finish?',
    a: 'Typical timelines: Australia 189/190 (12-18 months end-to-end), Canada Express Entry (6-12 months), NZ Green List Tier 1 (3-6 months), NZ SMC (12-18 months). LEAMSS provides a fixed-timeline guarantee on Express Entry profiles.' },
  { q: 'Can I migrate without an English test (IELTS/PTE)?',
    a: 'No major skilled visa pathway allows skipping the English test. Minimum requirements: Australia (IELTS 6.0 each band or equivalent PTE), Canada (CLB 7), New Zealand (IELTS 6.5). However, LEAMSS offers PTE/IELTS coaching as part of our PR package.' },
];

function FAQSection({ faqsOverride }) {
  const list = faqsOverride && faqsOverride.length > 0 ? faqsOverride : FAQS;
  return (
    <section className="py-20" style={{ background: BRAND.bgWarm }}>
      <div className="max-w-3xl mx-auto px-4">
        <SectionTitle eyebrow="FAQ" title="Quick answers to common migration questions" />
        <Accordion type="single" collapsible className="space-y-2" data-testid="faq-accordion">
          {list.map((f, i) => (
            <AccordionItem key={i} value={`faq-${i}`}
              className="rounded-xl bg-white px-5 border-0" style={{ border: `1px solid ${BRAND.border}` }}>
              <AccordionTrigger className="text-left font-semibold py-4 hover:no-underline" style={{ color: BRAND.ink }} data-testid={`faq-trigger-${i}`}>
                {f.q}
              </AccordionTrigger>
              <AccordionContent className="text-sm pb-4" style={{ color: BRAND.body }}>
                {f.a}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
}

// ─── Sticky lead footer ────────────────────────────────────────────────────
function StickyLeadFooter() {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', phone: '', message: '' });
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState(null);
  const [mountTime] = useState(() => Date.now());

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true); setError(null);
    try {
      const r = await axios.post(`${API}/public-atlas/lead`, {
        ...form, country_of_interest: '', atlas_code: 'mega-landing', atlas_title: 'Mega Landing Page',
        company_url: (Date.now() - mountTime) < 1500 ? 'bot' : '',
      });
      if (r.data.ok) setDone(true);
    } catch (e) { setError(e.response?.data?.detail || 'Submission failed'); }
    setSubmitting(false);
  };

  return (
    <>
      <div className="fixed bottom-0 left-0 right-0 z-30 shadow-2xl" data-testid="sticky-lead-bar"
        style={{ background: BRAND.primaryDk, color: '#fff', borderTop: `2px solid ${BRAND.accent}` }}>
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-bold">Got 60 seconds? Get a free expert call-back.</p>
            <p className="text-xs opacity-80">No spam · WhatsApp friendly · MARA registered consultants</p>
          </div>
          <div className="flex gap-2">
            <Button as="a" href={`https://wa.me/${WHATSAPP}`} target="_blank" rel="noreferrer" size="sm" data-testid="sticky-whatsapp">
              <MessageCircle className="w-4 h-4" />WhatsApp Now
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setOpen(true)} data-testid="sticky-callback">
              <Phone className="w-4 h-4" />Request Call
            </Button>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4"
            style={{ background: 'rgba(15,30,35,0.6)' }}
            onClick={() => setOpen(false)}
          >
            <motion.div
              initial={{ y: 60, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 60, opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="bg-white rounded-2xl w-full max-w-md p-7 relative"
              onClick={(e) => e.stopPropagation()}
              data-testid="lead-modal"
            >
              {done ? (
                <div className="text-center py-6" data-testid="lead-modal-success">
                  <CheckCircle2 className="w-12 h-12 mx-auto mb-3" style={{ color: BRAND.success }} />
                  <h3 className="font-serif-leamss text-2xl font-bold" style={{ color: BRAND.ink }}>Thank you!</h3>
                  <p className="text-sm mt-2" style={{ color: BRAND.body }}>Our expert will WhatsApp you within 24 hours.</p>
                  <Button variant="secondary" className="mt-5" onClick={() => setOpen(false)}>Close</Button>
                </div>
              ) : (
                <>
                  <p className="text-xs font-bold uppercase tracking-[0.18em]" style={{ color: BRAND.accent }}>Free Call-back</p>
                  <h3 className="font-serif-leamss text-2xl font-bold mt-1 mb-1" style={{ color: BRAND.ink }}>Talk to a MARA expert</h3>
                  <p className="text-xs mb-5" style={{ color: BRAND.muted }}>100% confidential · No obligation · 24-hour response</p>
                  <form onSubmit={submit} className="space-y-3">
                    <input required type="text" placeholder="Full name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                      className="w-full px-4 py-3 rounded-lg border outline-none" style={{ borderColor: BRAND.border }} data-testid="lead-modal-name" />
                    <input required type="email" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                      className="w-full px-4 py-3 rounded-lg border outline-none" style={{ borderColor: BRAND.border }} data-testid="lead-modal-email" />
                    <input required type="tel" placeholder="Phone (with country code)" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })}
                      className="w-full px-4 py-3 rounded-lg border outline-none" style={{ borderColor: BRAND.border }} data-testid="lead-modal-phone" />
                    <textarea placeholder="Tell us about your migration goals (optional)" value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })}
                      rows={2} className="w-full px-4 py-3 rounded-lg border outline-none resize-none" style={{ borderColor: BRAND.border }} data-testid="lead-modal-message" />
                    {error && <p className="text-xs" style={{ color: '#B91C1C' }}>{error}</p>}
                    <Button type="submit" className="w-full" size="lg" disabled={submitting} data-testid="lead-modal-submit">
                      {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                      {submitting ? 'Sending…' : 'Request Free Call-back'}
                    </Button>
                  </form>
                </>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// ATLAS HUB V2 — /atlas
// ═══════════════════════════════════════════════════════════════════════════
export function AtlasHubV2() {
  const [data, setData] = useState(null);
  useEffect(() => {
    axios.get(`${API}/public-atlas/featured`).then(r => {
      setData(r.data); applySEO(r.data.seo);
    }).catch(() => {});
  }, []);

  return (
    <LeamssShell>
      {/* Hero */}
      <section className="relative overflow-hidden py-16 lg:py-24" style={{ background: BRAND.bgWarm }}>
        <div className="max-w-7xl mx-auto px-4">
          <div className="max-w-3xl">
            <Pill color={BRAND.accent}>Migration Atlas</Pill>
            <h1 className="font-serif-leamss text-4xl sm:text-5xl lg:text-6xl font-bold leading-[1.05] mt-4"
              style={{ color: BRAND.ink }}>
              The verified migration<br />
              <span style={{ color: BRAND.primary }}>occupation atlas</span> for{' '}
              <span style={{ color: BRAND.accent, fontStyle: 'italic' }}>Indian professionals</span>
            </h1>
            <p className="mt-5 text-base sm:text-lg leading-relaxed max-w-2xl" style={{ color: BRAND.body }}>
              1,900+ verified ANZSCO + NOC 2021 codes for Australia, Canada & New Zealand migration.
              Visa pathways, eligibility, salary trends, assessing-body requirements — updated for 2026.
            </p>
            <div className="mt-7 flex gap-3 flex-wrap">
              <Button size="lg" as={Link} to="/start">Get AI Eligibility Score<ArrowRight className="w-4 h-4" /></Button>
              <Button variant="secondary" size="lg" as="a" href={`https://wa.me/${WHATSAPP}`} target="_blank" rel="noreferrer">
                <MessageCircle className="w-4 h-4" />Talk to Expert
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Country cards */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4">
          <SectionTitle eyebrow="Browse by Country" title="Pick your migration destination" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5" data-testid="atlas-hub-grid">
            {(data?.countries || []).map((c, i) => (
              <motion.div key={c.code} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }} transition={{ duration: 0.4, delay: i * 0.08 }}>
                <Link reloadDocument
                  to={`/atlas/${c.code.toLowerCase()}`}
                  className="relative block overflow-hidden rounded-2xl group h-80"
                  data-testid={`atlas-hub-country-${c.code}`}
                >
                  <img src={COUNTRY_HERO[c.code]} alt={c.name} className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" />
                  <div className="absolute inset-0" style={{ background: `linear-gradient(to bottom, transparent 30%, ${BRAND.primaryDk}F2)` }} />
                  <div className="absolute bottom-0 left-0 right-0 p-7 text-white">
                    <p className="text-xs uppercase tracking-[0.18em] opacity-80">{c.classification}</p>
                    <p className="font-serif-leamss text-4xl font-bold mt-1">{c.flag} {c.name}</p>
                    <div className="flex items-end justify-between mt-3">
                      <div>
                        <p className="text-3xl font-bold" style={{ color: BRAND.accent }}>{c.total}</p>
                        <p className="text-xs opacity-90">verified occupations</p>
                      </div>
                      <ArrowUpRight className="w-6 h-6 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
                    </div>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <FeaturedOccupationsSection />

      {/* Mid-page CTA */}
      <section className="py-12">
        <div className="max-w-5xl mx-auto px-4">
          <div className="rounded-3xl p-8 sm:p-12 flex flex-col sm:flex-row items-center justify-between gap-6 text-white"
            style={{ background: BRAND.primary }}>
            <div className="flex-1">
              <p className="text-xs uppercase tracking-[0.18em] opacity-80">Not sure where to start?</p>
              <h3 className="font-serif-leamss text-2xl sm:text-3xl font-bold mt-1">Take our 60-second AI Eligibility Quiz</h3>
              <p className="text-sm opacity-90 mt-2">Get a personalised scorecard across all 9 major pathways. Free. No login.</p>
            </div>
            <Button size="lg" as={Link} to="/start" data-testid="atlas-hub-cta-quiz">
              Start Quiz<ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </section>

      <SocialProofSection />
    </LeamssShell>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// ATLAS COUNTRY V2 — /atlas/:country
// ═══════════════════════════════════════════════════════════════════════════
export function AtlasCountryV2() {
  const { country: rawCountry } = useParams();
  const country = (rawCountry || '').toUpperCase();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const searchInputRef = useRef(null);

  const fetchList = async (targetPage = 1, query = '') => {
    setShowSuggestions(false);
    if (!['AU', 'CA', 'NZ'].includes(country)) {
      setData({ error: 'Country not found' });
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const r = await axios.get(`${API}/public-atlas/${country}/list`, {
        params: {
          limit: 50,
          offset: (targetPage - 1) * 50,
          search: query.trim() || undefined,
        },
      });
      setData(r.data);
      applySEO(r.data.seo);
    } catch (e) {
      setData({ error: 'Failed to load occupations' });
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

  const runSearch = () => {
    setPage(1);
    fetchList(1, search);
  };

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
    <LeamssShell>
      {/* Hero */}
      <section className="relative overflow-hidden h-[40vh] min-h-[320px]" data-testid="atlas-country-root">
        <img src={COUNTRY_HERO[country]} alt={cm.name || country} className="absolute inset-0 w-full h-full object-cover" />
        <div className="absolute inset-0" style={{ background: `linear-gradient(to right, ${BRAND.primaryDk}E0, ${BRAND.primaryDk}80 60%, transparent)` }} />
        <div className="relative h-full max-w-7xl mx-auto px-4 flex flex-col justify-end pb-12 text-white">
          <Link reloadDocument to="/atlas" className="text-xs hover:underline opacity-80 mb-3 inline-block">← Atlas Hub</Link>
          <h1 className="font-serif-leamss text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight">
            {cm.flag} Migrate to {cm.name || country}
          </h1>
          <p className="text-sm sm:text-base opacity-90 mt-2">
            {total} verified occupations · {cm.classification || '—'}
          </p>
        </div>
      </section>

      {/* Search + grid */}
      <section className="py-12">
        <div className="max-w-7xl mx-auto px-4">
          <div className="relative max-w-4xl mx-auto mb-8">
            <div className="rounded-xl p-2.5 bg-white flex items-center gap-2 shadow-sm" style={{ border: `1.5px solid ${BRAND.border}` }}>
              <Search className="w-4 h-4 ml-2 shrink-0" style={{ color: BRAND.muted }} />
              <input
                ref={searchInputRef}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onFocus={() => setShowSuggestions(true)}
                onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    runSearch();
                  } else if (e.key === 'Escape') {
                    setShowSuggestions(false);
                  }
                }}
                placeholder="Search by code, title, alternative title, or industry — e.g., 'marketing', 'software engineer', '225113', 'operations head'…"
                className="flex-1 outline-none px-2 py-1.5 text-sm bg-transparent min-w-0"
                data-testid="atlas-country-search"
              />
              {search && (
                <button
                  type="button"
                  onClick={() => { setSearch(''); setPage(1); fetchList(1, ''); }}
                  className="p-1 rounded-full text-slate-400 hover:text-slate-700 hover:bg-slate-100"
                  aria-label="Clear search"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
              <Button onClick={runSearch}>Search</Button>
            </div>

            {/* Typeahead dropdown */}
            {showSuggestions && suggestions.length > 0 && search.trim().length >= 2 && (
              <div
                className="absolute left-0 right-0 top-full mt-1.5 z-40 bg-white border rounded-xl shadow-xl max-h-80 overflow-y-auto"
                style={{ borderColor: BRAND.border }}
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
                    <span className="text-xs font-bold px-2 py-1 rounded shrink-0" style={{ background: `${BRAND.primary}12`, color: BRAND.primary }}>
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

          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <h2 className="text-lg font-bold" style={{ color: BRAND.ink }}>Browse occupations</h2>
            <span className="text-xs" style={{ color: BRAND.muted }}>
              Showing {total > 0 ? (page - 1) * pageSize + 1 : 0}–{Math.min(page * pageSize, total)} of {total} verified · sorted by code
            </span>
          </div>

          {loading ? (
            <div className="py-16 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto" style={{ color: BRAND.primary }} /></div>
          ) : data?.error ? (
            <p className="text-center py-16" style={{ color: BRAND.body }} data-testid="atlas-country-error">{data.error}</p>
          ) : (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" data-testid="atlas-country-grid">
                {(data?.items || []).map(it => <OccupationCard key={`${it.country_code}-${it.code}`} item={it} />)}
              </div>

              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-1.5 mt-10 flex-wrap" data-testid="atlas-pagination">
                  <button
                    onClick={() => { const prev = Math.max(1, page - 1); setPage(prev); fetchList(prev, search); window.scrollTo({ top: 400, behavior: 'smooth' }); }}
                    disabled={page === 1}
                    className="px-3 py-1.5 rounded-lg border text-xs font-bold bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition"
                    style={{ borderColor: BRAND.border }}
                  >
                    ← Prev
                  </button>
                  {getPageNumbers().map((num, idx) => (
                    num === '...' ? (
                      <span key={`ellipsis-${idx}`} className="w-8 text-center text-xs font-bold text-slate-400">…</span>
                    ) : (
                      <button
                        key={num}
                        onClick={() => { setPage(num); fetchList(num, search); window.scrollTo({ top: 400, behavior: 'smooth' }); }}
                        className="min-w-[36px] h-9 px-2 rounded-lg text-xs font-bold transition flex items-center justify-center"
                        style={{
                          background: page === num ? BRAND.primary : '#fff',
                          color: page === num ? '#fff' : BRAND.ink,
                          border: `1.5px solid ${page === num ? BRAND.primary : BRAND.border}`,
                        }}
                      >
                        {num}
                      </button>
                    )
                  ))}
                  <button
                    onClick={() => { const next = Math.min(totalPages, page + 1); setPage(next); fetchList(next, search); window.scrollTo({ top: 400, behavior: 'smooth' }); }}
                    disabled={page === totalPages}
                    className="px-3 py-1.5 rounded-lg border text-xs font-bold bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition"
                    style={{ borderColor: BRAND.border }}
                  >
                    Next →
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </section>
    </LeamssShell>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// ATLAS OCCUPATION V2 — /atlas/:country/:code
// ═══════════════════════════════════════════════════════════════════════════
export function AtlasOccupationV2() {
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
        if (active) { setData(r.data); applySEO(r.data.seo); }
      } catch (e) {
        if (active) setData({ error: e.response?.data?.detail || 'Not found' });
      }
      if (active) setLoading(false);
    })();
    return () => { active = false; };
  }, [country, code]);

  // Render — keep all hooks above this point.
  let body = null;
  if (loading) {
    body = <div className="py-32 text-center"><Loader2 className="w-8 h-8 animate-spin mx-auto" style={{ color: BRAND.primary }} /></div>;
  } else if (data?.error) {
    body = (
      <div className="py-32 text-center max-w-md mx-auto px-4" data-testid="atlas-occ-error">
        <p className="font-serif-leamss text-2xl font-bold" style={{ color: BRAND.ink }}>{data.error}</p>
        <Button variant="secondary" className="mt-5" onClick={() => navigate('/atlas')}>← Back to Atlas Hub</Button>
      </div>
    );
  }
  if (body) return <LeamssShell>{body}</LeamssShell>;

  const occ = data.occupation;
  const cm = data.country_meta;

  return (
    <LeamssShell>
      {/* Hero with landmark backdrop */}
      <section className="relative overflow-hidden" data-testid="atlas-occ-root">
        <div className="absolute inset-0">
          <img src={COUNTRY_HERO[country]} alt={cm.name} className="w-full h-full object-cover" />
          <div className="absolute inset-0" style={{ background: `linear-gradient(to right, ${BRAND.primaryDk}F0, ${BRAND.primaryDk}D0 50%, ${BRAND.primaryDk}90)` }} />
        </div>
        <div className="relative max-w-7xl mx-auto px-4 py-16 lg:py-20 text-white">
          <div className="text-xs opacity-80 mb-3">
            <Link reloadDocument to="/atlas" className="hover:underline">Atlas</Link>
            <ChevronRight className="w-3 h-3 inline mx-1" />
            <Link reloadDocument to={`/atlas/${country.toLowerCase()}`} className="hover:underline">{cm.flag} {cm.name}</Link>
            <ChevronRight className="w-3 h-3 inline mx-1" />
            <span>{occ.code}</span>
          </div>
          <div className="flex items-center gap-3 mb-3 flex-wrap">
            <Pill bg="rgba(255,255,255,0.18)" color="#fff">{cm.classification}</Pill>
            <Pill bg="rgba(255,255,255,0.18)" color="#fff"><CheckCircle2 className="w-3 h-3" />Verified</Pill>
            {occ.nz_green_list_tier && (
              <Pill color="#fff" bg={BRAND.accent}>🇳🇿 Green List Tier {occ.nz_green_list_tier}</Pill>
            )}
            {occ.teer_category !== undefined && occ.teer_category !== null && (
              <Pill bg="rgba(255,255,255,0.18)" color="#fff">TEER {occ.teer_category}</Pill>
            )}
          </div>
          <h1 className="font-serif-leamss text-4xl sm:text-5xl lg:text-6xl font-bold leading-[1.05]">
            {occ.title}
          </h1>
          <p className="font-mono text-sm mt-3 opacity-80">{cm.flag} {cm.name} · {occ.code}</p>
        </div>
      </section>

      <section className="py-12">
        <div className="max-w-7xl mx-auto px-4 grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-5">
            {occ.description && (
              <DetailCard title="About this Occupation">
                <p className="text-sm leading-relaxed whitespace-pre-line" style={{ color: BRAND.body }}>{occ.description}</p>
              </DetailCard>
            )}

            <DetailCard title="Eligibility & Classification">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {occ.skill_level && <MetricCard label="ANZSCO Skill Level" value={`Level ${occ.skill_level}`} />}
                {occ.teer_category !== undefined && occ.teer_category !== null && <MetricCard label="TEER Category" value={`TEER ${occ.teer_category}`} />}
                {occ.assessing_authority?.name && <MetricCard label="Assessing Body" value={occ.assessing_authority.name} />}
              </div>
              {occ.assessing_authority?.full_name && (
                <p className="text-xs mt-4 italic" style={{ color: BRAND.muted }}>
                  Full assessing body: {occ.assessing_authority.full_name}
                  {occ.assessing_authority.website && (
                    <> · <a href={occ.assessing_authority.website} target="_blank" rel="noreferrer" className="underline font-semibold" style={{ color: BRAND.primary }}>Official site ↗</a></>
                  )}
                </p>
              )}
            </DetailCard>

            {occ.visa_pathways && (
              <DetailCard title="Visa Pathways">
                <div className="flex flex-wrap gap-2">
                  {(occ.visa_pathways.visa_eligibility || []).map(v => (
                    <span key={v.visa_subclass} className="text-xs px-3 py-1.5 rounded-md font-mono font-semibold border"
                      style={{
                        background: v.eligible ? `${BRAND.primary}10` : BRAND.bgSoft,
                        color: v.eligible ? BRAND.primary : BRAND.muted,
                        borderColor: v.eligible ? BRAND.primary : BRAND.border,
                      }}>
                      {v.eligible ? '✓' : '✗'} {v.visa_subclass}
                    </span>
                  ))}
                </div>
              </DetailCard>
            )}

            {occ.ee_eligibility && (
              <DetailCard title="🇨🇦 Express Entry Eligibility">
                <div className="grid grid-cols-3 gap-2 mb-3">
                  <MetricCard label="FSWP" value={occ.ee_eligibility.fswp_eligible ? '✓' : '✗'} />
                  <MetricCard label="CEC"  value={occ.ee_eligibility.cec_eligible ? '✓' : '✗'} />
                  <MetricCard label="FSTP" value={occ.ee_eligibility.fstp_eligible ? '✓' : '✗'} />
                </div>
                {occ.ee_eligibility.category_details?.length > 0 && (
                  <div>
                    <p className="text-[10px] uppercase font-bold mb-2 tracking-wider" style={{ color: BRAND.muted }}>Category-Based Selection</p>
                    <div className="flex flex-wrap gap-1.5">
                      {occ.ee_eligibility.category_details.map(c => (
                        <Pill key={c.id} color={BRAND.accent}>{c.icon || ''} {c.label}</Pill>
                      ))}
                    </div>
                  </div>
                )}
              </DetailCard>
            )}

            {occ.aewv_eligibility && (
              <DetailCard title="🇳🇿 AEWV + SMC Eligibility">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm" style={{ color: BRAND.body }}>
                  <div>
                    <p className="font-bold mb-2" style={{ color: BRAND.primary }}>AEWV (Work Visa)</p>
                    <p><strong>Eligible:</strong> {occ.aewv_eligibility.eligible ? 'Yes' : 'No'}</p>
                    <p>Band: {occ.aewv_eligibility.occupational_band}</p>
                    <p>Max stay: {occ.aewv_eligibility.max_stay_years} years</p>
                  </div>
                  <div>
                    <p className="font-bold mb-2" style={{ color: BRAND.primary }}>SMC (Residency)</p>
                    <p><strong>Skill points:</strong> {occ.smc_points_breakdown?.skill_points_base} / {occ.smc_points_breakdown?.pass_mark}</p>
                    <p>Green List auto-pass: {occ.smc_points_breakdown?.green_list_auto_pass ? 'Yes' : 'No'}</p>
                  </div>
                </div>
              </DetailCard>
            )}

            {data.faqs?.length > 0 && (
              <DetailCard title="Frequently Asked Questions">
                <Accordion type="single" collapsible className="space-y-2" data-testid="atlas-occ-faq">
                  {data.faqs.map((f, i) => (
                    <AccordionItem key={i} value={`occ-faq-${i}`} className="border rounded-lg px-4" style={{ borderColor: BRAND.border }}>
                      <AccordionTrigger className="text-left font-semibold py-3 hover:no-underline text-sm" style={{ color: BRAND.ink }} data-testid={`atlas-faq-trigger-${i}`}>
                        {f.q}
                      </AccordionTrigger>
                      <AccordionContent className="text-sm leading-relaxed pb-4" style={{ color: BRAND.body }}>
                        {f.a}
                      </AccordionContent>
                    </AccordionItem>
                  ))}
                </Accordion>
              </DetailCard>
            )}

            {data.similar?.length > 0 && (
              <DetailCard title="Similar Occupations">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {data.similar.map(s => <OccupationCard key={`${s.country_code}-${s.code}`} item={s} compact />)}
                </div>
              </DetailCard>
            )}
          </div>

          {/* Sticky lead form */}
          <div className="lg:sticky lg:top-32 self-start">
            <OccupationLeadCapture atlas_code={occ.code} atlas_title={occ.title} country={country} />
          </div>
        </div>
      </section>
    </LeamssShell>
  );
}

function DetailCard({ title, children }) {
  return (
    <div className="rounded-2xl p-6 bg-white" style={{ border: `1px solid ${BRAND.border}` }}>
      <p className="text-[11px] uppercase font-bold mb-4 tracking-[0.14em]" style={{ color: BRAND.accent }}>{title}</p>
      {children}
    </div>
  );
}

function MetricCard({ label, value }) {
  return (
    <div className="rounded-lg p-3" style={{ background: BRAND.bgSoft, border: `1px solid ${BRAND.border}` }}>
      <p className="text-[10px] uppercase font-bold tracking-wider" style={{ color: BRAND.muted }}>{label}</p>
      <p className="text-xl font-bold mt-1 font-serif-leamss" style={{ color: BRAND.primary }}>{value}</p>
    </div>
  );
}

function OccupationLeadCapture({ atlas_code, atlas_title, country }) {
  const [form, setForm] = useState({ name: '', email: '', phone: '', message: '' });
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState(null);
  const [mountTime] = useState(() => Date.now());

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true); setError(null);
    try {
      const r = await axios.post(`${API}/public-atlas/lead`, {
        ...form, country_of_interest: country, atlas_code, atlas_title,
        company_url: (Date.now() - mountTime) < 1500 ? 'bot' : '',
      });
      if (r.data.ok) setDone(true);
    } catch (e) { setError(e.response?.data?.detail || 'Submission failed'); }
    setSubmitting(false);
  };

  if (done) {
    return (
      <div className="rounded-2xl p-7 text-center" style={{ background: `${BRAND.primary}10`, border: `1px solid ${BRAND.primary}30` }} data-testid="atlas-lead-success">
        <CheckCircle2 className="w-10 h-10 mx-auto mb-3" style={{ color: BRAND.primary }} />
        <p className="font-serif-leamss text-2xl font-bold" style={{ color: BRAND.ink }}>You&apos;re in!</p>
        <p className="text-sm mt-2" style={{ color: BRAND.body }}>A LEAMSS expert will WhatsApp you within 24 hours.</p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="rounded-2xl p-6 bg-white shadow-sm" style={{ border: `1px solid ${BRAND.border}` }} data-testid="atlas-lead-form">
      <p className="text-xs uppercase font-bold tracking-[0.14em]" style={{ color: BRAND.accent }}>
        <Sparkles className="w-3 h-3 inline mr-1" />Free Eligibility Check
      </p>
      <h3 className="font-serif-leamss text-2xl font-bold mt-1 mb-1" style={{ color: BRAND.ink }}>
        Talk to a MARA expert
      </h3>
      <p className="text-xs mb-5" style={{ color: BRAND.muted }}>
        For <strong>{atlas_title}</strong> · 100% confidential · No obligation
      </p>
      <div className="space-y-2.5">
        <FieldInput icon={UserIcon} placeholder="Full name" value={form.name} onChange={v => setForm({ ...form, name: v })} testid="atlas-lead-name" />
        <FieldInput icon={Mail} placeholder="Email" type="email" value={form.email} onChange={v => setForm({ ...form, email: v })} testid="atlas-lead-email" />
        <FieldInput icon={Phone} placeholder="Phone (with country code)" value={form.phone} onChange={v => setForm({ ...form, phone: v })} testid="atlas-lead-phone" />
        <textarea
          placeholder="Brief: experience, age, English score… (optional)"
          value={form.message}
          onChange={(e) => setForm({ ...form, message: e.target.value })}
          rows={3}
          className="w-full px-3 py-2.5 rounded-lg border outline-none text-sm resize-none"
          style={{ borderColor: BRAND.border }}
          data-testid="atlas-lead-message"
        />
        {error && <p className="text-xs" style={{ color: '#B91C1C' }}>{error}</p>}
        <Button type="submit" className="w-full" disabled={submitting || !form.name || !form.email || !form.phone} data-testid="atlas-lead-submit">
          {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          {submitting ? 'Sending…' : 'Get Free Eligibility Check'}
        </Button>
        <a href={`https://wa.me/${WHATSAPP}`} target="_blank" rel="noreferrer"
          className="block w-full text-center px-5 py-2.5 rounded-md text-sm font-semibold transition-all hover:brightness-110"
          style={{ background: '#25D366', color: '#fff' }} data-testid="atlas-lead-whatsapp">
          <MessageCircle className="w-4 h-4 inline mr-1" />Or WhatsApp now
        </a>
      </div>
      <p className="text-[10px] mt-4 italic text-center" style={{ color: BRAND.muted }}>
        By submitting, you agree to be contacted by LEAMSS migration advisors. We never share your data.
      </p>
    </form>
  );
}

function FieldInput({ icon: Icon, placeholder, value, onChange, type = 'text', testid }) {
  return (
    <div className="relative">
      <Icon className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5" style={{ color: BRAND.muted }} />
      <input
        type={type} placeholder={placeholder} value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full pl-9 pr-3 py-2.5 rounded-lg border outline-none text-sm"
        style={{ borderColor: BRAND.border }}
        data-testid={testid} required
      />
    </div>
  );
}