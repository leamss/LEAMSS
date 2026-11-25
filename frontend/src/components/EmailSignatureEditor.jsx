import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  PenTool, CheckCircle2, Upload, RotateCcw, Code, Eye,
  Building2, Globe, User, Phone, Mail, FileText, Check, Loader2, Sparkles, ExternalLink, Image as ImageIcon
} from 'lucide-react';
import { toast } from 'sonner';

export const DEFAULT_LEAMSS_LOGO =
  'https://leamss.com/public/assets/web/images/logo.png';;

/**
 * Builds standard bounded corporate HTML signature
 */
export function buildSignatureHtml({
  name = '',
  designation = '',
  phone = '',
  email = '',
  company = 'Ladhani Education And Migration Services Pvt Ltd.',
  cin = 'CIN-U85500MH2024OPC420610',
  website = 'www.leamss.com',
  logoUrl = DEFAULT_LEAMSS_LOGO,
  includeSocialLinks = true
}) {
  const safeName = (name || 'Immigration Consultant').trim();
  const safeDesignation = (designation || 'Immigration & Visa Advisor').trim();
  const safePhone = (phone || '+91 98765 43210').trim();
  const safeEmail = (email || 'advisor@leamss.com').trim();
  const safeCompany = (company || 'Ladhani Education And Migration Services Pvt Ltd.').trim();
  const safeCin = (cin || 'CIN-U85500MH2024OPC420610').trim();
  const safeWebsite = (website || 'www.leamss.com').trim();
  const websiteHref = safeWebsite.startsWith('http') ? safeWebsite : `https://${safeWebsite}`;
  const safeLogo = (logoUrl || DEFAULT_LEAMSS_LOGO).trim();

  return (
    `<div class="leamss-signature-block" data-signature-block="true" style="margin-top: 16px; font-family: Arial, Helvetica, sans-serif; color: #1e293b;">` +
    `<p style="margin: 0 0 10px 0; font-size: 13px; color: #334155; line-height: 1.4;">Warm Regards,<br/><strong>${safeName}</strong></p>` +
    `<table cellpadding="0" cellspacing="0" border="0" style="border-top: 1px solid #cbd5e1; padding-top: 10px; width: 100%; max-width: 520px; font-size: 12px; line-height: 1.5;">` +
    `<tr>` +
    `<td style="vertical-align: top; padding-right: 14px; width: 68px;">` +
    `<img src="${safeLogo}" alt="Logo" style="height: 38px; width: auto; max-width: 90px; display: block; object-fit: contain;" />` +
    `</td>` +
    `<td style="vertical-align: top;">` +
    `<div style="font-size: 11px; color: #0284c7; font-weight: bold;"><a href="${websiteHref}" target="_blank" rel="noopener noreferrer" style="color: #0284c7; text-decoration: none;">${safeWebsite}</a></div>` +
    `<div style="font-size: 12px; font-weight: bold; color: #0f172a; margin-top: 2px;">${safeCompany}</div>` +
    (safeCin ? `<div style="font-size: 10px; color: #64748b; font-weight: 500;">${safeCin}</div>` : '') +
    `<div style="font-size: 12px; font-weight: 600; color: #1e293b; margin-top: 4px;">${safeDesignation} - ${safeName}</div>` +
    `<div style="font-size: 11px; color: #475569;">Contact- <a href="tel:${safePhone}" style="color: #475569; text-decoration: none; font-weight: 500;">${safePhone}</a></div>` +
    (includeSocialLinks
      ? `<div style="font-size: 11px; color: #4f46e5; margin-top: 5px;">` +
        `<a href="${websiteHref}" target="_blank" rel="noopener noreferrer" style="color: #4f46e5; text-decoration: underline;">LEAMSS website</a> | ` +
        `<a href="https://www.linkedin.com/company/leamss" target="_blank" rel="noopener noreferrer" style="color: #4f46e5; text-decoration: underline;">LinkedIn</a> | ` +
        `<a href="https://www.instagram.com/leamss_official" target="_blank" rel="noopener noreferrer" style="color: #4f46e5; text-decoration: underline;">Instagram</a> | ` +
        `<a href="https://www.facebook.com/leamssofficial" target="_blank" rel="noopener noreferrer" style="color: #4f46e5; text-decoration: underline;">Facebook</a>` +
        `</div>`
      : '') +
    `<div style="font-size: 10px; color: #94a3b8; margin-top: 8px; font-style: italic; border-top: 1px dashed #e2e8f0; padding-top: 4px;">` +
    `Gateway info: Delivered directly from personal mailbox (${safeEmail})` +
    `</div>` +
    `</td>` +
    `</tr>` +
    `</table>` +
    `</div>`
  );
}

/**
 * Extracts form values from raw HTML or returns defaults based on current user
 */
export function parseSignatureHtml(html, currentUser = {}) {
  const fallbackName = currentUser.name || 'Pooja Patil';
  const fallbackRole =
    currentUser.designation ||
    currentUser.role_title ||
    (String(currentUser.name || '').toLowerCase().includes('pooja')
      ? 'Marketing & Technical Specialist'
      : 'Immigration & Visa Advisor');
  const fallbackPhone =
    currentUser.phone ||
    currentUser.mobile ||
    (String(currentUser.name || '').toLowerCase().includes('pooja')
      ? '7400403105'
      : '+91 98765 43210');
  const fallbackEmail = currentUser.email || 'advisor@leamss.com';

  const defaults = {
    name: fallbackName,
    designation: fallbackRole,
    phone: fallbackPhone,
    email: fallbackEmail,
    company: 'Ladhani Education And Migration Services Pvt Ltd.',
    cin: 'CIN-U85500MH2024OPC420610',
    website: 'www.leamss.com',
    logoUrl: DEFAULT_LEAMSS_LOGO,
    includeSocialLinks: true
  };

  if (!html || typeof html !== 'string' || !html.trim()) {
    return defaults;
  }

  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(`<div>${html}</div>`, 'text/html');

    // Extract Logo
    const imgEl = doc.querySelector('img');
    let logoUrl = imgEl ? imgEl.getAttribute('src') || '' : '';
    // Fix broken or external logo that was not loading
    if (!logoUrl || logoUrl.includes('leamss.com/leamss-logo.png')) {
      logoUrl = DEFAULT_LEAMSS_LOGO;
    }

    // Extract Name from <strong>
    let name = '';
    const strongEl = doc.querySelector('p strong, strong');
    if (strongEl) {
      name = strongEl.textContent.trim();
    }

    // Extract Phone
    let phone = '';
    const phoneEl = doc.querySelector('a[href^="tel:"]');
    if (phoneEl) {
      phone = phoneEl.textContent.trim();
    } else {
      const matchPhone = doc.body.textContent.match(/Contact[-:\s]*([+\d\s\-()]{8,20})/i);
      if (matchPhone) phone = matchPhone[1].trim();
    }

    // Extract Email from gateway text
    let email = '';
    const matchEmail = doc.body.textContent.match(/mailbox\s*\(([^)]+)\)/i);
    if (matchEmail) {
      email = matchEmail[1].trim();
    } else {
      const generalEmailMatch = doc.body.textContent.match(/[\w.-]+@[\w.-]+\.[a-zA-Z]{2,}/);
      if (generalEmailMatch) email = generalEmailMatch[0];
    }

    // Extract Designation
    let designation = '';
    const textNodes = [];
    const walk = (node) => {
      if (node.nodeType === 3 && node.nodeValue.trim()) {
        textNodes.push(node.nodeValue.trim());
      }
      for (let c = node.firstChild; c; c = c.nextSibling) walk(c);
    };
    walk(doc.body);

    for (const t of textNodes) {
      if (name && t.includes(name) && t.includes('-')) {
        const parts = t.split('-');
        if (parts[0].trim() !== name) {
          designation = parts[0].trim();
          break;
        }
      }
    }

    // Extract CIN
    let cin = '';
    for (const t of textNodes) {
      if (t.toUpperCase().includes('CIN-') || t.toUpperCase().includes('CIN:')) {
        cin = t.trim();
        break;
      }
    }

    // Extract Company
    let company = '';
    for (const t of textNodes) {
      if (t.toLowerCase().includes('ladhani') || t.toLowerCase().includes('services pvt')) {
        company = t.trim();
        break;
      }
    }

    // Extract Website
    let website = '';
    const webEl = doc.querySelector('a[href*="leamss.com"]');
    if (webEl) {
      website = webEl.textContent.trim();
    }

    return {
      name: name || defaults.name,
      designation: designation || defaults.designation,
      phone: phone || defaults.phone,
      email: email || defaults.email,
      company: company || defaults.company,
      cin: cin || defaults.cin,
      website: website || defaults.website,
      logoUrl: logoUrl || defaults.logoUrl,
      includeSocialLinks: html.toLowerCase().includes('linkedin') || html.toLowerCase().includes('instagram')
    };
  } catch (e) {
    console.warn('Could not parse signature HTML:', e);
    return defaults;
  }
}

/**
 * Visual Email Signature Editor with direct form editing, live visual preview, and logo uploader.
 */
export default function EmailSignatureEditor({
  initialSignatureHtml = '',
  currentUser = {},
  onSave,
  onClose,
  isSaving = false
}) {
  const [editorMode, setEditorMode] = useState('visual'); // 'visual' | 'html'
  const [formData, setFormData] = useState(() => parseSignatureHtml(initialSignatureHtml, currentUser));
  const [rawHtml, setRawHtml] = useState(initialSignatureHtml || '');
  const [showUrlInput, setShowUrlInput] = useState(false);
  const [customLogoUrl, setCustomLogoUrl] = useState('');
  const fileInputRef = useRef(null);

  // Sync initialSignatureHtml if it arrives asynchronously
  useEffect(() => {
    if (initialSignatureHtml && !rawHtml) {
      setRawHtml(initialSignatureHtml);
      setFormData(parseSignatureHtml(initialSignatureHtml, currentUser));
    }
  }, [initialSignatureHtml, currentUser, rawHtml]);

  // When form data changes in visual mode, keep rawHtml in sync
  const updateField = (field, value) => {
    setFormData((prev) => {
      const updated = { ...prev, [field]: value };
      const compiled = buildSignatureHtml(updated);
      setRawHtml(compiled);
      return updated;
    });
  };

  // Handle Logo Upload and resize on canvas to keep it lightweight (<10KB)
  const handleLogoUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error('Please upload an image file (PNG, JPG, SVG, WebP)');
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new Image();
      img.onload = () => {
        // Optimize logo dimensions: max height 50px, proportional width
        const maxH = 50;
        const scale = maxH / img.height;
        const targetW = Math.round(img.width * (scale < 1 ? scale : 1));
        const targetH = Math.round(img.height * (scale < 1 ? scale : 1));

        const canvas = document.createElement('canvas');
        canvas.width = targetW;
        canvas.height = targetH;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, targetW, targetH);
        const dataUrl = canvas.toDataURL('image/png', 0.92);

        updateField('logoUrl', dataUrl);
        toast.success('Custom logo uploaded & applied to signature preview!');
      };
      img.src = event.target.result;
    };
    reader.readAsDataURL(file);
    // Reset file input
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Reset logo to official LEAMSS corporate logo
  const handleResetLogo = () => {
    updateField('logoUrl', DEFAULT_LEAMSS_LOGO);
    toast.success('Restored official LEAMSS corporate logo');
  };

  // Apply custom URL logo
  const handleApplyLogoUrl = () => {
    if (!customLogoUrl.trim()) return;
    updateField('logoUrl', customLogoUrl.trim());
    setShowUrlInput(false);
    toast.success('Logo URL updated!');
  };

  // Restore entire template
  const handleRestoreDefaults = () => {
    const restored = parseSignatureHtml('', currentUser);
    setFormData(restored);
    const compiled = buildSignatureHtml(restored);
    setRawHtml(compiled);
    toast.success('Restored corporate standard signature defaults');
  };

  // Save handler
  const handleSave = () => {
    const finalHtml = editorMode === 'visual' ? buildSignatureHtml(formData) : rawHtml;
    if (onSave) {
      onSave(finalHtml);
    }
  };

  const isUsingDefaultLogo = formData.logoUrl === DEFAULT_LEAMSS_LOGO;

  return (
    <div className="space-y-4 text-xs">
      {/* Top Banner & Mode Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2.5 rounded-lg bg-indigo-50/80 border border-indigo-100 text-indigo-950">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-indigo-600 shrink-0" />
          <span className="text-[11px] leading-tight">
            <strong>Visual Signature Editor:</strong> Edit fields directly below. Your signature updates instantly in the live preview and auto-applies to all composed emails.
          </span>
        </div>
        <div className="inline-flex items-center bg-white p-0.5 rounded-lg border border-indigo-200 shrink-0 shadow-2xs">
          <button
            type="button"
            onClick={() => {
              if (editorMode === 'html') {
                setFormData(parseSignatureHtml(rawHtml, currentUser));
              }
              setEditorMode('visual');
            }}
            className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center gap-1 transition-all ${
              editorMode === 'visual'
                ? 'bg-indigo-600 text-white shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Sparkles className="w-3 h-3" />
            Visual Editor
          </button>
          <button
            type="button"
            onClick={() => {
              if (editorMode === 'visual') {
                setRawHtml(buildSignatureHtml(formData));
              }
              setEditorMode('html');
            }}
            className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center gap-1 transition-all ${
              editorMode === 'html'
                ? 'bg-indigo-600 text-white shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Code className="w-3 h-3" />
            HTML Code
          </button>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* MODE 1: VISUAL FORM (NO HTML CODE REQUIRED) */}
      {/* ──────────────────────────────────────────────────────────── */}
      {editorMode === 'visual' ? (
        <div className="space-y-3.5 bg-slate-50/60 p-3.5 rounded-xl border border-slate-200">
          {/* Logo Section */}
          <div className="bg-white p-3 rounded-lg border border-slate-200/90 shadow-2xs space-y-2">
            <div className="flex items-center justify-between">
              <label className="font-semibold text-slate-800 flex items-center gap-1.5 text-xs">
                <ImageIcon className="w-3.5 h-3.5 text-indigo-600" />
                Company Logo in Signature
              </label>
              <div className="flex items-center gap-1.5">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/png, image/jpeg, image/svg+xml, image/webp"
                  onChange={handleLogoUpload}
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold rounded-md text-[11px] border border-indigo-200 flex items-center gap-1 transition-colors"
                >
                  <Upload className="w-3 h-3" />
                  Upload New Logo
                </button>
                {!isUsingDefaultLogo && (
                  <button
                    type="button"
                    onClick={handleResetLogo}
                    className="px-2 py-1 text-slate-600 hover:text-slate-900 font-medium rounded-md text-[11px] border border-slate-200 flex items-center gap-1"
                    title="Reset to corporate LEAMSS logo"
                  >
                    <RotateCcw className="w-3 h-3" />
                    Reset to LEAMSS Logo
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setShowUrlInput(!showUrlInput)}
                  className="text-[11px] text-slate-400 hover:text-indigo-600 underline ml-1"
                >
                  {showUrlInput ? 'Hide URL' : 'Image URL'}
                </button>
              </div>
            </div>

            {/* Logo Preview Banner */}
            <div className="flex items-center gap-3 p-2 bg-slate-50 rounded border border-slate-100">
              <div className="bg-white p-1.5 rounded border border-slate-200 flex items-center justify-center min-w-[72px] h-[46px] shadow-2xs">
                {formData.logoUrl ? (
                  <img
                    src={formData.logoUrl}
                    alt="Active Signature Logo"
                    className="max-h-[38px] max-w-[80px] object-contain"
                  />
                ) : (
                  <span className="text-[10px] text-slate-400 italic">No Logo</span>
                )}
              </div>
              <div className="flex-1 text-[11px]">
                <div className="font-semibold text-slate-700 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                  {isUsingDefaultLogo ? 'Official LEAMSS Corporate Logo (Active)' : 'Custom Uploaded Logo (Active)'}
                </div>
                <div className="text-slate-500 text-[10px]">
                  Renders at 38px height with crisp high-resolution scaling across all email clients.
                </div>
              </div>
            </div>

            {/* Custom URL Input Field (Collapsible) */}
            {showUrlInput && (
              <div className="flex items-center gap-1.5 pt-1.5 border-t border-slate-100">
                <input
                  type="url"
                  placeholder="https://example.com/logo.png"
                  value={customLogoUrl}
                  onChange={(e) => setCustomLogoUrl(e.target.value)}
                  className="flex-1 px-2 py-1 text-xs border border-slate-200 rounded outline-none focus:border-indigo-500"
                />
                <button
                  type="button"
                  onClick={handleApplyLogoUrl}
                  className="px-2.5 py-1 bg-slate-800 text-white rounded text-xs font-semibold hover:bg-slate-900"
                >
                  Apply
                </button>
              </div>
            )}
          </div>

          {/* Form Fields: Grid Layout */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Full Name */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1 flex items-center gap-1">
                <User className="w-3 h-3 text-slate-400" />
                Full Name
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => updateField('name', e.target.value)}
                placeholder="e.g. Pooja Patil"
                className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded-lg outline-none focus:border-indigo-500 font-medium"
              />
            </div>

            {/* Job Title / Designation */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1 flex items-center gap-1">
                <PenTool className="w-3 h-3 text-slate-400" />
                Job Title / Designation
              </label>
              <input
                type="text"
                value={formData.designation}
                onChange={(e) => updateField('designation', e.target.value)}
                placeholder="e.g. Senior Immigration & Visa Advisor"
                className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded-lg outline-none focus:border-indigo-500 font-medium"
              />
            </div>

            {/* Phone Number */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1 flex items-center gap-1">
                <Phone className="w-3 h-3 text-slate-400" />
                Contact Phone / WhatsApp
              </label>
              <input
                type="text"
                value={formData.phone}
                onChange={(e) => updateField('phone', e.target.value)}
                placeholder="e.g. +91 74004 03105"
                className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded-lg outline-none focus:border-indigo-500 font-medium"
              />
            </div>

            {/* Official Email */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1 flex items-center gap-1">
                <Mail className="w-3 h-3 text-slate-400" />
                Official Email
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => updateField('email', e.target.value)}
                placeholder="e.g. pooja@leamss.com"
                className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded-lg outline-none focus:border-indigo-500 font-medium"
              />
            </div>

            {/* Company Name */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1 flex items-center gap-1">
                <Building2 className="w-3 h-3 text-slate-400" />
                Company Name
              </label>
              <input
                type="text"
                value={formData.company}
                onChange={(e) => updateField('company', e.target.value)}
                placeholder="Ladhani Education And Migration Services Pvt Ltd."
                className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded-lg outline-none focus:border-indigo-500 text-slate-700"
              />
            </div>

            {/* CIN / Corporate Registration */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1 flex items-center gap-1">
                <FileText className="w-3 h-3 text-slate-400" />
                CIN / Registration Number
              </label>
              <input
                type="text"
                value={formData.cin}
                onChange={(e) => updateField('cin', e.target.value)}
                placeholder="CIN-U85500MH2024OPC420610"
                className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded-lg outline-none focus:border-indigo-500 text-slate-700"
              />
            </div>

            {/* Website URL */}
            <div className="sm:col-span-2">
              <label className="block text-[11px] font-semibold text-slate-700 mb-1 flex items-center gap-1">
                <Globe className="w-3 h-3 text-slate-400" />
                Website URL
              </label>
              <input
                type="text"
                value={formData.website}
                onChange={(e) => updateField('website', e.target.value)}
                placeholder="www.leamss.com"
                className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded-lg outline-none focus:border-indigo-500 text-slate-700"
              />
            </div>
          </div>
        </div>
      ) : (
        /* ──────────────────────────────────────────────────────────── */
        /* MODE 2: RAW HTML CODE (ADVANCED) */
        /* ──────────────────────────────────────────────────────────── */
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="font-semibold text-slate-700 flex items-center gap-1.5">
              <Code className="w-3.5 h-3.5 text-slate-500" />
              Raw Signature HTML Source
            </label>
            <span className="text-[10px] text-slate-400">
              Preserves standard container <code className="bg-slate-100 px-1 py-0.5 rounded">.leamss-signature-block</code>
            </span>
          </div>
          <textarea
            rows={7}
            value={rawHtml}
            onChange={(e) => setRawHtml(e.target.value)}
            placeholder="Paste or customize your email signature HTML..."
            className="w-full p-2.5 font-mono text-[11px] bg-slate-900 text-emerald-400 rounded-lg border border-slate-700 outline-none focus:border-indigo-500 leading-relaxed shadow-inner"
          />
        </div>
      )}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* LIVE VISUAL PREVIEW (ALWAYS VISIBLE & INSTANTLY UPDATED) */}
      {/* ──────────────────────────────────────────────────────────── */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label className="font-bold text-slate-800 flex items-center gap-1.5 text-xs">
            <Eye className="w-3.5 h-3.5 text-emerald-600" />
            Live Visual Preview
            <span className="font-normal text-slate-500 text-[10px]">(What clients see in emails)</span>
          </label>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleRestoreDefaults}
              className="text-[11px] text-indigo-600 hover:text-indigo-800 font-semibold flex items-center gap-1"
            >
              <RotateCcw className="w-3 h-3" />
              Restore Corporate Defaults
            </button>
            <span className="text-[10px] bg-emerald-50 text-emerald-700 font-semibold px-2 py-0.5 rounded-full border border-emerald-200 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              Live Sync
            </span>
          </div>
        </div>

        {/* Mock Email Message Card with Rendered Signature */}
        <div className="p-4 border border-slate-200 rounded-xl bg-white shadow-2xs overflow-x-auto min-h-[140px] max-h-60 transition-all">
          <div
            dangerouslySetInnerHTML={{
              __html: editorMode === 'visual' ? buildSignatureHtml(formData) : rawHtml
            }}
          />
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* ACTIONS */}
      {/* ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between pt-2 border-t border-slate-200">
        <div className="text-[11px] text-slate-500">
          Default signature saves permanently to your profile.
        </div>
        <div className="flex items-center gap-2">
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 font-medium text-xs transition-colors"
            >
              Close
            </button>
          )}
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving}
            className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs flex items-center gap-1.5 shadow-sm transition-all disabled:opacity-50"
          >
            {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
            Save Default Signature
          </button>
        </div>
      </div>
    </div>
  );
}
