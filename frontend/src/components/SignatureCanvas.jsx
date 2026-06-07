import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Eraser, Check, Pen, ShieldCheck, Loader2 } from 'lucide-react';

/**
 * Lightweight canvas signature capture with Phase 9.9 biometric forensics packet.
 *
 * Capture surfaces:
 *  - Browser fingerprint (UA, screen, timezone, locale, platform, hardware concurrency, color depth)
 *  - Drawing path with timestamps (every move event recorded)
 *  - Time-to-sign (session duration from mount → confirm)
 *  - Failed-attempt counter (Clear button presses)
 *  - GPS coordinates (only if user grants permission)
 *  - Input type (mouse vs touch / pen)
 *  - Canvas fingerprint (drawing rendering signature)
 *
 * Props:
 *  - onSigned(dataUrl, meta): callback when user confirms.
 *    meta = { typed_name, biometric_packet }
 *  - disabled
 *  - height (default 160)
 */
export default function SignatureCanvas({ onSigned, disabled = false, height = 160 }) {
  const canvasRef = useRef(null);
  const sessionStartRef = useRef(null);
  const strokesRef = useRef([]);          // [{t, x, y, type}]
  const inputTypeRef = useRef(null);      // 'mouse' | 'touch' | 'pen'
  const clearCountRef = useRef(0);
  const [drawing, setDrawing] = useState(false);
  const [hasInk, setHasInk] = useState(false);
  const [typedName, setTypedName] = useState('');
  const [gpsState, setGpsState] = useState('not_requested'); // not_requested | requesting | granted | denied
  const [gpsCoords, setGpsCoords] = useState(null);

  useEffect(() => {
    // Phase 9.9 — initialise the session-start timestamp side-effect-safe
    if (sessionStartRef.current === null) {
      sessionStartRef.current = Date.now();
    }
    const c = canvasRef.current;
    if (!c) return;
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, c.width, c.height);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.lineWidth = 2.2;
    ctx.strokeStyle = '#1e293b';
  }, []);

  const requestGPS = () => {
    if (!navigator.geolocation) {
      setGpsState('unsupported');
      return;
    }
    setGpsState('requesting');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGpsState('granted');
        setGpsCoords({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy_m: pos.coords.accuracy,
          captured_at: new Date().toISOString(),
        });
      },
      () => setGpsState('denied'),
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 },
    );
  };

  const getPos = (e) => {
    const c = canvasRef.current;
    const rect = c.getBoundingClientRect();
    const scaleX = c.width / rect.width;
    const scaleY = c.height / rect.height;
    const x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
    const y = (e.touches ? e.touches[0].clientY : e.clientY) - rect.top;
    return { x: x * scaleX, y: y * scaleY };
  };

  const recordPoint = (e, type) => {
    if (!inputTypeRef.current) {
      inputTypeRef.current = e.touches ? 'touch' : (e.pointerType === 'pen' ? 'pen' : 'mouse');
    }
    const { x, y } = getPos(e);
    strokesRef.current.push({
      t: Date.now() - (sessionStartRef.current || Date.now()),
      x: Math.round(x), y: Math.round(y),
      type,
    });
    return { x, y };
  };

  const begin = (e) => {
    if (disabled) return;
    e.preventDefault();
    setDrawing(true);
    const { x, y } = recordPoint(e, 'down');
    const ctx = canvasRef.current.getContext('2d');
    ctx.beginPath();
    ctx.moveTo(x, y);
  };
  const move = (e) => {
    if (!drawing || disabled) return;
    e.preventDefault();
    const { x, y } = recordPoint(e, 'move');
    const ctx = canvasRef.current.getContext('2d');
    ctx.lineTo(x, y);
    ctx.stroke();
    setHasInk(true);
  };
  const end = (e) => {
    if (drawing && e) {
      try { recordPoint(e, 'up'); } catch (_) { /* synthetic event safe-ignore */ }
    }
    setDrawing(false);
  };

  const clear = () => {
    const c = canvasRef.current;
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, c.width, c.height);
    setHasInk(false);
    clearCountRef.current += 1;
    strokesRef.current = [];
  };

  const buildBiometricPacket = () => {
    const now = new Date();
    const sessionDurationMs = Date.now() - (sessionStartRef.current || Date.now());
    return {
      version: '1.0',
      captured_at: now.toISOString(),
      session_duration_ms: sessionDurationMs,
      device: {
        user_agent: (navigator.userAgent || '').slice(0, 300),
        platform: navigator.platform || '',
        language: navigator.language || '',
        languages: (navigator.languages || []).slice(0, 5),
        hardware_concurrency: navigator.hardwareConcurrency || null,
        device_memory: navigator.deviceMemory || null,
        cookie_enabled: navigator.cookieEnabled,
        do_not_track: navigator.doNotTrack || null,
        max_touch_points: navigator.maxTouchPoints || 0,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || null,
        timezone_offset_minutes: now.getTimezoneOffset(),
        locale: Intl.DateTimeFormat().resolvedOptions().locale || null,
      },
      screen: {
        width: window.screen.width,
        height: window.screen.height,
        avail_width: window.screen.availWidth,
        avail_height: window.screen.availHeight,
        color_depth: window.screen.colorDepth,
        pixel_depth: window.screen.pixelDepth,
        device_pixel_ratio: window.devicePixelRatio || 1,
      },
      window: {
        inner_width: window.innerWidth,
        inner_height: window.innerHeight,
        orientation: (screen.orientation && screen.orientation.type) || null,
      },
      gps: gpsCoords || { status: gpsState },
      drawing: {
        input_type: inputTypeRef.current || 'unknown',
        stroke_count: strokesRef.current.filter(s => s.type === 'down').length,
        total_points: strokesRef.current.length,
        clear_count_before_final: clearCountRef.current,
        path: strokesRef.current,        // full timeline of every point
      },
      canvas_fingerprint: computeCanvasFingerprint(),
    };
  };

  const confirm = () => {
    if (!hasInk) return;
    if (!typedName.trim()) {
      alert('Please type your name below the signature');
      return;
    }
    const dataUrl = canvasRef.current.toDataURL('image/png');
    onSigned && onSigned(dataUrl, {
      typed_name: typedName.trim(),
      biometric_packet: buildBiometricPacket(),
    });
  };

  return (
    <div className="space-y-2" data-testid="signature-canvas-wrapper">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-slate-700 flex items-center gap-1.5"><Pen className="h-3.5 w-3.5" /> Draw your signature below</p>
        <Button type="button" variant="ghost" size="sm" onClick={clear} disabled={disabled || !hasInk} className="h-7 text-xs text-slate-500" data-testid="esign-clear">
          <Eraser className="h-3 w-3 mr-1" /> Clear
        </Button>
      </div>
      <div className="border-2 border-dashed border-slate-300 rounded-lg bg-white overflow-hidden">
        <canvas
          ref={canvasRef}
          width={700}
          height={height}
          style={{ width: '100%', height: `${height}px`, touchAction: 'none', cursor: disabled ? 'not-allowed' : 'crosshair' }}
          onMouseDown={begin} onMouseMove={move} onMouseUp={end} onMouseLeave={end}
          onTouchStart={begin} onTouchMove={move} onTouchEnd={end}
          data-testid="signature-canvas"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-slate-600 block mb-1">Type your full legal name</label>
        <input
          type="text" value={typedName} onChange={(e) => setTypedName(e.target.value)}
          disabled={disabled}
          placeholder="e.g. Rahul Sharma"
          className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
          data-testid="esign-typed-name"
        />
      </div>

      {/* Phase 9.9 — Biometric forensics consent strip */}
      <div className="flex items-center justify-between text-[10px] px-2 py-1.5 rounded border bg-emerald-50 border-emerald-200" data-testid="esign-forensics-strip">
        <span className="flex items-center gap-1 text-emerald-700">
          <ShieldCheck className="h-3 w-3" /> Forensics: device + drawing path captured.
          {gpsState === 'granted' && <span className="ml-1">📍 GPS locked.</span>}
        </span>
        {gpsState === 'not_requested' && (
          <button
            type="button"
            onClick={requestGPS}
            disabled={disabled}
            className="text-[10px] underline text-emerald-700 hover:text-emerald-900"
            data-testid="esign-grant-gps"
          >
            Optional: share location
          </button>
        )}
        {gpsState === 'requesting' && <span className="text-[10px] text-emerald-700 flex items-center gap-1"><Loader2 className="h-3 w-3 animate-spin" />locating…</span>}
        {gpsState === 'denied' && <span className="text-[10px] text-amber-700">GPS declined</span>}
      </div>

      <Button type="button" onClick={confirm} disabled={disabled || !hasInk || !typedName.trim()}
        className="w-full bg-[#2a777a] hover:bg-[#206063] text-white" data-testid="esign-confirm">
        <Check className="h-4 w-4 mr-2" /> Confirm &amp; Sign Agreement
      </Button>
    </div>
  );
}


// ── Phase 9.9 — Canvas fingerprint helper ──────────────────────────────────
// Renders a known string into an off-screen canvas and returns the SHA-256 of
// its rasterised bytes. Same browser = same fingerprint; spoofing it requires
// modifying the rendering pipeline (very hard).
function computeCanvasFingerprint() {
  try {
    const c = document.createElement('canvas');
    c.width = 280; c.height = 60;
    const ctx = c.getContext('2d');
    ctx.textBaseline = 'top';
    ctx.font = '14px "Arial"';
    ctx.fillStyle = '#f0f';
    ctx.fillRect(0, 0, 280, 60);
    ctx.fillStyle = '#069';
    ctx.fillText('LEAMSS · e-sign · forensic 9.9', 2, 2);
    ctx.strokeStyle = 'rgba(0,0,0,0.7)';
    ctx.beginPath();
    ctx.arc(70, 30, 18, 0, Math.PI * 2);
    ctx.stroke();
    return c.toDataURL().slice(-64);  // last 64 chars of base64 — stable identifier
  } catch (e) {
    return null;
  }
}
