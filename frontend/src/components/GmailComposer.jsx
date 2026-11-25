import React, { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import axios from 'axios';
import { toast } from 'sonner';
import {
  Bold, Italic, Underline, Strikethrough,
  AlignLeft, AlignCenter, AlignRight, AlignJustify,
  List, ListOrdered, Indent, Outdent, Quote,
  Link as LinkIcon, Unlink, Image as ImageIcon, Paperclip,
  Smile, PenTool, Trash2, Send, Minus, Maximize2, Minimize2,
  X, Type, Palette, ChevronDown, Check, Loader2,
  FileText, File, Sparkles, LayoutTemplate, Undo2, Redo2,
  RemoveFormatting, AlertCircle, CheckCircle2, Upload, ExternalLink, Settings, Copy
} from 'lucide-react';
import EmailSignatureEditor from './EmailSignatureEditor';

const API = process.env.REACT_APP_BACKEND_URL ? `${process.env.REACT_APP_BACKEND_URL}/api` : '/api';

const FONT_FAMILIES = [
  { label: 'Sans Serif', value: 'Arial, sans-serif' },
  { label: 'Serif', value: 'Georgia, serif' },
  { label: 'Fixed Width', value: 'monospace' },
  { label: 'Wide', value: 'Arial Black, sans-serif' },
  { label: 'Garamond', value: 'Garamond, serif' },
  { label: 'Georgia', value: 'Georgia, serif' },
  { label: 'Tahoma', value: 'Tahoma, sans-serif' },
  { label: 'Trebuchet MS', value: '"Trebuchet MS", sans-serif' },
  { label: 'Verdana', value: 'Verdana, sans-serif' }
];

const FONT_SIZES = [
  { label: 'Small', value: '1', cssSize: '12px' },
  { label: 'Normal', value: '3', cssSize: '14px' },
  { label: 'Large', value: '5', cssSize: '18px' },
  { label: 'Huge', value: '7', cssSize: '24px' }
];

const TEXT_COLORS = [
  '#000000', '#434343', '#666666', '#999999', '#b7b7b7', '#cccccc', '#d9d9d9', '#efefef', '#f3f3f3', '#ffffff',
  '#980000', '#ff0000', '#ff9900', '#ffff00', '#00ff00', '#00ffff', '#4a86e8', '#0000ff', '#9900ff', '#ff00ff',
  '#e6b8af', '#f4cccc', '#fce5cd', '#fff2cc', '#d9ead3', '#d0e0e3', '#c9daf8', '#cfe2f3', '#d9d2e9', '#ead1dc',
  '#dd7e6b', '#ea9999', '#f9cb9c', '#ffe599', '#b6d7a8', '#a2c4c9', '#a4c2f4', '#9fc5e8', '#b4a7d6', '#d5a6bd',
  '#cc4125', '#e06666', '#f6b26b', '#ffd966', '#93c47d', '#76a5af', '#6d9eeb', '#6fa8dc', '#8e7cc3', '#c27ba0',
  '#a61c1c', '#cc0000', '#e69138', '#f1c232', '#6aa84f', '#45818e', '#3c78d8', '#3d85c6', '#674ea7', '#a64d79',
  '#852020', '#990000', '#b45f06', '#bf9000', '#38761d', '#134f5c', '#1155cc', '#0b5394', '#351c75', '#741b47',
  '#5b0f00', '#660000', '#783f04', '#7f6000', '#274e13', '#0c343d', '#1c4587', '#073763', '#20124d', '#4c1130'
];

const COMMON_EMOJIS = [
  '👋', '🤝', '✈️', '📄', '📅', '🌟', '✅', '📞', '✉️', '🇦🇺',
  '🇨🇦', '💼', '📍', '💡', '🔔', '⏳', '📌', '🎯', '🚀', '🙏',
  '👍', '👏', '🎉', '😊', '💬', '✍️', '📑', '🌏', '🛡️', '⭐'
];

function formatBytes(bytes, decimals = 1) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

export default function GmailComposer({
  isOpen,
  onClose,
  selectedLead,
  recipientEmail = '',
  initialSubject = '',
  initialBody = '',
  threadId = null,
  emailTemplates = [],
  emailServiceStatus = null,
  onEmailSent,
  currentUser = null,
  onOpenMailboxConfig,
  isExternalModalOpen = false
}) {
  // Window states: 'normal' | 'minimized' | 'maximized'
  const [windowState, setWindowState] = useState('normal');
  const savedWindowStateRef = useRef('normal');
  const wasExternalModalOpenRef = useRef(false);
  const [showFormatting, setShowFormatting] = useState(true);

  // Email Fields
  const [to, setTo] = useState('');
  const [cc, setCc] = useState('');
  const [bcc, setBcc] = useState('');
  const [showCc, setShowCc] = useState(false);
  const [showBcc, setShowBcc] = useState(false);
  const [subject, setSubject] = useState('');
  const [notifyByEmail, setNotifyByEmail] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState('');

  // Attachments
  const [attachments, setAttachments] = useState([]);
  const [uploadingAttachment, setUploadingAttachment] = useState(false);

  // Modals & Popovers
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [linkText, setLinkText] = useState('');
  const [linkUrl, setLinkUrl] = useState('');

  const [showImageModal, setShowImageModal] = useState(false);
  const [imageTab, setImageTab] = useState('upload'); // 'upload' | 'url'
  const [imageUrl, setImageUrl] = useState('');
  const [uploadingImage, setUploadingImage] = useState(false);

  const [showColorPopover, setShowColorPopover] = useState(false);
  const [colorMode, setColorMode] = useState('text'); // 'text' | 'bg'

  const [showEmojiPopover, setShowEmojiPopover] = useState(false);
  const [showSignatureMenu, setShowSignatureMenu] = useState(false);
  const [showSignatureModal, setShowSignatureModal] = useState(false);
  const [customSignatureHtml, setCustomSignatureHtml] = useState('');
  const [isCustomSignature, setIsCustomSignature] = useState(false);
  const [loadingSignature, setLoadingSignature] = useState(false);

  // AI Sales Assistant States
  const [showAiAssistant, setShowAiAssistant] = useState(false);
  const [aiEmailLoading, setAiEmailLoading] = useState(false);
  const [aiEmailQuery, setAiEmailQuery] = useState('');
  const [aiEmailResult, setAiEmailResult] = useState('');
  const [aiEmailSubject, setAiEmailSubject] = useState('');
  const [aiEmailTalkingPoints, setAiEmailTalkingPoints] = useState([]);

  // Sending state
  const [isSending, setIsSending] = useState(false);

  // Editor refs
  const editorRef = useRef(null);
  const savedSelectionRef = useRef(null);
  const fileInputRef = useRef(null);
  const imageInputRef = useRef(null);

  const getAuthHeader = useCallback(() => {
    const token = localStorage.getItem('token');
    return token ? { headers: { Authorization: `Bearer ${token}` } } : {};
  }, []);

  // Save active DOM selection before opening popovers/modals
  const saveSelection = useCallback(() => {
    const sel = window.getSelection();
    if (sel && sel.rangeCount > 0) {
      savedSelectionRef.current = sel.getRangeAt(0).cloneRange();
    }
  }, []);

  // Restore active DOM selection
  const restoreSelection = useCallback(() => {
    if (savedSelectionRef.current && editorRef.current) {
      editorRef.current.focus();
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(savedSelectionRef.current);
    }
  }, []);

  // Execute formatting command safely
  const formatDoc = useCallback((cmd, value = null) => {
    if (!editorRef.current) return;
    editorRef.current.focus();
    document.execCommand(cmd, false, value);
  }, []);

  // Template interpolation helper
  const interpolateTemplate = useCallback((text, lead) => {
    if (!text) return '';
    const nameVal = lead?.name || 'Client';
    const emailVal = lead?.email || '';
    const phoneVal = lead?.phone || '';
    const countryVal = lead?.country_of_interest || lead?.country || 'Australia';
    const programVal = lead?.program || lead?.visa_type || lead?.service || 'Immigration Assessment';
    const advisorVal = currentUser?.name || 'LEAMSS Immigration Advisor';
    const nowStr = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

    return text
      .replace(/\{\{?(client_name|name)\}?\}/gi, nameVal)
      .replace(/\{\{?(client_email|email)\}?\}/gi, emailVal)
      .replace(/\{\{?(phone|mobile)\}?\}/gi, phoneVal)
      .replace(/\{\{?(advisor|sales_person|consultant)\}?\}/gi, advisorVal)
      .replace(/\{\{?country\}?\}/gi, countryVal)
      .replace(/\{\{?(program|visa_type|service)\}?\}/gi, programVal)
      .replace(/\{\{?date\}?\}/gi, nowStr);
  }, [currentUser]);

  // Reliable signature detector ensuring anti-duplication
  const hasSignatureBlock = useCallback((html, sigHtml = '') => {
    if (!html) return false;
    if (html.includes('data-signature-block="true"') || html.includes('leamss-signature-block')) return true;
    if (html.includes('CIN-U85500MH2024OPC420610')) return true;
    if (html.includes('Ladhani Education') && html.includes('Services Pvt Ltd')) return true;
    if (sigHtml) {
      const textOnly = sigHtml.replace(/<[^>]*>/g, '').trim();
      if (textOnly && textOnly.length > 25 && html.includes(textOnly.slice(0, 30))) return true;
    }
    return false;
  }, []);

  // Load user default signature and automatically populate into editor
  const loadSignatureAndInit = useCallback(async (initialContent = '') => {
    let sig = customSignatureHtml;
    let isCustom = false;
    try {
      setLoadingSignature(true);
      const res = await axios.get(`${API}/crm/emails/signature`, getAuthHeader());
      if (res.data?.signature) {
        sig = res.data.signature;
        isCustom = Boolean(res.data.is_custom);
        setCustomSignatureHtml(sig);
        setIsCustomSignature(isCustom);
      }
    } catch (e) {
      console.error('Failed loading signature:', e);
    } finally {
      setLoadingSignature(false);
    }

    setTimeout(() => {
      if (!editorRef.current) return;

      const boundedSig = sig && !sig.includes('data-signature-block="true"')
        ? `<div class="leamss-signature-block" data-signature-block="true">${sig}</div>`
        : (sig || '');

      const rawInitial = (initialContent || '').trim();
      const alreadyHasSig = hasSignatureBlock(rawInitial, boundedSig);

      if (alreadyHasSig) {
        editorRef.current.innerHTML = rawInitial;
      } else if (!rawInitial) {
        // Fresh new email: focusable blank lines followed by default signature
        editorRef.current.innerHTML = `<p><br></p><p><br></p>${boundedSig}`;
      } else if (rawInitial.includes('<blockquote') || rawInitial.includes('On ') || rawInitial.includes('wrote:')) {
        // Reply / Thread: insert signature above quoted thread with blank line for typing
        editorRef.current.innerHTML = `<p><br></p>${boundedSig}<br/>${rawInitial}`;
      } else {
        editorRef.current.innerHTML = `${rawInitial}<br/><br/>${boundedSig}`;
      }

      editorRef.current.focus();
    }, 60);
  }, [getAuthHeader, hasSignatureBlock, customSignatureHtml]);

  // Load initial state when opened
  useEffect(() => {
    if (isOpen) {
      setWindowState('normal');
      const targetEmail = recipientEmail || selectedLead?.email || '';
      setTo(targetEmail);
      setSubject(initialSubject || '');
      setCc('');
      setBcc('');
      setShowCc(false);
      setShowBcc(false);
      setAttachments([]);
      setSelectedTemplateId('');
      setNotifyByEmail(false);

      // Automatically load and inject default signature
      loadSignatureAndInit(initialBody || '');
    }
  }, [isOpen, selectedLead, recipientEmail, initialSubject, initialBody, loadSignatureAndInit]);

  const loadSignature = useCallback(async () => {
    try {
      setLoadingSignature(true);
      const res = await axios.get(`${API}/crm/emails/signature`, getAuthHeader());
      if (res.data?.signature) {
        setCustomSignatureHtml(res.data.signature);
        setIsCustomSignature(Boolean(res.data.is_custom));
      }
    } catch (e) {
      console.error('Failed loading signature:', e);
    } finally {
      setLoadingSignature(false);
    }
  }, [getAuthHeader]);

  // Minimize composer when an external modal (e.g. Email & Mailbox Settings) is open
  useEffect(() => {
    if (isExternalModalOpen) {
      setWindowState(current => {
        if (current !== 'minimized') {
          savedWindowStateRef.current = current;
          return 'minimized';
        }
        return current;
      });
      wasExternalModalOpenRef.current = true;
    } else if (wasExternalModalOpenRef.current) {
      wasExternalModalOpenRef.current = false;
      const targetState = savedWindowStateRef.current || 'normal';
      setWindowState(targetState);
      loadSignature();
    }
  }, [isExternalModalOpen, loadSignature]);

  const handleSaveSignature = async (overrideSig = null) => {
    const sigToSave = overrideSig !== null ? overrideSig : customSignatureHtml;
    try {
      const res = await axios.put(`${API}/crm/emails/signature`, { signature: sigToSave }, getAuthHeader());
      const savedSig = res.data?.signature || sigToSave;
      setCustomSignatureHtml(savedSig);
      setIsCustomSignature(true);
      toast.success('Default email signature saved!');
      setShowSignatureModal(false);

      // Cleanly replace existing signature in active editor without duplicating
      if (editorRef.current && hasSignatureBlock(editorRef.current.innerHTML)) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(`<div>${editorRef.current.innerHTML}</div>`, 'text/html');
        const existingBlock = doc.body.querySelector('.leamss-signature-block, [data-signature-block="true"]');
        if (existingBlock) {
          existingBlock.outerHTML = savedSig;
          editorRef.current.innerHTML = doc.body.firstChild.innerHTML;
        }
      }
    } catch (e) {
      toast.error('Failed saving signature');
    }
  };

  const handleInsertSignature = async (sigHtml = null) => {
    let htmlToInsert = sigHtml || customSignatureHtml;
    if (!htmlToInsert) {
      toast.info('No signature found. Customize your signature in Email Settings.');
      setShowSignatureModal(true);
      return;
    }

    if (!htmlToInsert.includes('data-signature-block="true"')) {
      htmlToInsert = `<div class="leamss-signature-block" data-signature-block="true">${htmlToInsert}</div>`;
    }

    if (!editorRef.current) return;
    editorRef.current.focus();
    const currentHtml = editorRef.current.innerHTML;

    // Strict Anti-Duplication: Replace existing signature block if present
    if (hasSignatureBlock(currentHtml)) {
      const parser = new DOMParser();
      const doc = parser.parseFromString(`<div>${currentHtml}</div>`, 'text/html');
      const existingBlock = doc.body.querySelector('.leamss-signature-block, [data-signature-block="true"]');
      if (existingBlock) {
        existingBlock.outerHTML = htmlToInsert;
        editorRef.current.innerHTML = doc.body.firstChild.innerHTML;
        toast.success('Signature updated in email');
      } else {
        toast.info('Signature is already included in this email');
      }
    } else {
      editorRef.current.innerHTML = `${currentHtml}<br/>${htmlToInsert}`;
      toast.success('Signature added to email');
    }

    // Auto-save as permanent default on first manual addition!
    if (!isCustomSignature) {
      try {
        await axios.put(`${API}/crm/emails/signature`, { signature: htmlToInsert }, getAuthHeader());
        setIsCustomSignature(true);
        toast.success('Saved as default signature! It will now appear automatically in all new emails.');
      } catch (err) {
        console.warn('Auto-save signature on first add:', err);
      }
    }

    setShowSignatureMenu(false);
  };

  // Handle template selection
  const handleSelectTemplate = (tplId) => {
    setSelectedTemplateId(tplId);
    const tpl = emailTemplates.find(t => t.id === tplId);
    if (!tpl || !editorRef.current) return;

    const interpolatedSubj = interpolateTemplate(tpl.subject || '', selectedLead);
    const rawBody = tpl.body || tpl.body_html || '';
    const interpolatedBody = interpolateTemplate(rawBody, selectedLead);

    setSubject(interpolatedSubj);

    // Format body as paragraphs if plain text
    let formattedHtml = interpolatedBody;
    if (!formattedHtml.trim().startsWith('<')) {
      formattedHtml = formattedHtml
        .split('\n\n')
        .map(p => `<p>${p.replace(/\n/g, '<br/>')}</p>`)
        .join('');
    }

    // Auto-append signature if not already present
    const boundedSig = customSignatureHtml && !customSignatureHtml.includes('data-signature-block="true"')
      ? `<div class="leamss-signature-block" data-signature-block="true">${customSignatureHtml}</div>`
      : customSignatureHtml;

    if (boundedSig && !hasSignatureBlock(formattedHtml, boundedSig)) {
      formattedHtml += `<br/>${boundedSig}`;
    }

    editorRef.current.innerHTML = formattedHtml;
    editorRef.current.focus();
    toast.success(`Template "${tpl.name}" applied`);
  };

  // ────────────────────────────────────────────────────────────
  // AI SALES COMMUNICATION ASSISTANT (Email Proposals & Replies)
  // ────────────────────────────────────────────────────────────
  const handleGenerateAiEmail = async (intent = 'fees_proposal', customQuery = '') => {
    setAiEmailLoading(true);
    setShowAiAssistant(true);
    try {
      const q = customQuery || aiEmailQuery || (
        intent === 'fees_proposal' ? 'Provide official fee slabs and LEAMSS retainer breakdown' :
        intent === 'document_checklist' ? 'List mandatory documents required to initiate application' :
        intent === 'eligibility_breakdown' ? 'Explain eligibility criteria, points calculation and pass mark' :
        'Draft a comprehensive sales reply regarding migration pathways'
      );

      const res = await axios.post(`${API}/crm/ai/suggest-reply`, {
        channel: 'email',
        intent_type: intent,
        client_message: q,
        lead_id: selectedLead?.id,
        target_country: selectedLead?.interested_country || selectedLead?.country,
        service_interested: selectedLead?.service || selectedLead?.interested_program,
        lead_context: {
          name: selectedLead?.name || 'Valued Client',
          country: selectedLead?.interested_country || selectedLead?.country,
          service: selectedLead?.service || selectedLead?.interested_program,
          sales_rep_name: currentUser?.name || 'LEAMSS Consultant'
        }
      }, getAuthHeader());

      if (res.data?.success) {
        setAiEmailResult(res.data.suggested_text || res.data.reply_text || '');
        if (res.data.subject) {
          setAiEmailSubject(res.data.subject);
        }
        setAiEmailTalkingPoints(res.data.talking_points || []);
        toast.success('AI Email draft ready!');
      } else {
        toast.error('Could not generate AI email');
      }
    } catch (err) {
      console.error('Error generating AI email:', err);
      toast.error(err.response?.data?.detail || 'Failed to generate AI email');
    } finally {
      setAiEmailLoading(false);
    }
  };

  const handleApplyAiEmail = () => {
    if (!aiEmailResult || !editorRef.current) return;
    if (aiEmailSubject) {
      setSubject(aiEmailSubject);
    }

    let formattedHtml = aiEmailResult;
    if (!formattedHtml.trim().startsWith('<')) {
      formattedHtml = formattedHtml
        .split('\n\n')
        .map(p => `<p style="margin-bottom: 12px; line-height: 1.6;">${p.replace(/\n/g, '<br/>')}</p>`)
        .join('');
    }

    // Append signature if available
    const boundedSig = customSignatureHtml && !customSignatureHtml.includes('data-signature-block="true"')
      ? `<div class="leamss-signature-block" data-signature-block="true">${customSignatureHtml}</div>`
      : customSignatureHtml;

    if (boundedSig && !hasSignatureBlock(formattedHtml, boundedSig)) {
      formattedHtml += `<br/>${boundedSig}`;
    }

    editorRef.current.innerHTML = formattedHtml;
    editorRef.current.focus();
    toast.success('AI draft inserted into email editor!');
  };

  // Attachments upload handler
  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    setUploadingAttachment(true);
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);

        const res = await axios.post(`${API}/crm/emails/attachments/upload`, formData, {
          headers: {
            ...getAuthHeader().headers,
            'Content-Type': 'multipart/form-data'
          }
        });

        if (res.data?.success) {
          setAttachments(prev => [
            ...prev,
            {
              id: res.data.id,
              filename: res.data.filename,
              saved_filename: res.data.saved_filename,
              content_type: res.data.content_type,
              size: res.data.size,
              url: res.data.url
            }
          ]);
        }
      }
      toast.success(`${files.length} attachment${files.length > 1 ? 's' : ''} added`);
    } catch (err) {
      console.error('Attachment upload failed:', err);
      toast.error('Failed uploading attachment');
    } finally {
      setUploadingAttachment(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const removeAttachment = (indexToRemove) => {
    setAttachments(prev => prev.filter((_, idx) => idx !== indexToRemove));
  };

  // Inline Image Insertion
  const handleInsertImage = async () => {
    if (imageTab === 'url') {
      if (!imageUrl || !imageUrl.trim()) {
        toast.error('Please enter a valid image URL');
        return;
      }
      restoreSelection();
      const imgHtml = `<p><img src="${imageUrl.trim()}" alt="embedded image" style="max-width: 100%; border-radius: 6px; margin: 8px 0; display: inline-block;" /></p><p><br/></p>`;
      document.execCommand('insertHTML', false, imgHtml);
      setImageUrl('');
      setShowImageModal(false);
    } else {
      // Local image upload
      if (!imageInputRef.current?.files?.[0]) {
        toast.error('Please select an image file');
        return;
      }
      const file = imageInputRef.current.files[0];
      setUploadingImage(true);
      try {
        const formData = new FormData();
        formData.append('file', file);
        const res = await axios.post(`${API}/crm/emails/attachments/upload`, formData, {
          headers: {
            ...getAuthHeader().headers,
            'Content-Type': 'multipart/form-data'
          }
        });

        if (res.data?.url) {
          restoreSelection();
          const imgHtml = `<p><img src="${res.data.url}" alt="${file.name}" style="max-width: 100%; border-radius: 6px; margin: 8px 0; display: inline-block;" /></p><p><br/></p>`;
          document.execCommand('insertHTML', false, imgHtml);
          setShowImageModal(false);
          toast.success('Image inserted into email');
        }
      } catch (err) {
        toast.error('Failed uploading image');
      } finally {
        setUploadingImage(false);
        if (imageInputRef.current) imageInputRef.current.value = '';
      }
    }
  };

  // Hyperlink Insertion
  const handleInsertLink = () => {
    if (!linkUrl || !linkUrl.trim()) {
      toast.error('Please enter a link target URL');
      return;
    }
    let validUrl = linkUrl.trim();
    if (!validUrl.startsWith('http://') && !validUrl.startsWith('https://') && !validUrl.startsWith('mailto:')) {
      validUrl = `https://${validUrl}`;
    }

    restoreSelection();
    if (linkText && savedSelectionRef.current && savedSelectionRef.current.collapsed) {
      const linkHtml = `<a href="${validUrl}" target="_blank" style="color: #2563eb; text-decoration: underline;">${linkText}</a>`;
      document.execCommand('insertHTML', false, linkHtml);
    } else {
      document.execCommand('createLink', false, validUrl);
    }

    setLinkUrl('');
    setLinkText('');
    setShowLinkModal(false);
  };

  // Emoji Insertion
  const handleInsertEmoji = (emoji) => {
    restoreSelection();
    document.execCommand('insertText', false, emoji);
    setShowEmojiPopover(false);
  };

  // Color Selection
  const handleApplyColor = (color) => {
    restoreSelection();
    if (colorMode === 'text') {
      document.execCommand('foreColor', false, color);
    } else {
      document.execCommand('hiliteColor', false, color);
    }
    setShowColorPopover(false);
  };

  // Send Email Handler
  const handleSend = async () => {
    const cleanTo = (to || '').trim();
    if (!cleanTo || !cleanTo.includes('@')) {
      toast.error('Please enter a valid recipient email');
      return;
    }

    const cleanSubject = (subject || '').trim();
    if (!cleanSubject) {
      toast.error('Please enter an email subject line');
      return;
    }

    let htmlContent = editorRef.current ? editorRef.current.innerHTML.trim() : '';
    const textContent = editorRef.current ? editorRef.current.innerText.trim() : '';
    if (!textContent && !htmlContent.includes('<img')) {
      toast.error('Please compose an email message before sending');
      return;
    }

    // Ensure no duplicate signature blocks before dispatch
    if (editorRef.current) {
      const sigBlocks = editorRef.current.querySelectorAll('.leamss-signature-block, [data-signature-block="true"]');
      if (sigBlocks.length > 1) {
        for (let i = 0; i < sigBlocks.length - 1; i++) {
          sigBlocks[i].remove();
        }
        htmlContent = editorRef.current.innerHTML.trim();
      }
    }

    setIsSending(true);
    try {
      const payload = {
        lead_id: selectedLead?.id,
        to_email: cleanTo,
        contact_name: selectedLead?.name || cleanTo.split('@')[0],
        subject: cleanSubject,
        body_html: htmlContent,
        template_id: selectedTemplateId || null,
        thread_id: threadId || undefined,
        notify_by_email: notifyByEmail,
        save_as_default_signature: !isCustomSignature,
        cc: cc.trim() || undefined,
        bcc: bcc.trim() || undefined,
        attachments: attachments
      };

      const res = await axios.post(`${API}/crm/emails/send`, payload, getAuthHeader());

      const status = res.data.status;
      if (status === 'delivered') {
        if (res.data.fallback) {
          toast.success(`Email delivered to ${cleanTo} via relay! (Check Mailbox Settings for direct delivery notice)`);
        } else {
          toast.success(`Email delivered to ${cleanTo}`);
        }
      } else if (status === 'pending_configuration') {
        toast.success(`Email recorded in CRM. (Connect Mailbox App Password to send externally)`);
      } else if (status === 'failed') {
        toast.error(res.data.delivery_error || 'Email recorded, but mailbox rejected authentication.');
      } else {
        toast.success('Email sent successfully');
      }

      if (onEmailSent) {
        onEmailSent(res.data);
      }

      onClose();
    } catch (err) {
      console.error('Send error:', err);
      toast.error(err.response?.data?.detail || 'Failed delivering email');
    } finally {
      setIsSending(false);
    }
  };

  if (!isOpen) return null;

  // Minimized Floating Pill
  if (windowState === 'minimized') {
    return createPortal(
      <div
        data-gmail-composer="true"
        className="fixed bottom-0 right-8 z-40 w-80 bg-slate-900 text-white rounded-t-xl shadow-2xl border border-slate-700 flex items-center justify-between px-4 py-2.5 cursor-pointer hover:bg-slate-800 transition-all"
      >
        <div className="flex items-center gap-2 truncate" onClick={() => setWindowState('normal')}>
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
          <span className="font-semibold text-xs truncate">
            {subject ? subject : `Draft to: ${to || selectedLead?.name || 'New Message'}`}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setWindowState('normal')}
            className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-700"
            title="Expand"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-700"
            title="Close"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>,
      document.body
    );
  }

  // Normal or Maximized Compose Window
  const containerClasses = windowState === 'maximized'
    ? 'fixed inset-3 sm:inset-8 z-40 bg-white rounded-xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden animate-in fade-in duration-150'
    : 'fixed bottom-0 right-4 sm:right-8 z-40 w-full sm:w-[650px] max-w-[calc(100vw-16px)] h-[620px] max-h-[calc(100vh-40px)] bg-white rounded-t-xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden animate-in slide-in-from-bottom-4 duration-200';

  const composerContent = (
    <div data-gmail-composer="true" className={containerClasses}>
      {/* ──────────────────────────────────────────────────────────── */}
      {/* GMAIL HEADER BAR */}
      {/* ──────────────────────────────────────────────────────────── */}
      <div className="bg-slate-900 text-white px-4 py-2.5 flex items-center justify-between select-none shrink-0 rounded-t-xl">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-xs tracking-wide">
            {subject ? subject : 'New Message'}
          </span>
          {selectedLead?.name && (
            <span className="text-[11px] text-slate-400 hidden sm:inline">
              · {selectedLead.name}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setWindowState('minimized')}
            className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition-colors"
            title="Minimize"
          >
            <Minus className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setWindowState(windowState === 'maximized' ? 'normal' : 'maximized')}
            className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition-colors"
            title={windowState === 'maximized' ? 'Exit Full Screen' : 'Full Screen'}
          >
            {windowState === 'maximized' ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition-colors"
            title="Save draft and close"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* RECIPIENT FIELDS ("To", "Cc", "Bcc") */}
      {/* ──────────────────────────────────────────────────────────── */}
      <div className="border-b border-slate-100 bg-white shrink-0">
        {/* "To" Field */}
        <div className="flex items-center px-4 py-2 border-b border-slate-100 text-xs">
          <span className="text-slate-400 font-medium w-10 shrink-0">To</span>
          <div className="flex-1 flex items-center gap-1.5 min-w-0">
            {selectedLead?.name && selectedLead.email?.toLowerCase() === to?.toLowerCase() ? (
              <div className="inline-flex items-center gap-1.5 bg-indigo-50 border border-indigo-200 text-indigo-900 rounded-full px-2.5 py-0.5 text-xs font-semibold shrink-0">
                <span>{selectedLead.name}</span>
                <span className="text-indigo-600 font-normal text-[11px]">&lt;{to}&gt;</span>
                <button
                  type="button"
                  onClick={() => setTo('')}
                  className="hover:bg-indigo-200/60 rounded-full p-0.5 text-indigo-500 hover:text-indigo-900 ml-0.5"
                  title="Remove recipient"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ) : null}
            <input
              type="email"
              value={selectedLead?.name && selectedLead.email?.toLowerCase() === to?.toLowerCase() ? '' : to}
              onChange={(e) => setTo(e.target.value)}
              placeholder={selectedLead?.name && selectedLead.email?.toLowerCase() === to?.toLowerCase() ? '' : 'Recipients (client@example.com)'}
              className="flex-1 bg-transparent border-none outline-none text-xs text-slate-800 placeholder-slate-400 font-medium min-w-[120px]"
            />
          </div>
          <div className="flex items-center gap-1 text-[11px] font-semibold text-slate-500 shrink-0">
            {!showCc && (
              <button
                type="button"
                onClick={() => setShowCc(true)}
                className="hover:text-indigo-600 px-1 py-0.5 rounded hover:bg-slate-100"
              >
                Cc
              </button>
            )}
            {!showBcc && (
              <button
                type="button"
                onClick={() => setShowBcc(true)}
                className="hover:text-indigo-600 px-1 py-0.5 rounded hover:bg-slate-100"
              >
                Bcc
              </button>
            )}
          </div>
        </div>

        {/* Expandable "Cc" Field */}
        {showCc && (
          <div className="flex items-center px-4 py-1.5 border-b border-slate-100 text-xs animate-in fade-in duration-100">
            <span className="text-slate-400 font-medium w-10 shrink-0">Cc</span>
            <input
              type="text"
              value={cc}
              onChange={(e) => setCc(e.target.value)}
              placeholder="Add CC recipients (comma separated)"
              className="flex-1 bg-transparent border-none outline-none text-xs text-slate-800 placeholder-slate-400"
            />
            <button
              onClick={() => { setCc(''); setShowCc(false); }}
              className="text-slate-400 hover:text-slate-600 p-0.5"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        )}

        {/* Expandable "Bcc" Field */}
        {showBcc && (
          <div className="flex items-center px-4 py-1.5 border-b border-slate-100 text-xs animate-in fade-in duration-100">
            <span className="text-slate-400 font-medium w-10 shrink-0">Bcc</span>
            <input
              type="text"
              value={bcc}
              onChange={(e) => setBcc(e.target.value)}
              placeholder="Add BCC recipients (comma separated, blind copy)"
              className="flex-1 bg-transparent border-none outline-none text-xs text-slate-800 placeholder-slate-400"
            />
            <button
              onClick={() => { setBcc(''); setShowBcc(false); }}
              className="text-slate-400 hover:text-slate-600 p-0.5"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        )}

        {/* "Subject" Field */}
        <div className="flex items-center px-4 py-2 border-b border-slate-100 text-xs">
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Subject"
            className="w-full bg-transparent border-none outline-none text-xs font-semibold text-slate-900 placeholder-slate-400"
          />
        </div>

        {/* Admin Template Selector Strip */}
        <div className="px-4 py-1.5 bg-slate-50/80 flex items-center justify-between gap-2 border-b border-slate-100 text-[11px]">
          <div className="flex items-center gap-1.5 text-slate-600 min-w-0">
            <LayoutTemplate className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
            <span className="font-semibold text-slate-700 shrink-0">Template:</span>
            <select
              value={selectedTemplateId}
              onChange={(e) => handleSelectTemplate(e.target.value)}
              className="bg-white border border-slate-200 rounded px-2 py-0.5 text-[11px] text-slate-700 outline-none focus:border-indigo-500 max-w-[260px] truncate font-medium"
            >
              <option value="">-- Choose Admin Template --</option>
              {emailTemplates.map(tpl => (
                <option key={tpl.id} value={tpl.id}>
                  {tpl.name} ({tpl.category})
                </option>
              ))}
            </select>

            <button
              type="button"
              onClick={() => setShowAiAssistant(!showAiAssistant)}
              className={`px-2.5 py-0.5 rounded text-[11px] font-bold flex items-center gap-1.5 transition-all shrink-0 ${
                showAiAssistant
                  ? 'bg-purple-700 text-white shadow-xs'
                  : 'bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100'
              }`}
              title="AI Sales Assistant: Draft proposals, fee breakdowns, document requests"
            >
              <Sparkles className={`w-3.5 h-3.5 ${showAiAssistant ? 'text-amber-300' : 'text-purple-600'} animate-pulse`} />
              <span>AI Sales Assistant</span>
            </button>
          </div>

          {/* Mailbox Sending Badge & Email Settings */}
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[10px] text-emerald-700 font-semibold flex items-center gap-1 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
              From: {currentUser?.email || emailServiceStatus?.personal_mailbox?.smtp_user || 'sales mailbox'}
            </span>

            <button
              type="button"
              onClick={() => {
                if (onOpenMailboxConfig) {
                  savedWindowStateRef.current = windowState;
                  setWindowState('minimized');
                  onOpenMailboxConfig();
                } else {
                  setShowSignatureModal(true);
                }
              }}
              className="text-[10px] text-slate-700 hover:text-indigo-600 font-semibold flex items-center gap-1 bg-white hover:bg-slate-100 px-2 py-0.5 rounded border border-slate-200 transition-colors shadow-2xs"
              title="Configure Email & Default Signature Settings"
            >
              <Settings className="w-3 h-3 text-slate-500" />
              <span>Email Settings</span>
            </button>
          </div>
        </div>

        {/* ──────────────────────────────────────────────────────────── */}
        {/* AI SALES EMAIL ASSISTANT DRAWER */}
        {/* ──────────────────────────────────────────────────────────── */}
        {showAiAssistant && (
          <div className="bg-gradient-to-r from-purple-50/90 via-indigo-50/60 to-slate-50 border-b border-purple-200 p-3 space-y-2.5 animate-in slide-in-from-top-2 duration-150 text-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="p-1 rounded bg-purple-600 text-white">
                  <Sparkles className="w-3.5 h-3.5" />
                </span>
                <div>
                  <span className="font-bold text-slate-800 text-xs">AI Email Proposal & Reply Copilot</span>
                  <span className="ml-2 text-[10px] text-purple-700 bg-purple-100 px-1.5 py-0.5 rounded font-medium border border-purple-200">
                    {selectedLead?.interested_country || selectedLead?.country || 'Immigration'} Grounded
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowAiAssistant(false)}
                className="text-slate-400 hover:text-slate-700 p-1"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Preset Quick Actions */}
            <div className="flex flex-wrap items-center gap-1.5">
              <button
                type="button"
                onClick={() => handleGenerateAiEmail('fees_proposal', 'Draft complete formal fee proposal and installment schedule')}
                disabled={aiEmailLoading}
                className="px-2 py-1 bg-white hover:bg-purple-50 text-purple-800 border border-purple-200 rounded text-[11px] font-medium transition-colors"
              >
                💰 Formal Fee Proposal
              </button>
              <button
                type="button"
                onClick={() => handleGenerateAiEmail('eligibility_breakdown', 'Explain eligibility criteria, points calculation and pass mark')}
                disabled={aiEmailLoading}
                className="px-2 py-1 bg-white hover:bg-purple-50 text-purple-800 border border-purple-200 rounded text-[11px] font-medium transition-colors"
              >
                📊 Eligibility Breakdown
              </button>
              <button
                type="button"
                onClick={() => handleGenerateAiEmail('document_checklist', 'Provide comprehensive document submission checklist')}
                disabled={aiEmailLoading}
                className="px-2 py-1 bg-white hover:bg-purple-50 text-purple-800 border border-purple-200 rounded text-[11px] font-medium transition-colors"
              >
                📄 Document Checklist
              </button>
              <button
                type="button"
                onClick={() => handleGenerateAiEmail('process_roadmap', 'Explain step by step application timeline from filing to visa grant')}
                disabled={aiEmailLoading}
                className="px-2 py-1 bg-white hover:bg-purple-50 text-purple-800 border border-purple-200 rounded text-[11px] font-medium transition-colors"
              >
                🚀 Application Roadmap
              </button>
              <button
                type="button"
                onClick={() => handleGenerateAiEmail('objection_handling', 'Professional rebuttal addressing cost, timelines, and no guarantee disclaimer')}
                disabled={aiEmailLoading}
                className="px-2 py-1 bg-white hover:bg-purple-50 text-purple-800 border border-purple-200 rounded text-[11px] font-medium transition-colors"
              >
                🛡️ Follow-up & Rebuttal
              </button>
            </div>

            {/* Custom Instruction Box */}
            <div className="flex items-center gap-1.5 pt-0.5">
              <input
                type="text"
                placeholder="Or type specific instructions for email reply..."
                value={aiEmailQuery}
                onChange={(e) => setAiEmailQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !aiEmailLoading && aiEmailQuery.trim()) {
                    handleGenerateAiEmail('custom_email', aiEmailQuery);
                  }
                }}
                className="flex-1 bg-white border border-purple-200 rounded px-2.5 py-1 text-xs text-slate-800 outline-none focus:border-purple-400 placeholder:text-slate-400"
              />
              <button
                type="button"
                onClick={() => handleGenerateAiEmail('custom_email', aiEmailQuery)}
                disabled={aiEmailLoading || !aiEmailQuery.trim()}
                className="h-7 px-3 bg-purple-700 hover:bg-purple-800 text-white rounded text-xs font-bold transition-colors disabled:opacity-50 flex items-center gap-1 shrink-0"
              >
                {aiEmailLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                <span>Generate Draft</span>
              </button>
            </div>

            {/* AI Generated Preview & Insert Button */}
            {aiEmailResult && (
              <div className="bg-white border border-purple-300 rounded-lg p-2.5 space-y-2 mt-1 shadow-2xs">
                <div className="flex items-center justify-between border-b border-purple-100 pb-1.5">
                  <span className="font-semibold text-purple-900 text-[11px] flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-purple-600" />
                    AI Draft Preview ({aiEmailSubject ? `Subject: ${aiEmailSubject}` : 'Ready to Insert'})
                  </span>
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() => {
                        navigator.clipboard.writeText(`${aiEmailSubject ? `Subject: ${aiEmailSubject}\n\n` : ''}${aiEmailResult}`);
                        toast.success('Email draft copied to clipboard!');
                      }}
                      className="text-[10px] text-slate-600 hover:text-slate-900 px-2 py-0.5 rounded border border-slate-200 hover:bg-slate-50 flex items-center gap-1"
                    >
                      <Copy className="w-3 h-3" /> Copy
                    </button>
                    <button
                      type="button"
                      onClick={handleApplyAiEmail}
                      className="text-[11px] bg-purple-700 hover:bg-purple-800 text-white font-bold px-2.5 py-1 rounded flex items-center gap-1 shadow-2xs"
                    >
                      <Check className="w-3 h-3" /> Insert into Email
                    </button>
                  </div>
                </div>

                <div className="text-[11px] text-slate-700 leading-relaxed font-sans max-h-36 overflow-y-auto whitespace-pre-wrap bg-slate-50 p-2 rounded border border-slate-100">
                  {aiEmailResult}
                </div>

                {aiEmailTalkingPoints.length > 0 && (
                  <div className="flex flex-wrap gap-1 text-[10px] text-purple-800 pt-0.5">
                    <span className="font-semibold text-slate-500">Key Facts:</span>
                    {aiEmailTalkingPoints.map((tp, idx) => (
                      <span key={idx} className="bg-purple-50 border border-purple-200 px-1.5 py-0.5 rounded">
                        {tp}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* RICH TEXT EDITABLE CANVAS */}
      {/* ──────────────────────────────────────────────────────────── */}
      <div className="flex-1 relative flex flex-col min-h-0 bg-white overflow-hidden">
        <div
          ref={editorRef}
          contentEditable={true}
          onBlur={saveSelection}
          onKeyUp={saveSelection}
          onMouseUp={saveSelection}
          className="flex-1 p-4 overflow-y-auto outline-none text-slate-800 text-xs sm:text-sm font-sans leading-relaxed selection:bg-indigo-100 selection:text-indigo-900 focus:outline-none"
          style={{
            fontFamily: 'Arial, Helvetica, sans-serif',
            minHeight: '120px'
          }}
          data-placeholder="Type your message here..."
        />

        {/* ──────────────────────────────────────────────────────────── */}
        {/* ATTACHMENTS TRAY */}
        {/* ──────────────────────────────────────────────────────────── */}
        {attachments.length > 0 && (
          <div className="px-4 py-2 bg-slate-50/90 border-t border-slate-200 flex flex-wrap gap-2 max-h-24 overflow-y-auto shrink-0">
            {attachments.map((att, idx) => (
              <div
                key={att.id || idx}
                className="inline-flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-xs shadow-xs hover:border-slate-300 transition-colors"
              >
                {att.content_type?.includes('pdf') ? (
                  <FileText className="w-3.5 h-3.5 text-rose-500 shrink-0" />
                ) : att.content_type?.includes('image') ? (
                  <ImageIcon className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                ) : (
                  <File className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                )}
                <span className="font-semibold text-slate-800 max-w-[140px] truncate" title={att.filename}>
                  {att.filename}
                </span>
                <span className="text-[10px] text-slate-400 font-mono">
                  ({formatBytes(att.size)})
                </span>
                <button
                  type="button"
                  onClick={() => removeAttachment(idx)}
                  className="text-slate-400 hover:text-rose-600 rounded p-0.5"
                  title="Remove attachment"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* ──────────────────────────────────────────────────────────── */}
        {/* FLOATING / DOCKED FORMATTING TOOLBAR ("Aa") */}
        {/* ──────────────────────────────────────────────────────────── */}
        {showFormatting && (
          <div className="px-3 py-1.5 bg-slate-50 border-t border-slate-200 flex items-center flex-wrap gap-1 text-slate-700 shrink-0 select-none">
            {/* Undo / Redo */}
            <button
              type="button"
              onMouseDown={(e) => { e.preventDefault(); formatDoc('undo'); }}
              className="p-1.5 hover:bg-slate-200 rounded text-slate-600 hover:text-slate-900 transition-colors"
              title="Undo (Ctrl+Z)"
            >
              <Undo2 className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onMouseDown={(e) => { e.preventDefault(); formatDoc('redo'); }}
              className="p-1.5 hover:bg-slate-200 rounded text-slate-600 hover:text-slate-900 transition-colors"
              title="Redo (Ctrl+Y)"
            >
              <Redo2 className="w-3.5 h-3.5" />
            </button>

            <span className="w-px h-4 bg-slate-300 mx-1"></span>

            {/* Font Family Dropdown */}
            <select
              onChange={(e) => formatDoc('fontName', e.target.value)}
              className="h-7 text-xs bg-white border border-slate-200 rounded px-1.5 text-slate-700 outline-none cursor-pointer hover:border-slate-300 font-medium"
              title="Font Family"
            >
              {FONT_FAMILIES.map(f => (
                <option key={f.value} value={f.value}>{f.label}</option>
              ))}
            </select>

            {/* Font Size Dropdown */}
            <select
              onChange={(e) => formatDoc('fontSize', e.target.value)}
              defaultValue="3"
              className="h-7 text-xs bg-white border border-slate-200 rounded px-1.5 text-slate-700 outline-none cursor-pointer hover:border-slate-300 font-medium"
              title="Font Size"
            >
              {FONT_SIZES.map(s => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>

            <span className="w-px h-4 bg-slate-300 mx-1"></span>

            {/* Bold, Italic, Underline, Strikethrough */}
            <button
              type="button"
              onMouseDown={(e) => { e.preventDefault(); formatDoc('bold'); }}
              className="p-1.5 hover:bg-slate-200 rounded text-slate-700 font-bold hover:text-slate-900"
              title="Bold (Ctrl+B)"
            >
              <Bold className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onMouseDown={(e) => { e.preventDefault(); formatDoc('italic'); }}
              className="p-1.5 hover:bg-slate-200 rounded text-slate-700 italic hover:text-slate-900"
              title="Italic (Ctrl+I)"
            >
              <Italic className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onMouseDown={(e) => { e.preventDefault(); formatDoc('underline'); }}
              className="p-1.5 hover:bg-slate-200 rounded text-slate-700 underline hover:text-slate-900"
              title="Underline (Ctrl+U)"
            >
              <Underline className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onMouseDown={(e) => { e.preventDefault(); formatDoc('strikeThrough'); }}
              className="p-1.5 hover:bg-slate-200 rounded text-slate-700 hover:text-slate-900"
              title="Strikethrough"
            >
              <Strikethrough className="w-3.5 h-3.5" />
            </button>

            {/* Color Picker Button */}
            <div className="relative">
              <button
                type="button"
                onMouseDown={(e) => { e.preventDefault(); saveSelection(); setShowColorPopover(!showColorPopover); }}
                className="p-1.5 hover:bg-slate-200 rounded text-slate-700 hover:text-slate-900 flex items-center gap-0.5"
                title="Text / Background Color"
              >
                <Palette className="w-3.5 h-3.5 text-indigo-600" />
                <ChevronDown className="w-2.5 h-2.5 text-slate-400" />
              </button>

              {showColorPopover && (
                <div className="absolute bottom-8 left-0 z-[10000] bg-white border border-slate-200 rounded-lg shadow-xl p-3 w-64">
                  <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-slate-100 text-[11px] font-semibold">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => setColorMode('text')}
                        className={`px-2 py-0.5 rounded ${colorMode === 'text' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'}`}
                      >
                        Text Color
                      </button>
                      <button
                        type="button"
                        onClick={() => setColorMode('bg')}
                        className={`px-2 py-0.5 rounded ${colorMode === 'bg' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'}`}
                      >
                        Highlight
                      </button>
                    </div>
                    <button onClick={() => setShowColorPopover(false)} className="text-slate-400 hover:text-slate-600">
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                  <div className="grid grid-cols-10 gap-1">
                    {TEXT_COLORS.map(color => (
                      <button
                        key={color}
                        type="button"
                        onClick={() => handleApplyColor(color)}
                        style={{ backgroundColor: color }}
                        className="w-4 h-4 rounded-sm border border-slate-300 hover:scale-125 transition-transform"
                        title={color}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>

            <span className="w-px h-4 bg-slate-300 mx-1"></span>

            {/* Alignment Options */}
            <button
              type="button"
              onMouseDown={(e) => { e.preventDefault(); formatDoc('justifyLeft'); }}
              className="p-1.5 hover:bg-slate-200 rounded text-slate-700"
              title="Align Left"
            >
              <AlignLeft className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onMouseDown={(e) => { e.preventDefault(); formatDoc('justifyCenter'); }}
              className="p-1.5 hover:bg-slate-200 rounded text-slate-700"
              title="Align Center"
            >
              <AlignCenter className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onMouseDown={(e) => { e.preventDefault(); formatDoc('justifyRight'); }}
              className="p-1.5 hover:bg-slate-200 rounded text-slate-700"
              title="Align Right"
            >
              <AlignRight className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onMouseDown={(e) => { e.preventDefault(); formatDoc('justifyFull'); }}
              className="p-1.5 hover:bg-slate-200 rounded text-slate-700"
              title="Justify"
            >
              <AlignJustify className="w-3.5 h-3.5" />
            </button>

            <span className="w-px h-4 bg-slate-300 mx-1"></span>

            {/* Lists & Indentation */}
            <button
              type="button"
              onMouseDown={(e) => { e.preventDefault(); formatDoc('insertUnorderedList'); }}
              className="p-1.5 hover:bg-slate-200 rounded text-slate-700"
              title="Bulleted List"
            >
              <List className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onMouseDown={(e) => { e.preventDefault(); formatDoc('insertOrderedList'); }}
              className="p-1.5 hover:bg-slate-200 rounded text-slate-700"
              title="Numbered List"
            >
              <ListOrdered className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onMouseDown={(e) => { e.preventDefault(); formatDoc('outdent'); }}
              className="p-1.5 hover:bg-slate-200 rounded text-slate-700"
              title="Indent Less"
            >
              <Outdent className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onMouseDown={(e) => { e.preventDefault(); formatDoc('indent'); }}
              className="p-1.5 hover:bg-slate-200 rounded text-slate-700"
              title="Indent More"
            >
              <Indent className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onMouseDown={(e) => { e.preventDefault(); formatDoc('formatBlock', '<blockquote>'); }}
              className="p-1.5 hover:bg-slate-200 rounded text-slate-700"
              title="Quote"
            >
              <Quote className="w-3.5 h-3.5" />
            </button>

            <span className="w-px h-4 bg-slate-300 mx-1"></span>

            {/* Remove Formatting */}
            <button
              type="button"
              onMouseDown={(e) => { e.preventDefault(); formatDoc('removeFormat'); }}
              className="p-1.5 hover:bg-slate-200 rounded text-slate-700 hover:text-rose-600"
              title="Remove Formatting"
            >
              <RemoveFormatting className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* BOTTOM ACTION BAR (GMAIL STYLE) */}
      {/* ──────────────────────────────────────────────────────────── */}
      <div className="px-4 py-2.5 bg-white border-t border-slate-200 flex items-center justify-between shrink-0">
        {/* Left: Send Button & Quick Icons */}
        <div className="flex items-center gap-1.5 sm:gap-2">
          {/* Blue Send Button */}
          <button
            type="button"
            onClick={handleSend}
            disabled={isSending}
            className="h-9 px-4 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-full flex items-center gap-1.5 shadow-sm transition-all disabled:opacity-50"
          >
            {isSending ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <span>Send</span>
                <Send className="w-3 h-3 ml-0.5" />
              </>
            )}
          </button>

          {/* Toggle Formatting Toolbar "Aa" */}
          <button
            type="button"
            onClick={() => setShowFormatting(!showFormatting)}
            className={`p-2 rounded-full transition-colors ${showFormatting ? 'bg-slate-200 text-slate-900' : 'text-slate-600 hover:bg-slate-100'}`}
            title="Formatting options"
          >
            <span className="font-serif font-bold text-xs">Aa</span>
          </button>

          {/* Attach files (Paperclip) */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadingAttachment}
            className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-full transition-colors relative"
            title="Attach files"
          >
            {uploadingAttachment ? (
              <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
            ) : (
              <Paperclip className="w-4 h-4" />
            )}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={handleFileUpload}
          />

          {/* Insert link */}
          <button
            type="button"
            onClick={() => { saveSelection(); setShowLinkModal(true); }}
            className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-full transition-colors"
            title="Insert link"
          >
            <LinkIcon className="w-4 h-4" />
          </button>

          {/* Insert emoji */}
          <div className="relative">
            <button
              type="button"
              onClick={() => { saveSelection(); setShowEmojiPopover(!showEmojiPopover); }}
              className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-full transition-colors"
              title="Insert emoji"
            >
              <Smile className="w-4 h-4" />
            </button>

            {showEmojiPopover && (
              <div className="absolute bottom-11 left-0 z-[10000] bg-white border border-slate-200 rounded-xl shadow-2xl p-3 w-64">
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-100 text-xs font-semibold text-slate-700">
                  <span>Common Emojis</span>
                  <button onClick={() => setShowEmojiPopover(false)} className="text-slate-400 hover:text-slate-600">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="grid grid-cols-6 gap-2 text-lg">
                  {COMMON_EMOJIS.map(emoji => (
                    <button
                      key={emoji}
                      type="button"
                      onClick={() => handleInsertEmoji(emoji)}
                      className="p-1 hover:bg-slate-100 rounded text-center transition-transform hover:scale-125"
                    >
                      {emoji}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Insert photo / image */}
          <button
            type="button"
            onClick={() => { saveSelection(); setShowImageModal(true); }}
            className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-full transition-colors"
            title="Insert photo / image"
          >
            <ImageIcon className="w-4 h-4" />
          </button>

          {/* Insert signature */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowSignatureMenu(!showSignatureMenu)}
              className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-full transition-colors"
              title="Insert signature"
            >
              <PenTool className="w-4 h-4" />
            </button>

            {showSignatureMenu && (
              <div className="absolute bottom-11 left-0 z-[10000] bg-white border border-slate-200 rounded-xl shadow-2xl p-2 w-64 text-xs text-slate-700">
                <button
                  type="button"
                  onClick={() => handleInsertSignature()}
                  className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-100 font-medium flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <PenTool className="w-3.5 h-3.5 text-indigo-600" />
                    <span>Insert Default Signature</span>
                  </div>
                  {isCustomSignature ? (
                    <span className="text-[9px] bg-emerald-50 text-emerald-700 border border-emerald-200 px-1 py-0.2 rounded font-semibold">Saved Default</span>
                  ) : (
                    <span className="text-[9px] bg-slate-100 text-slate-600 px-1 py-0.2 rounded font-medium">Auto</span>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => { setShowSignatureMenu(false); setShowSignatureModal(true); }}
                  className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-100 font-medium flex items-center gap-2 border-t border-slate-100 mt-1 text-slate-700 hover:text-indigo-600"
                >
                  <Settings className="w-3.5 h-3.5 text-slate-500" />
                  Edit Default Signature & Settings
                </button>
              </div>
            )}
          </div>

          {/* CC to Gmail notification checkbox */}
          <label className="hidden sm:flex items-center gap-1.5 text-[11px] text-slate-600 cursor-pointer ml-2 select-none">
            <input
              type="checkbox"
              checked={notifyByEmail}
              onChange={(e) => setNotifyByEmail(e.target.checked)}
              className="w-3.5 h-3.5 rounded text-blue-600 focus:ring-blue-500 border-slate-300"
            />
            <span>CC my Gmail</span>
          </label>
        </div>

        {/* Right: Discard Draft Trash Button */}
        <div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-full transition-colors"
            title="Discard draft"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* MODAL: INSERT HYPERLINK */}
      {/* ──────────────────────────────────────────────────────────── */}
      {showLinkModal && (
        <div className="fixed inset-0 z-[10001] bg-slate-900/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 p-5 w-full max-w-sm space-y-4 animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b pb-2">
              <h4 className="font-bold text-sm text-slate-900 flex items-center gap-1.5">
                <LinkIcon className="w-4 h-4 text-indigo-600" /> Insert Hyperlink
              </h4>
              <button onClick={() => setShowLinkModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Text to display</label>
                <input
                  type="text"
                  value={linkText}
                  onChange={(e) => setLinkText(e.target.value)}
                  placeholder="e.g. Immigration Checklist"
                  className="w-full px-3 py-1.5 border border-slate-200 rounded-lg text-xs outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Target Web URL</label>
                <input
                  type="text"
                  value={linkUrl}
                  onChange={(e) => setLinkUrl(e.target.value)}
                  placeholder="https://example.com"
                  className="w-full px-3 py-1.5 border border-slate-200 rounded-lg text-xs outline-none focus:border-indigo-500"
                />
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 pt-2 border-t">
              <button
                type="button"
                onClick={() => setShowLinkModal(false)}
                className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleInsertLink}
                className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-lg"
              >
                Insert Link
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* MODAL: INSERT PHOTO / IMAGE */}
      {/* ──────────────────────────────────────────────────────────── */}
      {showImageModal && (
        <div className="fixed inset-0 z-[10001] bg-slate-900/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 p-5 w-full max-w-sm space-y-4 animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b pb-2">
              <h4 className="font-bold text-sm text-slate-900 flex items-center gap-1.5">
                <ImageIcon className="w-4 h-4 text-indigo-600" /> Insert Photo / Image
              </h4>
              <button onClick={() => setShowImageModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Tab selector */}
            <div className="flex border-b border-slate-200">
              <button
                type="button"
                onClick={() => setImageTab('upload')}
                className={`flex-1 py-1.5 text-xs font-semibold border-b-2 text-center ${imageTab === 'upload' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-800'}`}
              >
                Upload from Computer
              </button>
              <button
                type="button"
                onClick={() => setImageTab('url')}
                className={`flex-1 py-1.5 text-xs font-semibold border-b-2 text-center ${imageTab === 'url' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-800'}`}
              >
                Web Image URL
              </button>
            </div>

            <div className="space-y-3 text-xs pt-1">
              {imageTab === 'upload' ? (
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Choose image file (PNG, JPG, GIF)</label>
                  <input
                    ref={imageInputRef}
                    type="file"
                    accept="image/*"
                    className="w-full text-xs text-slate-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
                  />
                </div>
              ) : (
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Image URL</label>
                  <input
                    type="text"
                    value={imageUrl}
                    onChange={(e) => setImageUrl(e.target.value)}
                    placeholder="https://example.com/logo.png"
                    className="w-full px-3 py-1.5 border border-slate-200 rounded-lg text-xs outline-none focus:border-indigo-500"
                  />
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t">
              <button
                type="button"
                onClick={() => setShowImageModal(false)}
                className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleInsertImage}
                disabled={uploadingImage}
                className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-lg flex items-center gap-1.5"
              >
                {uploadingImage && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                Insert Image
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* MODAL: EDIT EMAIL SIGNATURE */}
      {/* ──────────────────────────────────────────────────────────── */}
      {showSignatureModal && (
        <div className="fixed inset-0 z-[10001] bg-slate-900/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 p-5 w-full max-w-3xl max-h-[90vh] overflow-y-auto space-y-4 animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b pb-2">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                  <PenTool className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="font-bold text-sm text-slate-900">
                    Default Email Signature
                  </h4>
                  <span className="text-[10px] text-slate-500">Auto-applies to all new emails you compose</span>
                </div>
              </div>
              <button onClick={() => setShowSignatureModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <EmailSignatureEditor
              initialSignatureHtml={customSignatureHtml}
              currentUser={{}}
              onSave={async (newHtml) => {
                await handleSaveSignature(newHtml);
              }}
              onClose={() => setShowSignatureModal(false)}
            />

            {onOpenMailboxConfig && (
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => {
                    setShowSignatureModal(false);
                    savedWindowStateRef.current = windowState;
                    setWindowState('minimized');
                    onOpenMailboxConfig();
                  }}
                  className="text-xs text-slate-500 hover:text-indigo-600 font-medium flex items-center gap-1"
                >
                  <Settings className="w-3.5 h-3.5" />
                  <span>Configure Full Email & Mailbox Settings</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );

  return createPortal(composerContent, document.body);
}
