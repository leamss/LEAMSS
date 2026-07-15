/**
 * Sales Leaderboard — ranks sales team members by target achievement %.
 * Read-only view for sales executives; managers/admins see the same data.
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Trophy, Medal, TrendingUp, IndianRupee, RefreshCw, Crown } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  if (num >= 1000) return `₹${(num / 1000).toFixed(1)}K`;
  return `₹${num.toLocaleString('en-IN')}`;
};

const RANK_STYLE = [
  { icon: Crown, color: 'text-amber-500', bg: 'bg-gradient-to-br from-amber-50 to-yellow-50', border: 'border-amber-300', ring: 'ring-2 ring-amber-300' },
  { icon: Medal, color: 'text-slate-400', bg: 'bg-gradient-to-br from-slate-50 to-slate-100', border: 'border-slate-300', ring: '' },
  { icon: Medal, color: 'text-amber-700', bg: 'bg-gradient-to-br from-orange-50 to-amber-50', border: 'border-orange-200', ring: '' },
];

const SalesLeaderboard = () => {
  const navigate = useNavigate();
  const [periodType, setPeriodType] = useState('monthly');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');

  const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/sales/targets/leaderboard`, {
        ...getAuthHeader(),
        params: { period_type: periodType, limit: 10 },
      });
      setData(res.data);
    } catch (e) {
      console.error('Failed to load leaderboard', e);
      setData(null);
    }
    setLoading(false);
  }, [periodType]);

  useEffect(() => { loadData(); }, [loadData]);

  const top = data?.top || [];
  const myEntry = top.find(t => t.user_id === currentUser.id);

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="bg-white border-b border-slate-200 px-4 sm:px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/portal/welcome')} className="p-2 rounded-lg hover:bg-slate-100 transition" data-testid="back-to-portal">
            <ArrowLeft className="h-5 w-5 text-slate-700" />
          </button>
          <div>
            <h1 className="text-lg font-bold text-slate-800 flex items-center gap-2">
              <Trophy className="h-5 w-5 text-amber-500" /> Sales Leaderboard
            </h1>
            <p className="text-xs text-slate-500">Ranked by target achievement %</p>
          </div>
        </div>
        <button onClick={loadData} className="text-sm text-[#2a777a] hover:underline flex items-center gap-1">
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </button>
      </div>

      <div className="p-4 sm:p-8 max-w-3xl mx-auto space-y-4">
        {/* Period toggle */}
        <div className="flex items-center bg-white border border-slate-200 rounded-lg p-1 w-fit">
          {['monthly', 'quarterly'].map(p => (
            <button
              key={p}
              onClick={() => setPeriodType(p)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium capitalize transition-colors ${periodType === p ? 'bg-[#2a777a] text-white' : 'text-slate-500 hover:text-slate-700'}`}
              data-testid={`period-${p}`}
            >
              {p}
            </button>
          ))}
        </div>

        {/* My rank summary */}
        {myEntry && (
          <Card className="p-4 bg-gradient-to-r from-[#2a777a] to-[#236466] text-white border-0">
            <p className="text-xs text-white/70">Your Rank</p>
            <div className="flex items-center justify-between mt-1">
              <p className="text-2xl font-bold">#{top.indexOf(myEntry) + 1} of {top.length}</p>
              <p className="text-lg font-semibold">{Math.round(myEntry.achievement?.overall_percentage || 0)}% achieved</p>
            </div>
          </Card>
        )}

        {loading ? (
          <div className="flex items-center justify-center h-40"><RefreshCw className="h-6 w-6 text-[#2a777a] animate-spin" /></div>
        ) : top.length === 0 ? (
          <Card className="p-10 text-center text-slate-500">
            <Trophy className="h-10 w-10 mx-auto mb-3 opacity-20" />
            <p className="text-sm font-medium">No leaderboard data for this period yet</p>
            <p className="text-xs mt-1">Rankings appear once sales targets are set and sales start coming in.</p>
          </Card>
        ) : (
          <div className="space-y-2">
            {top.map((entry, idx) => {
              const style = RANK_STYLE[idx] || { icon: TrendingUp, color: 'text-slate-400', bg: 'bg-white', border: 'border-slate-200', ring: '' };
              const RankIcon = style.icon;
              const pct = Math.round(entry.achievement?.overall_percentage || 0);
              const isMe = entry.user_id === currentUser.id;
              return (
                <Card
                  key={entry.id || idx}
                  className={`p-4 flex items-center gap-4 ${style.bg} ${style.border} ${style.ring} ${isMe ? 'ring-2 ring-[#2a777a]' : ''}`}
                  data-testid={`leaderboard-row-${idx}`}
                >
                  <div className="flex items-center justify-center w-10 h-10 flex-shrink-0">
                    {idx < 3 ? (
                      <RankIcon className={`h-7 w-7 ${style.color}`} />
                    ) : (
                      <span className="text-lg font-bold text-slate-400">#{idx + 1}</span>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm text-slate-800 truncate">
                      {entry.user_name || 'Sales Rep'} {isMe && <span className="text-xs text-[#2a777a]">(You)</span>}
                    </p>
                    <p className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                      <IndianRupee className="h-3 w-3" /> {formatINR(entry.achievement?.revenue)} of {formatINR(entry.targets?.revenue)}
                    </p>
                  </div>
                  <div className="text-right">
                    <Badge className={`text-sm font-bold ${pct >= 100 ? 'bg-emerald-100 text-emerald-700' : pct >= 50 ? 'bg-amber-100 text-amber-700' : 'bg-rose-100 text-rose-700'}`}>
                      {pct}%
                    </Badge>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default SalesLeaderboard;