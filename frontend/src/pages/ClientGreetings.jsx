import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { PartyPopper, Send, Loader2, History } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function ClientGreetings({ token }) {
  const [templates, setTemplates] = useState([]);
  const [history, setHistory] = useState([]);
  const [selected, setSelected] = useState(null);
  const [customMsg, setCustomMsg] = useState('');
  const [sendToAll, setSendToAll] = useState(true);
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState(null);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [tplRes, histRes] = await Promise.all([
        fetch(`${API}/api/greetings/templates`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API}/api/greetings/history`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      setTemplates(await tplRes.json());
      setHistory(await histRes.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const sendGreeting = async () => {
    setSending(true);
    try {
      const res = await fetch(`${API}/api/greetings/send`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          type: selected ? 'festival' : 'custom',
          template_name: selected || '',
          custom_message: customMsg,
          send_to_all_clients: sendToAll,
        })
      });
      const data = await res.json();
      setResult(data);
      setSelected(null); setCustomMsg('');
      fetchData();
    } catch (e) { console.error(e); }
    setSending(false);
  };

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" /></div>;

  return (
    <div className="space-y-6" data-testid="client-greetings">
      {result && (
        <Card className="border-green-200 bg-green-50"><CardContent className="pt-4"><p className="text-green-800 font-medium flex items-center gap-2"><PartyPopper className="w-5 h-5" /> {result.message}</p></CardContent></Card>
      )}

      {/* Festival Templates */}
      <Card>
        <CardHeader><CardTitle className="text-lg flex items-center gap-2"><PartyPopper className="w-5 h-5" /> Festival Greetings</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {templates.map(t => (
              <button key={t.name} onClick={() => { setSelected(t.name); setCustomMsg(t.message); }} className={`p-3 rounded-lg border-2 text-left transition-all ${selected === t.name ? 'border-[#2a777a] bg-[#2a777a]/5' : 'border-gray-200 hover:border-gray-300'}`} data-testid={`greeting-${t.name.toLowerCase()}`}>
                <p className="font-medium text-sm">{t.name}</p>
                <p className="text-xs text-gray-500 mt-1 line-clamp-2">{t.message.substring(0, 60)}...</p>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Custom Message */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Custom Message</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <textarea className="w-full border rounded-md p-2 text-sm" rows={3} placeholder="Write your greeting message..." value={customMsg} onChange={e => setCustomMsg(e.target.value)} data-testid="custom-greeting-msg" />
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={sendToAll} onChange={e => setSendToAll(e.target.checked)} /> Send to all active clients
            </label>
            <Button onClick={sendGreeting} disabled={!customMsg || sending} data-testid="send-greeting-btn">
              {sending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
              Send Greeting
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* History */}
      {history.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-sm flex items-center gap-2"><History className="w-4 h-4" /> Greeting History</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              {history.map(g => (
                <div key={g.id} className="flex items-center justify-between p-3 border rounded-lg bg-gray-50">
                  <div>
                    <p className="font-medium text-sm">{g.type === 'festival' ? g.template_name : 'Custom'} Greeting</p>
                    <p className="text-xs text-gray-500">By {g.sent_by_name} — {new Date(g.created_at).toLocaleDateString()}</p>
                  </div>
                  <Badge variant="outline">{g.recipients} recipients</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
