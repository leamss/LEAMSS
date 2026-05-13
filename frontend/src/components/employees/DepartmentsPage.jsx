import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import {
  Shield, TrendingUp, Megaphone, Briefcase, Users, Receipt, Server, ScrollText,
  Building2, Pencil, ChevronRight, UserCheck
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ICONS = { Shield, TrendingUp, Megaphone, Briefcase, Users, Receipt, Server, ScrollText, Building2 };

export default function DepartmentsPage({ onNavigate }) {
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [allInternalEmps, setAllInternalEmps] = useState([]);
  const [editDept, setEditDept] = useState(null);
  const [editForm, setEditForm] = useState({ name: '', description: '', head_user_id: '' });
  const token = localStorage.getItem('token');

  const load = async () => {
    setLoading(true);
    try {
      const [d, e] = await Promise.all([
        axios.get(`${API}/departments`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/employees?limit=500`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      setDepartments(d.data);
      setAllInternalEmps(e.data.items || []);
    } catch (err) {
      console.error('Failed to load departments:', err);
      toast.error('Failed to load departments');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const openEdit = (dept) => {
    setEditDept(dept);
    setEditForm({
      name: dept.name || '',
      description: dept.description || '',
      head_user_id: dept.head_user_id || 'none',
    });
  };

  const saveEdit = async () => {
    try {
      const body = {
        name: editForm.name,
        description: editForm.description,
        head_user_id: editForm.head_user_id === 'none' ? null : editForm.head_user_id,
      };
      await axios.patch(`${API}/departments/${editDept.key}`, body, { headers: { Authorization: `Bearer ${token}` } });
      toast.success(`${editDept.name} updated`);
      setEditDept(null);
      load();
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to update department';
      toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
  };

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-6">
        {Array.from({ length: 8 }).map((_, i) => <Card key={i} className="h-44 animate-pulse bg-slate-50" />)}
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6" data-testid="departments-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Departments</h1>
          <p className="text-slate-500 mt-1 text-sm">{departments.length} departments · {allInternalEmps.length} total employees</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {departments.map(dept => {
          const Icon = ICONS[dept.icon] || Building2;
          return (
            <Card key={dept.key} className="p-5 hover:shadow-lg transition-all cursor-pointer group relative overflow-hidden" data-testid={`dept-card-${dept.key}`}>
              <div className="absolute top-0 right-0 w-24 h-24 rounded-full opacity-10 group-hover:opacity-20 transition-opacity" style={{ background: dept.color, transform: 'translate(30%, -30%)' }} />
              <div className="flex items-start justify-between relative">
                <div className="p-3 rounded-xl" style={{ background: `${dept.color}15` }}>
                  <Icon className="h-6 w-6" style={{ color: dept.color }} />
                </div>
                <button onClick={(e) => { e.stopPropagation(); openEdit(dept); }} className="p-1.5 rounded-md hover:bg-slate-100 opacity-0 group-hover:opacity-100 transition-opacity" data-testid={`edit-dept-${dept.key}`}>
                  <Pencil className="h-4 w-4 text-slate-500" />
                </button>
              </div>

              <div className="mt-4">
                <h3 className="font-bold text-slate-900 text-lg">{dept.name}</h3>
                <p className="text-xs text-slate-500 mt-1 line-clamp-2">{dept.description || 'No description'}</p>
              </div>

              <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-slate-400" />
                  <span className="text-sm font-medium text-slate-700">{dept.employee_count} {dept.employee_count === 1 ? 'member' : 'members'}</span>
                </div>
                <Badge variant="outline" className="text-xs" style={{ color: dept.color, borderColor: `${dept.color}40` }}>{dept.key}</Badge>
              </div>

              {dept.head ? (
                <div className="mt-3 flex items-center gap-2 text-xs text-slate-600 bg-slate-50 rounded-md p-2">
                  <UserCheck className="h-3.5 w-3.5 text-slate-400" />
                  <span className="font-medium truncate">{dept.head.name}</span>
                  <span className="text-slate-400 truncate">· {dept.head.designation || 'Head'}</span>
                </div>
              ) : (
                <div className="mt-3 text-xs text-slate-400 italic flex items-center gap-2">
                  <UserCheck className="h-3.5 w-3.5" /> No head assigned
                </div>
              )}

              <button onClick={() => onNavigate('emp-list', { department: dept.key })} className="mt-3 w-full text-xs text-teal-700 hover:underline flex items-center justify-center gap-1" data-testid={`view-dept-emps-${dept.key}`}>
                View employees <ChevronRight className="h-3 w-3" />
              </button>
            </Card>
          );
        })}
      </div>

      {/* Edit dept dialog */}
      <Dialog open={!!editDept} onOpenChange={(v) => !v && setEditDept(null)}>
        <DialogContent data-testid="edit-dept-dialog">
          <DialogHeader><DialogTitle>Edit {editDept?.name}</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Name</Label>
              <Input value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} data-testid="edit-dept-name" />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea rows={3} value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} data-testid="edit-dept-desc" />
            </div>
            <div>
              <Label>Department Head</Label>
              <Select value={editForm.head_user_id} onValueChange={(v) => setEditForm({ ...editForm, head_user_id: v })}>
                <SelectTrigger data-testid="edit-dept-head"><SelectValue placeholder="Select head..." /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No head assigned</SelectItem>
                  {allInternalEmps.filter(u => u.department === editDept?.key).map(u => (
                    <SelectItem key={u.id} value={u.id}>{u.name} ({u.designation || u.rbac_role})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDept(null)} data-testid="cancel-edit-dept">Cancel</Button>
            <Button onClick={saveEdit} className="bg-teal-700 hover:bg-teal-800 text-white" data-testid="save-edit-dept">Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
