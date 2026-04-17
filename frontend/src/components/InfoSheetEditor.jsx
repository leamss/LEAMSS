import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  User, Upload, Save, ChevronDown, ChevronRight, Loader2, FileText, Plus, Trash2
} from 'lucide-react';

const HIDDEN_KEYS = ['id', 'case_id', 'client_id', 'created_at', 'updated_at', '_id',
  'required_fields', 'status', 'auto_filled_at', 'auto_filled_by', 'auto_filled_from',
  'auto_filled_data', 'change_history', 'updated_by', 'updated_by_role', 'auto_filled_from'];

const InfoSheetEditor = ({ caseData, API, getAuthHeader, onRefresh, extractingResume, setExtractingResume }) => {
  const [schema, setSchema] = useState(null);
  const [productSections, setProductSections] = useState([]);
  const [productLabel, setProductLabel] = useState('');
  const [formData, setFormData] = useState({});
  const [saving, setSaving] = useState(false);
  const [expandedSections, setExpandedSections] = useState({});
  const [dirty, setDirty] = useState(false);

  const loadSchema = useCallback(async () => {
    try {
      const productName = caseData?.product_name || '';
      const schemaUrl = productName 
        ? `${API}/cases/info-sheet-schema/${encodeURIComponent(productName)}`
        : `${API}/cases/info-sheet-schema`;
      
      const [schemaRes, sheetRes] = await Promise.all([
        axios.get(schemaUrl, getAuthHeader()),
        caseData ? axios.get(`${API}/cases/${caseData.id}/information-sheet`, getAuthHeader()) : null,
      ]);
      setSchema(schemaRes.data);
      setProductSections(schemaRes.data.product_sections || []);
      setProductLabel(schemaRes.data.product_label || '');
      if (sheetRes?.data?.exists) {
        setFormData(sheetRes.data.data || {});
      }
      // Auto-expand first section
      if (schemaRes.data?.sections?.length > 0) {
        setExpandedSections({ [schemaRes.data.sections[0].id]: true });
      }
    } catch (e) {
      console.error('Failed to load schema:', e);
    }
  }, [API, caseData, getAuthHeader]);

  useEffect(() => { loadSchema(); }, [loadSchema]);

  const updateField = (key, value) => {
    setFormData(prev => ({ ...prev, [key]: value }));
    setDirty(true);
  };

  const handleSave = async () => {
    if (!caseData) return;
    setSaving(true);
    try {
      const payload = { ...formData };
      // Remove internal fields
      HIDDEN_KEYS.forEach(k => delete payload[k]);
      await axios.post(`${API}/cases/${caseData.id}/information-sheet`, payload, getAuthHeader());
      toast.success('Information sheet saved successfully!');
      setDirty(false);
      onRefresh?.();
    } catch (e) {
      toast.error('Failed to save. Please try again.');
    }
    setSaving(false);
  };

  const handleResumeUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !caseData) return;
    setExtractingResume(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('case_id', caseData.id);
      fd.append('document_type', 'resume');
      const uploadRes = await axios.post(`${API}/documents/upload`, fd, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}`, 'Content-Type': 'multipart/form-data' }
      });
      const docId = uploadRes.data?.id || uploadRes.data?.document_id;
      if (docId) {
        const extractRes = await axios.post(
          `${API}/ai-intel/extract-resume-to-infosheet/${caseData.id}?document_id=${docId}`,
          {}, getAuthHeader()
        );
        toast.success(extractRes.data.message || `Extracted ${extractRes.data.fields_filled} fields!`);
        loadSchema(); // Reload to get the new data
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to extract. Try a clearer document.');
    } finally {
      setExtractingResume(false);
      e.target.value = '';
    }
  };

  const handleExportPDF = async () => {
    if (!caseData) return;
    try {
      const res = await axios.get(`${API}/reports/export/info-sheet/${caseData.id}`, {
        ...getAuthHeader(),
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `LEAMSS_InfoSheet_${caseData.case_id || ''}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Info Sheet PDF downloaded!');
    } catch (e) {
      toast.error('Failed to export PDF. Save your data first.');
    }
  };

  const toggleSection = (id) => {
    setExpandedSections(prev => ({ ...prev, [id]: !prev[id] }));
  };

  // Get count of repeatable entries — scans ALL existing data, no upper limit
  const getEntryCount = (section) => {
    let maxFound = 0;
    const maxLimit = section.max_entries || 20;
    // Scan up to a reasonable high number to find all existing entries
    for (let i = 1; i <= Math.max(maxLimit, 50); i++) {
      const prefix = `${section.entry_prefix}_${i}`;
      const hasData = section.entry_fields.some(f => {
        const val = formData[`${prefix}_${f.key}`];
        return val && String(val).trim();
      });
      if (hasData) maxFound = i;
    }
    return Math.max(maxFound, 1);
  };

  const addEntry = (section) => {
    const currentCount = getEntryCount(section);
    // Always allow adding — no hard limit
    const prefix = `${section.entry_prefix}_${currentCount + 1}`;
    updateField(`${prefix}_${section.entry_fields[0].key}`, '');
  };

  const removeEntry = (section, index) => {
    const prefix = `${section.entry_prefix}_${index}`;
    const newData = { ...formData };
    section.entry_fields.forEach(f => {
      delete newData[`${prefix}_${f.key}`];
    });
    setFormData(newData);
    setDirty(true);
  };

  const renderField = (field, keyPrefix = '') => {
    const fullKey = keyPrefix ? `${keyPrefix}_${field.key}` : field.key;
    const value = formData[fullKey] || '';

    if (field.type === 'select') {
      return (
        <select
          value={value}
          onChange={e => updateField(fullKey, e.target.value)}
          className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#2a777a]/30 focus:border-[#2a777a]"
          data-testid={`info-field-${fullKey}`}
        >
          <option value="">Select...</option>
          {field.options?.map(opt => <option key={opt} value={opt}>{opt}</option>)}
        </select>
      );
    }

    if (field.type === 'textarea') {
      return (
        <textarea
          value={value}
          onChange={e => updateField(fullKey, e.target.value)}
          rows={3}
          className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2a777a]/30 focus:border-[#2a777a] resize-y"
          placeholder={field.label}
          data-testid={`info-field-${fullKey}`}
        />
      );
    }

    return (
      <Input
        type={field.type === 'date' ? 'date' : 'text'}
        value={value}
        onChange={e => updateField(fullKey, e.target.value)}
        placeholder={field.label}
        className="focus:ring-2 focus:ring-[#2a777a]/30 focus:border-[#2a777a]"
        data-testid={`info-field-${fullKey}`}
      />
    );
  };

  if (!schema) {
    return (
      <Card className="p-12 text-center bg-white shadow-md border-0">
        <Loader2 className="h-8 w-8 animate-spin mx-auto text-[#2a777a]" />
        <p className="mt-2 text-slate-500">Loading information sheet...</p>
      </Card>
    );
  }

  return (
    <div className="space-y-4" data-testid="info-sheet-editor">
      {/* Header with actions */}
      <Card className="p-4 bg-white shadow-md border-0">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
              <User className="h-5 w-5 text-[#2a777a]" />
              Required Information Sheet
            </h3>
            <p className="text-sm text-slate-500 mt-1">Fill all sections below. Upload resume to auto-fill fields.</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleExportPDF} data-testid="export-info-pdf-btn">
              <FileText className="h-4 w-4 mr-1" /> Export PDF
            </Button>
            <label className="cursor-pointer">
              <input type="file" className="hidden" accept=".pdf,.doc,.docx,.txt" onChange={handleResumeUpload} />
              <Button variant="outline" size="sm" className="text-[#2a777a] border-[#2a777a]" disabled={extractingResume} asChild>
                <span data-testid="upload-resume-btn">
                  {extractingResume ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Upload className="h-4 w-4 mr-1" />}
                  {extractingResume ? 'Extracting...' : 'Upload Resume & Auto-Fill'}
                </span>
              </Button>
            </label>
            <Button
              className="bg-[#2a777a] hover:bg-[#236466]"
              size="sm"
              onClick={handleSave}
              disabled={saving || !dirty}
              data-testid="save-info-sheet-btn"
            >
              {saving ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Save className="h-4 w-4 mr-1" />}
              {saving ? 'Saving...' : 'Save All Changes'}
            </Button>
          </div>
        </div>
      </Card>

      {/* Sections */}
      {schema.sections.map((section) => (
        <Card key={section.id} className="bg-white shadow-md border-0 overflow-hidden" data-testid={`section-${section.id}`}>
          {/* Section header */}
          <button
            onClick={() => toggleSection(section.id)}
            className="w-full flex items-center justify-between px-6 py-4 hover:bg-slate-50 transition-colors"
            data-testid={`toggle-section-${section.id}`}
          >
            <div className="flex items-center gap-3">
              {expandedSections[section.id] ? <ChevronDown className="h-5 w-5 text-[#2a777a]" /> : <ChevronRight className="h-5 w-5 text-slate-400" />}
              <h4 className="text-base font-bold text-slate-800">{section.title}</h4>
              <Badge className="bg-[#2a777a]/10 text-[#2a777a] text-xs">
                {section.fields ? `${section.fields.length} fields` : section.repeatable ? 'Repeatable' : ''}
              </Badge>
            </div>
          </button>

          {/* Section content */}
          {expandedSections[section.id] && (
            <div className="px-6 pb-6 border-t border-slate-100">
              {/* Regular fields */}
              {section.fields && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-4">
                  {section.fields.map((field) => (
                    <div key={field.key} className="space-y-1">
                      <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide flex items-center gap-1">
                        {field.label}
                        {field.required && <span className="text-red-500">*</span>}
                      </label>
                      {renderField(field)}
                    </div>
                  ))}
                </div>
              )}

              {/* Repeatable entries */}
              {section.repeatable && (
                <div className="pt-4 space-y-4">
                  {Array.from({ length: getEntryCount(section) }, (_, idx) => {
                    const entryNum = idx + 1;
                    const prefix = `${section.entry_prefix}_${entryNum}`;
                    return (
                      <div key={entryNum} className="border border-slate-200 rounded-lg p-4 bg-slate-50/50" data-testid={`entry-${prefix}`}>
                        <div className="flex items-center justify-between mb-3">
                          <h5 className="text-sm font-semibold text-slate-700">{section.title} #{entryNum}</h5>
                          {entryNum > 1 && (
                            <Button size="sm" variant="ghost" className="text-red-500 hover:bg-red-50 h-7 px-2" onClick={() => removeEntry(section, entryNum)}>
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                          {section.entry_fields.map((field) => (
                            <div key={`${prefix}_${field.key}`} className="space-y-1">
                              <label className="text-xs font-medium text-slate-500">{field.label}</label>
                              {renderField(field, prefix)}
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                  {/* Always show Add button */}
                  <Button variant="outline" size="sm" className="text-[#2a777a] border-[#2a777a]" onClick={() => addEntry(section)} data-testid={`add-${section.entry_prefix}`}>
                    <Plus className="h-4 w-4 mr-1" /> Add {section.title.replace(/s$/, '').replace(' History', '')}
                  </Button>
                </div>
              )}
            </div>
          )}
        </Card>
      ))}

      {/* Product-Specific Sections */}
      {productSections.length > 0 && (
        <>
          <div className="flex items-center gap-2 pt-2">
            <div className="h-0.5 flex-1 bg-gradient-to-r from-[#f7620b]/30 to-transparent" />
            <Badge className="bg-[#f7620b]/10 text-[#f7620b] text-xs font-bold border-0 px-3 whitespace-nowrap" data-testid="product-sections-badge">
              {productLabel || 'Product-Specific'}
            </Badge>
            <div className="h-0.5 flex-1 bg-gradient-to-l from-[#f7620b]/30 to-transparent" />
          </div>

          {productSections.map((section) => (
            <Card key={section.id} className="bg-white shadow-md border-0 overflow-hidden border-l-4 border-l-[#f7620b]" data-testid={`product-section-${section.id}`}>
              <button
                onClick={() => toggleSection(section.id)}
                className="w-full flex items-center justify-between px-6 py-4 hover:bg-slate-50 transition-colors"
                data-testid={`toggle-section-${section.id}`}
              >
                <div className="flex items-center gap-3">
                  {expandedSections[section.id] ? <ChevronDown className="h-5 w-5 text-[#f7620b]" /> : <ChevronRight className="h-5 w-5 text-slate-400" />}
                  <h4 className="text-base font-bold text-slate-800">{section.title}</h4>
                  <Badge className="bg-[#f7620b]/10 text-[#f7620b] text-xs">{section.fields?.length || 0} fields</Badge>
                </div>
              </button>
              {expandedSections[section.id] && (
                <div className="px-6 pb-6 border-t border-slate-100">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-4">
                    {(section.fields || []).map((field) => (
                      <div key={field.key} className="space-y-1">
                        <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide flex items-center gap-1">
                          {field.label}
                          {field.required && <span className="text-red-500">*</span>}
                        </label>
                        {renderField(field)}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          ))}
        </>
      )}

      {/* Sticky save bar */}
      {dirty && (
        <div className="sticky bottom-4 flex justify-center z-10">
          <Button className="bg-[#2a777a] hover:bg-[#236466] shadow-xl px-8 py-3 text-base" onClick={handleSave} disabled={saving} data-testid="sticky-save-btn">
            {saving ? <Loader2 className="h-5 w-5 mr-2 animate-spin" /> : <Save className="h-5 w-5 mr-2" />}
            {saving ? 'Saving...' : 'Save All Changes'}
          </Button>
        </div>
      )}
    </div>
  );
};

export default InfoSheetEditor;
