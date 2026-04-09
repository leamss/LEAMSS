import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, Play, CheckCircle, Upload, Eye, MessageCircle, ArrowRightLeft, StickyNote, Plus, Clock, AlertTriangle } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const iconMap = {
  play: Play, check: CheckCircle, upload: Upload, eye: Eye,
  message: MessageCircle, transfer: ArrowRightLeft, note: StickyNote,
  plus: Plus, clock: Clock
};

const colorMap = {
  blue: 'bg-blue-100 text-blue-600 border-blue-200',
  green: 'bg-green-100 text-green-600 border-green-200',
  red: 'bg-red-100 text-red-600 border-red-200',
  purple: 'bg-purple-100 text-purple-600 border-purple-200',
  teal: 'bg-teal-100 text-teal-600 border-teal-200',
  orange: 'bg-orange-100 text-orange-600 border-orange-200',
  yellow: 'bg-yellow-100 text-yellow-600 border-yellow-200',
  amber: 'bg-amber-100 text-amber-600 border-amber-200',
};

export default function CaseTimeline({ caseId, token }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => { if (caseId) fetchTimeline(); }, [caseId]);

  const fetchTimeline = async () => {
    try {
      const res = await fetch(`${API}/api/timeline/case/${caseId}`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      setEvents(data.events || []);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const filtered = filter === 'all' ? events : events.filter(e => e.type.includes(filter));
  const types = [...new Set(events.map(e => e.type))];

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" /></div>;

  return (
    <div data-testid="case-timeline">
      {/* Filter chips */}
      <div className="flex gap-2 mb-6 flex-wrap">
        <Badge variant={filter === 'all' ? 'default' : 'outline'} className="cursor-pointer" onClick={() => setFilter('all')}>All ({events.length})</Badge>
        {types.map(t => (
          <Badge key={t} variant={filter === t ? 'default' : 'outline'} className="cursor-pointer text-xs" onClick={() => setFilter(t)}>
            {t.replace(/_/g, ' ')}
          </Badge>
        ))}
      </div>

      {/* Timeline */}
      <div className="relative">
        <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-200" />
        <div className="space-y-4">
          {filtered.map((event, i) => {
            const IconComp = iconMap[event.icon] || Plus;
            const colorClass = colorMap[event.color] || colorMap.blue;
            return (
              <div key={i} className="relative pl-14">
                <div className={`absolute left-3 w-7 h-7 rounded-full flex items-center justify-center border-2 ${colorClass}`}>
                  <IconComp className="w-3.5 h-3.5" />
                </div>
                <Card className="border-0 shadow-sm hover:shadow-md transition-shadow">
                  <CardContent className="py-3 px-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-medium text-sm">{event.title}</p>
                        {event.description && <p className="text-xs text-gray-500 mt-0.5">{event.description}</p>}
                      </div>
                      <span className="text-[10px] text-gray-400 whitespace-nowrap ml-3">
                        {event.timestamp ? new Date(event.timestamp).toLocaleDateString('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </div>
            );
          })}
        </div>
      </div>

      {filtered.length === 0 && (
        <Card><CardContent className="py-8 text-center text-gray-500"><Clock className="w-12 h-12 mx-auto mb-3 text-gray-300" /><p>No timeline events found.</p></CardContent></Card>
      )}
    </div>
  );
}
