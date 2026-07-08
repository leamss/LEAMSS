import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Globe, ShieldCheck } from 'lucide-react';

// const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
// const API = `${BACKEND_URL}/api`;
const API = "http://127.0.0.1:8001/api";

const Login = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      const { token, user } = response.data;
      
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));
      
      toast.success('Login successful!');

      // Forced password change AFTER admin reset → block all routes
      if (user.must_change_password_on_next_login) {
        navigate('/force-change-password');
        return;
      }

      // Smart redirect — uses rbac_role primarily, falls back to legacy role
      const role = user.rbac_role || user.role;
      const fixedRoutes = {
        admin: '/admin',
        admin_owner: '/admin',
        partner: '/partner',
        case_manager: '/case-manager',
        client: '/client',
        // Phase 4A — Internal sales roles
        sales_executive: '/sales/dashboard',
        sr_sales_executive: '/sales/dashboard',
        sales_manager: '/sales/dashboard',
        sales_head: '/sales/dashboard',
        // Phase 4C.6 — External vendor portal
        vendor: '/vendor/dashboard',
      };
      navigate(fixedRoutes[role] || '/portal/welcome');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      <div 
        className="hidden lg:flex lg:w-1/2 bg-cover bg-center relative"
        style={{ backgroundImage: `url('https://images.unsplash.com/photo-1726533765275-a69cfd7f9897?crop=entropy&cs=srgb&fm=jpg&q=85')` }}
      >
        <div className="absolute inset-0 bg-slate-900/60" />
        <div className="relative z-10 flex flex-col justify-center p-12 text-white">
          <div className="bg-white/95 rounded-2xl p-4 inline-block mb-6 backdrop-blur-sm shadow-xl">
            <img src="/leamss-logo.png" alt="LEAMSS Logo" className="h-20 object-contain" />
          </div>
          <h1 className="text-3xl font-bold mb-4" style={{ fontFamily: 'Merriweather, serif' }}>
            Ladhani Education & Migration Services
          </h1>
          <p className="text-lg text-slate-200">
            Streamline your immigration and visa consulting process with our comprehensive management system.
          </p>
        </div>
      </div>

      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="flex items-center gap-2 mb-8">
            <ShieldCheck className="h-8 w-8 text-[#2a777a]" />
            <h2 className="text-2xl font-bold" style={{ fontFamily: 'Merriweather, serif' }}>Login</h2>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="email" data-testid="email-label">Email Address</Label>
              <Input
                id="email"
                type="email"
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                data-testid="email-input"
                className="h-11"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" data-testid="password-label">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                data-testid="password-input"
                className="h-11"
              />
            </div>

            <Button
              type="submit"
              disabled={loading}
              data-testid="login-button"
              className="w-full h-11 bg-[#2a777a] hover:bg-[#236466] text-white font-medium"
            >
              {loading ? 'Logging in...' : 'Login'}
            </Button>
          </form>

          <div className="mt-3 text-center">
            <a href="/forgot-password" className="text-xs text-slate-500 hover:text-[#2a777a] underline" data-testid="forgot-password-link">
              Forgot Password?
            </a>
          </div>

          <div className="mt-8 p-4 bg-[#2a777a]/10 border border-[#2a777a]/30 rounded-lg">
            <p className="text-sm text-slate-600 font-medium mb-2">Demo Credentials:</p>
            <p className="text-xs text-slate-500">Admin: admin@leamss.com / Admin@123</p>
            <p className="text-xs text-slate-500">Partner: partner@leamss.com / Partner@123</p>
            <p className="text-xs text-slate-500">Case Manager: manager@leamss.com / Manager@123</p>
            <p className="text-xs text-slate-500">Client: client@leamss.com / Client@123</p>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2 text-center">
            <a href="/eligibility" className="block bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-200 rounded-lg p-3 hover:shadow-md transition" data-testid="public-eligibility-link">
              <p className="text-xs font-bold text-amber-800">✨ AI Eligibility Score</p>
              <p className="text-[10px] text-amber-700 mt-0.5">90 sec · No login</p>
            </a>
            <a href="/visa-compare" className="block bg-gradient-to-br from-leamss-teal_50 to-leamss-teal_50 border border-leamss-teal_50 rounded-lg p-3 hover:shadow-md transition" data-testid="public-compare-link">
              <p className="text-xs font-bold text-leamss-teal">⚖️ Compare Visas</p>
              <p className="text-[10px] text-leamss-teal mt-0.5">Side-by-side · Free</p>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
