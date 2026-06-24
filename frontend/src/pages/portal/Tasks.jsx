import { useEffect, useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Plus, ArrowLeft, MessageSquare, Clock, AlertCircle,
  CheckSquare, Filter, History,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const STATUS_COLUMNS = [
  { id: 'todo', label: 'To Do', accent: 'bg-slate-100 border-slate-300', dot: 'bg-slate-400' },
  { id: 'in_progress', label: 'In Progress', accent: 'bg-leamss-teal-50 border-leamss-teal-300', dot: 'bg-leamss-teal-500' },
  { id: 'review', label: 'Review', accent: 'bg-amber-50 border-amber-300', dot: 'bg-amber-500' },
  { id: 'done', label: 'Done', accent: 'bg-emerald-50 border-emerald-300', dot: 'bg-emerald-500' },
  { id: 'blocked', label: 'Blocked', accent: 'bg-leamss-red-50 border-leamss-red-300', dot: 'bg-leamss-red-500' },
];

const PRIORITY_COLORS = {
  low: 'bg-slate-100 text-slate-600',
  medium: 'bg-sky-100 text-sky-700',
  high: 'bg-leamss-orange-100 text-leamss-orange-700',
  urgent: 'bg-leamss-red-100 text-leamss-red-700',
};

const formatDate = d => d ? new Date(d).toLocaleDateString(undefined, { day: '2-digit', month: 'short' }) : '—';
const isOverdue = (due, status) => due && status !== 'done' && new Date(due) < new Date(new Date().toDateString());

// ────────────────── Task Card ──────────────────
const TaskCard = ({ task, onClick }) => {
  const overdue = isOverdue(task.due_date, task.status);
  return (
    <Card
      onClick={onClick}
      className="p-3 cursor-pointer hover:shadow-md transition-all bg-white"
      draggable
      onDragStart={e => e.dataTransfer.setData('taskId', task.id)}
      data-testid={`task-card-${task.id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-slate-800 leading-tight flex-1">{task.title}</p>
        <Badge className={`${PRIORITY_COLORS[task.priority] || PRIORITY_COLORS.medium} text-[10px] capitalize px-1.5`}>
          {task.priority}
        </Badge>
      </div>
      {task.description && (
        <p className="text-xs text-slate-500 line-clamp-2 mt-1.5">{task.description}</p>
      )}
      <div className="flex items-center gap-2 mt-2 flex-wrap">
        {task.tags?.slice(0, 3).map(t => (
          <Badge key={t} variant="outline" className="text-[10px] py-0">{t}</Badge>
        ))}
      </div>
      <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-100">
        <div className="flex items-center gap-2">
          {task.assignee && (
            <div className="h-5 w-5 rounded-full bg-gradient-to-br from-leamss-teal-500 to-leamss-teal-700 text-white text-[10px] flex items-center justify-center font-semibold">
              {(task.assignee.name || '?').charAt(0).toUpperCase()}
            </div>
          )}
          {task.comment_count > 0 && (
            <span className="text-[10px] text-slate-500 inline-flex items-center gap-0.5">
              <MessageSquare className="h-3 w-3" /> {task.comment_count}
            </span>
          )}
        </div>
        <span className={`text-[10px] inline-flex items-center gap-0.5 ${overdue ? 'text-leamss-red-600 font-semibold' : 'text-slate-500'}`}>
          {overdue ? <AlertCircle className="h-3 w-3" /> : <Clock className="h-3 w-3" />}
          {formatDate(task.due_date)}
        </span>
      </div>
    </Card>
  );
};

// ────────────────── Task Detail Modal ──────────────────
const TaskDetailModal = ({ task, open, onClose, onSave, onComment, canEdit }) => {
  const [draft, setDraft] = useState(task || {});
  const [commentText, setCommentText] = useState('');
  useEffect(() => { setDraft(task || {}); setCommentText(''); }, [task]);

  if (!task) return null;

  const handleSave = async () => {
    const changes = {};
    ['title', 'description', 'priority', 'assignee_id', 'due_date', 'status'].forEach(k => {
      if (draft[k] !== task[k]) changes[k] = draft[k];
    });
    if (Object.keys(changes).length === 0) { onClose(); return; }
    await onSave(task.id, changes);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="task-detail-modal">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckSquare className="h-4 w-4 text-leamss-teal-600" />
            <Input
              value={draft.title || ''}
              onChange={e => setDraft({ ...draft, title: e.target.value })}
              disabled={!canEdit}
              className="text-lg font-semibold border-0 focus-visible:ring-0 px-1 h-auto"
              data-testid="task-edit-title"
            />
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <Label className="text-xs">Status</Label>
              <Select value={draft.status || 'todo'} onValueChange={v => setDraft({ ...draft, status: v })}>
                <SelectTrigger className="h-8 text-xs" data-testid="task-edit-status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STATUS_COLUMNS.map(c => (
                    <SelectItem key={c.id} value={c.id}>{c.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Priority</Label>
              <Select value={draft.priority || 'medium'} onValueChange={v => setDraft({ ...draft, priority: v })} disabled={!canEdit}>
                <SelectTrigger className="h-8 text-xs" data-testid="task-edit-priority">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {['low', 'medium', 'high', 'urgent'].map(p => (
                    <SelectItem key={p} value={p}>{p}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Due date</Label>
              <Input
                type="date"
                value={(draft.due_date || '').slice(0, 10)}
                onChange={e => setDraft({ ...draft, due_date: e.target.value })}
                disabled={!canEdit}
                className="h-8 text-xs"
                data-testid="task-edit-due-date"
              />
            </div>
            <div>
              <Label className="text-xs">Assignee</Label>
              <p className="text-xs font-medium text-slate-700 mt-1">{task.assignee?.name || '—'}</p>
            </div>
          </div>

          <div>
            <Label className="text-xs">Description</Label>
            <Textarea
              value={draft.description || ''}
              onChange={e => setDraft({ ...draft, description: e.target.value })}
              disabled={!canEdit}
              rows={4}
              data-testid="task-edit-description"
            />
          </div>

          <div>
            <Label className="text-xs font-semibold flex items-center gap-1"><MessageSquare className="h-3 w-3" /> Comments ({(task.comments || []).length})</Label>
            <div className="space-y-2 mt-2 max-h-40 overflow-y-auto pr-2">
              {(task.comments || []).map(c => (
                <div key={c.id} className="p-2 bg-slate-50 rounded text-xs border border-slate-100" data-testid={`comment-${c.id}`}>
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-800">{c.author_name}</span>
                    <span className="text-slate-400">{new Date(c.created_at).toLocaleString()}</span>
                  </div>
                  <p className="text-slate-700 mt-1 whitespace-pre-wrap">{c.text}</p>
                </div>
              ))}
              {(task.comments || []).length === 0 && <p className="text-xs text-slate-400 italic">No comments yet</p>}
            </div>
            <div className="flex gap-2 mt-2">
              <Input
                value={commentText}
                onChange={e => setCommentText(e.target.value)}
                placeholder="Add a comment…"
                className="text-xs"
                data-testid="task-comment-input"
              />
              <Button
                size="sm"
                variant="outline"
                onClick={async () => {
                  if (!commentText.trim()) return;
                  await onComment(task.id, commentText);
                  setCommentText('');
                }}
                data-testid="task-comment-submit"
              >
                Post
              </Button>
            </div>
          </div>

          {(task.audit_history || []).length > 0 && (
            <details className="text-xs text-slate-500">
              <summary className="cursor-pointer flex items-center gap-1"><History className="h-3 w-3" /> Audit history ({task.audit_history.length})</summary>
              <div className="mt-2 space-y-1 pl-4">
                {task.audit_history.slice().reverse().map((h, i) => (
                  <div key={i} className="text-[10px]">
                    <span className="font-semibold">{h.actor_name}</span> · {h.action} · <span className="text-slate-400">{new Date(h.timestamp).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </details>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} data-testid="task-modal-cancel">Close</Button>
          {canEdit && <Button onClick={handleSave} className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid="task-modal-save">Save changes</Button>}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ────────────────── New Task Dialog ──────────────────
const NewTaskDialog = ({ open, onClose, onCreate, employees, currentUserId, isManager }) => {
  const [form, setForm] = useState({
    title: '',
    description: '',
    assignee_id: currentUserId,
    priority: 'medium',
    status: 'todo',
    due_date: '',
    tags: '',
  });
  useEffect(() => {
    if (open) setForm({ title: '', description: '', assignee_id: currentUserId, priority: 'medium', status: 'todo', due_date: '', tags: '' });
  }, [open, currentUserId]);

  const submit = async () => {
    if (!form.title.trim()) { toast.error('Title is required'); return; }
    await onCreate({
      ...form,
      tags: form.tags ? form.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
    });
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg" data-testid="new-task-modal">
        <DialogHeader>
          <DialogTitle>New Task</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Title *</Label>
            <Input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="What needs to be done?" data-testid="new-task-title" />
          </div>
          <div>
            <Label>Description</Label>
            <Textarea rows={3} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} data-testid="new-task-description" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Assignee</Label>
              <Select value={form.assignee_id} onValueChange={v => setForm({ ...form, assignee_id: v })} disabled={!isManager}>
                <SelectTrigger data-testid="new-task-assignee"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(employees || []).map(e => (
                    <SelectItem key={e.id} value={e.id}>{e.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Priority</Label>
              <Select value={form.priority} onValueChange={v => setForm({ ...form, priority: v })}>
                <SelectTrigger data-testid="new-task-priority"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {['low', 'medium', 'high', 'urgent'].map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Status</Label>
              <Select value={form.status} onValueChange={v => setForm({ ...form, status: v })}>
                <SelectTrigger data-testid="new-task-status"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {STATUS_COLUMNS.map(s => <SelectItem key={s.id} value={s.id}>{s.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Due date</Label>
              <Input type="date" value={form.due_date} onChange={e => setForm({ ...form, due_date: e.target.value })} data-testid="new-task-due-date" />
            </div>
          </div>
          <div>
            <Label>Tags (comma-separated)</Label>
            <Input value={form.tags} onChange={e => setForm({ ...form, tags: e.target.value })} placeholder="frontend, urgent, q1" data-testid="new-task-tags" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={submit} className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid="new-task-create">Create task</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ────────────────── Main Tasks Page ──────────────────
export default function Tasks({ mode = 'me' }) {
  /** mode: 'me' for /portal/my-tasks (assignee=me), 'all' for /admin/employee-tasks */
  const navigate = useNavigate();
  const [tasks, setTasks] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTask, setActiveTask] = useState(null);
  const [newTaskOpen, setNewTaskOpen] = useState(false);
  const [filterPriority, setFilterPriority] = useState('all');
  const [filterAssignee, setFilterAssignee] = useState('all');

  const token = localStorage.getItem('token');
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const loadTasks = useCallback(async () => {
    const params = mode === 'me' ? { assignee_id: 'me' } : {};
    const { data } = await axios.get(`${API}/tasks`, { ...auth, params });
    setTasks(data);
  }, [mode, token]);

  const load = useCallback(async () => {
    try {
      const [me, emps] = await Promise.all([
        axios.get(`${API}/auth/me`, auth),
        axios.get(`${API}/employees?limit=200`, auth).catch(() => ({ data: [] })),
      ]);
      setCurrentUser(me.data);
      // /api/employees may return {employees: [...], pagination} OR raw array. Handle both.
      const empData = emps.data;
      const empList = Array.isArray(empData) ? empData : (empData?.employees || empData?.items || []);
      setEmployees(empList);
      await loadTasks();
    } catch (e) {
      navigate('/');
    } finally {
      setLoading(false);
    }
  }, [loadTasks, navigate, token]);

  useEffect(() => {
    if (!token) { navigate('/'); return; }
    load();
  }, [load, navigate, token]);

  const isManager = useMemo(() => {
    if (!currentUser) return false;
    const rbac = (currentUser.rbac_role || '').toLowerCase();
    const perms = currentUser.permissions || [];
    return perms.includes('*') || currentUser.role === 'admin' || ['admin', 'owner', 'head', 'manager', 'lead'].some(k => rbac.includes(k));
  }, [currentUser]);

  const filteredTasks = useMemo(() => {
    return tasks.filter(t => {
      if (filterPriority !== 'all' && t.priority !== filterPriority) return false;
      if (mode === 'all' && filterAssignee !== 'all' && t.assignee_id !== filterAssignee) return false;
      return true;
    });
  }, [tasks, filterPriority, filterAssignee, mode]);

  const handleDrop = async (e, columnId) => {
    e.preventDefault();
    const taskId = e.dataTransfer.getData('taskId');
    if (!taskId) return;
    const task = tasks.find(t => t.id === taskId);
    if (!task || task.status === columnId) return;
    try {
      await axios.patch(`${API}/tasks/${taskId}`, { status: columnId }, auth);
      toast.success(`Moved to ${STATUS_COLUMNS.find(s => s.id === columnId)?.label}`);
      loadTasks();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update');
    }
  };

  const handleSave = async (id, changes) => {
    try {
      await axios.patch(`${API}/tasks/${id}`, changes, auth);
      toast.success('Task saved');
      loadTasks();
    } catch (err) { toast.error(err.response?.data?.detail || 'Save failed'); }
  };
  const handleComment = async (id, text) => {
    try {
      await axios.post(`${API}/tasks/${id}/comments`, { text }, auth);
      const { data } = await axios.get(`${API}/tasks/${id}`, auth);
      setActiveTask(data);
      loadTasks();
    } catch (err) { toast.error(err.response?.data?.detail || 'Comment failed'); }
  };
  const handleCreate = async (form) => {
    try {
      await axios.post(`${API}/tasks`, form, auth);
      toast.success('Task created');
      loadTasks();
    } catch (err) { toast.error(err.response?.data?.detail || 'Create failed'); }
  };

  if (loading) return <div className="flex items-center justify-center h-screen text-slate-500">Loading tasks…</div>;

  return (
    <div className="min-h-screen bg-slate-50" data-testid={`tasks-page-${mode}`}>
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin/portal-hub')} data-testid="tasks-back-hub">
              <ArrowLeft className="h-4 w-4 mr-1.5" /> Hub
            </Button>
            <div>
              <h1 className="text-lg font-bold text-slate-900">{mode === 'me' ? 'My Tasks' : 'Employee Tasks'}</h1>
              <p className="text-xs text-slate-500">{tasks.length} total · drag cards between columns</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Select value={filterPriority} onValueChange={setFilterPriority}>
              <SelectTrigger className="h-8 text-xs w-32" data-testid="filter-priority">
                <Filter className="h-3 w-3 mr-1" /><SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All priorities</SelectItem>
                {['low', 'medium', 'high', 'urgent'].map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}
              </SelectContent>
            </Select>
            {mode === 'all' && (
              <Select value={filterAssignee} onValueChange={setFilterAssignee}>
                <SelectTrigger className="h-8 text-xs w-40" data-testid="filter-assignee">
                  <SelectValue placeholder="All assignees" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All assignees</SelectItem>
                  {employees.map(e => <SelectItem key={e.id} value={e.id}>{e.name}</SelectItem>)}
                </SelectContent>
              </Select>
            )}
            <Button onClick={() => setNewTaskOpen(true)} size="sm" className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid="new-task-btn">
              <Plus className="h-4 w-4 mr-1" /> New Task
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 md:px-6 py-6">
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-3" data-testid="kanban-board">
          {STATUS_COLUMNS.map(col => {
            const colTasks = filteredTasks.filter(t => t.status === col.id);
            return (
              <div
                key={col.id}
                onDragOver={e => e.preventDefault()}
                onDrop={e => handleDrop(e, col.id)}
                className={`rounded-lg border-2 border-dashed ${col.accent} p-3 min-h-[300px]`}
                data-testid={`kanban-column-${col.id}`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className={`h-2 w-2 rounded-full ${col.dot}`} />
                    <h3 className="text-sm font-bold text-slate-700">{col.label}</h3>
                  </div>
                  <Badge variant="outline" className="text-[10px] font-mono">{colTasks.length}</Badge>
                </div>
                <div className="space-y-2">
                  {colTasks.map(t => (
                    <TaskCard key={t.id} task={t} onClick={() => setActiveTask(t)} />
                  ))}
                  {colTasks.length === 0 && <p className="text-xs text-slate-400 italic text-center py-8">No tasks</p>}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <TaskDetailModal
        task={activeTask}
        open={!!activeTask}
        onClose={() => setActiveTask(null)}
        onSave={handleSave}
        onComment={handleComment}
        canEdit={isManager || activeTask?.assignee_id === currentUser?.id}
      />
      <NewTaskDialog
        open={newTaskOpen}
        onClose={() => setNewTaskOpen(false)}
        onCreate={handleCreate}
        employees={employees}
        currentUserId={currentUser?.id}
        isManager={isManager}
      />
    </div>
  );
}
