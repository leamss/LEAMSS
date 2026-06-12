/**
 * Phase 18.6 — Global Application Error Boundary.
 *
 * Wraps top-level route groups (`/sales/*`, `/admin/*`, …) so a render crash
 * inside one component renders a friendly fallback instead of the React dev
 * red-overlay or a fully blank app shell.
 *
 * Side-effect: POSTs the captured error to `POST /api/client-errors` so the
 * ops team can triage. Best-effort — swallows any reporting failure.
 *
 * React requires class components for error boundaries (no functional API).
 */
import React from 'react';
import axios from 'axios';
import { AlertTriangle, RotateCcw, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';

const BRAND = {
  forest: '#1F4D44',
  forestDark: '#173B34',
  burnt: '#D4633F',
  warm: '#FAFAF7',
  cream: '#F5F2EC',
};

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, componentStack: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    const componentStack = info?.componentStack || '';
    this.setState({ componentStack });

    // Best-effort report to backend. Swallow all failures so we don't
    // mask the original render error with a network error.
    try {
      const token = (typeof window !== 'undefined') ? window.localStorage.getItem('token') : null;
      if (!token) return;
      const route = (typeof window !== 'undefined' && window.location)
        ? `${window.location.pathname}${window.location.search}`.slice(0, 500)
        : '';
      axios.post(`${API}/client-errors`, {
        message: String(error?.message || error || 'Unknown error').slice(0, 500),
        stack: String(error?.stack || '').slice(0, 5000),
        componentStack: componentStack.slice(0, 5000),
        route,
        scope: this.props.scope || 'unknown',
        userAgent: (typeof navigator !== 'undefined' ? navigator.userAgent : '').slice(0, 300),
        timestamp: new Date().toISOString(),
      }, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 5000,
      }).catch(() => { /* ignore */ });
    } catch {
      /* ignore */
    }
  }

  handleReload = () => {
    if (typeof window !== 'undefined') {
      // Phase 18.6 — clear the dev crash flag before reload so the user can
      // escape a forced-crash test cycle with a single click.
      try { window.localStorage.removeItem('__leamss_force_crash__'); } catch { /* ignore */ }
      window.location.reload();
    }
  };

  handleHome = () => {
    if (typeof window !== 'undefined') window.location.assign('/');
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    const isDev = process.env.NODE_ENV !== 'production';
    const msg = String(this.state.error?.message || this.state.error || 'Unknown error');

    return (
      <div
        className="min-h-screen flex items-center justify-center p-6"
        style={{ background: BRAND.warm }}
        data-testid="error-boundary-fallback"
      >
        <div className="max-w-lg w-full rounded-2xl border border-slate-200 bg-white shadow-xl p-8 text-center" style={{ background: BRAND.cream }}>
          <div className="mx-auto rounded-full h-14 w-14 flex items-center justify-center mb-4" style={{ background: '#FFF1EB' }}>
            <AlertTriangle className="h-7 w-7" style={{ color: BRAND.burnt }} />
          </div>
          <h1 className="text-2xl font-bold mb-1" style={{ color: BRAND.forestDark, fontFamily: 'Georgia, serif' }}>
            Something went wrong here
          </h1>
          <p className="text-sm text-slate-600 mb-6">
            This section hit an unexpected error. We've already notified the team.
            You can try reloading the page, or head back to the home dashboard.
          </p>

          {isDev && (
            <div className="text-left mb-6 rounded-lg border border-rose-200 bg-rose-50 p-3 max-h-44 overflow-auto" data-testid="error-boundary-dev-detail">
              <p className="text-[10px] uppercase tracking-wider font-bold text-rose-700 mb-1">Dev detail</p>
              <p className="text-[11px] font-mono text-rose-900 break-words">{msg}</p>
              {this.state.componentStack && (
                <pre className="text-[10px] font-mono text-rose-700 mt-1 whitespace-pre-wrap">
                  {this.state.componentStack.split('\n').slice(0, 6).join('\n')}
                </pre>
              )}
            </div>
          )}

          <div className="flex gap-2 justify-center flex-wrap">
            <Button
              onClick={this.handleReload}
              className="text-white hover:opacity-90"
              style={{ background: BRAND.burnt }}
              data-testid="error-boundary-reload-btn"
            >
              <RotateCcw className="h-4 w-4 mr-1.5" />Reload page
            </Button>
            <Button
              variant="outline"
              onClick={this.handleHome}
              className="border-slate-300 text-slate-700"
              data-testid="error-boundary-home-btn"
            >
              <Home className="h-4 w-4 mr-1.5" />Back to Home
            </Button>
          </div>

          {this.props.scope && (
            <p className="text-[10px] text-slate-400 mt-5 uppercase tracking-wider">scope: {this.props.scope}</p>
          )}
        </div>
      </div>
    );
  }
}

export default AppErrorBoundary;
