/**
 * Phase 20.2.1 — Brand Guide
 *
 * Single-page reference for LEAMSS brand tokens, components, gradients & typography.
 * Admin-only. Used by designers + future contractors + visual QA.
 */
import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Palette, Type, Layers, Hash, Copy, Check, Square } from 'lucide-react';
import { toast } from 'sonner';

const TOKENS = [
  { name: 'leamss-teal', hex: '#0D9488', role: 'Primary · Branding · Navigation' },
  { name: 'leamss-orange', hex: '#F97316', role: 'Accent · CTA · Highlights' },
  { name: 'leamss-red', hex: '#DC2626', role: 'Destructive · Alerts · Important' },
  { name: 'leamss-bg_white', hex: '#FFFFFF', role: 'Base background' },
  { name: 'leamss-teal_50', hex: '#F0FDFA', role: 'Soft teal tint (hover/section bg)' },
  { name: 'leamss-orange_50', hex: '#FFF7ED', role: 'Soft orange tint (highlights)' },
  { name: 'leamss-red_50', hex: '#FEF2F2', role: 'Soft red tint (warning bg)' },
];

const GRADIENTS = [
  { name: 'Hero · teal → orange', cls: 'from-leamss-teal to-leamss-orange', use: 'Page heroes, primary banners' },
  { name: 'CTA · orange → red', cls: 'from-leamss-orange to-leamss-red', use: 'Urgent CTAs, limited-time offers' },
  { name: 'Soft · teal_50 → orange_50', cls: 'from-leamss-teal_50 to-leamss-orange_50', use: 'Section backgrounds' },
];

const TYPOGRAPHY = [
  { label: 'H1 — Page Title', cls: 'text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight' },
  { label: 'H2 — Section Heading', cls: 'text-2xl sm:text-3xl font-bold' },
  { label: 'H3 — Sub-heading', cls: 'text-lg sm:text-xl font-semibold' },
  { label: 'Body Large', cls: 'text-base sm:text-lg' },
  { label: 'Body Regular', cls: 'text-base' },
  { label: 'Body Small', cls: 'text-sm text-slate-600' },
  { label: 'Caption / Helper', cls: 'text-xs text-slate-500' },
];

const SPACING = [
  { label: 'Tight', cls: 'space-y-1', visual: 'gap 4px' },
  { label: 'Compact', cls: 'space-y-2', visual: 'gap 8px' },
  { label: 'Default', cls: 'space-y-3', visual: 'gap 12px' },
  { label: 'Comfortable', cls: 'space-y-4', visual: 'gap 16px' },
  { label: 'Spacious', cls: 'space-y-6', visual: 'gap 24px' },
  { label: 'Section', cls: 'space-y-8', visual: 'gap 32px' },
];

function CopyButton({ value, testid }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard?.writeText(value);
        setCopied(true);
        toast.success(`Copied: ${value}`);
        setTimeout(() => setCopied(false), 1500);
      }}
      data-testid={testid}
      className="text-[10px] text-slate-500 hover:text-leamss-teal flex items-center gap-1 transition"
      title={`Copy ${value}`}
    >
      {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
      <code>{value}</code>
    </button>
  );
}

function Swatch({ token }) {
  return (
    <div className="border rounded-lg p-3 bg-white" data-testid={`brand-token-${token.name}`}>
      <div className={`h-12 rounded-md mb-2 bg-${token.name}`} style={{ background: token.hex }} />
      <p className="text-xs font-bold text-slate-800">{token.name}</p>
      <p className="text-[10px] text-slate-500">{token.role}</p>
      <div className="mt-2 flex justify-between items-center">
        <CopyButton value={`bg-${token.name}`} testid={`copy-bg-${token.name}`} />
        <CopyButton value={token.hex} testid={`copy-hex-${token.name}`} />
      </div>
    </div>
  );
}

export default function BrandGuide() {
  return (
    <div className="max-w-6xl mx-auto p-6 space-y-8" data-testid="brand-guide-page">
      <header className="space-y-2">
        <h1 className="text-4xl font-bold text-leamss-teal flex items-center gap-3">
          <Palette className="h-8 w-8" /> LEAMSS Brand Guide
        </h1>
        <p className="text-slate-600">Single source of truth for colours, gradients, components & typography. Phase 20.2.1 · Jun 2026.</p>
      </header>

      {/* TOKENS */}
      <section data-testid="section-tokens">
        <h2 className="text-2xl font-bold mb-3 flex items-center gap-2">
          <Hash className="h-5 w-5 text-leamss-orange" />Colour Tokens
        </h2>
        <p className="text-sm text-slate-600 mb-4">Use Tailwind class names (left) or raw hex (right). NEVER hardcode hex literals in components — always use tokens.</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {TOKENS.map(t => <Swatch key={t.name} token={t} />)}
        </div>
      </section>

      {/* BUTTONS */}
      <section data-testid="section-buttons">
        <h2 className="text-2xl font-bold mb-3 flex items-center gap-2">
          <Square className="h-5 w-5 text-leamss-orange" />Buttons
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <Card className="p-3 space-y-2">
            <Button className="w-full bg-leamss-teal hover:bg-leamss-teal/90 text-white" data-testid="btn-primary">Primary</Button>
            <code className="text-[10px] text-slate-500 block">bg-leamss-teal</code>
          </Card>
          <Card className="p-3 space-y-2">
            <Button className="w-full bg-leamss-orange hover:bg-leamss-orange/90 text-white" data-testid="btn-accent">Accent CTA</Button>
            <code className="text-[10px] text-slate-500 block">bg-leamss-orange</code>
          </Card>
          <Card className="p-3 space-y-2">
            <Button className="w-full bg-leamss-red hover:bg-leamss-red/90 text-white" data-testid="btn-destructive">Destructive</Button>
            <code className="text-[10px] text-slate-500 block">bg-leamss-red</code>
          </Card>
          <Card className="p-3 space-y-2">
            <Button variant="outline" className="w-full border-leamss-teal text-leamss-teal hover:bg-leamss-teal_50" data-testid="btn-outline">Outline</Button>
            <code className="text-[10px] text-slate-500 block">border-leamss-teal</code>
          </Card>
          <Card className="p-3 space-y-2">
            <Button variant="ghost" className="w-full text-leamss-teal hover:bg-leamss-teal_50" data-testid="btn-ghost">Ghost</Button>
            <code className="text-[10px] text-slate-500 block">text-leamss-teal</code>
          </Card>
          <Card className="p-3 space-y-2">
            <Button disabled className="w-full" data-testid="btn-disabled">Disabled</Button>
            <code className="text-[10px] text-slate-500 block">disabled</code>
          </Card>
        </div>
      </section>

      {/* BADGES */}
      <section data-testid="section-badges">
        <h2 className="text-2xl font-bold mb-3 flex items-center gap-2">
          <Layers className="h-5 w-5 text-leamss-orange" />Badges
        </h2>
        <div className="flex flex-wrap gap-2">
          <Badge className="bg-leamss-teal text-white">Success</Badge>
          <Badge className="bg-leamss-teal_50 text-leamss-teal border border-leamss-teal/30">Info</Badge>
          <Badge className="bg-leamss-orange text-white">Warning</Badge>
          <Badge className="bg-leamss-orange_50 text-leamss-orange border border-leamss-orange/30">Highlight</Badge>
          <Badge className="bg-leamss-red text-white">Error</Badge>
          <Badge className="bg-leamss-red_50 text-leamss-red border border-leamss-red/30">Alert</Badge>
          <Badge variant="outline" className="text-slate-600">Neutral</Badge>
        </div>
      </section>

      {/* GRADIENTS */}
      <section data-testid="section-gradients">
        <h2 className="text-2xl font-bold mb-3 flex items-center gap-2">
          <Palette className="h-5 w-5 text-leamss-orange" />Gradients
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {GRADIENTS.map((g, i) => (
            <div key={i} className="space-y-2" data-testid={`gradient-${i}`}>
              <div className={`h-20 rounded-lg bg-gradient-to-br ${g.cls}`} />
              <p className="text-xs font-bold text-slate-800">{g.name}</p>
              <p className="text-[10px] text-slate-500">{g.use}</p>
              <code className="text-[10px] text-slate-500 block">bg-gradient-to-br {g.cls}</code>
            </div>
          ))}
        </div>
      </section>

      {/* TYPOGRAPHY */}
      <section data-testid="section-typography">
        <h2 className="text-2xl font-bold mb-3 flex items-center gap-2">
          <Type className="h-5 w-5 text-leamss-orange" />Typography
        </h2>
        <Card className="p-4 space-y-3">
          {TYPOGRAPHY.map((t, i) => (
            <div key={i} className="flex justify-between items-baseline border-b last:border-0 pb-2" data-testid={`typo-${i}`}>
              <span className={t.cls}>{t.label}</span>
              <code className="text-[10px] text-slate-500 ml-3 shrink-0">{t.cls}</code>
            </div>
          ))}
        </Card>
      </section>

      {/* SPACING */}
      <section data-testid="section-spacing">
        <h2 className="text-2xl font-bold mb-3 flex items-center gap-2">
          <Layers className="h-5 w-5 text-leamss-orange" />Spacing Scale
        </h2>
        <Card className="p-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {SPACING.map((s, i) => (
              <div key={i} className="border rounded p-3 bg-leamss-teal_50" data-testid={`spacing-${i}`}>
                <p className="text-xs font-bold">{s.label}</p>
                <p className="text-[10px] text-slate-500">{s.visual} · <code>{s.cls}</code></p>
              </div>
            ))}
          </div>
        </Card>
      </section>

      {/* CARDS */}
      <section data-testid="section-cards">
        <h2 className="text-2xl font-bold mb-3">Card Variants</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Card className="p-4 border-l-4 border-l-leamss-teal" data-testid="card-primary">
            <p className="text-xs font-bold text-leamss-teal">PRIMARY CARD</p>
            <p className="text-sm mt-1">Use for main content + summaries</p>
          </Card>
          <Card className="p-4 border-l-4 border-l-leamss-orange bg-leamss-orange_50" data-testid="card-accent">
            <p className="text-xs font-bold text-leamss-orange">ACCENT CARD</p>
            <p className="text-sm mt-1">Use for CTAs + featured content</p>
          </Card>
          <Card className="p-4 border-l-4 border-l-leamss-red bg-leamss-red_50" data-testid="card-alert">
            <p className="text-xs font-bold text-leamss-red">ALERT CARD</p>
            <p className="text-sm mt-1">Use for warnings + errors</p>
          </Card>
        </div>
      </section>

      <footer className="text-center text-xs text-slate-500 pt-6 border-t">
        LEAMSS Brand Guide · Phase 20.2.1 · Jun 2026 · Tailwind tokens defined in <code>frontend/tailwind.config.js</code>
      </footer>
    </div>
  );
}
