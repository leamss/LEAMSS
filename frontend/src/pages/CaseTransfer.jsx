import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowRightLeft, UserCheck, Loader2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function CaseTransfer({ token, role }) {
  const [cases, setCases] = useState([]);
  const [cms, setCms] = useState([]);
  const [selectedCase, setSelectedCase] = useState('');
  const [targetCM, setTargetCM] = useState('');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [transfers, setTransfers] = useState([]);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [casesRes, usersRes] = await Promise.all([
        fetch(`${API}/api/cases`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API}/api/users`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      const casesData = await casesRes.json();
      setCases(Array.isArray(casesData) ? casesData.filter(c => c.status === 'active') : []);
      const usersData = await usersRes.json();
      setCms((Array.isArray(usersData) ? usersData : []).filter(u => u.role === 'case_manager' && u.status === 'active'));
    } catch (e) { console.error(e); }
  };

  const transferCase = async () => {
    if (!selectedCase || !targetCM) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/cases/transfer`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ case_id: selectedCase, to_case_manager_id: targetCM, reason })
      });
      const data = await res.json();
      setResult(data);
      setSelectedCase(''); setTargetCM(''); setReason('');
      fetchData();
      // Load transfer history for selected case
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const autoAssign = async (caseId) => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/cases/auto-assign`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ case_id: caseId })
      });
      const data = await res.json();
      setResult(data);
      fetchData();
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const loadHistory = async (caseId) => {
    try {
      const res = await fetch(`${API}/api/cases/transfer-history/${caseId}`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      setTransfers(Array.isArray(data) ? data : []);
    } catch (e) { console.error(e); }
  };

  return (
    <div className="space-y-6" data-testid="case-transfer">
      {result && (
        <Card className="border-green-200 bg-green-50">
          <CardContent className="pt-4"><p className="text-green-800 font-medium">{result.message}</p></CardContent>
        </Card>
      )}

      {/* Transfer Form */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Transfer Case</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <select className="border rounded-md p-2 text-sm" value={selectedCase} onChange={e => { setSelectedCase(e.target.value); if (e.target.value) loadHistory(e.target.value); }} data-testid="transfer-case-select">
              <option value="">Select Case</option>
              {cases.map(c => <option key={c.id} value={c.id}>{c.case_id} — {c.client_name}</option>)}
            </select>
            <select className="border rounded-md p-2 text-sm" value={targetCM} onChange={e => setTargetCM(e.target.value)} data-testid="transfer-cm-select">
              <option value="">Target Case Manager</option>
              {cms.map(cm => <option key={cm.id} value={cm.id}>{cm.name}</option>)}
            </select>
            <input type="text" placeholder="Reason for transfer" className="border rounded-md p-2 text-sm" value={reason} onChange={e => setReason(e.target.value)} data-testid="transfer-reason-input" />
          </div>
          <div className="flex gap-2">
            <Button onClick={transferCase} disabled={!selectedCase || !targetCM || loading} data-testid="transfer-btn">
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <ArrowRightLeft className="w-4 h-4 mr-2" />}
              Transfer Case
            </Button>
            {role === 'admin' && selectedCase && (
              <Button variant="outline" onClick={() => autoAssign(selectedCase)} disabled={loading} data-testid="auto-assign-btn">
                <UserCheck className="w-4 h-4 mr-2" /> Auto-Assign
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Transfer History */}
      {transfers.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-lg">Transfer History</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-3">
              {transfers.map(t => (
                <div key={t.id} className="flex items-center gap-3 p-3 border rounded-lg bg-gray-50">
                  <ArrowRightLeft className="w-5 h-5 text-blue-500" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">{t.from_cm_name} → {t.to_cm_name}</p>
                    <p className="text-xs text-gray-500">By {t.transferred_by_name} — {t.reason || 'No reason'}</p>
                  </div>
                  <span className="text-xs text-gray-400">{new Date(t.created_at).toLocaleDateString()}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Case list with current CM */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Active Cases Assignment</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {cases.map(c => (
              <div key={c.id} className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50">
                <div>
                  <p className="font-medium text-sm">{c.case_id}</p>
                  <p className="text-xs text-gray-500">{c.client_name} — {c.product_name}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{c.case_manager_name || 'Unassigned'}</Badge>
                  {role === 'admin' && !c.case_manager_id && (
                    <Button size="sm" variant="outline" onClick={() => autoAssign(c.id)} data-testid={`auto-assign-${c.id}`}>
                      <UserCheck className="w-3 h-3 mr-1" /> Auto
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
