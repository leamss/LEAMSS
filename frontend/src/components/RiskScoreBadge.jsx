import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { Badge } from '@/components/ui/badge';
import { Brain, TrendingUp, TrendingDown } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function RiskScoreBadge({ paId, showFactors = false }) {
  const [risk, setRisk] = useState(null);
  const [loading, setLoading] = useState(true);

  const getAuth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const load = useCallback(async () => {
    if (!paId) return;
    try {
      setLoading(true);
      const r = await axios.get(`${API}/intelligence/risk/${paId}`, getAuth());
      setRisk(r.data);
    } catch (e) { /* silent */ }
    setLoading(false);
  }, [paId]);

  useEffect(() => { load(); }, [load]);

  if (loading || !risk) return null;

  const palette = risk.color === 'green'
    ? 'bg-emerald-100 text-emerald-700 border-emerald-200'
    : risk.color === 'amber'
    ? 'bg-amber-100 text-amber-700 border-amber-200'
    : 'bg-red-100 text-red-700 border-red-200';

  return (
    <div className="space-y-2" data-testid={`risk-badge-${paId}`}>
      <Badge className={`${palette} border h-6`}>
        <Brain className="h-3 w-3 mr-1" /> {risk.label} · {risk.score}/100
      </Badge>
      {showFactors && risk.factors?.length > 0 && (
        <div className="space-y-0.5 text-[10px]">
          {risk.factors.slice(0, 6).map((f, i) => {
            const pos = f.delta >= 0;
            const Icon = pos ? TrendingUp : TrendingDown;
            const text = f['+'] || f['-'];
            return (
              <div key={i} className={`flex items-center gap-1 ${pos ? 'text-emerald-700' : 'text-red-600'}`}>
                <Icon className="h-2.5 w-2.5" />
                <span>{text} ({pos ? '+' : ''}{f.delta})</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
