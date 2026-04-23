import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Eraser, Check, Pen } from 'lucide-react';

/**
 * Lightweight canvas signature capture.
 * Props:
 *  - onSigned(dataUrl, meta): callback when user confirms
 *  - disabled
 *  - height (default 160)
 */
export default function SignatureCanvas({ onSigned, disabled = false, height = 160 }) {
  const canvasRef = useRef(null);
  const [drawing, setDrawing] = useState(false);
  const [hasInk, setHasInk] = useState(false);
  const [typedName, setTypedName] = useState('');

  useEffect(() => {
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

  const getPos = (e) => {
    const c = canvasRef.current;
    const rect = c.getBoundingClientRect();
    const scaleX = c.width / rect.width;
    const scaleY = c.height / rect.height;
    const x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
    const y = (e.touches ? e.touches[0].clientY : e.clientY) - rect.top;
    return { x: x * scaleX, y: y * scaleY };
  };

  const begin = (e) => {
    if (disabled) return;
    e.preventDefault();
    setDrawing(true);
    const { x, y } = getPos(e);
    const ctx = canvasRef.current.getContext('2d');
    ctx.beginPath();
    ctx.moveTo(x, y);
  };
  const move = (e) => {
    if (!drawing || disabled) return;
    e.preventDefault();
    const { x, y } = getPos(e);
    const ctx = canvasRef.current.getContext('2d');
    ctx.lineTo(x, y);
    ctx.stroke();
    setHasInk(true);
  };
  const end = () => setDrawing(false);

  const clear = () => {
    const c = canvasRef.current;
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, c.width, c.height);
    setHasInk(false);
  };

  const confirm = () => {
    if (!hasInk) return;
    if (!typedName.trim()) {
      alert('Please type your name below the signature');
      return;
    }
    const dataUrl = canvasRef.current.toDataURL('image/png');
    onSigned && onSigned(dataUrl, { typed_name: typedName.trim() });
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
      <Button type="button" onClick={confirm} disabled={disabled || !hasInk || !typedName.trim()}
        className="w-full bg-[#2a777a] hover:bg-[#206063] text-white" data-testid="esign-confirm">
        <Check className="h-4 w-4 mr-2" /> Confirm & Sign Agreement
      </Button>
    </div>
  );
}
