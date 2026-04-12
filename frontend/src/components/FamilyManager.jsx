import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Users, Plus, Edit, Trash2, User, CheckCircle, Loader2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const FamilyManager = ({ token }) => {
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialog, setDialog] = useState({ open: false, mode: 'add', data: { name: '', relationship: '', age: '', passport_number: '', date_of_birth: '', included_in_application: false, notes: '' } });
  const [saving, setSaving] = useState(false);

  const headers = { Authorization: `Bearer ${token}` };

  const loadMembers = async () => {
    try {
      const res = await axios.get(`${API}/client-tools/family/members`, { headers });
      setMembers(res.data || []);
    } catch (e) { /* no members */ }
    setLoading(false);
  };

  useEffect(() => { loadMembers(); }, []);

  const handleSave = async () => {
    if (!dialog.data.name || !dialog.data.relationship) {
      toast.error('Name and relationship are required');
      return;
    }
    setSaving(true);
    try {
      const payload = { ...dialog.data, age: parseInt(dialog.data.age) || 0 };
      if (dialog.mode === 'add') {
        await axios.post(`${API}/client-tools/family/add`, payload, { headers });
        toast.success(`${dialog.data.name} added`);
      } else {
        await axios.put(`${API}/client-tools/family/${dialog.data.id}`, payload, { headers });
        toast.success('Updated');
      }
      setDialog({ ...dialog, open: false });
      loadMembers();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed');
    }
    setSaving(false);
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Remove ${name}?`)) return;
    try {
      await axios.delete(`${API}/client-tools/family/${id}`, { headers });
      toast.success('Removed');
      loadMembers();
    } catch (e) {
      toast.error('Failed to remove');
    }
  };

  const relIcons = { spouse: 'ring', child: 'baby', parent: 'user', sibling: 'users' };
  const relColors = { spouse: 'bg-pink-100 text-pink-700 border-pink-200', child: 'bg-blue-100 text-blue-700 border-blue-200', parent: 'bg-amber-100 text-amber-700 border-amber-200', sibling: 'bg-purple-100 text-purple-700 border-purple-200' };

  if (loading) return <div className="flex items-center justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" /></div>;

  return (
    <div className="space-y-6" data-testid="family-manager">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5 text-[#2a777a]" />
          <h3 className="text-lg font-semibold text-slate-800">Family Members</h3>
          <Badge className="bg-slate-100 text-slate-700">{members.length}</Badge>
        </div>
        <Button onClick={() => setDialog({ open: true, mode: 'add', data: { name: '', relationship: '', age: '', passport_number: '', date_of_birth: '', included_in_application: false, notes: '' } })}
          className="bg-[#2a777a] hover:bg-[#236466] text-white" data-testid="add-family-btn">
          <Plus className="h-4 w-4 mr-1" />Add Member
        </Button>
      </div>

      {members.length === 0 ? (
        <Card className="p-12 text-center">
          <Users className="h-12 w-12 text-slate-300 mx-auto mb-4" />
          <p className="text-lg font-semibold text-slate-600">No Family Members Added</p>
          <p className="text-sm text-slate-400 mt-1">Add family members who may be included in your application</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {members.map((m, idx) => (
            <Card key={m.id} className="p-5 hover:shadow-md transition-shadow" data-testid={`family-member-${idx}`}>
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-full bg-slate-100"><User className="h-5 w-5 text-slate-600" /></div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-semibold text-slate-800">{m.name}</h4>
                      <Badge className={relColors[m.relationship] || 'bg-slate-100 text-slate-700'}>{m.relationship}</Badge>
                      {m.included_in_application && <Badge className="bg-emerald-100 text-emerald-700">In Application</Badge>}
                    </div>
                    {m.age > 0 && <p className="text-sm text-slate-500">Age: {m.age}</p>}
                    {m.passport_number && <p className="text-sm text-slate-500">Passport: {m.passport_number}</p>}
                    {m.date_of_birth && <p className="text-sm text-slate-500">DOB: {m.date_of_birth}</p>}
                    {m.notes && <p className="text-xs text-slate-400 mt-1">{m.notes}</p>}
                  </div>
                </div>
                <div className="flex gap-1">
                  <Button variant="outline" size="sm" onClick={() => setDialog({ open: true, mode: 'edit', data: m })} data-testid={`edit-member-${idx}`}><Edit className="h-4 w-4" /></Button>
                  <Button variant="destructive" size="sm" onClick={() => handleDelete(m.id, m.name)} data-testid={`delete-member-${idx}`}><Trash2 className="h-4 w-4" /></Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={dialog.open} onOpenChange={(o) => setDialog({ ...dialog, open: o })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{dialog.mode === 'add' ? 'Add' : 'Edit'} Family Member</DialogTitle>
            <DialogDescription>Enter details of your family member</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Full Name *</Label>
                <Input value={dialog.data.name} onChange={(e) => setDialog({ ...dialog, data: { ...dialog.data, name: e.target.value } })} data-testid="family-name-input" />
              </div>
              <div>
                <Label>Relationship *</Label>
                <Select value={dialog.data.relationship} onValueChange={(v) => setDialog({ ...dialog, data: { ...dialog.data, relationship: v } })}>
                  <SelectTrigger data-testid="family-rel-select"><SelectValue placeholder="Select" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="spouse">Spouse</SelectItem>
                    <SelectItem value="child">Child</SelectItem>
                    <SelectItem value="parent">Parent</SelectItem>
                    <SelectItem value="sibling">Sibling</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div><Label>Age</Label><Input type="number" value={dialog.data.age} onChange={(e) => setDialog({ ...dialog, data: { ...dialog.data, age: e.target.value } })} /></div>
              <div><Label>Date of Birth</Label><Input type="date" value={dialog.data.date_of_birth} onChange={(e) => setDialog({ ...dialog, data: { ...dialog.data, date_of_birth: e.target.value } })} /></div>
              <div><Label>Passport No.</Label><Input value={dialog.data.passport_number} onChange={(e) => setDialog({ ...dialog, data: { ...dialog.data, passport_number: e.target.value } })} /></div>
            </div>
            <div>
              <Label>Notes</Label>
              <Textarea value={dialog.data.notes} onChange={(e) => setDialog({ ...dialog, data: { ...dialog.data, notes: e.target.value } })} placeholder="Any additional details..." rows={2} />
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={dialog.data.included_in_application} onChange={(e) => setDialog({ ...dialog, data: { ...dialog.data, included_in_application: e.target.checked } })} className="rounded" data-testid="family-included-checkbox" />
              <span className="text-sm font-medium">Include in immigration application</span>
            </label>
            <div className="flex gap-3 justify-end">
              <Button variant="outline" onClick={() => setDialog({ ...dialog, open: false })}>Cancel</Button>
              <Button onClick={handleSave} disabled={saving} className="bg-[#2a777a] hover:bg-[#236466] text-white" data-testid="save-family-btn">
                {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                {dialog.mode === 'add' ? 'Add Member' : 'Save Changes'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default FamilyManager;
