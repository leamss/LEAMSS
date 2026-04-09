import { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Star, ThumbsUp, Users, TrendingUp } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function HappinessScoreWidget({ token }) {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch(`${API}/api/surveys/stats`, { headers: { Authorization: `Bearer ${token}` } });
        setStats(await res.json());
      } catch (e) { console.error(e); }
    };
    fetchStats();
  }, []);

  if (!stats || stats.total === 0) return null;

  const nps = stats.recommend_pct || 0;
  const npsColor = nps >= 70 ? 'text-green-500' : nps >= 40 ? 'text-amber-500' : 'text-red-500';
  const npsLabel = nps >= 70 ? 'Excellent' : nps >= 40 ? 'Good' : 'Needs Improvement';

  return (
    <Card className="bg-gradient-to-br from-white to-green-50/50 border border-green-100" data-testid="happiness-score-widget">
      <CardContent className="pt-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600 flex items-center gap-1.5">
              <ThumbsUp className="w-4 h-4 text-green-500" /> Client Happiness Score
            </p>
            <div className="flex items-baseline gap-2 mt-1">
              <span className={`text-3xl font-bold ${npsColor}`}>{nps}%</span>
              <span className="text-xs text-gray-500">{npsLabel}</span>
            </div>
          </div>
          <div className="text-right">
            <div className="flex items-center gap-1">
              {[1,2,3,4,5].map(i => (
                <Star key={i} className={`w-4 h-4 ${i <= Math.round(stats.avg_rating) ? 'text-yellow-400 fill-yellow-400' : 'text-gray-200'}`} />
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-1">{stats.avg_rating}/5 avg ({stats.total} reviews)</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
