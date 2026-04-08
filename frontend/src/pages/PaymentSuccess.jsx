import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CheckCircle, Loader2, XCircle } from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const PaymentSuccess = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('checking');
  const [paymentData, setPaymentData] = useState(null);
  const sessionId = searchParams.get('session_id');

  useEffect(() => {
    if (!sessionId) { setStatus('error'); return; }
    let attempts = 0;
    const maxAttempts = 8;

    const pollStatus = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await axios.get(`${API}/payments/status/${sessionId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setPaymentData(res.data);

        if (res.data.payment_status === 'paid') {
          setStatus('success');
          return;
        } else if (res.data.status === 'expired') {
          setStatus('expired');
          return;
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(pollStatus, 2500);
        } else {
          setStatus('timeout');
        }
      } catch {
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(pollStatus, 2500);
        } else {
          setStatus('error');
        }
      }
    };

    pollStatus();
  }, [sessionId]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
      <Card className="max-w-md w-full p-8 text-center" data-testid="payment-result">
        {status === 'checking' && (
          <>
            <Loader2 className="h-16 w-16 text-[#2a777a] animate-spin mx-auto mb-4" />
            <h2 className="text-xl font-bold text-slate-800 mb-2">Verifying Payment...</h2>
            <p className="text-slate-500">Please wait while we confirm your payment.</p>
          </>
        )}
        {status === 'success' && (
          <>
            <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="h-10 w-10 text-emerald-600" />
            </div>
            <h2 className="text-2xl font-bold text-slate-800 mb-2">Payment Successful!</h2>
            <p className="text-slate-500 mb-1">Amount: ₹{(paymentData?.amount || 0).toLocaleString()}</p>
            <p className="text-sm text-slate-400 mb-6">Your payment has been processed successfully. Your case will be updated shortly.</p>
            <Button onClick={() => navigate('/')} className="bg-[#2a777a] hover:bg-[#236466] text-white w-full" data-testid="go-to-dashboard-btn">
              Go to Dashboard
            </Button>
          </>
        )}
        {(status === 'error' || status === 'timeout' || status === 'expired') && (
          <>
            <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <XCircle className="h-10 w-10 text-red-600" />
            </div>
            <h2 className="text-2xl font-bold text-slate-800 mb-2">
              {status === 'expired' ? 'Payment Expired' : 'Payment Issue'}
            </h2>
            <p className="text-slate-500 mb-6">
              {status === 'expired' ? 'Your payment session has expired. Please try again.' : 'We could not verify your payment. If money was deducted, it will be refunded automatically.'}
            </p>
            <Button onClick={() => navigate('/')} className="bg-[#2a777a] hover:bg-[#236466] text-white w-full" data-testid="go-back-btn">
              Back to Dashboard
            </Button>
          </>
        )}
      </Card>
    </div>
  );
};

export default PaymentSuccess;
