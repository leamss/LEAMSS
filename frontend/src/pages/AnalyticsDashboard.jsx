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
      const [trendRes, statusRes, productsRes, partnersRes, monthlyRes, completionRes] = await Promise.all([
        axios.get(`${API_URL}/api/analytics/sales-trend?days=${period}`, { headers }),
        axios.get(`${API_URL}/api/analytics/sales-by-status`, { headers }),
        axios.get(`${API_URL}/api/analytics/top-products`, { headers }),
        axios.get(`${API_URL}/api/analytics/top-partners`, { headers }),
        axios.get(`${API_URL}/api/analytics/monthly-revenue`, { headers }),
        axios.get(`${API_URL}/api/analytics/case-completion-rate`, { headers })
      ]);

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
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
          <p className="text-gray-500">Insights and performance metrics</p>
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
                  ₹{salesTrend?.revenue?.reduce((a, b) => a + b, 0)?.toLocaleString() || 0}
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
                  ₹{salesTrend?.commission?.reduce((a, b) => a + b, 0)?.toLocaleString() || 0}
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
                  {salesTrend?.sales_count?.reduce((a, b) => a + b, 0) || 0}
                </p>
              </div>
              <div className="h-12 w-12 bg-purple-100 rounded-full flex items-center justify-center">
                <FileText className="h-6 w-6 text-purple-600" />
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
                  {caseCompletion?.completion_rate || 0}%
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
              {salesByStatus?.labels?.map((label, idx) => (
                <div key={label} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div 
                      className="w-3 h-3 rounded-full" 
                      style={{ backgroundColor: statusColors[label] || '#6b7280' }}
                    />
                    <span className="capitalize">{label}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="font-medium">{salesByStatus.counts[idx]}</span>
                    <span className="text-gray-500">
                      ₹{salesByStatus.amounts[idx]?.toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
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
              {monthlyRevenue?.labels?.map((month, idx) => {
                const revenue = monthlyRevenue.revenue[idx] || 0;
                const maxRevenue = Math.max(...(monthlyRevenue.revenue || [1]));
                const width = maxRevenue > 0 ? (revenue / maxRevenue) * 100 : 0;
                
                return (
                  <div key={month} className="flex items-center gap-2">
                    <span className="w-8 text-xs text-gray-500">{month}</span>
                    <div className="flex-1 bg-gray-100 rounded h-4 overflow-hidden">
                      <div 
                        className="bg-indigo-500 h-full rounded transition-all"
                        style={{ width: `${width}%` }}
                      />
                    </div>
                    <span className="w-24 text-xs text-right">
                      {revenue > 0 ? `₹${(revenue/1000).toFixed(0)}K` : '-'}
                    </span>
                  </div>
                );
              })}
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
              {topProducts.map((product, idx) => (
                <div key={product.id} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600 font-bold">
                      {idx + 1}
                    </div>
                    <div>
                      <p className="font-medium">{product.name}</p>
                      <p className="text-sm text-gray-500">{product.sales_count} sales</p>
                    </div>
                  </div>
                  <p className="font-medium text-green-600">
                    ₹{product.total_revenue?.toLocaleString()}
                  </p>
                </div>
              ))}
              {topProducts.length === 0 && (
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
              {topPartners.map((partner, idx) => (
                <div key={partner.id} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center text-purple-600 font-bold">
                      {idx + 1}
                    </div>
                    <div>
                      <p className="font-medium">{partner.name}</p>
                      <p className="text-sm text-gray-500">{partner.sales_count} sales</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-green-600">
                      ₹{partner.total_revenue?.toLocaleString()}
                    </p>
                    <p className="text-xs text-gray-500">
                      Commission: ₹{partner.total_commission?.toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
              {topPartners.length === 0 && (
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
