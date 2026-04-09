import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CheckSquare, AlertTriangle, ArrowRight, Loader2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function BulkOperations({ token, role }) {
  const [cases, setCases] = useState([]);
  const [docs, setDocs] = useState([]);
  const [selectedCases, setSelectedCases] = useState([]);
  const [selectedDocs, setSelectedDocs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [tab, setTab] = useState('cases');

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [casesRes, docsRes] = await Promise.all([
        fetch(`${API}/api/cases`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API}/api/documents/case/all-pending`, { headers: { Authorization: `Bearer ${token}` } }).catch(() => null)
      ]);
      const casesData = await casesRes.json();
      setCases(Array.isArray(casesData) ? casesData.filter(c => c.status === 'active') : []);
      if (docsRes?.ok) {
        const docsData = await docsRes.json();
        setDocs(Array.isArray(docsData) ? docsData : []);
      }
    } catch (e) { console.error(e); }
  };

  const toggleCase = (id) => setSelectedCases(prev => prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]);
  const toggleDoc = (id) => setSelectedDocs(prev => prev.includes(id) ? prev.filter(d => d !== id) : [...prev, id]);

  const bulkAdvanceCases = async () => {
    if (!selectedCases.length) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/cases/bulk-advance`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ case_ids: selectedCases, notes: 'Bulk advanced' })
      });
      const data = await res.json();
      setResults({ type: 'advance', data });
      setSelectedCases([]);
      fetchData();
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const bulkReviewDocs = async (status) => {
    if (!selectedDocs.length) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/documents/bulk-review`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ document_ids: selectedDocs, status, comment: `Bulk ${status}` })
      });
      const data = await res.json();
      setResults({ type: 'review', data });
      setSelectedDocs([]);
      fetchData();
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  return (
    <div className="space-y-6" data-testid="bulk-operations">
      <div className="flex gap-2">
        <Button variant={tab === 'cases' ? 'default' : 'outline'} onClick={() => setTab('cases')} data-testid="bulk-tab-cases">
          <ArrowRight className="w-4 h-4 mr-2" /> Bulk Advance Cases
        </Button>
        <Button variant={tab === 'docs' ? 'default' : 'outline'} onClick={() => setTab('docs')} data-testid="bulk-tab-docs">
          <CheckSquare className="w-4 h-4 mr-2" /> Bulk Review Documents
        </Button>
      </div>

      {results && (
        <Card className="border-green-200 bg-green-50">
          <CardContent className="pt-4">
            <p className="font-medium text-green-800">
              {results.type === 'advance' ? `${results.data.advanced} cases advanced` : `${results.data.processed} documents processed`}
            </p>
          </CardContent>
        </Card>
      )}

      {tab === 'cases' && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Active Cases ({cases.length})</CardTitle>
            <Button onClick={bulkAdvanceCases} disabled={!selectedCases.length || loading} data-testid="bulk-advance-btn">
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <ArrowRight className="w-4 h-4 mr-2" />}
              Advance Selected ({selectedCases.length})
            </Button>
          </CardHeader>
          <CardContent>
            {cases.length === 0 ? <p className="text-gray-500 text-sm">No active cases</p> : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {cases.map(c => (
                  <div key={c.id} className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${selectedCases.includes(c.id) ? 'bg-blue-50 border-blue-300' : 'hover:bg-gray-50'}`} onClick={() => toggleCase(c.id)}>
                    <input type="checkbox" checked={selectedCases.includes(c.id)} onChange={() => toggleCase(c.id)} className="w-4 h-4" />
                    <div className="flex-1">
                      <p className="font-medium text-sm">{c.case_id}</p>
                      <p className="text-xs text-gray-500">{c.client_name} — Step: {c.current_step}</p>
                    </div>
                    <Badge variant="outline">{c.current_step_order || 0}/{c.total_steps || '?'}</Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {tab === 'docs' && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Pending Documents ({docs.length})</CardTitle>
            <div className="flex gap-2">
              <Button variant="default" onClick={() => bulkReviewDocs('approved')} disabled={!selectedDocs.length || loading} data-testid="bulk-approve-btn">
                {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CheckSquare className="w-4 h-4 mr-2" />}
                Approve ({selectedDocs.length})
              </Button>
              <Button variant="destructive" onClick={() => bulkReviewDocs('rejected')} disabled={!selectedDocs.length || loading} data-testid="bulk-reject-btn">
                Reject ({selectedDocs.length})
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {docs.length === 0 ? <p className="text-gray-500 text-sm">No pending documents. Documents awaiting review will appear here.</p> : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {docs.map(d => (
                  <div key={d.id} className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${selectedDocs.includes(d.id) ? 'bg-blue-50 border-blue-300' : 'hover:bg-gray-50'}`} onClick={() => toggleDoc(d.id)}>
                    <input type="checkbox" checked={selectedDocs.includes(d.id)} onChange={() => toggleDoc(d.id)} className="w-4 h-4" />
                    <div className="flex-1">
                      <p className="font-medium text-sm">{d.filename}</p>
                      <p className="text-xs text-gray-500">{d.document_type} — {d.uploaded_by_name || 'Unknown'}</p>
                    </div>
                    <Badge variant="secondary">{d.status}</Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
