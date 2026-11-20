import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Clock, ListChecks, ShieldCheck, AlertCircle, CheckCircle2,
  FileText, ExternalLink, Globe, Layers, Lock, Unlock
} from 'lucide-react';

export default function CaseManagerPerspectiveView({ product }) {
  const [filterScope, setFilterScope] = useState('all');

  const timeline = product?.processing_timeline || {};
  const stages = timeline?.stages || [];
  const checklist = product?.document_checklist_template || [];
  const conditions = product?.visa_conditions || [];
  const workflowSteps = product?.workflow_steps || [];

  const filteredDocs = checklist.filter((d) => {
    if (filterScope === 'all') return true;
    if (filterScope === 'primary') return d.required_for === 'primary_applicant';
    if (filterScope === 'spouse') return d.required_for === 'spouse';
    if (filterScope === 'mandatory') return d.is_mandatory;
    return true;
  });

  return (
    <div className="space-y-4 text-xs">
      {/* Top Delivery Header */}
      <Card className="p-4 bg-gradient-to-r from-blue-500/10 via-indigo-500/10 to-slate-500/10 border-2 border-blue-300 space-y-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-blue-600" />
            <div>
              <h2 className="text-base font-extrabold text-slate-900">
                Case Delivery Roadmap • {product?.name}
              </h2>
              <p className="text-[11px] text-slate-500">
                Standardised operational workflow stages, statutory form codes, and compliance standards.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Badge className="bg-blue-100 text-blue-800 text-xs">
              SLA: {timeline?.standard_duration || '6 - 9 months'}
            </Badge>
            {product?.last_verified_at && (
              <Badge className="bg-emerald-100 text-emerald-800 text-xs gap-1">
                <ShieldCheck className="h-3 w-3" />
                Compliance Verified
              </Badge>
            )}
          </div>
        </div>

        {/* Quick official links */}
        <div className="flex items-center gap-2 pt-1 flex-wrap">
          {product?.migrate_page_url && (
            <a
              href={product.migrate_page_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-[11px] text-blue-600 bg-white px-2 py-0.5 rounded border border-blue-200 hover:bg-blue-50"
            >
              <ExternalLink className="h-3 w-3" />Migrate Portal
            </a>
          )}
          {(product?.official_urls || []).map((url, i) => (
            <a
              key={i}
              href={url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-[11px] text-emerald-700 bg-white px-2 py-0.5 rounded border border-emerald-200 hover:bg-emerald-50"
            >
              <Globe className="h-3 w-3" />Official Government Portal
            </a>
          ))}
        </div>
      </Card>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 1. STEP-BY-STEP WORKFLOW TIMELINE ROADMAP                     */}
      {/* ───────────────────────────────────────────────────────────── */}
      <Card className="p-4 bg-white border border-slate-200 space-y-3">
        <div className="flex items-center justify-between pb-2 border-b">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-blue-600" />
            <h3 className="font-extrabold text-slate-900 text-sm">
              Standard Case Delivery Milestones ({stages.length} Stages)
            </h3>
          </div>
          <span className="text-[11px] text-slate-500 font-medium">Estimated SLA Turnarounds</span>
        </div>

        {stages.length === 0 ? (
          <p className="text-slate-400 italic py-4 text-center">No stages defined for this product.</p>
        ) : (
          <div className="space-y-3 relative before:absolute before:left-5 before:top-4 before:bottom-4 before:w-0.5 before:bg-slate-200">
            {stages.map((st, idx) => (
              <div key={idx} className="relative pl-10">
                <div className="absolute left-2.5 top-3.5 -translate-x-1/2 w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center font-extrabold text-[11px] shadow-sm z-10">
                  {st.stage_order || idx + 1}
                </div>

                <Card className="p-3 bg-slate-50 border border-slate-200 space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <h4 className="font-bold text-slate-900 text-xs">{st.stage_name || st.stage}</h4>
                    <Badge variant="outline" className="text-[10px] bg-white gap-1">
                      <Clock className="h-3 w-3 text-slate-400" />
                      {st.duration_days ? `${st.duration_days} days SLA` : st.duration || '14 days'}
                    </Badge>
                  </div>

                  {st.description && (
                    <p className="text-[11px] text-slate-600">{st.description}</p>
                  )}

                  {st.government_fees && (
                    <p className="text-[10px] text-emerald-700 font-semibold bg-emerald-50 p-1.5 rounded">
                      Fee payable at this stage: {st.government_fees}
                    </p>
                  )}
                </Card>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 2. STATUTORY DOCUMENT CHECKLIST MATRIX                        */}
      {/* ───────────────────────────────────────────────────────────── */}
      <Card className="p-4 bg-white border border-slate-200 space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b">
          <div className="flex items-center gap-2">
            <ListChecks className="h-4 w-4 text-emerald-600" />
            <h3 className="font-extrabold text-slate-900 text-sm">
              Document Checklist & Statutory Form Matrix ({checklist.length})
            </h3>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setFilterScope('all')}
              className={`px-2.5 py-0.5 rounded text-[11px] font-semibold transition ${
                filterScope === 'all' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600'
              }`}
            >
              All ({checklist.length})
            </button>
            <button
              onClick={() => setFilterScope('mandatory')}
              className={`px-2.5 py-0.5 rounded text-[11px] font-semibold transition ${
                filterScope === 'mandatory' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600'
              }`}
            >
              Mandatory Only
            </button>
            <button
              onClick={() => setFilterScope('primary')}
              className={`px-2.5 py-0.5 rounded text-[11px] font-semibold transition ${
                filterScope === 'primary' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600'
              }`}
            >
              Primary Applicant
            </button>
          </div>
        </div>

        {filteredDocs.length === 0 ? (
          <p className="text-slate-400 italic py-4 text-center">No matching document requirements found.</p>
        ) : (
          <div className="space-y-2">
            {filteredDocs.map((doc, idx) => (
              <div key={idx} className="p-2.5 bg-slate-50 border rounded-lg flex items-start justify-between gap-3">
                <div className="space-y-1 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-bold text-slate-900 text-xs">{doc.document_name}</span>
                    {doc.form_code && (
                      <Badge className="bg-purple-100 text-purple-800 font-mono text-[9px] py-0 px-1.5">
                        {doc.form_code}
                      </Badge>
                    )}
                    <Badge variant="outline" className="text-[9px] py-0 px-1.5">
                      {doc.category || 'Statutory Dossier'}
                    </Badge>
                    {doc.is_mandatory !== false ? (
                      <Badge className="bg-rose-50 text-rose-700 text-[9px] py-0 px-1.5">Mandatory</Badge>
                    ) : (
                      <Badge className="bg-slate-100 text-slate-600 text-[9px] py-0 px-1.5">Optional</Badge>
                    )}
                  </div>

                  {doc.standard && (
                    <p className="text-[10px] text-blue-700 font-medium">Standard: {doc.standard}</p>
                  )}

                  {doc.description && (
                    <p className="text-[10px] text-slate-500">{doc.description}</p>
                  )}
                </div>

                <div className="text-right shrink-0">
                  <span className="text-[10px] text-slate-500 font-semibold block capitalize">
                    {(doc.required_for || 'all_applicants').replace('_', ' ')}
                  </span>
                  {doc.is_locked_until_paid && (
                    <span className="text-[9px] text-amber-700 font-bold flex items-center gap-0.5 justify-end mt-0.5">
                      <Lock className="h-2.5 w-2.5" />Stage Gated
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 3. VISA CONDITIONS & STATUTORY COMPLIANCE                     */}
      {/* ───────────────────────────────────────────────────────────── */}
      <Card className="p-4 bg-white border border-slate-200 space-y-2.5">
        <div className="flex items-center gap-2 pb-1.5 border-b">
          <ShieldCheck className="h-4 w-4 text-purple-600" />
          <h3 className="font-extrabold text-slate-900 text-sm">
            Statutory Visa Conditions & Compliance Warnings ({conditions.length})
          </h3>
        </div>

        {conditions.length === 0 ? (
          <p className="text-slate-400 italic">No specific visa conditions recorded.</p>
        ) : (
          <div className="space-y-1">
            {conditions.map((c, idx) => (
              <div key={idx} className="flex items-center gap-2 p-2 bg-purple-50/50 border border-purple-100 rounded text-[11px] text-purple-950">
                <CheckCircle2 className="h-3.5 w-3.5 text-purple-600 shrink-0" />
                <span>{c}</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
