import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Globe, Package, Loader2, TrendingUp } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const countryFlags = { Canada: '🇨🇦', Australia: '🇦🇺', UK: '🇬🇧', USA: '🇺🇸', UAE: '🇦🇪', Germany: '🇩🇪', 'New Zealand': '🇳🇿', India: '🇮🇳', Other: '🌐' };

export default function CountryProductAnalytics({ token }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('country');

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const res = await fetch(`${API}/api/analytics/country-product`, { headers: { Authorization: `Bearer ${token}` } });
      setData(await res.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" /></div>;
  if (!data) return null;

  const countries = data.by_country || [];
  const products = data.by_product || [];
  const maxCases = Math.max(...(view === 'country' ? countries : products).map(i => i.total_cases), 1);

  return (
    <div className="space-y-6" data-testid="country-product-analytics">
      <div className="flex gap-2">
        <Badge variant={view === 'country' ? 'default' : 'outline'} className="cursor-pointer" onClick={() => setView('country')}>
          <Globe className="w-3 h-3 mr-1" /> By Country
        </Badge>
        <Badge variant={view === 'product' ? 'default' : 'outline'} className="cursor-pointer" onClick={() => setView('product')}>
          <Package className="w-3 h-3 mr-1" /> By Product
        </Badge>
      </div>

      {view === 'country' && (
        <div className="space-y-4">
          {countries.map(c => (
            <Card key={c.country} className="hover:shadow-sm transition-shadow">
              <CardContent className="pt-4">
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-2xl">{countryFlags[c.country] || '🌐'}</span>
                  <div className="flex-1">
                    <p className="font-medium">{c.country}</p>
                    <p className="text-xs text-gray-500">{c.products?.join(', ')}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-lg">{c.total_cases}</p>
                    <p className="text-xs text-gray-500">cases</p>
                  </div>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2 mb-2">
                  <div className="bg-[#2a777a] h-2 rounded-full transition-all" style={{ width: `${(c.total_cases / maxCases) * 100}%` }} />
                </div>
                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div><span className="font-bold text-blue-600">{c.active}</span> Active</div>
                  <div><span className="font-bold text-green-600">{c.completed}</span> Done</div>
                  <div><span className="font-bold text-purple-600">${c.revenue?.toLocaleString()}</span> Revenue</div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {view === 'product' && (
        <div className="space-y-3">
          {products.map(p => (
            <Card key={p.name} className="hover:shadow-sm transition-shadow">
              <CardContent className="pt-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="font-medium text-sm">{p.name}</p>
                  <Badge variant="outline">{p.total_cases} cases</Badge>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2 mb-2">
                  <div className="bg-[#f7620b] h-2 rounded-full transition-all" style={{ width: `${(p.total_cases / maxCases) * 100}%` }} />
                </div>
                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div><span className="font-bold text-blue-600">{p.active}</span> Active</div>
                  <div><span className="font-bold text-green-600">{p.completed}</span> Done</div>
                  <div><span className="font-bold text-purple-600">${p.revenue?.toLocaleString()}</span> Revenue</div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
