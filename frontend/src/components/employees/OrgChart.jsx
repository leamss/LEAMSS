import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronRight, Network, Users } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DEPT_BORDERS = {
  admin: 'border-l-violet-500 bg-violet-50/40',
  sales: 'border-l-emerald-500 bg-emerald-50/40',
  marketing: 'border-l-orange-500 bg-orange-50/40',
  operations: 'border-l-cyan-500 bg-cyan-50/40',
  hr: 'border-l-pink-500 bg-pink-50/40',
  accounts: 'border-l-teal-500 bg-teal-50/40',
  it: 'border-l-slate-500 bg-slate-50/40',
  compliance: 'border-l-rose-500 bg-rose-50/40',
};

const Node = ({ user, depth, onSelect, expandedIds, toggle }) => {
  const hasKids = user.children && user.children.length > 0;
  const isExpanded = expandedIds.has(user.id);

  return (
    <div className="relative">
      {/* Connection line from parent */}
      {depth > 0 && (
        <div className="absolute -left-6 top-0 bottom-0 w-px bg-slate-200" />
      )}
      {depth > 0 && (
        <div className="absolute -left-6 top-7 w-6 h-px bg-slate-200" />
      )}

      <div className={`flex items-stretch gap-3 mb-2 ml-${depth > 0 ? '6' : '0'}`}>
        <div className={`flex-1 border-l-4 ${DEPT_BORDERS[user.department] || 'border-l-slate-300'} bg-white rounded-md shadow-sm hover:shadow-md transition-all`} data-testid={`org-node-${user.id}`}>
          <div className="flex items-center gap-3 p-3">
            {hasKids && (
              <button onClick={() => toggle(user.id)} className="p-1 hover:bg-slate-100 rounded" data-testid={`toggle-${user.id}`}>
                {isExpanded ? <ChevronDown className="h-4 w-4 text-slate-500" /> : <ChevronRight className="h-4 w-4 text-slate-500" />}
              </button>
            )}
            {!hasKids && <div className="w-6" />}

            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-teal-500 to-indigo-600 flex items-center justify-center text-white font-semibold text-sm flex-shrink-0">
              {(user.name || '?').charAt(0).toUpperCase()}
            </div>

            <div className="flex-1 min-w-0 cursor-pointer" onClick={() => onSelect(user.id)}>
              <div className="flex items-center gap-2 flex-wrap">
                <p className="font-semibold text-slate-800 text-sm">{user.name}</p>
                <Badge variant="outline" className="text-[10px] font-mono">{user.employee_id || '—'}</Badge>
                {user.employment_status === 'on_leave' && <Badge className="bg-amber-100 text-amber-700 text-[10px]">on leave</Badge>}
              </div>
              <p className="text-xs text-slate-500 mt-0.5 truncate">{user.designation || user.rbac_role} · {user.department || '—'}</p>
            </div>

            {hasKids && (
              <div className="flex items-center gap-1 text-xs text-slate-500">
                <Users className="h-3 w-3" /> {user.children.length}
              </div>
            )}
          </div>
        </div>
      </div>

      {hasKids && isExpanded && (
        <div className="ml-6 mt-2 space-y-2">
          {user.children.map(c => <Node key={c.id} user={c} depth={depth + 1} onSelect={onSelect} expandedIds={expandedIds} toggle={toggle} />)}
        </div>
      )}
    </div>
  );
};

export default function OrgChart({ onSelect }) {
  const [roots, setRoots] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [expandedIds, setExpandedIds] = useState(new Set());
  const token = localStorage.getItem('token');

  useEffect(() => {
    const load = async () => {
      try {
        const res = await axios.get(`${API}/employees/org-chart`, { headers: { Authorization: `Bearer ${token}` } });
        setRoots(res.data.roots || []);
        setTotal(res.data.total || 0);
        // Auto-expand all at first
        const allIds = new Set();
        const collect = (arr) => arr.forEach(n => { allIds.add(n.id); if (n.children) collect(n.children); });
        collect(res.data.roots || []);
        setExpandedIds(allIds);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [token]);

  const toggle = (id) => {
    setExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const expandAll = () => {
    const allIds = new Set();
    const collect = (arr) => arr.forEach(n => { allIds.add(n.id); if (n.children) collect(n.children); });
    collect(roots);
    setExpandedIds(allIds);
  };

  const collapseAll = () => setExpandedIds(new Set());

  return (
    <div className="space-y-6 p-6" data-testid="org-chart-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <Network className="h-7 w-7 text-teal-700" /> Organization Chart
          </h1>
          <p className="text-slate-500 mt-1 text-sm">{total} employees · {roots.length} top-level node{roots.length !== 1 ? 's' : ''}</p>
        </div>
        <div className="flex gap-2 text-sm">
          <button onClick={expandAll} className="px-3 py-1.5 text-teal-700 hover:bg-teal-50 rounded-md" data-testid="expand-all">Expand all</button>
          <button onClick={collapseAll} className="px-3 py-1.5 text-slate-600 hover:bg-slate-50 rounded-md" data-testid="collapse-all">Collapse all</button>
        </div>
      </div>

      <Card className="p-6">
        {loading ? (
          <div className="space-y-3">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-16 bg-slate-50 animate-pulse rounded" />)}</div>
        ) : roots.length === 0 ? (
          <div className="text-center py-12 text-slate-500">
            <Network className="h-10 w-10 mx-auto mb-3 text-slate-300" />
            <p>No employees yet — add some via the "Add Employee" form</p>
          </div>
        ) : (
          <div className="space-y-2" data-testid="org-tree">
            {roots.map(r => <Node key={r.id} user={r} depth={0} onSelect={onSelect} expandedIds={expandedIds} toggle={toggle} />)}
          </div>
        )}
      </Card>

      {/* Legend */}
      <Card className="p-4">
        <p className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-3">Legend — Department Colors</p>
        <div className="flex flex-wrap gap-3 text-xs">
          {Object.entries(DEPT_BORDERS).map(([key, cls]) => (
            <div key={key} className={`flex items-center gap-2 px-2 py-1 rounded border-l-4 ${cls}`}>
              <span className="capitalize text-slate-700 font-medium">{key}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
