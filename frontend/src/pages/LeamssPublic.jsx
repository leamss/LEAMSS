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
  MessageCircle, Calculator, Plane, Shield, Clock, ArrowUpRight, MapPin, Info, Download,
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

const LOGO_URL = 'https://leamss.com/public/assets/web/images/logo.webp';
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
  upsert('og:title', seo.og_title || seo.page_title, true);
  upsert('og:description', seo.og_description || seo.meta_description, true);
  upsert('og:image', seo.og_image, true);
  upsert('og:type', 'article', true);
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
          <Link to="/atlas" data-testid="leamss-logo" className="flex items-center gap-2">
            <img src={LOGO_URL} alt="LEAMSS — Ladhani Education & Migration Services" className="h-12 w-auto" />
          </Link>
          <nav className="hidden md:flex items-center gap-6 text-sm font-medium" style={{ color: headerTextColor }}>
            <Link to="/atlas" className="hover:opacity-80 transition-opacity">Atlas</Link>
            <Link to="/start" className="hover:opacity-80 transition-opacity">Eligibility Quiz</Link>
            <Link to="/atlas/au" className="hover:opacity-80 transition-opacity">🇦🇺 Australia</Link>
            <Link to="/atlas/ca" className="hover:opacity-80 transition-opacity">🇨🇦 Canada</Link>
            <Link to="/atlas/nz" className="hover:opacity-80 transition-opacity">🇳🇿 New Zealand</Link>
            <a href={`https://wa.me/${WHATSAPP}`} target="_blank" rel="noreferrer"
              className="px-4 py-2 rounded-md text-white font-semibold transition-all hover:brightness-110"
              style={{ background: BRAND.accent }}
              data-testid="header-whatsapp-cta"
            >
              Book Free Consultation
            </a>
          </nav>
        </div>
      </header>

      {children}

      {/* Footer */}
      <footer style={{ background: BRAND.primaryDk, color: '#FFFFFF' }}>
        <div className="max-w-7xl mx-auto px-4 py-12 grid grid-cols-1 md:grid-cols-4 gap-8 text-sm">
          <div>
            <img src={LOGO_URL} alt="LEAMSS" className="h-12 w-auto mb-3 brightness-0 invert" />
            <p className="text-white/80 leading-relaxed">
              <strong>Ladhani Education & Migration Services (OPC) Pvt. Ltd</strong><br />
              India&apos;s trusted immigration experts. We value emotions.
            </p>
            <p className="text-white/70 text-xs mt-3">Office No. 10, Londhe Compound, Laxmi Chambers,<br />Near Gaondevi Maidan, Thane West — 400602</p>
          </div>
          <div>
            <p className="font-bold mb-3 font-serif-leamss text-lg">Browse Atlas</p>
            <ul className="space-y-1.5 text-white/80">
              <li><Link to="/atlas/au" className="hover:text-white">🇦🇺 Australia ANZSCO</Link></li>
              <li><Link to="/atlas/ca" className="hover:text-white">🇨🇦 Canada NOC 2021</Link></li>
              <li><Link to="/atlas/nz" className="hover:text-white">🇳🇿 New Zealand</Link></li>
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
            © 2026 Ladhani Education & Migration Services (OPC) Pvt. Ltd · MARA Registered · 100% Refund Guarantee Policy
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
      meta_description: 'Free AI eligibility check + verified ANZSCO/NOC atlas + visa comparison for AU, CA, NZ. 100% refund guarantee on negative skill assessment. India\'s most trusted migration consultancy since 2014.',
      canonical_url: `${window.location.origin}/start`,
      og_image: LOGO_URL,
      json_ld: {
        "@context": "https://schema.org",
        "@graph": [
          {
            "@type": "Organization",
            "name": "Ladhani Education & Migration Services (OPC) Pvt. Ltd",
            "alternateName": "LEAMSS",
            "url": "https://www.leamss.com",
            "logo": LOGO_URL,
            "address": { "@type": "PostalAddress", "addressLocality": "Thane", "addressRegion": "Maharashtra", "addressCountry": "IN" },
            "contactPoint": { "@type": "ContactPoint", "telephone": "+91-77188-82427", "contactType": "customer service" },
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
              <Button variant="secondary" size="lg" as={Link} to="/atlas" data-testid="hero-browse-atlas">
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
            { code: 'AU', name: 'Australia', desc: 'ANZSCO · 932 verified codes', img: COUNTRY_HERO.AU },
            { code: 'CA', name: 'Canada',    desc: 'NOC 2021 · Express Entry + 11 PNPs', img: COUNTRY_HERO.CA },
            { code: 'NZ', name: 'New Zealand', desc: 'Green List Tier 1 + Tier 2 · AEWV', img: COUNTRY_HERO.NZ },
          ].map((c, i) => (
            <motion.div
              key={c.code}
              initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.6, delay: 0.15 + i * 0.1 }}
            >
              <Link
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

// ─── Eligibility Quiz Section ──────────────────────────────────────────────
const QUIZ_STEPS = [
  { id: 'age', label: 'Your Age', type: 'number', placeholder: 'e.g., 28', min: 18, max: 60 },
  { id: 'education', label: 'Highest Education', type: 'select', options: ['PhD', 'Masters', 'Bachelors', 'Diploma', 'Class 12'] },
  { id: 'english_score', label: 'English Test Score', type: 'select', options: ['IELTS 8+', 'IELTS 7.0-7.5', 'IELTS 6.5', 'IELTS 6.0', 'PTE 79+', 'PTE 65', 'PTE 50', 'Not taken yet'] },
  { id: 'work_experience_years', label: 'Years of Work Experience', type: 'number', placeholder: 'e.g., 5', min: 0, max: 40 },
  { id: 'occupation', label: 'Your Occupation / Job Title', type: 'text', placeholder: 'e.g., Software Engineer, Registered Nurse, Civil Engineer' },
  { id: 'has_job_offer', label: 'Do you have a job offer abroad?', type: 'radio', options: [
    { value: 'no', label: 'Not yet' }, { value: 'yes', label: '✅ Yes, I have an offer' },
  ] },
  { id: 'country', label: 'Preferred Country', type: 'radio', options: [
    { value: 'AU', label: '🇦🇺 Australia' }, { value: 'CA', label: '🇨🇦 Canada' }, { value: 'NZ', label: '🇳🇿 New Zealand' }, { value: 'any', label: '✨ All three — show me everything' },
  ] },
];

function EligibilityQuizSection() {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [computing, setComputing] = useState(false);

  const setAns = (id, val) => setAnswers(prev => ({ ...prev, [id]: val }));

  const submit = async () => {
    setComputing(true);
    try {
      const countryMap = { AU: 'Australia', CA: 'Canada', NZ: 'New Zealand' };
      const pref = countryMap[answers.country];
      const payload = {
        full_name: 'Website Visitor',
        age: Number(answers.age || 28),
        education: answers.education || 'Bachelors',
        english_score: answers.english_score || 'IELTS 6.5',
        work_experience_years: Number(answers.work_experience_years || 3),
        occupation: (answers.occupation || '').trim() || 'Not specified',
        has_job_offer: answers.has_job_offer === 'yes',
        consent_to_contact: false,
        preferred_countries: pref ? [pref] : null,
      };
      const r = await axios.post(`${API}/eligibility/score`, payload);
      setResult({ ...r.data, _country: pref || null });
    } catch (e) {
      setResult({ error: formatApiError(e, 'Failed to compute score') });
    }
    setComputing(false);
  };

  const next = () => {
    if (step < QUIZ_STEPS.length - 1) setStep(step + 1);
    else submit();
  };
  const back = () => setStep(Math.max(0, step - 1));
  const reset = () => { setStep(0); setAnswers({}); setResult(null); };

  const progress = ((step + 1) / QUIZ_STEPS.length) * 100;
  const currentStep = QUIZ_STEPS[step];
  const isValid = answers[currentStep?.id] !== undefined && answers[currentStep?.id] !== '';

  return (
    <section id="quiz" className="py-20" style={{ background: BRAND.bg }}>
      <div className="max-w-5xl mx-auto px-4">
        <SectionTitle
          eyebrow="Free · 60 Seconds · No Login"
          title="Find your best-fit visa pathway in 60 seconds"
          sub="We rank 8+ pathways (Express Entry, 189/190/491, UK, Germany, NZ Green List) by how well they fit your profile — an indicative shortlist to guide your choice, not an official visa score. Always confirm with a LEAMSS expert before deciding."
        />

        <div className="rounded-2xl overflow-hidden shadow-lg" style={{ background: BRAND.bgSoft, border: `1px solid ${BRAND.border}` }} data-testid="quiz-card">
          {!result ? (
            <>
              <div className="h-1.5 bg-white">
                <motion.div
                  initial={{ width: '0%' }} animate={{ width: `${progress}%` }} transition={{ duration: 0.4 }}
                  style={{ background: BRAND.accent, height: '100%' }} />
              </div>
              <div className="p-8 lg:p-12">
                <div className="flex items-center justify-between mb-6">
                  <p className="text-xs font-bold uppercase tracking-wider" style={{ color: BRAND.muted }}>
                    Step {step + 1} of {QUIZ_STEPS.length}
                  </p>
                  <p className="text-xs" style={{ color: BRAND.muted }}>
                    <Clock className="w-3 h-3 inline mr-1" />~30 sec remaining
                  </p>
                </div>
                <AnimatePresence mode="wait">
                  <motion.div
                    key={step}
                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.25 }}
                  >
                    <h3 className="font-serif-leamss text-3xl sm:text-4xl font-bold mb-6" style={{ color: BRAND.ink }}>
                      {currentStep.label}
                    </h3>
                    {(currentStep.type === 'number' || currentStep.type === 'text') && (
                      <input
                        type={currentStep.type}
                        autoFocus
                        value={answers[currentStep.id] || ''}
                        onChange={(e) => setAns(currentStep.id, e.target.value)}
                        placeholder={currentStep.placeholder}
                        min={currentStep.min} max={currentStep.max}
                        className="w-full px-5 py-4 rounded-lg text-lg font-medium border-2 outline-none focus:border-current"
                        style={{ borderColor: BRAND.border, color: BRAND.ink }}
                        data-testid={`quiz-input-${currentStep.id}`}
                      />
                    )}
                    {currentStep.type === 'select' && (
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {currentStep.options.map(opt => (
                          <button
                            key={opt}
                            onClick={() => setAns(currentStep.id, opt)}
                            className="px-4 py-3 rounded-lg text-sm font-medium border-2 transition-all hover:shadow-sm text-left"
                            style={{
                              borderColor: answers[currentStep.id] === opt ? BRAND.accent : BRAND.border,
                              background: answers[currentStep.id] === opt ? `${BRAND.accent}10` : '#fff',
                              color: BRAND.ink,
                            }}
                            data-testid={`quiz-option-${currentStep.id}-${opt.replace(/\s+/g, '-').toLowerCase()}`}
                          >
                            {opt}
                          </button>
                        ))}
                      </div>
                    )}
                    {currentStep.type === 'radio' && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {currentStep.options.map(opt => (
                          <button
                            key={opt.value}
                            onClick={() => setAns(currentStep.id, opt.value)}
                            className="px-5 py-4 rounded-lg text-base font-semibold border-2 transition-all hover:shadow-sm text-left"
                            style={{
                              borderColor: answers[currentStep.id] === opt.value ? BRAND.accent : BRAND.border,
                              background: answers[currentStep.id] === opt.value ? `${BRAND.accent}10` : '#fff',
                              color: BRAND.ink,
                            }}
                            data-testid={`quiz-radio-${opt.value}`}
                          >
                            {opt.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </motion.div>
                </AnimatePresence>

                <div className="flex items-center justify-between mt-8">
                  <Button variant="ghost" onClick={back} disabled={step === 0}>← Back</Button>
                  <Button onClick={next} disabled={!isValid || computing} data-testid="quiz-next-btn">
                    {computing ? <Loader2 className="w-4 h-4 animate-spin" /> :
                      step === QUIZ_STEPS.length - 1 ? <>Get My Score<Sparkles className="w-4 h-4" /></> :
                      <>Next<ArrowRight className="w-4 h-4" /></>}
                  </Button>
                </div>
              </div>
            </>
          ) : (
            <QuizResult result={result} onReset={reset} />
          )}
        </div>
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

function FactorBar({ b }) {
  const pct = b.max > 0 ? Math.round((b.earned / b.max) * 100) : 0;
  const color = pct >= 80 ? BRAND.success : pct >= 50 ? BRAND.primary : BRAND.accent;
  return (
    <div className="py-1.5" data-testid={`factor-${b.factor}`}>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="font-semibold" style={{ color: BRAND.ink }}>{b.label}</span>
        <span className="font-bold tabular-nums" style={{ color }}>{b.earned}<span style={{ color: BRAND.muted }}>/{b.max}</span></span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: BRAND.border }}>
        <div style={{ width: `${pct}%`, background: color, height: '100%' }} />
      </div>
      <p className="text-[11px] mt-1" style={{ color: BRAND.muted }}>{b.reason}</p>
    </div>
  );
}

function PathwayResultCard({ p, isBest }) {
  const [open, setOpen] = useState(isBest);
  const tm = tierMeta(p.tier);
  return (
    <div className="rounded-xl border overflow-hidden bg-white" style={{ borderColor: isBest ? BRAND.accent : BRAND.border, borderWidth: isBest ? 2 : 1 }} data-testid={`pathway-card-${p.score}`}>
      <div className="p-5">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div>
            {isBest && <Pill color={BRAND.accent}>★ Best Match</Pill>}
            <p className="text-sm font-bold mt-1" style={{ color: BRAND.ink }}>{p.name}</p>
            {p.estimated_timeline && <p className="text-[11px] mt-0.5" style={{ color: BRAND.muted }}>⏱ {p.estimated_timeline}</p>}
          </div>
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full whitespace-nowrap" style={{ background: tm.bg, color: tm.color }}>{tm.label}</span>
        </div>
        <div className="flex items-baseline gap-1">
          <span className="text-4xl font-bold font-serif-leamss" style={{ color: tm.color }}>{p.score}</span>
          <span className="text-sm" style={{ color: BRAND.muted }}>/ 100</span>
        </div>
        <div className="h-2 rounded-full overflow-hidden mt-2" style={{ background: BRAND.border }}>
          <div style={{ width: `${p.score}%`, background: tm.color, height: '100%' }} />
        </div>
        {p.notes && <p className="text-xs mt-3" style={{ color: BRAND.body }}>{p.notes}</p>}
        {(p.strengths?.length > 0) && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {p.strengths.slice(0, 3).map((s, i) => (
              <span key={i} className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: '#E8F3E9', color: BRAND.success }}>✓ {s}</span>
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
          <ChevronDown className="w-3.5 h-3.5 transition-transform" style={{ transform: open ? 'rotate(180deg)' : 'none' }} />
        </button>
      </div>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }} style={{ overflow: 'hidden', background: BRAND.bgSoft }}
          >
            <div className="px-5 py-4 border-t" style={{ borderColor: BRAND.border }}>
              <p className="text-[11px] font-bold uppercase tracking-wider mb-2" style={{ color: BRAND.muted }}>Profile strength {typeof p.raw_score === 'number' ? `· ${p.raw_score}/100` : ''}</p>
              {(p.breakdown || []).map((b, i) => <FactorBar key={i} b={b} />)}
              {(p.adjustments?.length > 0) && (
                <div className="mt-3 pt-3 border-t" style={{ borderColor: BRAND.border }}>
                  <p className="text-[11px] font-bold uppercase tracking-wider mb-2" style={{ color: BRAND.muted }}>Pathway adjustments</p>
                  {p.adjustments.map((a, i) => (
                    <div key={i} className="flex items-start justify-between gap-2 py-1" data-testid="adjustment-row">
                      <div className="flex-1">
                        <span className="text-xs font-semibold" style={{ color: BRAND.ink }}>{a.label}</span>
                        <p className="text-[11px]" style={{ color: BRAND.muted }}>{a.reason}</p>
                      </div>
                      <span className="text-xs font-bold tabular-nums whitespace-nowrap" style={{ color: BRAND.accent }}>{a.delta}</span>
                    </div>
                  ))}
                  <div className="flex items-center justify-between mt-2 pt-2 border-t" style={{ borderColor: BRAND.border }}>
                    <span className="text-xs font-bold" style={{ color: BRAND.ink }}>Final score</span>
                    <span className="text-sm font-bold" style={{ color: tm.color }}>{p.score}/100</span>
                  </div>
                </div>
              )}
              {p.gaps_to_fix?.length > 0 && (
                <div className="mt-3 pt-3 border-t" style={{ borderColor: BRAND.border }}>
                  <p className="text-[11px] font-bold mb-1" style={{ color: BRAND.accent }}>To improve your score:</p>
                  <ul className="text-[11px] space-y-0.5 ml-4" style={{ color: BRAND.body }}>
                    {p.gaps_to_fix.map((g, i) => <li key={i} className="list-disc">{g}</li>)}
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
      await axios.post(`${API}/eligibility/lead`, {
        score_id: scoreId,
        name: form.name.trim() || 'Website Visitor',
        email: isEmail ? form.contact.trim() : null,
        mobile: isEmail ? null : form.contact.trim(),
        preferred_country: country || null,
      });
      setDone(true);
    } catch (e) { /* swallow — non-blocking */ setDone(true); }
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
    `✅ Best fit: ${topName || 'My pathway'} — ${topScore ?? ''}/100\n\n` +
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
  const pathways = Object.entries(result.pathways || {})
    .map(([slug, p]) => ({ slug, ...p }))
    .sort((a, b) => (b.score || 0) - (a.score || 0));
  const top = result.top_recommendation;
  return (
    <div className="p-8 lg:p-12" data-testid="quiz-result">
      <div className="flex items-center justify-between mb-2 flex-wrap gap-3">
        <p className="text-xs font-bold uppercase tracking-[0.16em]" style={{ color: BRAND.accent }}>Your Pathway Fit Ranking</p>
        <Button variant="ghost" size="sm" onClick={onReset}>↻ Re-take</Button>
      </div>
      <h3 className="font-serif-leamss text-3xl sm:text-4xl font-bold mb-3" style={{ color: BRAND.ink }}>
        {pathways[0] ? `Best Fit: ${pathways[0].name}` : 'Your eligibility breakdown'}
      </h3>

      {/* Prominent honesty disclaimer */}
      <div className="rounded-xl p-4 mb-5 flex gap-3" style={{ background: BRAND.bgWarm, border: `1.5px solid ${BRAND.accent}` }} data-testid="score-disclaimer">
        <Info className="w-5 h-5 shrink-0 mt-0.5" style={{ color: BRAND.accent }} />
        <div>
          <p className="text-sm font-bold" style={{ color: BRAND.ink }}>
            This is a “best-fit” ranking — not an official visa eligibility score
          </p>
          <p className="text-xs mt-1 leading-relaxed" style={{ color: BRAND.body }}>
            These numbers rank <b>which pathways suit your profile best</b> (based on your details and how selective each route is) so you can shortlist the right option. They are <b>not</b> the official points / CRS scores used by immigration authorities. Your real eligibility depends on document verification, skills assessment and current policy — so <b>please speak to a LEAMSS expert before making any decision</b>, to avoid any confusion.
          </p>
        </div>
      </div>

      {result.overall_summary && (
        <p className="text-sm sm:text-base mb-5 max-w-3xl" style={{ color: BRAND.body }}>{result.overall_summary}</p>
      )}
      <div className="rounded-lg px-4 py-2.5 mb-6 inline-flex items-center gap-2 text-xs" style={{ background: BRAND.bgSoft, color: BRAND.muted, border: `1px solid ${BRAND.border}` }}>
        <Shield className="w-3.5 h-3.5" style={{ color: BRAND.primary }} />
        How we rank: your <b style={{ color: BRAND.ink }}>&nbsp;age, education, experience, English, occupation</b>&nbsp;& job offer — tap "How is this calculated?" on any card.
      </div>

      {result.score_id && (
        <ScorecardActions
          scoreId={result.score_id}
          topName={pathways[0]?.name}
          topScore={pathways[0]?.score}
          country={result._country}
        />
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {pathways.map((p) => (
          <PathwayResultCard key={p.slug} p={p} isBest={p.slug === top} />
        ))}
      </div>
      <div className="mt-8 rounded-xl p-5 flex flex-wrap items-center justify-between gap-4" style={{ background: BRAND.primary, color: '#fff' }}>
        <div>
          <p className="font-serif-leamss text-xl font-bold">Get your personalised detailed report</p>
          <p className="text-sm opacity-90">Talk to a MARA-registered LEAMSS expert. 100% refund if assessment fails.</p>
        </div>
        <QuizLeadForm scoreId={result.score_id} country={result._country} />
      </div>
      <p className="text-[11px] mt-4 text-center" style={{ color: BRAND.muted }}>
        Indicative assessment only. Final eligibility depends on document verification, skills assessment & current policy.
      </p>
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
    <Link
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
              <Link
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
              1,500+ verified ANZSCO + NOC 2021 codes for Australia, Canada & New Zealand migration.
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
                <Link
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

  useEffect(() => {
    let active = true;
    (async () => {
      if (!['AU', 'CA', 'NZ'].includes(country)) {
        if (active) { setData({ error: 'Country not found' }); setLoading(false); }
        return;
      }
      setLoading(true);
      try {
        const r = await axios.get(`${API}/public-atlas/${country}/list`, { params: { limit: 120 } });
        if (active) { setData(r.data); applySEO(r.data.seo); }
      } catch (e) {
        if (active) setData({ error: 'Failed to load' });
      }
      if (active) setLoading(false);
    })();
    return () => { active = false; };
  }, [country]);

  const runSearch = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/public-atlas/${country}/list`, { params: { limit: 120, search: search || undefined } });
      setData(r.data);
    } catch (e) { setData({ error: 'Failed to search' }); }
    setLoading(false);
  };

  const cm = data?.country_meta || {};

  return (
    <LeamssShell>
      {/* Hero */}
      <section className="relative overflow-hidden h-[40vh] min-h-[320px]" data-testid="atlas-country-root">
        <img src={COUNTRY_HERO[country]} alt={cm.name || country} className="absolute inset-0 w-full h-full object-cover" />
        <div className="absolute inset-0" style={{ background: `linear-gradient(to right, ${BRAND.primaryDk}E0, ${BRAND.primaryDk}80 60%, transparent)` }} />
        <div className="relative h-full max-w-7xl mx-auto px-4 flex flex-col justify-end pb-12 text-white">
          <Link to="/atlas" className="text-xs hover:underline opacity-80 mb-3 inline-block">← Atlas Hub</Link>
          <h1 className="font-serif-leamss text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight">
            {cm.flag} Migrate to {cm.name || country}
          </h1>
          <p className="text-sm sm:text-base opacity-90 mt-2">
            {data?.total ?? '—'} verified occupations · {cm.classification || '—'}
          </p>
        </div>
      </section>

      {/* Search + grid */}
      <section className="py-12">
        <div className="max-w-7xl mx-auto px-4">
          <div className="rounded-xl p-3 bg-white flex items-center gap-2 mb-8 shadow-sm" style={{ border: `1px solid ${BRAND.border}` }}>
            <Search className="w-4 h-4 ml-2" style={{ color: BRAND.muted }} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && runSearch()}
              placeholder={`Search ${cm.name || country} occupations — e.g., 261313 or Software Engineer`}
              className="flex-1 outline-none px-2 py-2 text-sm"
              data-testid="atlas-country-search"
            />
            <Button onClick={runSearch}>Search</Button>
          </div>

          {loading ? (
            <div className="py-16 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto" style={{ color: BRAND.primary }} /></div>
          ) : data?.error ? (
            <p className="text-center py-16" style={{ color: BRAND.body }} data-testid="atlas-country-error">{data.error}</p>
          ) : (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" data-testid="atlas-country-grid">
              {(data?.items || []).map(it => <OccupationCard key={`${it.country_code}-${it.code}`} item={it} />)}
            </div>
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
            <Link to="/atlas" className="hover:underline">Atlas</Link>
            <ChevronRight className="w-3 h-3 inline mx-1" />
            <Link to={`/atlas/${country.toLowerCase()}`} className="hover:underline">{cm.flag} {cm.name}</Link>
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
