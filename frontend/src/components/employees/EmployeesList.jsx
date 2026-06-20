import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Search, Download, Plus, Filter, Eye } from 'lucide-react';
import EmployeeDetailModal from './EmployeeDetailModal';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const STATUS_COLORS = {
  active: 'bg-emerald-100 text-emerald-700 border-emerald-300',
  on_leave: 'bg-amber-100 text-amber-700 border-amber-300',
  terminated: 'bg-rose-100 text-rose-700 border-rose-300',
  resigned: 'bg-slate-100 text-slate-700 border-slate-300',
};

const DEPT_COLORS = {
  admin: 'bg-leamss-red-100 text-leamss-red-700',
  sales: 'bg-emerald-100 text-emerald-700',
  marketing: 'bg-orange-100 text-orange-700',
  operations: 'bg-cyan-100 text-cyan-700',
  hr: 'bg-pink-100 text-pink-700',
  accounts: 'bg-teal-100 text-teal-700',
  it: 'bg-slate-100 text-slate-700',
  compliance: 'bg-rose-100 text-rose-700',
};

export default function EmployeesList({ initialFilter, onNavigate, onOpenDetail }) {
  const [employees, setEmployees] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState({
    department: initialFilter?.department || 'all',
    role: 'all',
    status: 'all',
  });
  const [selectedId, setSelectedId] = useState(initialFilter?.employeeId || null);
  const token = localStorage.getItem('token');

  const load = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.department !== 'all') params.append('department', filters.department);
      if (filters.role !== 'all') params.append('role', filters.role);
      if (filters.status !== 'all') params.append('status', filters.status);
      if (search) params.append('search', search);
      params.append('limit', '200');

      const [emps, depts, allRoles] = await Promise.all([
        axios.get(`${API}/employees?${params.toString()}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/departments`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/departments/_meta/roles`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      setEmployees(emps.data.items || []);
      setDepartments(depts.data);
      setRoles(allRoles.data);
    } catch (err) {
      console.error('Failed to load employees:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [filters, search]);

  const exportCSV = () => {
    const headers = ['Employee ID', 'Name', 'Email', 'Designation', 'Department', 'Role', 'Status', 'Date of Joining'];
    const rows = employees.map(u => [
      u.employee_id || '', u.name || '', u.email || '', u.designation || '',
      u.department || '', u.rbac_role || '', u.employment_status || '',
      u.date_of_joining ? new Date(u.date_of_joining).toLocaleDateString() : ''
    ]);
    const csv = [headers, ...rows].map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `employees-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 p-6" data-testid="employees-list-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">All Employees</h1>
          <p className="text-slate-500 mt-1 text-sm">{employees.length} {employees.length === 1 ? 'employee' : 'employees'} {filters.department !== 'all' && `in ${filters.department}`}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={exportCSV} data-testid="export-csv-btn"><Download className="h-4 w-4 mr-2" /> Export CSV</Button>
          <Button onClick={() => onNavigate('emp-add')} className="bg-teal-700 hover:bg-teal-800 text-white" data-testid="list-add-employee-btn"><Plus className="h-4 w-4 mr-2" /> Add Employee</Button>
        </div>
      </div>

      <Card className="p-4">
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input placeholder="Search by name, email, or employee ID..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" data-testid="employees-search" />
          </div>
          <Select value={filters.department} onValueChange={(v) => setFilters({ ...filters, department: v })}>
            <SelectTrigger className="w-44" data-testid="filter-dept"><Filter className="h-3 w-3 mr-1" /><SelectValue placeholder="Department" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Departments</SelectItem>
              {departments.map(d => <SelectItem key={d.key} value={d.key}>{d.name}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={filters.role} onValueChange={(v) => setFilters({ ...filters, role: v })}>
            <SelectTrigger className="w-44" data-testid="filter-role"><SelectValue placeholder="Role" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Roles</SelectItem>
              {roles.filter(r => filters.department === 'all' || r.department === filters.department).map(r => <SelectItem key={r.key} value={r.key}>{r.name}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={filters.status} onValueChange={(v) => setFilters({ ...filters, status: v })}>
            <SelectTrigger className="w-36" data-testid="filter-status"><SelectValue placeholder="Status" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="inactive">Inactive</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Card>

      <Card className="overflow-hidden">
        {loading ? (
          <div className="p-6 space-y-2">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-12 bg-slate-50 animate-pulse rounded" />)}</div>
        ) : employees.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <Filter className="h-8 w-8 mx-auto mb-2 text-slate-300" />
            <p>No employees match your filters</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-600">
                <tr>
                  <th className="text-left p-4 font-semibold">Employee</th>
                  <th className="text-left p-4 font-semibold">Designation</th>
                  <th className="text-left p-4 font-semibold">Department</th>
                  <th className="text-left p-4 font-semibold">Role</th>
                  <th className="text-left p-4 font-semibold">Status</th>
                  <th className="text-right p-4 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {employees.map(u => (
                  <tr key={u.id} className="hover:bg-slate-50 transition-colors cursor-pointer" onClick={() => setSelectedId(u.id)} data-testid={`emp-row-${u.id}`}>
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-teal-500 to-leamss-teal-600 flex items-center justify-center text-white font-semibold text-sm flex-shrink-0">
                          {(u.name || '?').charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-medium text-slate-800">{u.name}</p>
                          <p className="text-xs text-slate-500">{u.employee_id || '—'} · {u.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="p-4 text-slate-700">{u.designation || <span className="text-slate-400 italic">Not set</span>}</td>
                    <td className="p-4">
                      <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${DEPT_COLORS[u.department] || 'bg-slate-100 text-slate-700'}`}>{u.department || '—'}</span>
                    </td>
                    <td className="p-4 text-slate-700 font-mono text-xs">{u.rbac_role}</td>
                    <td className="p-4">
                      <Badge variant="outline" className={STATUS_COLORS[u.employment_status] || STATUS_COLORS.active}>{u.employment_status || 'active'}</Badge>
                    </td>
                    <td className="p-4 text-right">
                      <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); setSelectedId(u.id); }} data-testid={`view-emp-${u.id}`}><Eye className="h-3.5 w-3.5 mr-1" /> View</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {selectedId && (
        <EmployeeDetailModal
          employeeId={selectedId}
          onClose={() => setSelectedId(null)}
          onUpdated={() => { load(); }}
        />
      )}
    </div>
  );
}
