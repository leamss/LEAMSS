/**
 * Phase 6.10 Part 3 — Public Country Guide
 * Route: /countries/:code
 *
 * Public-facing read-only page that only renders VERIFIED guides.
 * Designed for SEO + lead-gen. No login required.
 */
import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, AlertCircle, Globe2, ShieldCheck, Mail, ChevronDown } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PublicCountryGuide() {
  const { code } = useParams();
  const [guide, setGuide] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [openFaq, setOpenFaq] = useState(0);

  useEffect(() => {
    axios.get(`${API}/country-guides/public/${code}`)
      .then(r => setGuide(r.data))
      .catch(e => setError(e.response?.data?.detail || 'Guide not found'))
      .finally(() => setLoading(false));
  }, [code]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-400" data-testid="public-guide-loading">
        <Loader2 className="h-6 w-6 animate-spin mr-2" />Loading guide…
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6" data-testid="public-guide-error">
        <Card className="max-w-md w-full p-8 text-center">
          <AlertCircle className="h-12 w-12 mx-auto mb-3 text-rose-500" />
          <h2 className="text-base font-bold mb-1">{error}</h2>
          <p className="text-xs text-slate-500 mb-4">
            The guide may not be published yet. Please check our other country pages.
          </p>
          <Link to="/countries" className="text-indigo-600 text-sm hover:underline">← Browse all countries</Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white" data-testid="public-guide-page">
      {/* HERO */}
      <header className="bg-gradient-to-br from-indigo-700 via-blue-700 to-cyan-600 text-white">
        <div className="max-w-5xl mx-auto px-6 py-12 md:py-16">
          <Link to="/" className="text-xs text-indigo-200 hover:underline mb-4 inline-block">
            ← LEAMSS Home
          </Link>
          <div className="flex items-center gap-3 mb-3">
            <Badge className="bg-emerald-500 text-white border-0" data-testid="verified-badge">
              <ShieldCheck className="h-3 w-3 mr-1" />Verified Guide
            </Badge>
            <span className="text-xs text-indigo-100">
              Last updated: {new Date(guide.updated_at).toLocaleDateString()}
            </span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-2" data-testid="hero-title">
            {guide.hero?.title || `${guide.flag} ${guide.name}`}
          </h1>
          <p className="text-base md:text-lg text-indigo-100 max-w-2xl" data-testid="hero-subtitle">
            {guide.hero?.subtitle || guide.tagline}
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <a href="#contact" className="bg-amber-400 hover:bg-amber-300 text-slate-900 px-5 py-2 rounded font-semibold text-sm transition"
               data-testid="hero-cta-contact">
              Talk to a Counsellor
            </a>
            <a href="/eligibility" className="border border-white/40 hover:bg-white/10 px-5 py-2 rounded font-semibold text-sm transition"
               data-testid="hero-cta-eligibility">
              Check Eligibility (Free)
            </a>
          </div>
        </div>
      </header>

      {/* SECTIONS */}
      <main className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {(guide.sections || []).map(s => (
          s.body_markdown ? (
            <section key={s.key} className="prose prose-slate max-w-none" data-testid={`section-${s.key}`}>
              <h2 className="text-2xl font-bold text-slate-800 mb-3 border-b pb-2">{s.title}</h2>
              <div className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
                {s.body_markdown}
              </div>
            </section>
          ) : null
        ))}

        {/* FAQ */}
        {guide.faq?.length > 0 && (
          <section data-testid="faq-section">
            <h2 className="text-2xl font-bold text-slate-800 mb-4 border-b pb-2">Frequently Asked Questions</h2>
            <div className="space-y-2">
              {guide.faq.map((f, i) => (
                <Card key={i} className="overflow-hidden" data-testid={`faq-item-${i}`}>
                  <button
                    onClick={() => setOpenFaq(openFaq === i ? -1 : i)}
                    className="w-full text-left px-4 py-3 flex items-center justify-between hover:bg-slate-50"
                  >
                    <span className="text-sm font-semibold text-slate-800">{f.question}</span>
                    <ChevronDown className={`h-4 w-4 text-slate-500 transition ${openFaq === i ? 'rotate-180' : ''}`} />
                  </button>
                  {openFaq === i && (
                    <div className="px-4 pb-4 text-sm text-slate-600 leading-relaxed">
                      {f.answer}
                    </div>
                  )}
                </Card>
              ))}
            </div>
          </section>
        )}

        {/* CONTACT */}
        <section id="contact" className="bg-slate-900 text-white rounded-lg p-6 md:p-8" data-testid="contact-section">
          <div className="flex items-center gap-3 mb-3">
            <Mail className="h-6 w-6 text-amber-300" />
            <h3 className="text-xl font-bold">Ready to start your {guide.name} journey?</h3>
          </div>
          <p className="text-sm text-slate-300 mb-4">
            Book a free consultation with our certified migration counsellors.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div>
              <p className="text-slate-400">Website</p>
              <p className="font-mono">www.leamss.com</p>
            </div>
            <div>
              <p className="text-slate-400">Email</p>
              <p className="font-mono">rohit@leamss.com</p>
            </div>
            <div>
              <p className="text-slate-400">Phone</p>
              <p className="font-mono">1800-210-2427</p>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-slate-100 border-t py-4 text-center text-xs text-slate-500">
        © Ladhani Education &amp; Migration Services Pvt. Ltd. · We Value Emotions
      </footer>
    </div>
  );
}
