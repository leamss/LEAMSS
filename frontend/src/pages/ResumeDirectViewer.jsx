import React, { useEffect } from 'react';
import { useParams } from 'react-router-dom';

export default function ResumeDirectViewer() {
  const params = useParams();
  const fileId = params.fileId || params['*'] || '';
  const cleanId = String(fileId).replace(/^\/+/, '').split(/[?#/]/)[0];
  const backendBase = (process.env.REACT_APP_BACKEND_URL || '').replace(/\/+$/, '');

  useEffect(() => {
    if (cleanId) {
      window.location.replace(`${backendBase}/api/cockpit/resume/${cleanId}`);
    }
  }, [cleanId, backendBase]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', fontFamily: 'sans-serif', color: '#12433B' }}>
      <div style={{ width: 40, height: 40, border: '3px solid #E4EAE8', borderTopColor: '#12433B', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
      <p style={{ marginTop: 16, fontSize: 14, fontWeight: 600 }}>Loading candidate resume...</p>
      <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
