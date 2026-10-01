/**
 * Node.js script to enrich all AU occupation static HTML files with complete JSA & ABS data.
 */
const fs = require('fs');
const path = require('path');
const PROJECT_ROOT = path.resolve(__dirname, '..');
const xlsx = require(path.join(PROJECT_ROOT, 'frontend', 'node_modules', 'xlsx'));
const JSA_DIR = path.join(PROJECT_ROOT, 'backend', 'data', 'jsa_imports');
const PUBLIC_AU_DIR = path.join(PROJECT_ROOT, 'frontend', 'public', 'atlas', 'au');
const BUILD_AU_DIR = path.join(PROJECT_ROOT, 'frontend', 'build', 'atlas', 'au');

function getAnzscoSkillLevel(codeStr) {
  const code = String(codeStr || '').trim();
  if (!code) return 1;
  const major = code[0];
  const submajor = code.length >= 2 ? code.slice(0, 2) : code;
  const unit = code.length >= 4 ? code.slice(0, 4) : code;

  if (major === '2') return 1; // Professionals
  if (major === '1') { // Managers
    if (submajor === '11' || submajor === '13') {
      if (unit === '1331' && code.startsWith('133112')) return 2;
      return 1;
    }
    if (submajor === '12') { // Farmers
      if (['1211', '1212', '1214'].includes(unit)) return 1;
      if (unit === '1213') {
        if (code.startsWith('121311') || code.startsWith('121316')) return 2;
        return 1;
      }
      return 1;
    }
    if (submajor === '14') return 2;
    return 1;
  }
  if (major === '3') { // Technicians and Trades
    if (submajor === '31') return 2;
    return 3;
  }
  if (major === '4') { // Community & Personal Service
    if (['4111', '4112', '4113', '4114', '4117', '4412', '4413'].includes(unit)) return 2;
    if (['4115', '4116', '4511', '4512', '4521', '4522', '4523', '4524'].includes(unit)) return 3;
    return 4;
  }
  if (major === '5') { // Clerical & Admin
    if (['5111', '5112'].includes(unit)) return 2;
    if (['5121', '5122'].includes(unit)) return 3;
    return 4;
  }
  if (major === '6') { // Sales
    if (['6111', '6112'].includes(unit)) return 3;
    return 4;
  }
  if (major === '7') return 4; // Machinery Operators
  if (major === '8') return 5; // Labourers
  return 1;
}

function slugify(name) {
  let s = String(name || '').toLowerCase();
  for (const ch of ",.;:()/&'") {
    s = s.replace(new RegExp('\\' + ch, 'g'), '');
  }
  return s.split(/\s+/).filter(Boolean).join('-');
}

function parseJsaData() {
  console.log('Loading JSA Excel files...');
  const occWb = xlsx.readFile(path.join(JSA_DIR, 'occupation_profiles_feb_2026.xlsx'));
  const projWb = xlsx.readFile(path.join(JSA_DIR, 'employment_projections_may_2025_2035.xlsx'));
  const indWb = xlsx.readFile(path.join(JSA_DIR, 'industry_data_feb_2026.xlsx'));

  // Industry slug map
  const indSlugMap = {};
  const indRows = xlsx.utils.sheet_to_json(indWb.Sheets['Table_1'], { header: 1 });
  for (let r = 7; r < indRows.length; r++) {
    const row = indRows[r];
    if (row && row[0]) {
      const name = String(row[0]).trim();
      indSlugMap[name] = slugify(name);
    }
  }

  // 4-digit code data map
  const code4Map = {};

  // Table 1 - Overview
  const t1 = xlsx.utils.sheet_to_json(occWb.Sheets['Table_1'], { header: 1 });
  for (let r = 7; r < t1.length; r++) {
    const row = t1[r];
    if (!row || !row[0]) continue;
    const c4 = String(row[0]).trim().padStart(4, '0');
    code4Map[c4] = code4Map[c4] || {};
    code4Map[c4].employed_count = typeof row[2] === 'number' ? row[2] : null;
    code4Map[c4].part_time_pct = typeof row[3] === 'number' ? row[3] : null;
    code4Map[c4].female_pct = typeof row[4] === 'number' ? row[4] : null;
    code4Map[c4].weekly_all = typeof row[5] === 'number' ? row[5] : null;
    code4Map[c4].median_age = typeof row[6] === 'number' ? row[6] : null;
  }

  // Table 4 - Earnings
  const t4 = xlsx.utils.sheet_to_json(occWb.Sheets['Table_4'], { header: 1 });
  for (let r = 7; r < t4.length; r++) {
    const row = t4[r];
    if (!row || !row[0]) continue;
    const c4 = String(row[0]).trim().padStart(4, '0');
    code4Map[c4] = code4Map[c4] || {};
    code4Map[c4].ft_share_pct = typeof row[2] === 'number' ? row[2] : null;
    code4Map[c4].weekly_ft = typeof row[4] === 'number' ? row[4] : (code4Map[c4].weekly_all || null);
    code4Map[c4].hourly_ft = typeof row[5] === 'number' ? row[5] : null;
    if (code4Map[c4].weekly_ft) {
      code4Map[c4].annual_ft = Math.round(code4Map[c4].weekly_ft * 52);
    }
  }

  // Table 5 - Top Industries
  const t5 = xlsx.utils.sheet_to_json(occWb.Sheets['Table_5'], { header: 1 });
  for (let r = 7; r < t5.length; r++) {
    const row = t5[r];
    if (!row || !row[0] || !row[2]) continue;
    const c4 = String(row[0]).trim().padStart(4, '0');
    code4Map[c4] = code4Map[c4] || {};
    code4Map[c4].top_industries = code4Map[c4].top_industries || [];
    const indName = String(row[2]).trim();
    if (indName && !code4Map[c4].top_industries.includes(indName) && code4Map[c4].top_industries.length < 5) {
      code4Map[c4].top_industries.push(indName);
    }
  }

  // Table 8 - Education Attainment
  const t8 = xlsx.utils.sheet_to_json(occWb.Sheets['Table_8'], { header: 1 });
  for (let r = 7; r < t8.length; r++) {
    const row = t8[r];
    if (!row || !row[0]) continue;
    const c4 = String(row[0]).trim().padStart(4, '0');
    code4Map[c4] = code4Map[c4] || {};
    code4Map[c4].education = {
      postgrad_pct: typeof row[2] === 'number' ? row[2] : 0,
      bachelor_pct: typeof row[3] === 'number' ? row[3] : 0,
      diploma_pct: typeof row[4] === 'number' ? row[4] : 0,
      certIII_IV_pct: typeof row[5] === 'number' ? row[5] : 0,
      year12_pct: typeof row[6] === 'number' ? row[6] : 0,
    };
  }

  // Projections - Table 6
  const tProj = xlsx.utils.sheet_to_json(projWb.Sheets['Table_6 Occupation Unit Group'], { header: 1 });
  for (let r = 4; r < tProj.length; r++) {
    const row = tProj[r];
    if (!row || !row[2]) continue;
    const c4 = String(row[2]).trim().padStart(4, '0');
    code4Map[c4] = code4Map[c4] || {};
    const emp2025 = typeof row[5] === 'number' ? Math.round(row[5] * 1000) : null;
    const emp2030 = typeof row[6] === 'number' ? Math.round(row[6] * 1000) : null;
    const emp2035 = typeof row[7] === 'number' ? Math.round(row[7] * 1000) : null;
    const growth10y = typeof row[11] === 'number' ? row[11] * 100 : null;

    let growthLabel = 'Moderate';
    if (growth10y !== null) {
      if (growth10y >= 15) growthLabel = 'Very Strong';
      else if (growth10y >= 8) growthLabel = 'Strong';
      else if (growth10y >= 2) growthLabel = 'Moderate';
      else if (growth10y >= -2) growthLabel = 'Stable';
      else growthLabel = 'Declining';
    }

    code4Map[c4].projections = {
      emp2025,
      emp2030,
      emp2035,
      growth10y: growth10y !== null ? Math.round(growth10y * 10) / 10 : null,
      growthLabel,
    };
  }

  return { code4Map, indSlugMap };
}

function enrichOccupationHtml(html, code, jsaInfo, indSlugMap) {
  const code4 = String(code).slice(0, 4);
  const skillLevel = getAnzscoSkillLevel(code);
  const data = jsaInfo[code4] || {};

  // 1. Ensure ANZSCO Skill Level is inside Skill assessment essentials
  if (!html.includes('ANZSCO Skill Level') && !html.includes('ANZSCO SKILL LEVEL')) {
    const skillLevelMetric = `
<div class="metric">
    <div class="ml">ANZSCO Skill Level</div>
    <div class="mv">Level ${skillLevel}</div>
    <div class="ms">of 5 (1 = highest)</div>
</div>
`;
    // Insert right after <div class="metric-grid"> inside essentials card
    html = html.replace(/<div class="metric-grid">/, `<div class="metric-grid">${skillLevelMetric}`);
  }

  // 2. Build Salary Card
  let salaryCardHtml = '';
  const weekly = data.weekly_ft || data.weekly_all;
  const annual = data.annual_ft || (weekly ? Math.round(weekly * 52) : null);
  const hourly = data.hourly_ft || (weekly ? Math.round(weekly / 38) : null);

  if (weekly || annual) {
    salaryCardHtml = `
      <article class="card">
        <span class="card-eyebrow">Salary &middot; ABS via JSA</span>
        <h2 class="card-title">💰 Median earnings (full-time)</h2>
        <div class="metric-grid" style="grid-template-columns:repeat(3,1fr)">
          ${weekly ? `<div class="metric"><div class="ml">Weekly</div><div class="mv">AUD&nbsp;$${weekly.toLocaleString()}</div></div>` : ''}
          ${annual ? `<div class="metric"><div class="ml">Annual (&times; 52)</div><div class="mv" style="color:var(--burnt)">AUD&nbsp;$${annual.toLocaleString()}</div></div>` : ''}
          ${hourly ? `<div class="metric"><div class="ml">Hourly</div><div class="mv">$${Math.round(hourly)}/hr</div></div>` : ''}
        </div>
        <p style="font-size:11px;color:var(--muted);margin-top:14px">
          Source: <strong>ABS via JSA Feb 2026</strong> &middot; 4-digit ANZSCO ${code4} parent rate
        </p>
      </article>
`;
  }

  // 3. Build Employment Outlook Card
  let outlookCardHtml = '';
  if (data.projections && data.projections.growthLabel) {
    const proj = data.projections;
    const pillClass = ['Very Strong', 'Strong'].includes(proj.growthLabel) ? 'pill-emerald' : (proj.growthLabel === 'Moderate' ? 'pill-amber' : 'pill-slate');
    const sign = (proj.growth10y !== null && proj.growth10y >= 0) ? '+' : '';
    const growthStr = proj.growth10y !== null ? `${sign}${proj.growth10y}% by 2035` : '';

    outlookCardHtml = `
      <article class="card">
        <span class="card-eyebrow">10-year Outlook &middot; JSA Projections</span>
        <h2 class="card-title">📈 Employment outlook to 2035</h2>
        <div style="display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:14px">
          <span class="pill ${pillClass}">
            ${proj.growthLabel} demand
          </span>
          ${growthStr ? `<span style="font-weight:700;color:var(--forest)">${growthStr}</span>` : ''}
        </div>
        <div class="metric-grid" style="grid-template-columns:repeat(3,1fr)">
          ${proj.emp2025 ? `<div class="metric"><div class="ml">Workers in 2025</div><div class="mv">${proj.emp2025.toLocaleString()}</div></div>` : ''}
          ${proj.emp2030 ? `<div class="metric"><div class="ml">Projected 2030</div><div class="mv">${proj.emp2030.toLocaleString()}</div></div>` : ''}
          ${proj.emp2035 ? `<div class="metric"><div class="ml">Projected 2035</div><div class="mv" style="color:var(--burnt)">${proj.emp2035.toLocaleString()}</div></div>` : ''}
        </div>
        <p style="font-size:11px;color:var(--muted);margin-top:14px">
          Source: <strong>JSA Employment Projections May 2025-2035</strong> &middot; 4-digit ANZSCO ${code4} parent rate
        </p>
      </article>
`;
  }

  // 4. Build Top Employing Industries Card
  let industriesCardHtml = '';
  const topInds = data.top_industries || [];
  if (topInds.length > 0) {
    const listItems = topInds.map((name, idx) => {
      const slug = indSlugMap[name] || slugify(name);
      return `
    <li style="display:flex;align-items:center;gap:10px">
        <span style="width:20px;height:20px;border-radius:6px;background:var(--burnt);color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:11px;font-weight:700">
            ${idx + 1}
        </span>
        <a href="/atlas/au/industry/${slug}/" style="font-size:14px;color:var(--burnt);font-weight:600;text-decoration:none">
            ${name} &rarr;
        </a>
    </li>`;
    }).join('\n');

    industriesCardHtml = `
      <article class="card card-cream">
        <span class="card-eyebrow">Where workers go</span>
        <h2 class="card-title">🏭 Top employing industries</h2>
        <ul style="list-style:none;display:flex;flex-direction:column;gap:8px">
          ${listItems}
        </ul>
        <p style="font-size:11px;color:var(--muted);margin-top:12px">Source: ABS via JSA Feb 2026 (ranked by share of employment) &middot; <em>Click any industry for hub page</em></p>
      </article>
`;
  }

  // 5. Build Education Profile Card
  let eduCardHtml = '';
  if (data.education) {
    const ed = data.education;
    const bachPlus = (ed.postgrad_pct || 0) + (ed.bachelor_pct || 0);
    const summaryText = bachPlus >= 50 ? `Most workers (${Math.round(bachPlus)}%) have a Bachelor degree or higher.`
      : (bachPlus >= 25 ? `A solid share (${Math.round(bachPlus)}%) hold a Bachelor or higher.`
      : `This role is dominated by Certificate / Diploma holders.`);

    const bars = [
      ['Postgrad', ed.postgrad_pct],
      ['Bachelor', ed.bachelor_pct],
      ['Diploma', ed.diploma_pct],
      ['Cert III/IV', ed.certIII_IV_pct],
      ['Year 12', ed.year12_pct]
    ].filter(([_, v]) => v && v > 0);

    if (bars.length > 0) {
      const barRows = bars.map(([name, v]) => `
          <div style="display:flex;align-items:center;gap:10px">
            <span style="width:90px;color:var(--muted)">${name}</span>
            <div style="flex:1;background:var(--border);height:18px;border-radius:4px;overflow:hidden">
              <div style="height:100%;width:${v}%;background:var(--forest);"></div>
            </div>
            <span style="width:42px;text-align:right;font-weight:700;color:var(--ink)">${Math.round(v)}%</span>
          </div>`).join('\n');

      eduCardHtml = `
      <article class="card">
        <span class="card-eyebrow">Education profile</span>
        <h2 class="card-title">🎓 Workforce qualifications</h2>
        <p style="font-size:15px;color:var(--ink);font-weight:600;margin-bottom:14px">
          ${summaryText}
        </p>
        <div style="display:flex;flex-direction:column;gap:8px;font-size:12px">
          ${barRows}
        </div>
        <p style="font-size:11px;color:var(--muted);margin-top:12px">Source: ABS via JSA Feb 2026</p>
      </article>
`;
    }
  }

  // Combine JSA cards to inject
  const combinedJsaCards = salaryCardHtml + outlookCardHtml + industriesCardHtml + eduCardHtml;

  // Replace any existing salary / outlook / industries / education / coming soon cards or insert cleanly
  // If "Overview" / "About this occupation" card exists, insert right after it
  if (!html.includes('Salary &middot; ABS via JSA') && !html.includes('Salary · ABS via JSA')) {
    // Remove "Coming Soon" card if present
    html = html.replace(/<article class="card"[^>]*style="background:#FCFBF7[^"]*"[\s\S]*?<\/article>/g, '');
    
    // Find where About this occupation ends
    const aboutMatch = html.match(/(<article class="card">[\s\S]*?<h2 class="card-title">About this occupation<\/h2>[\s\S]*?<\/article>)/);
    if (aboutMatch) {
      html = html.replace(aboutMatch[0], aboutMatch[0] + '\n' + combinedJsaCards);
    } else {
      // Otherwise insert after Skill assessment essentials
      const essMatch = html.match(/(<article class="card">[\s\S]*?<h2 class="card-title">Skill assessment essentials<\/h2>[\s\S]*?<\/article>)/);
      if (essMatch) {
        html = html.replace(essMatch[0], essMatch[0] + '\n' + combinedJsaCards);
      }
    }
  }

  return html;
}

function main() {
  const { code4Map, indSlugMap } = parseJsaData();
  console.log(`Parsed JSA data for ${Object.keys(code4Map).length} 4-digit ANZSCO unit groups.`);

  // Get all AU occupation directories
  const dirs = fs.readdirSync(PUBLIC_AU_DIR).filter(d => {
    return fs.statSync(path.join(PUBLIC_AU_DIR, d)).isDirectory() && !['industry', 'state'].includes(d);
  });

  console.log(`Found ${dirs.length} AU occupation directories to enrich.`);
  let updatedCount = 0;

  for (const code of dirs) {
    const pubFile = path.join(PUBLIC_AU_DIR, code, 'index.html');
    const bldFile = path.join(BUILD_AU_DIR, code, 'index.html');

    if (fs.existsSync(pubFile)) {
      const origHtml = fs.readFileSync(pubFile, 'utf8');
      const enrichedHtml = enrichOccupationHtml(origHtml, code, code4Map, indSlugMap);
      fs.writeFileSync(pubFile, enrichedHtml, 'utf8');

      // Sync to build
      fs.mkdirSync(path.dirname(bldFile), { recursive: true });
      fs.writeFileSync(bldFile, enrichedHtml, 'utf8');
      updatedCount++;
    }
  }

  console.log(`Enriched and synchronized ${updatedCount} AU occupation HTML files!`);
}

main();
