/**
 * Phase 6.10 Part 3 — Public Country Index
 * Route: /countries
 *
 * Lists all VERIFIED country guides as cards. Public-facing landing.
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Loader2, ArrowRight, Globe2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PublicCountryIndex() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/country-guides/public`)
      .then(r => setItems(r.data.items || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white" data-testid="public-countries-index">
      <header className="bg-gradient-to-br from-indigo-700 via-blue-700 to-cyan-600 text-white">
        <div className="max-w-5xl mx-auto px-6 py-12">
          <Link to="/" className="text-xs text-indigo-200 hover:underline mb-4 inline-block">← LEAMSS Home</Link>
          <h1 className="text-4xl font-bold mb-2 flex items-center gap-3">
            <Globe2 className="h-9 w-9" />Where would you like to migrate?
          </h1>
          <p className="text-indigo-100 max-w-2xl">
            Browse verified country guides crafted by our migration experts. Each guide covers PR pathways, eligibility, fees, and timelines.
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10">
        {loading ? (
          <div className="flex items-center justify-center py-20 text-slate-400">
            <Loader2 className="h-6 w-6 animate-spin mr-2" />Loading countries…
          </div>
        ) : items.length === 0 ? (
          <Card className="p-10 text-center">
            <p className="text-slate-500">No published country guides yet — check back soon.</p>
            <Link to="/eligibility" className="text-indigo-600 hover:underline text-sm mt-3 inline-block">
              Or check your eligibility directly →
            </Link>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {items.map(g => (
              <Link
                key={g.country_code}
                to={`/countries/${g.country_code}`}
                className="block"
                data-testid={`country-card-${g.country_code}`}
              >
                <Card className="p-5 hover:shadow-lg hover:-translate-y-1 transition border-l-4 border-indigo-500 h-full">
                  <div className="text-5xl mb-3">{g.flag}</div>
                  <h2 className="text-xl font-bold text-slate-800">{g.name}</h2>
                  <p className="text-xs text-slate-500 mt-1 mb-3 line-clamp-2">
                    {g.hero?.subtitle || g.tagline}
                  </p>
                  <span className="text-xs text-indigo-600 font-semibold flex items-center gap-1">
                    Read full guide <ArrowRight className="h-3 w-3" />
                  </span>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
