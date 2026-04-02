import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { 
  CreditCard, CheckCircle, XCircle, Clock, 
  IndianRupee, FileText, TrendingUp, Loader2
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Payment Button Component
export const PaymentButton = ({ 
  saleId, 
  caseId, 
  packageId, 
  amount, 
  label = "Pay Now",
  variant = "default",
  className = ""
}) => {
  const [loading, setLoading] = useState(false);
  const token = localStorage.getItem('token');

  const handlePayment = async () => {
    if (!token) {
      toast.error('Please login to continue');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(
        `${API_URL}/api/payments/checkout/session`,
        {
          sale_id: saleId,
          case_id: caseId,
          package_id: packageId,
          origin_url: window.location.origin
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      // Redirect to Stripe checkout
      window.location.href = response.data.checkout_url;
    } catch (error) {
      console.error('Payment error:', error);
      toast.error(error.response?.data?.detail || 'Payment failed');
    }
    setLoading(false);
  };

  return (
    <Button 
      onClick={handlePayment} 
      disabled={loading}
      variant={variant}
      className={className}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
      ) : (
        <CreditCard className="h-4 w-4 mr-2" />
      )}
      {label} {amount && `(₹${amount.toLocaleString()})`}
    </Button>
  );
};

// Payment Success Page
export const PaymentSuccess = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const token = localStorage.getItem('token');

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');

    if (sessionId && token) {
      checkPaymentStatus(sessionId);
    } else {
      setLoading(false);
    }
  }, [token]);

  const checkPaymentStatus = async (sessionId) => {
    try {
      const response = await axios.get(
        `${API_URL}/api/payments/checkout/status/${sessionId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setStatus(response.data);
    } catch (error) {
      console.error('Status check error:', error);
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-indigo-600 mx-auto mb-4" />
          <p className="text-gray-500">Verifying payment...</p>
        </div>
      </div>
    );
  }

  const isPaid = status?.status === 'paid';

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <Card className="w-full max-w-md">
        <CardContent className="pt-8 text-center">
          {isPaid ? (
            <>
              <div className="h-16 w-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="h-10 w-10 text-green-600" />
              </div>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">Payment Successful!</h1>
              <p className="text-gray-500 mb-6">
                Your payment of ₹{status?.amount?.toLocaleString()} has been received.
              </p>
              <div className="bg-gray-50 rounded-lg p-4 mb-6 text-left">
                <p className="text-sm text-gray-500 mb-1">Transaction ID</p>
                <p className="font-mono text-sm">{status?.session_id?.substring(0, 20)}...</p>
                {status?.paid_at && (
                  <>
                    <p className="text-sm text-gray-500 mt-3 mb-1">Paid on</p>
                    <p className="text-sm">{new Date(status.paid_at).toLocaleString()}</p>
                  </>
                )}
              </div>
            </>
          ) : (
            <>
              <div className="h-16 w-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Clock className="h-10 w-10 text-yellow-600" />
              </div>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">Payment Processing</h1>
              <p className="text-gray-500 mb-6">
                Your payment is being processed. Please wait a moment.
              </p>
            </>
          )}
          <Button onClick={() => window.location.href = '/'} className="w-full">
            Return to Dashboard
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};

// Payment Cancel Page
export const PaymentCancel = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <Card className="w-full max-w-md">
        <CardContent className="pt-8 text-center">
          <div className="h-16 w-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <XCircle className="h-10 w-10 text-red-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Payment Cancelled</h1>
          <p className="text-gray-500 mb-6">
            Your payment was cancelled. No charges have been made.
          </p>
          <div className="space-y-3">
            <Button onClick={() => window.history.back()} className="w-full">
              Try Again
            </Button>
            <Button variant="outline" onClick={() => window.location.href = '/'} className="w-full">
              Return to Dashboard
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// Payment History Component
export const PaymentHistory = () => {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/payments/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTransactions(response.data);
    } catch (error) {
      console.error('History fetch error:', error);
    }
    setLoading(false);
  };

  const getStatusBadge = (status) => {
    const styles = {
      paid: 'bg-green-100 text-green-700',
      pending: 'bg-yellow-100 text-yellow-700',
      initiated: 'bg-blue-100 text-blue-700',
      failed: 'bg-red-100 text-red-700',
      expired: 'bg-gray-100 text-gray-700',
      refunded: 'bg-purple-100 text-purple-700'
    };
    return `px-2 py-1 rounded-full text-xs font-medium ${styles[status] || styles.pending}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Payment History
        </CardTitle>
        <CardDescription>Your recent payment transactions</CardDescription>
      </CardHeader>
      <CardContent>
        {transactions.length > 0 ? (
          <div className="space-y-4">
            {transactions.map((tx) => (
              <div 
                key={tx.id} 
                className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center gap-4">
                  <div className="h-10 w-10 bg-indigo-100 rounded-full flex items-center justify-center">
                    <IndianRupee className="h-5 w-5 text-indigo-600" />
                  </div>
                  <div>
                    <p className="font-medium">
                      {tx.payment_type?.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </p>
                    <p className="text-sm text-gray-500">
                      {tx.created_at ? new Date(tx.created_at).toLocaleDateString() : '-'}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold">₹{tx.amount?.toLocaleString()}</p>
                  <span className={getStatusBadge(tx.status)}>
                    {tx.status?.toUpperCase()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <CreditCard className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>No payment history</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// Admin Payment Stats Component
export const PaymentStats = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/payments/stats`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setStats(response.data);
    } catch (error) {
      console.error('Stats fetch error:', error);
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Collected</p>
                <p className="text-2xl font-bold text-green-600">
                  ₹{stats.total_collected?.toLocaleString() || 0}
                </p>
              </div>
              <div className="h-12 w-12 bg-green-100 rounded-full flex items-center justify-center">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Pending Payments</p>
                <p className="text-2xl font-bold text-yellow-600">
                  ₹{stats.total_pending?.toLocaleString() || 0}
                </p>
              </div>
              <div className="h-12 w-12 bg-yellow-100 rounded-full flex items-center justify-center">
                <Clock className="h-6 w-6 text-yellow-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Success Rate</p>
                <p className="text-2xl font-bold">
                  {stats.status_breakdown?.paid && stats.status_breakdown
                    ? Math.round((stats.status_breakdown.paid / 
                        Object.values(stats.status_breakdown).reduce((a, b) => a + b, 0)) * 100)
                    : 0}%
                </p>
              </div>
              <div className="h-12 w-12 bg-indigo-100 rounded-full flex items-center justify-center">
                <TrendingUp className="h-6 w-6 text-indigo-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Transactions */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Transactions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {stats.recent_transactions?.map((tx) => (
              <div 
                key={tx.id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div>
                  <p className="font-medium">₹{tx.amount?.toLocaleString()}</p>
                  <p className="text-sm text-gray-500">
                    {tx.created_at ? new Date(tx.created_at).toLocaleString() : '-'}
                  </p>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  tx.status === 'paid' ? 'bg-green-100 text-green-700' :
                  tx.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {tx.status?.toUpperCase()}
                </span>
              </div>
            ))}
            {stats.recent_transactions?.length === 0 && (
              <p className="text-center text-gray-500 py-4">No recent transactions</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default { PaymentButton, PaymentSuccess, PaymentCancel, PaymentHistory, PaymentStats };
