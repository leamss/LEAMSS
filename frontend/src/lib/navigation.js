/**
 * Safe Navigation & Back Handler for LEAMSS Portal
 * Resolves cyclic back navigation loops and guarantees clean back navigation across all portal pages.
 */

/**
 * Returns the natural role-based dashboard route for the current user.
 * @param {Object} [user] - Optional user object. If omitted, reads from localStorage.
 * @returns {string} The dashboard route path.
 */
export function getRoleDashboard(user) {
  let currentUser = user;
  if (!currentUser) {
    try {
      currentUser = JSON.parse(localStorage.getItem('user') || '{}');
    } catch {
      currentUser = {};
    }
  }

  const role = (currentUser?.rbac_role || currentUser?.role || '').toLowerCase();

  // Admin roles
  if (['admin', 'admin_owner', 'super_admin'].includes(role)) {
    return '/admin';
  }

  // Sales roles
  if (['sales_executive', 'sr_sales_executive', 'sales_manager', 'sales_head', 'sales'].includes(role)) {
    return '/sales/my-crm';
  }

  // Partner
  if (role === 'partner') {
    return '/partner';
  }

  // Case manager
  if (role === 'case_manager') {
    return '/case-manager';
  }

  // Client
  if (role === 'client') {
    return '/client';
  }

  // Fallback default
  return '/portal/welcome';
}

/**
 * Performs a safe back navigation:
 * 1. Checks if the browser session history contains a previous entry within the SPA (idx > 0).
 * 2. If it does, calls navigate(-1) so that the user cleanly steps back in history.
 * 3. If there is no previous internal history entry (e.g. user refreshed or opened directly),
 *    navigates to fallbackPath (or the user's role dashboard) using replace to prevent trapping.
 *
 * @param {Function} navigate - The React Router navigate function.
 * @param {string} [fallbackPath] - Optional fallback route if no history exists.
 */
export function handleSafeBack(navigate, fallbackPath) {
  if (typeof navigate !== 'function') return;

  // React Router v6 assigns idx: 0 to the initial entry of the SPA in window.history.state.
  // idx > 0 guarantees there is a valid previous page inside this SPA session.
  const hasHistory =
    typeof window !== 'undefined' &&
    window.history &&
    typeof window.history.state?.idx === 'number' &&
    window.history.state.idx > 0;

  if (hasHistory) {
    navigate(-1);
  } else {
    const target = fallbackPath || getRoleDashboard();
    navigate(target, { replace: true });
  }
}
