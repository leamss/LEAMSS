import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { 
  BarChart3, TrendingUp, Users, Package, Download, 
  FileText, PieChart, Activity, Calendar
} from 'lucide-react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AnalyticsDashboard = () => {
  const [salesTrend, setSalesTrend] = useState(null);
  const [salesByStatus, setSalesByStatus] = useState(null);
  const [topProducts, setTopProducts] = useState([]);
  const [topPartners, setTopPartners] = useState([]);
  const [monthlyRevenue, setMonthlyRevenue] = useState(null);
  const [caseCompletion, setCaseCompletion] = useState(null);
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('30');

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    fetchAnalytics();
  }, [period]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const [dashRes, trendRes, statusRes, productsRes, partnersRes, monthlyRes, completionRes] = await Promise.all([
        axios.get(`${API_URL}/api/analytics/dashboard?days=${period}`, { headers }).catch(() => ({ data: {} })),
        axios.get(`${API_URL}/api/analytics/sales-trend?days=${period}`, { headers }).catch(() => ({ data: { data: [] } })),
        axios.get(`${API_URL}/api/analytics/sales-by-status`, { headers }).catch(() => ({ data: { data: [] } })),
        axios.get(`${API_URL}/api/analytics/top-products`, { headers }).catch(() => ({ data: { data: [] } })),
        axios.get(`${API_URL}/api/analytics/top-partners`, { headers }).catch(() => ({ data: { data: [] } })),
        axios.get(`${API_URL}/api/analytics/monthly-revenue`, { headers }).catch(() => ({ data: { data: [] } })),
        axios.get(`${API_URL}/api/analytics/case-completion-rate`, { headers }).catch(() => ({ data: { rate: 0 } }))
      ]);

      setDashboardData(dashRes.data);
      setSalesTrend(trendRes.data);
      setSalesByStatus(statusRes.data);
      setTopProducts(productsRes.data);
      setTopPartners(partnersRes.data);
      setMonthlyRevenue(monthlyRes.data);
      setCaseCompletion(completionRes.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    }
    setLoading(false);
  };

  const exportReport = async (type, format) => {
    try {
      const response = await axios.get(`${API_URL}/api/export/${type}/${format}`, {
        headers,
        responseType: format === 'csv' ? 'blob' : 'text'
      });

      if (format === 'csv') {
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `${type}_report.csv`);
        document.body.appendChild(link);
        link.click();
        link.remove();
      } else {
        const win = window.open('', '_blank');
        win.document.write(response.data);
      }
    } catch (error) {
      console.error('Export error:', error);
    }
  };

  const statusColors = {
    pending: '#f59e0b',
    approved: '#22c55e',
    rejected: '#ef4444',
    active: '#3b82f6',
    completed: '#22c55e',
    on_hold: '#6b7280'
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-leamss-teal-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-4 md:p-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => window.history.back()} data-testid="analytics-back-btn">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Analytics Dashboard</h1>
            <p className="text-gray-500">Insights and performance metrics</p>
          </div>
        </div>
        <div className="flex gap-3">
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="Period" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Last 7 days</SelectItem>
              <SelectItem value="30">Last 30 days</SelectItem>
              <SelectItem value="90">Last 90 days</SelectItem>
              <SelectItem value="365">Last year</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={() => exportReport('sales', 'csv')}>
            <Download className="h-4 w-4 mr-2" />
            Export Sales
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Revenue</p>
                <p className="text-2xl font-bold">
                  ₹{(dashboardData?.total_revenue || salesTrend?.data?.reduce((a, b) => a + (b.revenue || 0), 0) || 0).toLocaleString()}
                </p>
              </div>
              <div className="h-12 w-12 bg-green-100 rounded-full flex items-center justify-center">
                <TrendingUp className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Commission</p>
                <p className="text-2xl font-bold">
                  ₹{(dashboardData?.total_commission || 0).toLocaleString()}
                </p>
              </div>
              <div className="h-12 w-12 bg-blue-100 rounded-full flex items-center justify-center">
                <BarChart3 className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Sales</p>
                <p className="text-2xl font-bold">
                  {dashboardData?.total_sales || salesTrend?.data?.reduce((a, b) => a + (b.count || 0), 0) || 0}
                </p>
              </div>
              <div className="h-12 w-12 bg-leamss-orange-100 rounded-full flex items-center justify-center">
                <FileText className="h-6 w-6 text-leamss-orange-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Completion Rate</p>
                <p className="text-2xl font-bold">
                  {dashboardData?.completion_rate || caseCompletion?.rate || 0}%
                </p>
              </div>
              <div className="h-12 w-12 bg-orange-100 rounded-full flex items-center justify-center">
                <Activity className="h-6 w-6 text-orange-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Sales by Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PieChart className="h-5 w-5" />
              Sales by Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {(salesByStatus?.data || []).map((item) => (
                <div key={item.status} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div 
                      className="w-3 h-3 rounded-full" 
                      style={{ backgroundColor: statusColors[item.status] || '#6b7280' }}
                    />
                    <span className="capitalize">{item.status}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="font-medium">{item.count}</span>
                    <span className="text-gray-500">
                      ₹{(item.total || 0).toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
              {(!salesByStatus?.data || salesByStatus.data.length === 0) && (
                <p className="text-sm text-gray-500 text-center">No data available</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Monthly Revenue */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Monthly Revenue {monthlyRevenue?.year}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {(monthlyRevenue?.data || []).map((item) => {
                const revenue = item.revenue || 0;
                const maxRevenue = Math.max(...(monthlyRevenue?.data || []).map(d => d.revenue || 0), 1);
                const width = maxRevenue > 0 ? (revenue / maxRevenue) * 100 : 0;
                
                return (
                  <div key={item.month} className="flex items-center gap-2">
                    <span className="w-16 text-xs text-gray-500">{item.month}</span>
                    <div className="flex-1 bg-gray-100 rounded h-4 overflow-hidden">
                      <div 
                        className="bg-leamss-teal-500 h-full rounded transition-all"
                        style={{ width: `${width}%` }}
                      />
                    </div>
                    <span className="w-24 text-xs text-right">
                      {revenue > 0 ? `₹${(revenue/1000).toFixed(0)}K` : '-'}
                    </span>
                  </div>
                );
              })}
              {(!monthlyRevenue?.data || monthlyRevenue.data.length === 0) && (
                <p className="text-sm text-gray-500 text-center">No data available</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Top Performers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Top Products */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Package className="h-5 w-5" />
              Top Products
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {(topProducts?.data || []).map((product, idx) => (
                <div key={idx} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-leamss-teal-100 rounded-full flex items-center justify-center text-leamss-teal-600 font-bold">
                      {idx + 1}
                    </div>
                    <div>
                      <p className="font-medium">{product.product_name}</p>
                      <p className="text-sm text-gray-500">{product.count} sales</p>
                    </div>
                  </div>
                  <p className="font-medium text-green-600">
                    ₹{(product.revenue || 0).toLocaleString()}
                  </p>
                </div>
              ))}
              {(!topProducts?.data || topProducts.data.length === 0) && (
                <p className="text-gray-500 text-center py-4">No data available</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Top Partners */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Top Partners
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {(topPartners?.data || []).map((partner, idx) => (
                <div key={idx} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-leamss-orange-100 rounded-full flex items-center justify-center text-leamss-orange-600 font-bold">
                      {idx + 1}
                    </div>
                    <div>
                      <p className="font-medium">{partner.partner_name}</p>
                      <p className="text-sm text-gray-500">{partner.count} sales</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-green-600">
                      ₹{(partner.revenue || 0).toLocaleString()}
                    </p>
                    <p className="text-xs text-gray-500">
                      Commission: ₹{(partner.commission || 0).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
              {(!topPartners?.data || topPartners.data.length === 0) && (
                <p className="text-gray-500 text-center py-4">No data available</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Export Options */}
      <Card>
        <CardHeader>
          <CardTitle>Export Reports</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Button variant="outline" onClick={() => exportReport('sales', 'csv')}>
              <FileText className="h-4 w-4 mr-2" />
              Sales (CSV)
            </Button>
            <Button variant="outline" onClick={() => exportReport('sales', 'html')}>
              <FileText className="h-4 w-4 mr-2" />
              Sales (Print)
            </Button>
            <Button variant="outline" onClick={() => exportReport('cases', 'csv')}>
              <FileText className="h-4 w-4 mr-2" />
              Cases (CSV)
            </Button>
            <Button variant="outline" onClick={() => exportReport('commission', 'csv')}>
              <FileText className="h-4 w-4 mr-2" />
              Commission (CSV)
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AnalyticsDashboard;
