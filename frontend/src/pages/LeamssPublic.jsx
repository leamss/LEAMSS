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
  MessageCircle, Calculator, Plane, Shield, Clock, ArrowUpRight, MapPin,
} from 'lucide-react';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';

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
  useEffect(() => {
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
          {
            "@type": "FAQPage",
            "mainEntity": FAQS.map(f => ({
              "@type": "Question",
              "name": f.q,
              "acceptedAnswer": { "@type": "Answer", "text": f.a },
            })),
          },
        ],
      },
    });
  }, []);

  return (
    <LeamssShell>
      <Hero />
      <TrustStrip />
      <EligibilityQuizSection />
      <VisaCompareSection />
      <FeaturedOccupationsSection />
      <BrowseAtlasSection />
      <SocialProofSection />
      <FAQSection />
      <StickyLeadFooter />
    </LeamssShell>
  );
}

// ─── Hero ──────────────────────────────────────────────────────────────────
function Hero() {
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
              <Shield className="w-3 h-3" />100% Refund Guarantee · MARA Registered
            </Pill>
            <h1 className="font-serif-leamss text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-bold leading-[1.05] mt-5"
              style={{ color: BRAND.ink }}>
              Find your migration
              <br />
              <span style={{ color: BRAND.primary }}>pathway</span> in{' '}
              <span style={{ color: BRAND.accent, fontStyle: 'italic' }}>60 seconds</span>.
            </h1>
            <p className="mt-6 text-lg lg:text-xl leading-relaxed max-w-xl" style={{ color: BRAND.body }}>
              Free AI eligibility check across 80+ visa categories for Australia, Canada & New Zealand.
              No login. No spam. Just an honest scorecard.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button size="lg" data-testid="hero-start-quiz" onClick={() => document.getElementById('quiz')?.scrollIntoView({ behavior: 'smooth' })}>
                Start AI Eligibility Quiz<ArrowRight className="w-4 h-4" />
              </Button>
              <Button variant="secondary" size="lg" as={Link} to="/atlas" data-testid="hero-browse-atlas">
                Browse Migration Atlas
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
                  <span className="font-bold ml-1" style={{ color: BRAND.ink }}>4.9 / 5</span>
                </div>
                <p className="text-xs" style={{ color: BRAND.muted }}>from 500+ Google reviews</p>
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
function TrustStrip() {
  const items = [
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
  { id: 'age', label: 'Age', type: 'number', placeholder: 'e.g., 28', min: 18, max: 60 },
  { id: 'education', label: 'Highest Education', type: 'select', options: ['PhD', 'Masters', 'Bachelors', 'Diploma', 'Class 12'] },
  { id: 'english_score', label: 'English Test Score', type: 'select', options: ['IELTS 8+', 'IELTS 7.0-7.5', 'IELTS 6.5', 'IELTS 6.0', 'PTE 79+', 'PTE 65', 'PTE 50', 'Not taken yet'] },
  { id: 'work_experience_years', label: 'Years of Work Experience', type: 'number', placeholder: 'e.g., 5', min: 0, max: 30 },
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
      const payload = {
        age: Number(answers.age || 28),
        education: answers.education || 'Bachelors',
        english_score: answers.english_score || 'IELTS 6.5',
        work_experience_years: Number(answers.work_experience_years || 3),
        occupation: '',
        has_job_offer: false,
        consent_to_contact: false,
      };
      const r = await axios.post(`${API}/eligibility/score`, payload);
      setResult(r.data);
    } catch (e) {
      setResult({ error: e.response?.data?.detail || 'Failed to compute score' });
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
          title="AI Eligibility Score across all major pathways"
          sub="Powered by Claude Sonnet. We score you against 8+ visa pathways (189, 190, 491, 482, 186, Express Entry, NZ Green List, AEWV) and show you honest odds."
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
                    {currentStep.type === 'number' && (
                      <input
                        type="number"
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

function QuizResult({ result, onReset }) {
  if (result.error) {
    return (
      <div className="p-12 text-center" data-testid="quiz-error">
        <p className="text-base font-bold" style={{ color: '#B91C1C' }}>{result.error}</p>
        <Button variant="secondary" className="mt-4" onClick={onReset}>Try Again</Button>
      </div>
    );
  }
  const pathways = Object.entries(result.pathways || {})
    .sort(([, a], [, b]) => (b.score || 0) - (a.score || 0))
    .slice(0, 6);
  return (
    <div className="p-8 lg:p-12" data-testid="quiz-result">
      <div className="flex items-center justify-between mb-2 flex-wrap gap-3">
        <p className="text-xs font-bold uppercase tracking-[0.16em]" style={{ color: BRAND.accent }}>Your AI Scorecard</p>
        <Button variant="ghost" size="sm" onClick={onReset}>↻ Re-take</Button>
      </div>
      <h3 className="font-serif-leamss text-3xl sm:text-4xl font-bold mb-6" style={{ color: BRAND.ink }}>
        {result.top_recommendation ? `Best Match: ${result.top_recommendation}` : 'Your eligibility breakdown'}
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {pathways.map(([id, p]) => (
          <div key={id} className="rounded-lg p-4 border" style={{ background: '#fff', borderColor: BRAND.border }}>
            <div className="flex items-center justify-between mb-1">
              <p className="text-sm font-bold" style={{ color: BRAND.ink }}>{p.title || id}</p>
              <Pill color={p.tier === 'gold' ? BRAND.accent : p.tier === 'silver' ? BRAND.primary : BRAND.muted}>
                {p.tier || 'review'}
              </Pill>
            </div>
            <div className="flex items-baseline gap-1 mt-2">
              <span className="text-3xl font-bold font-serif-leamss" style={{ color: BRAND.primary }}>{p.score || 0}</span>
              <span className="text-sm" style={{ color: BRAND.muted }}>/ 100</span>
            </div>
            <div className="h-1.5 rounded-full overflow-hidden mt-2" style={{ background: BRAND.border }}>
              <div style={{ width: `${p.score || 0}%`, background: p.tier === 'gold' ? BRAND.accent : BRAND.primary, height: '100%' }} />
            </div>
            <p className="text-xs mt-2 line-clamp-2" style={{ color: BRAND.body }}>{p.notes || p.summary || ''}</p>
          </div>
        ))}
      </div>
      <div className="mt-8 rounded-lg p-5 flex flex-wrap items-center justify-between gap-4" style={{ background: BRAND.primary, color: '#fff' }}>
        <div>
          <p className="font-serif-leamss text-xl font-bold">Get a personalised detailed report</p>
          <p className="text-sm opacity-90">Talk to a MARA-registered LEAMSS expert. 100% refund if assessment fails.</p>
        </div>
        <Button as="a" href={`https://wa.me/${WHATSAPP}`} data-testid="quiz-cta-whatsapp">
          WhatsApp Expert<MessageCircle className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}

// ─── Visa Compare Section ──────────────────────────────────────────────────
const COMPARE_DATA = [
  {
    country: 'Australia', flag: '🇦🇺', code: 'AU',
    pathways: [
      { name: 'Subclass 189 (Skilled Independent)', pts: 65, age: '< 45', english: 'IELTS 6.0', time: '8-12 mo', highlight: true },
      { name: 'Subclass 190 (State Nominated)',    pts: 65, age: '< 45', english: 'IELTS 6.0', time: '6-10 mo' },
      { name: 'Subclass 491 (Regional)',           pts: 65, age: '< 45', english: 'IELTS 6.0', time: '6-9 mo' },
    ],
  },
  {
    country: 'Canada', flag: '🇨🇦', code: 'CA',
    pathways: [
      { name: 'Express Entry — FSW',     pts: 67, age: '< 45', english: 'CLB 7',   time: '6-8 mo', highlight: true },
      { name: 'Provincial Nominee (PNP)', pts: '60+CRS', age: 'Varies', english: 'CLB 5-7', time: '12-18 mo' },
      { name: 'Quebec PSTQ',             pts: '50+',    age: 'Varies', english: 'French B2', time: '24-36 mo' },
    ],
  },
  {
    country: 'New Zealand', flag: '🇳🇿', code: 'NZ',
    pathways: [
      { name: 'Green List Tier 1 (Straight to Residence)', pts: 'N/A (auto)', age: '< 55', english: 'IELTS 6.5', time: '3-6 mo', highlight: true },
      { name: 'Green List Tier 2 (Work-to-Residence)',     pts: 'N/A',        age: '< 55', english: 'IELTS 6.5', time: '24 mo work + 6 mo' },
      { name: 'SMC 6-Point System',                        pts: 6,            age: '< 55', english: 'IELTS 6.5', time: '12-18 mo' },
    ],
  },
];

function VisaCompareSection() {
  return (
    <section className="py-20" style={{ background: BRAND.bgSoft }}>
      <div className="max-w-7xl mx-auto px-4">
        <SectionTitle
          eyebrow="Side-by-Side Visa Compare"
          title="Choose the pathway that fits your profile"
          sub="9 most-applied visa programs across AU, CA, NZ — points, age limits, English requirements, processing time."
        />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5" data-testid="visa-compare-grid">
          {COMPARE_DATA.map((c, idx) => (
            <motion.div
              key={c.code}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-50px' }}
              transition={{ duration: 0.5, delay: idx * 0.1 }}
              className="rounded-2xl overflow-hidden bg-white"
              style={{ border: `1px solid ${BRAND.border}` }}
            >
              <div className="p-6 flex items-center justify-between" style={{ background: BRAND.primary, color: '#fff' }}>
                <p className="font-serif-leamss text-2xl font-bold">{c.flag} {c.country}</p>
                <Link to={`/atlas/${c.code.toLowerCase()}`} className="text-xs hover:underline opacity-90">
                  Browse atlas →
                </Link>
              </div>
              <div className="p-5 space-y-4">
                {c.pathways.map((p, i) => (
                  <div key={i} className="border-b last:border-b-0 pb-4 last:pb-0" style={{ borderColor: BRAND.border }}>
                    <div className="flex items-start justify-between mb-2">
                      <p className="text-sm font-bold flex-1" style={{ color: BRAND.ink }}>{p.name}</p>
                      {p.highlight && <Pill color={BRAND.accent}>Popular</Pill>}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <CompareRow label="Min Points" value={p.pts} />
                      <CompareRow label="Age Limit"  value={p.age} />
                      <CompareRow label="English"    value={p.english} />
                      <CompareRow label="Processing" value={p.time} />
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>

        <p className="text-center text-xs mt-8" style={{ color: BRAND.muted }}>
          Want a side-by-side mathematical comparison with your specific profile? <Link to="/visa-compare" className="font-semibold underline" style={{ color: BRAND.primary }}>Use detailed Visa Compare tool →</Link>
        </p>
      </div>
    </section>
  );
}

const CompareRow = ({ label, value }) => (
  <div>
    <p className="text-[10px] uppercase font-bold tracking-wider" style={{ color: BRAND.muted }}>{label}</p>
    <p className="font-medium mt-0.5" style={{ color: BRAND.ink }}>{value}</p>
  </div>
);

// ─── Featured Occupations ──────────────────────────────────────────────────
function FeaturedOccupationsSection() {
  const [items, setItems] = useState([]);
  useEffect(() => {
    axios.get(`${API}/public-atlas/featured`).then(r => setItems(r.data.items || [])).catch(() => {});
  }, []);
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

function SocialProofSection() {
  return (
    <section className="py-20">
      <div className="max-w-7xl mx-auto px-4">
        <SectionTitle eyebrow="Trusted by 80,000+ Indians" title="Real stories. Real outcomes."
          sub="From Mumbai to Sydney. Pune to Toronto. Delhi to Auckland. Here's what our clients say." />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="testimonials-grid">
          {TESTIMONIALS.map((t, i) => (
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

function FAQSection() {
  return (
    <section className="py-20" style={{ background: BRAND.bgWarm }}>
      <div className="max-w-3xl mx-auto px-4">
        <SectionTitle eyebrow="FAQ" title="Quick answers to common migration questions" />
        <Accordion type="single" collapsible className="space-y-2" data-testid="faq-accordion">
          {FAQS.map((f, i) => (
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
