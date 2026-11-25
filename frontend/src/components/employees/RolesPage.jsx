import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { 
  Shield, Plus, Search, Users, ArrowUpRight, 
  Layers, CheckCircle2, ChevronRight, Lock
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || (typeof window !== 'undefined' && window.location.hostname.includes('leamss.com') ? 'https://api.leamss.com' : 'http://localhost:8001');
const API = `${BACKEND_URL}/api`;

const DEPT_BADGES = {
  admin: 'bg-rose-50 text-rose-700 border-rose-200',
  sales: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  marketing: 'bg-orange-50 text-orange-700 border-orange-200',
  operations: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  hr: 'bg-pink-50 text-pink-700 border-pink-200',
  accounts: 'bg-sky-50 text-sky-700 border-sky-200',
  it: 'bg-slate-100 text-slate-800 border-slate-300',
  compliance: 'bg-purple-50 text-purple-700 border-purple-200',
};

const LEVEL_LABELS = {
  1: { label: 'L1 · Executive', color: 'bg-slate-100 text-slate-700' },
  2: { label: 'L2 · Specialist', color: 'bg-blue-50 text-blue-700' },
  3: { label: 'L3 · Lead / Manager', color: 'bg-amber-50 text-amber-700' },
  4: { label: 'L4 · Dept Head', color: 'bg-emerald-50 text-emerald-700' },
  5: { label: 'L5 · Executive Dir', color: 'bg-indigo-50 text-indigo-700' },
  6: { label: 'L6 · Owner / Board', color: 'bg-purple-50 text-purple-700' },
};

export default function RolesPage({ onNavigate }) {
  const [roles, setRoles] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [selectedDept, setSelectedDept] = useState('all');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  // Add role dialog state
  const [showAddModal, setShowAddModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    name: '',
    department: 'it',
    hierarchy_level: '2',
    description: '',
  });

  const token = localStorage.getItem('token');
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const loadData = async () => {
    setLoading(true);
    try {
      const [rRes, dRes] = await Promise.all([
        axios.get(`${API}/roles?hide_admin=false`, auth),
        axios.get(`${API}/departments`, auth),
      ]);
      setRoles(rRes.data || []);
      setDepartments(dRes.data || []);
    } catch (err) {
      console.error(err);
      toast.error('Failed to load roles');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleCreateRole = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) {
      toast.error('Role name is required');
      return;
    }
    setSubmitting(true);
    try {
      const res = await axios.post(`${API}/roles`, {
        name: form.name.trim(),
        department: form.department,
        hierarchy_level: Number(form.hierarchy_level) || 1,
        description: form.description || undefined,
      }, auth);
      toast.success(`Role '${res.data.name}' created successfully!`);
      setShowAddModal(false);
      setForm({ name: '', department: 'it', hierarchy_level: '2', description: '' });
      loadData();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to create role');
    } finally {
      setSubmitting(false);
    }
  };

  const filteredRoles = useMemo(() => {
    return roles.filter(r => {
      const matchDept = selectedDept === 'all' || r.department === selectedDept;
      const matchSearch = !search || 
        r.name?.toLowerCase().includes(search.toLowerCase()) ||
        r.key?.toLowerCase().includes(search.toLowerCase()) ||
        r.description?.toLowerCase().includes(search.toLowerCase());
      return matchDept && matchSearch;
    });
  }, [roles, selectedDept, search]);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6" data-testid="roles-page">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Shield className="h-6 w-6 text-teal-700" />
            Roles & Permissions
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Configure company job roles, hierarchy levels, and supervisory reporting structure.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button 
            onClick={() => setShowAddModal(true)} 
            className="bg-teal-700 hover:bg-teal-800 text-white shadow-sm flex items-center gap-2"
            data-testid="sidebar-add-role-btn"
          >
            <Plus className="h-4 w-4" /> Add Role
          </Button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <Card className="p-4 bg-white border-slate-200">
        <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
          {/* Department Filter Tabs */}
          <div className="flex items-center gap-1.5 flex-wrap w-full sm:w-auto">
            <button
              onClick={() => setSelectedDept('all')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                selectedDept === 'all' 
                  ? 'bg-teal-700 text-white shadow-sm' 
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              All Departments ({roles.length})
            </button>
            {departments.map(d => {
              const count = roles.filter(r => r.department === d.key).length;
              return (
                <button
                  key={d.key}
                  onClick={() => setSelectedDept(d.key)}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    selectedDept === d.key 
                      ? 'bg-teal-700 text-white shadow-sm' 
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {d.name} ({count})
                </button>
              );
            })}
          </div>

          {/* Search Box */}
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
            <Input
              type="text"
              placeholder="Search roles..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 text-xs h-8"
              data-testid="search-roles-input"
            />
          </div>
        </div>
      </Card>

      {/* Roles Grid */}
      {loading ? (
        <div className="p-12 text-center text-slate-400">Loading roles...</div>
      ) : filteredRoles.length === 0 ? (
        <Card className="p-12 text-center text-slate-400">
          <p className="text-sm font-medium">No roles found matching your filter</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredRoles.map(role => {
            const levelInfo = LEVEL_LABELS[role.hierarchy_level] || { label: `L${role.hierarchy_level}`, color: 'bg-slate-100' };
            const deptClass = DEPT_BADGES[role.department] || 'bg-slate-50 text-slate-700 border-slate-200';
            const deptName = departments.find(d => d.key === role.department)?.name || role.department || 'General';

            return (
              <Card key={role.key} className="p-5 border-slate-200 hover:shadow-md transition-shadow flex flex-col justify-between">
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div>
                      <h3 className="font-semibold text-slate-900 text-base">{role.name}</h3>
                      <p className="font-mono text-[11px] text-slate-400">{role.key}</p>
                    </div>
                    <Badge variant="outline" className={`text-xs px-2 py-0.5 capitalize border ${deptClass}`}>
                      {deptName}
                    </Badge>
                  </div>

                  <p className="text-xs text-slate-600 line-clamp-2 mt-2 mb-3">
                    {role.description || 'Standard departmental authorization profile.'}
                  </p>
                </div>

                <div className="pt-3 border-t border-slate-100 space-y-2 text-xs">
                  <div className="flex items-center justify-between text-slate-500">
                    <span>Hierarchy Level</span>
                    <span className={`px-2 py-0.5 rounded font-medium text-[11px] ${levelInfo.color}`}>
                      {levelInfo.label}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-slate-500">
                    <span>Reports To</span>
                    <span className="font-medium text-slate-700 truncate max-w-[150px]">
                      {role.reports_to_roles && role.reports_to_roles.length > 0 
                        ? role.reports_to_roles.join(', ')
                        : 'Top Level / Direct'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-slate-500">
                    <span>Permissions</span>
                    <span className="text-teal-700 font-semibold">
                      {role.permissions ? (role.permissions.includes('*') ? 'Full System (*)' : `${role.permissions.length} items`) : '0 items'}
                    </span>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Add Role Dialog Modal */}
      <Dialog open={showAddModal} onOpenChange={setShowAddModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-teal-700" />
              Add New Role
            </DialogTitle>
          </DialogHeader>

          <form onSubmit={handleCreateRole} className="space-y-4 py-2">
            <div>
              <Label>Role Name *</Label>
              <Input
                placeholder="e.g. QA Automation Engineer, Cloud Architect"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
                autoFocus
              />
            </div>

            <div>
              <Label>Department *</Label>
              <Select value={form.department} onValueChange={(v) => setForm({ ...form, department: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {departments.map(d => (
                    <SelectItem key={d.key} value={d.key}>{d.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Hierarchy Level *</Label>
              <Select value={form.hierarchy_level} onValueChange={(v) => setForm({ ...form, hierarchy_level: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">L1 — Entry / Executive (Reports to L2/L3)</SelectItem>
                  <SelectItem value="2">L2 — Specialist / Mid-Level (Reports to L3/L4)</SelectItem>
                  <SelectItem value="3">L3 — Lead / Manager (Can supervise team)</SelectItem>
                  <SelectItem value="4">L4 — Department Head (Reports to Top Admin)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Description (Optional)</Label>
              <Input
                placeholder="Key responsibilities and access scope"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>

            <DialogFooter className="mt-4 flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setShowAddModal(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={submitting} className="bg-teal-700 hover:bg-teal-800 text-white">
                {submitting ? 'Creating...' : 'Create Role'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
