import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

/**
 * Route-level permission guard.
 *
 * Matches backend's PermissionService logic:
 *  - Owner wildcard `*` passes any check
 *  - Resource wildcards `pa.*` and `pa.view.*`
 *  - Hierarchy: all > dept > team > own (wider scope passes narrower)
 *
 * Usage:
 *   <RequirePermission anyOf={['employee.view.all', 'user.view.all']}>
 *     <AdminPage />
 *   </RequirePermission>
 *
 *   <RequirePermission anyOf={['*']} allowRoles={['admin_owner']}>
 *     <SuperAdminPage />
 *   </RequirePermission>
 */
const SCOPE_LEVEL = { all: 4, dept: 3, team: 2, own: 1, any: 4, pool: 2 };

function _hasPermission(perms, key) {
  if (!perms || perms.length === 0) return false;
  if (perms.includes('*')) return true;
  if (perms.includes(key)) return true;

  const parts = key.split('.');
  if (parts.length < 3) return false;
  const [resource, action, scope] = parts;

  if (perms.includes(`${resource}.*`) || perms.includes(`${resource}.${action}.*`)) return true;

  const required = SCOPE_LEVEL[scope] ?? 1;
  for (const p of perms) {
    const pp = p.split('.');
    if (pp.length < 3) continue;
    const [pr, pa, ps] = pp;
    if (pr !== resource || pa !== action) continue;
    if ((SCOPE_LEVEL[ps] ?? 0) >= required) return true;
  }
  return false;
}

function hasAnyPermission(user, keys) {
  return keys.some(k => _hasPermission(user.permissions, k));
}

export default function RequirePermission({ anyOf = [], allowRoles = [], children, fallback = '/portal/welcome' }) {
  const navigate = useNavigate();
  const [state, setState] = useState({ loading: true, allowed: false });

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/'); return; }

    const verify = async () => {
      try {
        const r = await axios.get(`${API}/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
        const user = r.data;
        const role = user.rbac_role || user.role;

        const roleAllowed = allowRoles.length > 0 && allowRoles.includes(role);
        const permAllowed = anyOf.length > 0 && hasAnyPermission(user, anyOf);

        if (roleAllowed || permAllowed) {
          setState({ loading: false, allowed: true });
        } else {
          toast.error("Access denied — you don't have permission for this page.");
          // Redirect to user's natural dashboard
          const fixed = { admin: '/admin', admin_owner: '/admin', partner: '/partner', case_manager: '/case-manager', client: '/client' };
          navigate(fixed[role] || fallback);
        }
      } catch {
        navigate('/');
      }
    };
    verify();
  }, [navigate, allowRoles, anyOf, fallback]);

  if (state.loading) {
    return <div className="min-h-screen flex items-center justify-center text-slate-500">Verifying access...</div>;
  }
  if (!state.allowed) return null;
  return children;
}
