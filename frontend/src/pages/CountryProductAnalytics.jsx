import { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Globe, Package, Loader2, Users, Download, ChevronDown, ChevronRight } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const countryFlags = { Canada: '🇨🇦', Australia: '🇦🇺', UK: '🇬🇧', USA: '🇺🇸', UAE: '🇦🇪', Germany: '🇩🇪', 'New Zealand': '🇳🇿', India: '🇮🇳', Singapore: '🇸🇬', Europe: '🇪🇺', Other: '🌐' };

export default function CountryProductAnalytics({ token }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('country');
  const [expanded, setExpanded] = useState(null);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const res = await fetch(`${API}/api/analytics/country-product`, { headers: { Authorization: `Bearer ${token}` } });
      setData(await res.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const downloadReport = () => {
    const items = view === 'country' ? (data?.by_country || []) : (data?.by_product || []);
    const rows = [['Name', 'Sales', 'Revenue (₹)', 'Received (₹)', 'Commission (₹)', 'Partner', 'Partner Sales', 'Partner Revenue (₹)']];
    items.forEach(item => {
      const name = view === 'country' ? item.country : item.name;
      if (item.partners?.length) {
        item.partners.forEach(p => {
          rows.push([name, item.total_sales, item.revenue, item.received || 0, item.commission || 0, p.name, p.sales, p.revenue]);
        });
      } else {
        rows.push([name, item.total_sales, item.revenue, item.received || 0, item.commission || 0, '-', '-', '-']);
      }
    });
    const csv = rows.map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${view}_analytics_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link); link.click(); link.remove();
  };

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" /></div>;
  if (!data) return null;

  const countries = data.by_country || [];
  const products = data.by_product || [];
  const items = view === 'country' ? countries : products;
  const maxRev = Math.max(...items.map(i => i.revenue || 0), 1);

  return (
    <div className="space-y-5" data-testid="country-product-analytics">
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <Button variant={view === 'country' ? 'default' : 'outline'} size="sm" onClick={() => { setView('country'); setExpanded(null); }}
            className={view === 'country' ? 'bg-[#2a777a] hover:bg-[#236466]' : ''} data-testid="view-country">
            <Globe className="w-4 h-4 mr-1" />By Country
          </Button>
          <Button variant={view === 'product' ? 'default' : 'outline'} size="sm" onClick={() => { setView('product'); setExpanded(null); }}
            className={view === 'product' ? 'bg-[#2a777a] hover:bg-[#236466]' : ''} data-testid="view-product">
            <Package className="w-4 h-4 mr-1" />By Product
          </Button>
        </div>
        <Button variant="outline" size="sm" onClick={downloadReport} data-testid="download-cp-report"><Download className="h-4 w-4 mr-1" />Export CSV</Button>
      </div>

      <div className="space-y-3">
        {items.map((item, idx) => {
          const name = view === 'country' ? item.country : item.name;
          const isExpanded = expanded === name;
          return (
            <Card key={name} className="overflow-hidden" data-testid={`cp-card-${idx}`}>
              <div className="p-4 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors" onClick={() => setExpanded(isExpanded ? null : name)}>
                <div className="flex items-center gap-3">
                  {isExpanded ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
                  {view === 'country' && <span className="text-xl">{countryFlags[name] || '🌐'}</span>}
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-semibold text-slate-800 dark:text-white">{name}</h4>
                      <Badge variant="outline" className="text-xs">{item.total_sales} sales</Badge>
                      {item.partners?.length > 0 && <Badge className="bg-slate-100 text-slate-600 text-xs"><Users className="h-3 w-3 mr-1" />{item.partners.length} partners</Badge>}
                    </div>
                    {view === 'country' && item.products?.length > 0 && (
                      <p className="text-xs text-slate-500 mt-0.5">{item.products.join(', ')}</p>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-[#2a777a]">₹{(item.revenue || 0).toLocaleString()}</p>
                    <p className="text-xs text-slate-500">Received: ₹{(item.received || 0).toLocaleString()}</p>
                  </div>
                </div>
                {/* Revenue bar */}
                <div className="w-full bg-slate-100 rounded-full h-2 mt-3">
                  <div className={`h-2 rounded-full transition-all ${view === 'country' ? 'bg-[#2a777a]' : 'bg-[#f7620b]'}`} style={{ width: `${(item.revenue / maxRev) * 100}%` }} />
                </div>
                <div className="grid grid-cols-3 gap-4 mt-2 text-xs text-center">
                  <div><span className="font-bold text-[#2a777a]">₹{(item.revenue || 0).toLocaleString()}</span><br/><span className="text-slate-500">Revenue</span></div>
                  <div><span className="font-bold text-emerald-600">₹{(item.received || 0).toLocaleString()}</span><br/><span className="text-slate-500">Received</span></div>
                  <div><span className="font-bold text-amber-600">₹{(item.commission || 0).toLocaleString()}</span><br/><span className="text-slate-500">Commission</span></div>
                </div>
              </div>

              {/* Partner Drill-down */}
              {isExpanded && item.partners?.length > 0 && (
                <div className="border-t bg-slate-50/50 dark:bg-slate-800/30 p-4">
                  <h5 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-1"><Users className="h-4 w-4" />Partner Breakdown</h5>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-xs text-slate-500">
                          <th className="text-left p-2">Partner</th>
                          <th className="text-right p-2">Sales</th>
                          <th className="text-right p-2">Revenue (₹)</th>
                          <th className="text-right p-2">Received (₹)</th>
                          <th className="text-right p-2">Commission (₹)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {item.partners.map((p, pi) => (
                          <tr key={pi} className="border-t" data-testid={`partner-drill-${idx}-${pi}`}>
                            <td className="p-2 font-medium text-slate-800 dark:text-white">{p.name}</td>
                            <td className="p-2 text-right">{p.sales}</td>
                            <td className="p-2 text-right font-semibold">₹{(p.revenue || 0).toLocaleString()}</td>
                            <td className="p-2 text-right text-emerald-600">₹{(p.received || 0).toLocaleString()}</td>
                            <td className="p-2 text-right text-amber-600">₹{(p.commission || 0).toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
