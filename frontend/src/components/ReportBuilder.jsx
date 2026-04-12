import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  FileText, Download, Loader2, TrendingUp, Users, Briefcase,
  User, ClipboardList, RotateCcw, Calendar
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ReportBuilder = ({ token }) => {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [report, setReport] = useState(null);
  const [filters, setFilters] = useState({
    report_type: '',
    date_from: '',
    date_to: '',
    partner_id: '',
    product_id: '',
    status: '',
  });
  const [partners, setPartners] = useState([]);
  const [products, setProducts] = useState([]);

  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    const load = async () => {
      try {
        const [tplRes, usersRes, productsRes] = await Promise.all([
          axios.get(`${API}/admin-super/report-templates`, { headers }),
          axios.get(`${API}/users`, { headers }),
          axios.get(`${API}/products`, { headers }),
        ]);
        setTemplates(tplRes.data || []);
        setPartners((usersRes.data || []).filter(u => u.role === 'partner'));
        setProducts(productsRes.data || []);
      } catch (e) {
        toast.error('Failed to load report templates');
      }
      setLoading(false);
    };
    load();
  }, []);

  const generateReport = async (reportType) => {
    setGenerating(true);
    setReport(null);
    try {
      const payload = { ...filters, report_type: reportType || filters.report_type };
      const res = await axios.post(`${API}/admin-super/report-builder/generate`, payload, { headers });
      setReport(res.data);
      toast.success(`${res.data.title} generated with ${res.data.rows?.length || 0} records`);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to generate report');
    }
    setGenerating(false);
  };

  const downloadCSV = () => {
    if (!report || !report.rows || report.rows.length === 0) {
      toast.error('No data to export');
      return;
    }
    const cols = report.columns || Object.keys(report.rows[0]);
    const csvRows = [
      cols.join(','),
      ...report.rows.map(row =>
        cols.map(c => {
          let val = row[c] ?? '';
          val = String(val).replace(/"/g, '""');
          return val.includes(',') || val.includes('\n') || val.includes('"') ? `"${val}"` : val;
        }).join(',')
      )
    ];
    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${report.title?.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    toast.success('Report downloaded');
  };

  const printReport = () => {
    if (!report || !report.rows || report.rows.length === 0) {
      toast.error('No data to print');
      return;
    }
    const cols = report.columns || Object.keys(report.rows[0]);
    const html = `<!DOCTYPE html><html><head><title>${report.title}</title>
    <style>body{font-family:Arial,sans-serif;padding:20px}h1{color:#2a777a;margin-bottom:10px}
    .summary{display:flex;gap:20px;margin:15px 0;flex-wrap:wrap}.stat{padding:10px 15px;background:#f1f5f9;border-radius:8px}
    .stat-label{font-size:11px;color:#666}.stat-value{font-size:18px;font-weight:bold;color:#2a777a}
    table{width:100%;border-collapse:collapse;margin-top:15px}th{background:#2a777a;color:white;padding:8px;text-align:left}
    td{padding:8px;border-bottom:1px solid #e2e8f0}.footer{margin-top:20px;text-align:center;font-size:11px;color:#999}</style>
    </head><body><h1>${report.title}</h1><p>Generated: ${new Date().toLocaleString()}</p>
    ${report.summary ? `<div class="summary">${Object.entries(report.summary).map(([k,v]) => `<div class="stat"><div class="stat-label">${k.replace(/_/g,' ')}</div><div class="stat-value">${typeof v === 'number' ? v.toLocaleString() : v}</div></div>`).join('')}</div>` : ''}
    <table><thead><tr>${cols.map(c => `<th>${c}</th>`).join('')}</tr></thead>
    <tbody>${report.rows.map(row => `<tr>${cols.map(c => `<td>${row[c] ?? ''}</td>`).join('')}</tr>`).join('')}</tbody></table>
    <div class="footer">LEAMSS Portal - Ladhani Education & Migration Services</div></body></html>`;
    const w = window.open('', '_blank');
    w.document.write(html);
    w.document.close();
    w.focus();
    setTimeout(() => w.print(), 500);
  };

  const iconMap = {
    'trending-up': TrendingUp,
    'users': Users,
    'briefcase': Briefcase,
    'user': User,
    'clipboard-list': ClipboardList,
    'rotate-ccw': RotateCcw,
  };

  if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" /></div>;

  return (
    <div className="space-y-6" data-testid="report-builder">
      {/* Templates Grid */}
      {!report && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.map((tpl, idx) => {
              const Icon = iconMap[tpl.icon] || FileText;
              return (
                <Card key={tpl.id} className="p-5 hover:shadow-lg transition-shadow cursor-pointer group border-2 hover:border-[#2a777a]"
                  onClick={() => { setFilters({ ...filters, report_type: tpl.report_type }); generateReport(tpl.report_type); }}
                  data-testid={`template-${tpl.id}`}
                >
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-[#2a777a]/10 text-[#2a777a] group-hover:bg-[#2a777a] group-hover:text-white transition-colors">
                      <Icon className="h-6 w-6" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-800 group-hover:text-[#2a777a]">{tpl.name}</h4>
                      <p className="text-sm text-slate-500 mt-1">{tpl.description}</p>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>

          {/* Custom Filters */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
              <Calendar className="h-5 w-5 text-[#2a777a]" />Custom Report with Filters
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
              <div>
                <Label>Report Type</Label>
                <Select value={filters.report_type} onValueChange={(v) => setFilters({ ...filters, report_type: v })}>
                  <SelectTrigger data-testid="report-type-select"><SelectValue placeholder="Select type" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="revenue">Revenue</SelectItem>
                    <SelectItem value="cases">Cases</SelectItem>
                    <SelectItem value="partners">Partners</SelectItem>
                    <SelectItem value="clients">Clients</SelectItem>
                    <SelectItem value="pre_assessments">Pre-Assessments</SelectItem>
                    <SelectItem value="refunds">Refunds</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>From Date</Label>
                <Input type="date" value={filters.date_from} onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} data-testid="report-date-from" />
              </div>
              <div>
                <Label>To Date</Label>
                <Input type="date" value={filters.date_to} onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} data-testid="report-date-to" />
              </div>
              <div>
                <Label>Partner</Label>
                <Select value={filters.partner_id} onValueChange={(v) => setFilters({ ...filters, partner_id: v === 'all' ? '' : v })}>
                  <SelectTrigger data-testid="report-partner-filter"><SelectValue placeholder="All Partners" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Partners</SelectItem>
                    {partners.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
              <div>
                <Label>Product</Label>
                <Select value={filters.product_id} onValueChange={(v) => setFilters({ ...filters, product_id: v === 'all' ? '' : v })}>
                  <SelectTrigger data-testid="report-product-filter"><SelectValue placeholder="All Products" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Products</SelectItem>
                    {products.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Status</Label>
                <Input placeholder="Filter by status..." value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })} data-testid="report-status-filter" />
              </div>
              <div className="flex items-end">
                <Button onClick={() => generateReport()} disabled={generating || !filters.report_type} className="w-full bg-[#2a777a] hover:bg-[#236466] text-white" data-testid="generate-report-btn">
                  {generating ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <FileText className="h-4 w-4 mr-1" />}
                  Generate Report
                </Button>
              </div>
              <div className="flex items-end">
                <Button variant="outline" onClick={() => setFilters({ report_type: '', date_from: '', date_to: '', partner_id: '', product_id: '', status: '' })} className="w-full" data-testid="clear-filters-btn">
                  Clear Filters
                </Button>
              </div>
            </div>
          </Card>
        </>
      )}

      {/* Report Results */}
      {report && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-xl font-bold text-slate-800">{report.title}</h3>
              <p className="text-sm text-slate-500">{report.rows?.length || 0} records | Generated: {new Date().toLocaleString()}</p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setReport(null)} data-testid="back-to-templates">Back to Templates</Button>
              <Button variant="outline" onClick={downloadCSV} data-testid="download-csv-btn"><Download className="h-4 w-4 mr-1" />CSV</Button>
              <Button className="bg-[#2a777a] hover:bg-[#236466] text-white" onClick={printReport} data-testid="print-report-btn"><FileText className="h-4 w-4 mr-1" />Print / PDF</Button>
            </div>
          </div>

          {/* Summary Stats */}
          {report.summary && (
            <div className="flex flex-wrap gap-3">
              {Object.entries(report.summary).map(([key, val]) => (
                <Card key={key} className="p-3 min-w-[140px]">
                  <p className="text-xs text-slate-500 capitalize">{key.replace(/_/g, ' ')}</p>
                  <p className="text-lg font-bold text-[#2a777a]">{typeof val === 'number' ? val.toLocaleString() : val}</p>
                </Card>
              ))}
            </div>
          )}

          {/* Data Table */}
          <Card className="overflow-hidden">
            <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 sticky top-0">
                  <tr>
                    {(report.columns || []).map(col => (
                      <th key={col} className="text-left p-3 font-medium text-slate-600 whitespace-nowrap">{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(report.rows || []).map((row, idx) => (
                    <tr key={idx} className="border-t hover:bg-slate-50" data-testid={`report-row-${idx}`}>
                      {(report.columns || []).map(col => (
                        <td key={col} className="p-3 text-slate-700 whitespace-nowrap">
                          {typeof row[col] === 'number'
                            ? (col.toLowerCase().includes('fee') || col.toLowerCase().includes('amount') || col.toLowerCase().includes('revenue') || col.toLowerCase().includes('received') || col.toLowerCase().includes('pending') || col.toLowerCase().includes('commission') || col.toLowerCase().includes('refund'))
                              ? `₹${row[col].toLocaleString()}`
                              : row[col].toLocaleString()
                            : (row[col] && typeof row[col] === 'string' && row[col].match(/^\d{4}-\d{2}-\d{2}T/))
                              ? new Date(row[col]).toLocaleDateString()
                              : (row[col] ?? '-')
                          }
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {generating && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-[#2a777a] mr-3" />
          <p className="text-slate-600">Generating report...</p>
        </div>
      )}
    </div>
  );
};

export default ReportBuilder;
