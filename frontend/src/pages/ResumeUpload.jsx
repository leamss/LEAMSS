import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Loader2, UploadCloud, CheckCircle2, FileText, AlertCircle } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TEAL = '#12433B';
const ORANGE = '#D4633F';
const GOLD = '#C99A3B';

export default function ResumeUpload() {
  const { token } = useParams();
  const fileRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [info, setInfo] = useState(null);
  const [error, setError] = useState(null);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [done, setDone] = useState(null);

  useEffect(() => {
    axios.get(`${API}/public/resume-upload/${token}`)
      .then((r) => setInfo(r.data))
      .catch((e) => setError(e?.response?.data?.detail || 'This upload link is invalid or has expired.'))
      .finally(() => setLoading(false));
  }, [token]);

  const submit = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await axios.post(`${API}/public/resume-upload/${token}`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setDone(r.data?.message || 'Thank you! Your resume was received.');
    } catch (e) {
      setError(e?.response?.data?.detail || 'Upload failed. Please try again or reply to our email with your resume.');
    } finally {
      setUploading(false);
    }
  };

  const onPick = (e) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  };

  return (
    <div style={{ minHeight: '100vh', background: '#eef2f0', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20, fontFamily: 'Arial, Helvetica, sans-serif' }}>
      <div style={{ width: 560, maxWidth: '100%', background: '#fff', borderRadius: 18, overflow: 'hidden', boxShadow: '0 10px 40px rgba(18,67,59,0.15)' }} data-testid="resume-upload-card">
        <div style={{ height: 5, background: '#FF9933' }} />
        <div style={{ height: 5, background: '#fff' }} />
        <div style={{ height: 5, background: '#138808' }} />
        <div style={{ background: TEAL, padding: '26px 32px' }}>
          <div style={{ color: '#fff', fontFamily: 'Georgia, serif', fontSize: 21, fontWeight: 800 }}>Ladhani Education &amp; Migration Services</div>
          <div style={{ color: GOLD, fontSize: 12, fontWeight: 600, marginTop: 5, letterSpacing: 0.4 }}>GLOBAL EDUCATION &amp; IMMIGRATION EXPERTS</div>
        </div>

        <div style={{ padding: '30px 32px' }}>
          {loading && (
            <div style={{ textAlign: 'center', padding: 40 }} data-testid="resume-upload-loading">
              <Loader2 className="animate-spin" style={{ margin: '0 auto', color: TEAL }} size={32} />
            </div>
          )}

          {!loading && error && !info && (
            <div style={{ textAlign: 'center', padding: 20 }} data-testid="resume-upload-invalid">
              <AlertCircle size={40} style={{ color: ORANGE, margin: '0 auto' }} />
              <p style={{ color: '#1F2A37', fontSize: 16, fontWeight: 700, marginTop: 12 }}>Link not available</p>
              <p style={{ color: '#5B6B7B', fontSize: 14 }}>{error}</p>
            </div>
          )}

          {!loading && info && done && (
            <div style={{ textAlign: 'center', padding: 20 }} data-testid="resume-upload-success">
              <CheckCircle2 size={48} style={{ color: '#138808', margin: '0 auto' }} />
              <p style={{ color: TEAL, fontSize: 20, fontWeight: 800, marginTop: 14 }}>Resume Received!</p>
              <p style={{ color: '#5B6B7B', fontSize: 14, lineHeight: 1.7, marginTop: 6 }}>{done}</p>
            </div>
          )}

          {!loading && info && !done && (
            <div>
              <p style={{ color: '#1F2A37', fontSize: 16, margin: '0 0 6px' }}>Dear {info.client_name},</p>
              <p style={{ color: '#5B6B7B', fontSize: 14, lineHeight: 1.7 }}>
                To prepare your personalised Australia PR Pre-Assessment, please upload your latest resume/CV below.
                It only takes a minute — no login required.
              </p>

              {info.already_uploaded && (
                <div style={{ background: '#eaf6ee', border: '1px solid #cfe9d8', borderRadius: 10, padding: '10px 14px', margin: '14px 0', color: '#138808', fontSize: 13, fontWeight: 700 }}>
                  ✓ A resume is already on file. Uploading again will replace it.
                </div>
              )}

              <div
                onClick={() => fileRef.current?.click()}
                style={{ border: `2px dashed ${file ? TEAL : '#c7d3ce'}`, borderRadius: 14, padding: '30px 20px', textAlign: 'center', cursor: 'pointer', marginTop: 18, background: '#f8faf9', transition: 'border-color 0.2s' }}
                data-testid="resume-dropzone"
              >
                {file ? (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, color: TEAL }}>
                    <FileText size={22} />
                    <span style={{ fontWeight: 700, fontSize: 14 }} data-testid="resume-filename">{file.name}</span>
                  </div>
                ) : (
                  <div>
                    <UploadCloud size={38} style={{ color: ORANGE, margin: '0 auto' }} />
                    <p style={{ color: '#1F2A37', fontSize: 15, fontWeight: 700, marginTop: 10 }}>Click to choose your resume</p>
                    <p style={{ color: '#94a3b8', fontSize: 12, marginTop: 4 }}>PDF or Word (.pdf, .doc, .docx) · max 15 MB</p>
                  </div>
                )}
              </div>
              <input ref={fileRef} type="file" accept=".pdf,.doc,.docx,.txt" style={{ display: 'none' }} onChange={onPick} data-testid="resume-file-input" />

              {error && <p style={{ color: '#B44A3A', fontSize: 13, marginTop: 12 }} data-testid="resume-error">{error}</p>}

              <button
                onClick={submit}
                disabled={!file || uploading}
                style={{ width: '100%', marginTop: 20, background: (!file || uploading) ? '#9db3ac' : ORANGE, color: '#fff', border: 'none', borderRadius: 30, padding: '15px 0', fontSize: 16, fontWeight: 800, cursor: (!file || uploading) ? 'not-allowed' : 'pointer' }}
                data-testid="resume-submit-btn"
              >
                {uploading ? <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><Loader2 className="animate-spin" size={18} /> Uploading…</span> : '📄  Upload My Resume'}
              </button>
              <p style={{ color: '#94a3b8', fontSize: 12, textAlign: 'center', marginTop: 12 }}>
                Trouble uploading? Simply reply to our email with your resume attached.
              </p>
            </div>
          )}
        </div>

        <div style={{ background: TEAL, padding: '16px 32px' }}>
          <div style={{ color: '#b9c6c2', fontSize: 11 }}>☎ +91 77188 82427 · ✉ info@leamss.com · 🌐 www.leamss.com</div>
        </div>
      </div>
    </div>
  );
}
