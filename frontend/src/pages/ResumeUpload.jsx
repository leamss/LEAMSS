import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Loader2, UploadCloud, CheckCircle2, FileText, User, Phone, Mail } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || (typeof window !== 'undefined' && window.location.hostname.includes('leamss.com') ? 'https://api.leamss.com' : 'http://localhost:8001');
const API = `${BACKEND_URL}/api`;

const TEAL = '#12433B';
const ORANGE = '#D4633F';
const GOLD = '#C99A3B';

export default function ResumeUpload() {
  const { token } = useParams();
  const fileRef = useRef(null);
  const [loading, setLoading] = useState(false);
  const [clientName, setClientName] = useState('');
  const [clientPhone, setClientPhone] = useState('');
  const [clientEmail, setClientEmail] = useState('');
  const [error, setError] = useState(null);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [done, setDone] = useState(null);

  useEffect(() => {
    if (token && token !== 'undefined' && token !== 'null' && token !== 'direct') {
      setLoading(true);
      axios.get(`${API}/public/resume-upload/${encodeURIComponent(token)}`)
        .then((r) => {
          if (r.data?.client_name && r.data.client_name !== 'Applicant') {
            setClientName(r.data.client_name);
          }
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [token]);

  const submit = async () => {
    if (!file) {
      setError('Please select a resume file to upload.');
      return;
    }
    const cleanToken = (!token || token === 'undefined' || token === 'null') ? 'direct' : token;
    setUploading(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      if (clientName) fd.append('name', clientName);
      if (clientPhone) fd.append('phone', clientPhone);
      if (clientEmail) fd.append('email', clientEmail);

      const r = await axios.post(`${API}/public/resume-upload/${encodeURIComponent(cleanToken)}`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setDone(r.data?.message || 'Thank you! Your resume was received successfully.');
    } catch (e) {
      try {
        const fdFallback = new FormData();
        fdFallback.append('file', file);
        if (clientName) fdFallback.append('name', clientName);
        if (clientPhone) fdFallback.append('phone', clientPhone);
        if (clientEmail) fdFallback.append('email', clientEmail);

        const r2 = await axios.post(`${API}/public/resume-upload/direct`, fdFallback, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        setDone(r2.data?.message || 'Thank you! Your resume was received successfully.');
      } catch (e2) {
        setError(e?.response?.data?.detail || e2?.response?.data?.detail || 'Upload failed. Please try again or share your resume on WhatsApp.');
      }
    } finally {
      setUploading(false);
    }
  };

  const onPick = (e) => {
    const f = e.target.files?.[0];
    if (f) {
      setFile(f);
      setError(null);
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: '#eef2f0', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px 16px', fontFamily: 'Arial, Helvetica, sans-serif' }}>
      <div style={{ width: 540, maxWidth: '100%', background: '#fff', borderRadius: 16, overflow: 'hidden', boxShadow: '0 10px 40px rgba(18,67,59,0.12)' }} data-testid="resume-upload-card">
        <div style={{ height: 4, background: '#FF9933' }} />
        <div style={{ height: 4, background: '#fff' }} />
        <div style={{ height: 4, background: '#138808' }} />
        
        <div style={{ background: TEAL, padding: '24px 28px' }}>
          <div style={{ color: '#fff', fontFamily: 'Georgia, serif', fontSize: 20, fontWeight: 800 }}>Ladhani Education &amp; Migration Services</div>
          <div style={{ color: GOLD, fontSize: 11, fontWeight: 600, marginTop: 4, letterSpacing: 0.5 }}>GLOBAL EDUCATION &amp; IMMIGRATION EXPERTS</div>
        </div>

        <div style={{ padding: '28px 28px' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 40 }} data-testid="resume-upload-loading">
              <Loader2 className="animate-spin" style={{ margin: '0 auto', color: TEAL }} size={32} />
            </div>
          ) : done ? (
            <div style={{ textAlign: 'center', padding: '20px 10px' }} data-testid="resume-upload-success">
              <CheckCircle2 size={52} style={{ color: '#138808', margin: '0 auto' }} />
              <p style={{ color: TEAL, fontSize: 20, fontWeight: 800, marginTop: 14 }}>Resume Received!</p>
              <p style={{ color: '#5B6B7B', fontSize: 14, lineHeight: 1.7, marginTop: 8 }}>
                {done}
              </p>
              <div style={{ marginTop: 24, padding: 14, background: '#f0fdf4', borderRadius: 10, border: '1px solid #bbf7d0', color: '#166534', fontSize: 13 }}>
                Our immigration team will review your qualifications, calculate your PR points score, and proceed with your Pre-Assessment.
              </div>
            </div>
          ) : (
            <div>
              <div style={{ marginBottom: 18 }}>
                <h2 style={{ color: '#1F2A37', fontSize: 18, fontWeight: 800, margin: '0 0 6px' }}>
                  {clientName ? `Hello, ${clientName}` : 'Upload Your Resume / CV'}
                </h2>
                <p style={{ color: '#5B6B7B', fontSize: 13, lineHeight: 1.6, margin: 0 }}>
                  To calculate your accurate Australia PR points score and evaluate your eligibility, please upload your latest Resume / CV. No login required.
                </p>
              </div>

              {!clientName && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14 }}>
                  <div style={{ position: 'relative' }}>
                    <User size={15} style={{ position: 'absolute', left: 10, top: 12, color: '#94a3b8' }} />
                    <input
                      type="text"
                      placeholder="Your Full Name (Optional)"
                      value={clientName}
                      onChange={(e) => setClientName(e.target.value)}
                      style={{ width: '100%', padding: '10px 10px 10px 32px', fontSize: 13, border: '1px solid #d1d5db', borderRadius: 8, boxSizing: 'border-box' }}
                    />
                  </div>
                  <div style={{ position: 'relative' }}>
                    <Phone size={15} style={{ position: 'absolute', left: 10, top: 12, color: '#94a3b8' }} />
                    <input
                      type="text"
                      placeholder="WhatsApp Phone (Optional)"
                      value={clientPhone}
                      onChange={(e) => setClientPhone(e.target.value)}
                      style={{ width: '100%', padding: '10px 10px 10px 32px', fontSize: 13, border: '1px solid #d1d5db', borderRadius: 8, boxSizing: 'border-box' }}
                    />
                  </div>
                </div>
              )}

              <div
                onClick={() => fileRef.current?.click()}
                style={{
                  border: `2px dashed ${file ? TEAL : '#cbd5e1'}`,
                  borderRadius: 12,
                  padding: '28px 16px',
                  textAlign: 'center',
                  cursor: 'pointer',
                  background: file ? '#f0fdf4' : '#f8fafc',
                  transition: 'all 0.2s'
                }}
                data-testid="resume-dropzone"
              >
                {file ? (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, color: TEAL }}>
                    <FileText size={32} />
                    <span style={{ fontWeight: 700, fontSize: 14 }} data-testid="resume-filename">{file.name}</span>
                    <span style={{ fontSize: 11, color: '#64748b' }}>Click to change file</span>
                  </div>
                ) : (
                  <div>
                    <UploadCloud size={40} style={{ color: ORANGE, margin: '0 auto' }} />
                    <p style={{ color: '#1F2A37', fontSize: 15, fontWeight: 700, margin: '10px 0 4px' }}>Click to choose your Resume / CV</p>
                    <p style={{ color: '#94a3b8', fontSize: 12, margin: 0 }}>PDF or Word (.pdf, .doc, .docx) · max 15 MB</p>
                  </div>
                )}
              </div>
              <input ref={fileRef} type="file" accept=".pdf,.doc,.docx,.txt" style={{ display: 'none' }} onChange={onPick} data-testid="resume-file-input" />

              {error && <p style={{ color: '#dc2626', fontSize: 13, marginTop: 10, marginBottom: 0 }} data-testid="resume-error">{error}</p>}

              <button
                onClick={submit}
                disabled={!file || uploading}
                style={{
                  width: '100%',
                  marginTop: 18,
                  background: (!file || uploading) ? '#94a3b8' : ORANGE,
                  color: '#fff',
                  border: 'none',
                  borderRadius: 25,
                  padding: '14px 0',
                  fontSize: 15,
                  fontWeight: 800,
                  cursor: (!file || uploading) ? 'not-allowed' : 'pointer',
                  boxShadow: (!file || uploading) ? 'none' : '0 4px 14px rgba(212,99,63,0.3)',
                  transition: 'background 0.2s'
                }}
                data-testid="resume-submit-btn"
              >
                {uploading ? (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                    <Loader2 className="animate-spin" size={18} /> Uploading…
                  </span>
                ) : '🟢 UPLOAD RESUME'}
              </button>

              <p style={{ color: '#94a3b8', fontSize: 12, textAlign: 'center', marginTop: 14, marginBottom: 0 }}>
                Uploaded files are strictly encrypted &amp; used only for Australia Immigration Pre-Assessment.
              </p>
            </div>
          )}
        </div>

        <div style={{ background: '#f8fafc', borderTop: '1px solid #e2e8f0', padding: '12px 28px', textAlign: 'center' }}>
          <div style={{ color: '#64748b', fontSize: 11 }}>LEAMSS — Toll-Free: 1800-210-2427 · info@leamss.com · www.leamss.com</div>
        </div>
      </div>
    </div>
  );
}

