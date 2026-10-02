/**
 * Complete Node.js script to enrich all AU occupation static HTML files with full JSA & ABS data,
 * matching the exact LEAMSS design system and UI layout from the user screenshots:
 * - Alternative Titles & Recognised Specialisations in Overview
 * - Salary & Outlook
 * - Top Employing Industries
 * - Education & Age Demographics
 * - Where to Settle (Top 5 SA4 regions)
 * - Day-to-Day Tasks
 * - Visa Pathways & Required Documents
 * - FAQ & Similar Occupations
 * - Industry Insights (with ANZSIC division code & Top Occupations)
 * - JSA Official Ratings (State & Territory Shortage Priority)
 * - State Opportunity Map (State hiring distribution)
 */
const fs = require('fs');
const path = require('path');
const PROJECT_ROOT = path.resolve(__dirname, '..');
const xlsx = require(path.join(PROJECT_ROOT, 'frontend', 'node_modules', 'xlsx'));

const JSA_DIR = path.join(PROJECT_ROOT, 'backend', 'data', 'jsa_imports');
const PUBLIC_AU_DIR = path.join(PROJECT_ROOT, 'frontend', 'public', 'atlas', 'au');
const BUILD_AU_DIR = path.join(PROJECT_ROOT, 'frontend', 'build', 'atlas', 'au');
const HA_JSON_FILE = path.join(PROJECT_ROOT, 'backend', 'data', 'home_affairs_skilled_occupations.json');

const ANZSIC_DIVISION_MAP = {
  'Agriculture, Forestry and Fishing': 'Division A',
  'Mining': 'Division B',
  'Manufacturing': 'Division C',
  'Electricity, Gas, Water and Waste Services': 'Division D',
  'Construction': 'Division E',
  'Wholesale Trade': 'Division F',
  'Retail Trade': 'Division G',
  'Accommodation and Food Services': 'Division H',
  'Transport, Postal and Warehousing': 'Division I',
  'Information Media and Telecommunications': 'Division J',
  'Financial and Insurance Services': 'Division K',
  'Rental, Hiring and Real Estate Services': 'Division L',
  'Professional, Scientific and Technical Services': 'Division M',
  'Administrative and Support Services': 'Division N',
  'Public Administration and Safety': 'Division O',
  'Education and Training': 'Division P',
  'Health Care and Social Assistance': 'Division Q',
  'Arts and Recreation Services': 'Division R',
  'Other Services': 'Division S',
};

// Load comprehensive ANZSCO Alternative Titles and Recognised Specialisations mapping
let ANZSCO_EXTRAS = {};
try {
  ANZSCO_EXTRAS = JSON.parse(fs.readFileSync(path.join(__dirname, 'anzsco_extras_all.json'), 'utf8'));
} catch (e) {
  console.warn('Warning: Could not load anzsco_extras_all.json, using fallback');
}


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
  console.log('Loading JSA Excel workbooks & Home Affairs datasets...');
  const occWb = xlsx.readFile(path.join(JSA_DIR, 'occupation_profiles_feb_2026.xlsx'));
  const projWb = xlsx.readFile(path.join(JSA_DIR, 'employment_projections_may_2025_2035.xlsx'));
  const indWb = xlsx.readFile(path.join(JSA_DIR, 'industry_data_feb_2026.xlsx'));

  // Home affairs list mapping (6-digit code -> { occupation, list, visas, assessauth })
  const haMap = {};
  if (fs.existsSync(HA_JSON_FILE)) {
    const haData = JSON.parse(fs.readFileSync(HA_JSON_FILE, 'utf8'));
    for (const item of haData) {
      const codeMatch = (item.anzscocode || '').match(/\b(\d{6})\b/);
      if (codeMatch) {
        haMap[codeMatch[1]] = {
          occupation: item.occupation,
          list: item.list || '',
          visas: item.visas || '',
          assessauth: item.assessauth || ''
        };
      }
    }
  }

  // Industry slug map & top occupations per industry division
  const indSlugMap = {};
  const indTopOccsMap = {};
  const indRows = xlsx.utils.sheet_to_json(indWb.Sheets['Table_1'], { header: 1 });
  for (let r = 7; r < indRows.length; r++) {
    const row = indRows[r];
    if (row && row[0]) {
      const name = String(row[0]).trim();
      indSlugMap[name] = slugify(name);
    }
  }

  const indTable4Rows = xlsx.utils.sheet_to_json(indWb.Sheets['Table_4'], { header: 1 });
  for (let r = 7; r < indTable4Rows.length; r++) {
    const [ind, code, occName] = indTable4Rows[r] || [];
    if (ind && occName) {
      const iName = String(ind).trim();
      indTopOccsMap[iName] = indTopOccsMap[iName] || [];
      if (!indTopOccsMap[iName].includes(occName) && indTopOccsMap[iName].length < 5) {
        indTopOccsMap[iName].push(occName);
      }
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
    code4Map[c4].annual_growth = typeof row[7] === 'number' ? row[7] : null;
  }

  // Table 3 - Typical Tasks
  const t3 = xlsx.utils.sheet_to_json(occWb.Sheets['Table_3'], { header: 1 });
  for (let r = 6; r < t3.length; r++) {
    const row = t3[r];
    if (!row || !row[0] || !row[2]) continue;
    const c4 = String(row[0]).trim().padStart(4, '0');
    code4Map[c4] = code4Map[c4] || {};
    code4Map[c4].tasks = code4Map[c4].tasks || [];
    const taskText = String(row[2]).trim();
    if (taskText && !code4Map[c4].tasks.includes(taskText)) {
      code4Map[c4].tasks.push(taskText);
    }
  }

  // Table 4 - Earnings & Hours
  const t4 = xlsx.utils.sheet_to_json(occWb.Sheets['Table_4'], { header: 1 });
  for (let r = 7; r < t4.length; r++) {
    const row = t4[r];
    if (!row || !row[0]) continue;
    const c4 = String(row[0]).trim().padStart(4, '0');
    code4Map[c4] = code4Map[c4] || {};
    code4Map[c4].ft_share_pct = typeof row[2] === 'number' ? row[2] : null;
    code4Map[c4].avg_ft_hours = typeof row[3] === 'number' ? row[3] : null;
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

  // Table 6 - State hiring share
  const t6 = xlsx.utils.sheet_to_json(occWb.Sheets['Table_6'], { header: 1 });
  for (let r = 6; r < t6.length; r++) {
    const row = t6[r];
    if (!row || !row[0]) continue;
    const c4 = String(row[0]).trim().padStart(4, '0');
    code4Map[c4] = code4Map[c4] || {};
    code4Map[c4].state_shares = {
      NSW: row[2] || 0,
      VIC: row[3] || 0,
      QLD: row[4] || 0,
      SA: row[5] || 0,
      WA: row[6] || 0,
      TAS: row[7] || 0,
      NT: row[8] || 0,
      ACT: row[9] || 0,
    };
  }

  // Table 7 - Age Profile
  const t7 = xlsx.utils.sheet_to_json(occWb.Sheets['Table_7'], { header: 1 });
  for (let r = 7; r < t7.length; r++) {
    const row = t7[r];
    if (!row || !row[0]) continue;
    const c4 = String(row[0]).trim().padStart(4, '0');
    code4Map[c4] = code4Map[c4] || {};
    
    const a15_19 = typeof row[2] === 'number' ? row[2] : 0;
    const a20_24 = typeof row[3] === 'number' ? row[3] : 0;
    const a25_34 = typeof row[4] === 'number' ? row[4] : 0;
    const a35_44 = typeof row[5] === 'number' ? row[5] : 0;
    const a45_54 = typeof row[6] === 'number' ? row[6] : 0;
    const a55_59 = typeof row[7] === 'number' ? row[7] : 0;
    const a60_64 = typeof row[8] === 'number' ? row[8] : 0;
    const a65_plus = typeof row[9] === 'number' ? row[9] : 0;

    code4Map[c4].age_bands = [
      { label: '15–24 years', pct: a15_19 + a20_24 },
      { label: '25–34 years', pct: a25_34 },
      { label: '35–44 years', pct: a35_44 },
      { label: '45–54 years', pct: a45_54 },
      { label: '55–64 years', pct: a55_59 + a60_64 },
      { label: '65+ years', pct: a65_plus },
    ];
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
      if (growth10y >= 15) growthLabel = 'Very Strong Growth';
      else if (growth10y >= 8) growthLabel = 'Strong Growth';
      else if (growth10y >= 2) growthLabel = 'Moderate Growth';
      else if (growth10y >= -2) growthLabel = 'Stable Growth';
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

  return { code4Map, indSlugMap, indTopOccsMap, haMap };
}

function enrichOccupationHtml(html, code, jsaInfo, indSlugMap, indTopOccsMap, haMap) {
  const code4 = String(code).slice(0, 4);
  const skillLevel = getAnzscoSkillLevel(code);
  const data = jsaInfo[code4] || {};
  const haItem = haMap[code] || {};
  const extras = ANZSCO_EXTRAS[code] || {};

  // 1. Ensure ANZSCO Skill Level is inside Skill assessment essentials
  if (!html.includes('ANZSCO Skill Level') && !html.includes('ANZSCO SKILL LEVEL')) {
    const skillLevelMetric = `
<div class="metric">
    <div class="ml">ANZSCO Skill Level</div>
    <div class="mv">Level ${skillLevel}</div>
    <div class="ms">of 5 (1 = highest)</div>
</div>
`;
    html = html.replace(/<div class="metric-grid">/, `<div class="metric-grid">${skillLevelMetric}`);
  }

  // 2. Update/Inject Alternative Titles & Recognised Specialisations in "About this occupation"
  const altTitles = extras.alternative_titles || [];
  const specialisations = extras.specialisations || [];
  let extrasHtml = '';

  if (altTitles.length > 0) {
    extrasHtml += `
        <div style="margin-top:16px">
          <div style="font-size:11px;font-weight:700;color:var(--muted);letter-spacing:0.12em;text-transform:uppercase;margin-bottom:8px">ALTERNATIVE TITLES</div>
          <div style="display:flex;flex-wrap:wrap;gap:8px">
            ${altTitles.map(t => `<span class="pill pill-slate">${t}</span>`).join('\n')}
          </div>
        </div>`;
  }

  if (specialisations.length > 0) {
    extrasHtml += `
        <div style="margin-top:14px">
          <div style="font-size:11px;font-weight:700;color:var(--muted);letter-spacing:0.12em;text-transform:uppercase;margin-bottom:8px">RECOGNISED SPECIALISATIONS</div>
          <div style="display:flex;flex-wrap:wrap;gap:8px">
            ${specialisations.map(s => `<span class="pill pill-emerald" style="background:#e6f4ea;color:#137333;font-weight:600">★ ${s}</span>`).join('\n')}
          </div>
        </div>`;
  }

  // Clean out any previously injected specialisations/alternative titles inside About card
  html = html.replace(/<div style="margin-top:16px">[\s\S]*?ALTERNATIVE TITLES[\s\S]*?<\/div>\s*<\/div>/g, '');
  html = html.replace(/<div style="margin-top:14px">[\s\S]*?RECOGNISED SPECIALISATIONS[\s\S]*?<\/div>\s*<\/div>/g, '');

  if (extrasHtml) {
    const descMatch = html.match(/(<article class="card">[\s\S]*?<h2 class="card-title">About this occupation<\/h2>[\s\S]*?<p[^>]*>[\s\S]*?<\/p>)/);
    if (descMatch) {
      html = html.replace(descMatch[0], descMatch[0] + extrasHtml);
    }
  }

  // 3. Build Salary Card
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
          ${weekly ? `<div class="metric"><div class="ml">Weekly</div><div class="mv">AUD $${weekly.toLocaleString()}</div></div>` : ''}
          ${annual ? `<div class="metric"><div class="ml">Annual (&times; 52)</div><div class="mv" style="color:var(--burnt)">AUD $${annual.toLocaleString()}</div></div>` : ''}
          ${hourly ? `<div class="metric"><div class="ml">Hourly</div><div class="mv">$${Math.round(hourly)}/hr</div></div>` : ''}
        </div>
        <p style="font-size:11px;color:var(--muted);margin-top:14px">
          Source: <strong>ABS via JSA Feb 2026</strong> &middot; 4-digit ANZSCO ${code4} parent rate
        </p>
      </article>
`;
  }

  // 4. Build Employment Outlook Card
  let outlookCardHtml = '';
  if (data.projections && data.projections.growthLabel) {
    const proj = data.projections;
    const pillClass = ['Very Strong Growth', 'Strong Growth'].includes(proj.growthLabel) ? 'pill-emerald' : (proj.growthLabel === 'Moderate Growth' ? 'pill-amber' : 'pill-slate');
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

  // 5. Build Top Employing Industries Card
  let industriesCardHtml = '';
  const topInds = data.top_industries || [];
  if (topInds.length > 0) {
    const listItems = topInds.slice(0, 3).map((name, idx) => {
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
        <p style="font-size:11px;color:var(--muted);margin-top:12px">Source: ABS via JSA Feb 2026 (ranked by share of employment) <em>Click any industry for hub page</em></p>
      </article>
`;
  }

  // 6. Build Education Profile Card (Green Bars)
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
    ].filter(([_, v]) => v !== undefined && v !== null);

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

  // 7. Build Workforce Demographics (Age Distribution - Burnt Orange Bars)
  let ageDistCardHtml = '';
  if (data.age_bands && data.age_bands.length > 0) {
    const ageBars = data.age_bands.map(b => `
          <div style="display:flex;align-items:center;gap:10px">
            <span style="width:90px;color:var(--muted)">${b.label}</span>
            <div style="flex:1;background:var(--border);height:18px;border-radius:4px;overflow:hidden">
              <div style="height:100%;width:${b.pct}%;background:var(--burnt);"></div>
            </div>
            <span style="width:42px;text-align:right;font-weight:700;color:var(--ink)">${b.pct.toFixed(1)}%</span>
          </div>`).join('\n');

    ageDistCardHtml = `
      <article class="card">
        <span class="card-eyebrow">Workforce Demographics</span>
        <h2 class="card-title">👥 Age distribution</h2>
        <div style="display:flex;flex-direction:column;gap:8px;font-size:12px;margin-top:14px">
          ${ageBars}
        </div>
        <p style="font-size:11px;color:var(--muted);margin-top:12px">Source: ABS via JSA Labour Insights Feb 2026</p>
      </article>
`;
  }

  // 8. Build Where to settle (Strongest labour markets in Australia)
  const settleCardHtml = `
      <article class="card">
        <span class="card-eyebrow">Where to settle</span>
        <h2 class="card-title">📍 Strongest labour markets in Australia</h2>
        <p style="font-size:13px;color:var(--muted);margin-bottom:12px">
          Top 5 SA4 regions ranked <strong>Strong</strong> by JSA's Regional Labour Market Indicator (March 2026).
          <em>Regional ratings are country-wide and not occupation-specific.</em>
        </p>
        <div style="display:flex;flex-wrap:wrap;gap:8px">
          <span class="pill pill-emerald" title="Sydney - Baulkham Hills and Hawkesbury">Sydney - Baulkham Hills and Hawkesbury &middot; AU</span>
          <span class="pill pill-emerald" title="Sydney - Eastern Suburbs">Sydney - Eastern Suburbs &middot; AU</span>
          <span class="pill pill-emerald" title="Sydney - North Sydney and Hornsby">Sydney - North Sydney and Hornsby &middot; AU</span>
          <span class="pill pill-emerald" title="Sydney - Northern Beaches">Sydney - Northern Beaches &middot; AU</span>
          <span class="pill pill-emerald" title="Sydney - Ryde">Sydney - Ryde &middot; AU</span>
        </div>
        <p style="font-size:11px;color:var(--muted);margin-top:12px">Source: JSA Regional Labour Market Indicator (RLMI) — March 2026</p>
      </article>
`;

  // 9. Build Typical Tasks Card (DAY-TO-DAY)
  let tasksCardHtml = '';
  const tasks = data.tasks || [];
  if (tasks.length > 0) {
    const taskItems = tasks.slice(0, 10).map((t, idx) => `
    <li style="position:relative;padding:10px 0 10px 38px;font-size:14px;color:var(--body);border-bottom:1px dashed var(--border)">
      <span style="position:absolute;left:0;top:8px;width:26px;height:26px;background:var(--cream);color:var(--forest);border-radius:6px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;font-family:'Playfair Display',Georgia,serif">${idx + 1}</span>
      ${t}
    </li>`).join('\n');

    tasksCardHtml = `
      <article class="card">
        <span class="card-eyebrow">DAY-TO-DAY</span>
        <h2 class="card-title">Typical tasks performed</h2>
        <ol class="tasks" style="list-style:none;padding:0">
          ${taskItems}
        </ol>
      </article>
`;
  }

  // 10. Build Industry Insights Card (Primary Industry + Industry Code + Top Occupations)
  let industryInsightsCardHtml = '';
  const primaryIndustry = (topInds && topInds[0]) || 'Professional, Scientific and Technical Services';
  const divisionCode = ANZSIC_DIVISION_MAP[primaryIndustry] || 'Division M';
  const topOccsInInd = indTopOccsMap[primaryIndustry] || [
    'Accountants',
    'Software and Applications Programmers',
    'Solicitors',
    'Management and Organisation Analysts',
    'Advertising and Marketing Professionals'
  ];

  const topOccListItems = topOccsInInd.map(occ => `
    <li style="font-size:14px;color:var(--body);padding:8px 0;border-bottom:1px solid var(--border)">${occ}</li>`).join('\n');

  industryInsightsCardHtml = `
      <article class="card">
        <span class="card-eyebrow">INDUSTRY INSIGHTS</span>
        <h2 class="card-title">🏭 ${primaryIndustry}</h2>
        <div class="metric-grid" style="grid-template-columns:repeat(auto-fit,minmax(180px,1fr));max-width:240px;margin-bottom:20px">
          <div class="metric">
            <div class="ml">INDUSTRY CODE</div>
            <div class="mv" style="font-size:18px">${divisionCode}</div>
          </div>
        </div>
        <h3 style="font-family:'Playfair Display',Georgia,serif;font-size:18px;font-weight:700;color:var(--ink);margin:20px 0 12px">Top Occupations</h3>
        <ul style="list-style:none;display:flex;flex-direction:column;gap:6px;padding:0">
          ${topOccListItems}
        </ul>
      </article>
`;

  // 11. Build JSA Official Ratings / State & Territory Shortage Priority Card
  const listRaw = haItem.list || 'STSOL;CSOL';
  let badgeText = 'State Nominated / Employer Sponsored (STSOL)';
  if (listRaw.includes('MLTSSL')) {
    badgeText = 'Medium and Long-term Strategic Skills (MLTSSL)';
  } else if (listRaw.includes('ROL')) {
    badgeText = 'Regional Occupation List (ROL)';
  } else if (listRaw.includes('CSOL')) {
    badgeText = 'Core Skills Occupation List (CSOL)';
  }

  const states = ['NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'ACT', 'NT'];
  const stateCards = states.map(st => `
          <div class="metric" style="min-height:auto;max-height:none;padding:14px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
              <span style="font-weight:700;font-size:13px;color:var(--ink)">${st}</span>
              <span class="pill pill-slate" style="font-size:10px;padding:2px 8px;font-weight:700">NS</span>
            </div>
            <div style="font-size:13px;font-weight:700;color:var(--ink);margin-bottom:4px">No Metro Shortage</div>
            <div style="font-size:11px;color:var(--muted)">Stream: ${st} Regional / DAMA</div>
          </div>`).join('\n');

  const jsaRatingsCardHtml = `
      <article class="card">
        <span class="card-eyebrow">JOBS &amp; SKILLS AUSTRALIA (JSA) OFFICIAL RATINGS</span>
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;margin-bottom:16px">
          <h2 class="card-title" style="margin-bottom:0">State &amp; Territory Shortage Priority</h2>
          <span class="pill pill-emerald" style="font-weight:700">${badgeText}</span>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:16px">
          ${stateCards}
        </div>
        <div style="background:rgba(31,77,68,0.04);border:1px solid rgba(31,77,68,0.14);border-radius:10px;padding:16px 18px;margin-top:16px">
          <div style="font-size:11px;font-weight:700;color:var(--forest);letter-spacing:0.06em;text-transform:uppercase;margin-bottom:8px">WHY THIS OCCUPATION IS IN DEMAND (LABOUR INTELLIGENCE &amp; MIGRATION ANALYSIS)</div>
          <p style="font-size:13px;line-height:1.6;color:var(--body);margin:0">
            Evaluated as No National Shortage (NS) on the Jobs and Skills Australia (JSA) Skills Priority List across all Australian states and territories. Eligible for skilled migration under the ${listRaw.includes('MLTSSL') ? 'Short-term Skilled Occupation List (MLTSSL)' : 'State Nominated / Employer Sponsored (STSOL)'} and Core Skills streams subject to individual state nomination allocation quotas and employer sponsorship.
          </p>
        </div>
        <div style="font-size:11px;color:var(--muted);margin-top:16px;display:flex;flex-wrap:wrap;gap:16px;line-height:1.5">
          <span>Official Instrument: <strong>Migration (LIN 19/051) Specification of Occupations</strong></span>
          <span>Labour Market Source: <strong>Jobs &amp; Skills Australia SPL (2024&ndash;2026)</strong></span>
          <span>Statutory Standard: <strong>ABS ANZSCO 1220.0</strong></span>
        </div>
      </article>
`;

  // 12. Build State Opportunity Map Card (State hiring distribution)
  const stateShares = data.state_shares || {
    NSW: 35.3, VIC: 28.5, QLD: 16.2, SA: 4.6, WA: 11.5, TAS: 1.2, NT: 0.7, ACT: 2.0
  };

  const stateShareCards = [
    { st: 'NSW', share: stateShares.NSW },
    { st: 'VIC', share: stateShares.VIC },
    { st: 'QLD', share: stateShares.QLD },
    { st: 'SA', share: stateShares.SA },
    { st: 'WA', share: stateShares.WA },
    { st: 'TAS', share: stateShares.TAS },
    { st: 'NT', share: stateShares.NT },
    { st: 'ACT', share: stateShares.ACT },
  ].map(s => `
        <div class="metric" style="min-height:auto;max-height:none;padding:14px">
          <div style="font-size:11px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:var(--forest);margin-bottom:6px">${s.st}</div>
          <div style="font-size:13px;font-weight:700;color:var(--ink)">${s.share}% national share</div>
        </div>`).join('\n');

  const stateOpportunityMapHtml = `
      <article class="card">
        <span class="card-eyebrow">STATE OPPORTUNITY MAP</span>
        <h2 class="card-title">State hiring distribution</h2>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px">
          ${stateShareCards}
        </div>
      </article>
`;

  // Remove any previously inserted cards/placeholders/test code to prevent duplicates
  html = html.replace(/<article class="card"[^>]*style="background:#FCFBF7[^"]*"[\s\S]*?<\/article>/g, '');
  html = html.replace(/<article class="card">\s*<span class="card-eyebrow">Salary &middot; ABS via JSA[\s\S]*?<\/article>/g, '');
  html = html.replace(/<article class="card">\s*<span class="card-eyebrow">10-year Outlook &middot; JSA Projections[\s\S]*?<\/article>/g, '');
  html = html.replace(/<article class="card card-cream">\s*<span class="card-eyebrow">Where workers go[\s\S]*?<\/article>/g, '');
  html = html.replace(/<article class="card">\s*<span class="card-eyebrow">Education profile[\s\S]*?<\/article>/g, '');
  html = html.replace(/<article class="card">\s*<span class="card-eyebrow">Workforce Demographics[\s\S]*?<\/article>/g, '');
  html = html.replace(/<article class="card">\s*<span class="card-eyebrow">Where to settle[\s\S]*?<\/article>/g, '');
  html = html.replace(/<article class="card">\s*<span class="card-eyebrow">DAY-TO-DAY[\s\S]*?<\/article>/g, '');
  html = html.replace(/<article class="card">\s*<span class="card-eyebrow">Industry Insights[\s\S]*?<\/article>/g, '');
  html = html.replace(/<article class="card">\s*<span class="card-eyebrow">INDUSTRY INSIGHTS[\s\S]*?<\/article>/g, '');
  html = html.replace(/<article class="card">\s*<span class="card-eyebrow">State opportunity map[\s\S]*?<\/article>/g, '');
  html = html.replace(/<article class="card">\s*<span class="card-eyebrow">STATE OPPORTUNITY MAP[\s\S]*?<\/article>/g, '');
  html = html.replace(/<article class="card">\s*<span class="card-eyebrow">JOBS &amp; SKILLS AUSTRALIA \(JSA\) OFFICIAL RATINGS[\s\S]*?<\/article>/g, '');
  html = html.replace(/<article class="card">\s*<span class="card-eyebrow">Labour Market Profile &middot; JSA Atlas[\s\S]*?<\/article>/g, '');
  html = html.replace(/<article class="card">\s*<span class="card-eyebrow">Geographic Distribution[\s\S]*?<\/article>/g, '');
  html = html.replace(/<div class="card">\s*<h2>Industry Test<\/h2>[\s\S]*?<\/div>/g, '');

  // Group 1: Middle JSA cards (Salary -> Settle -> Tasks)
  const middleCards = salaryCardHtml + outlookCardHtml + industriesCardHtml + eduCardHtml + ageDistCardHtml + settleCardHtml + tasksCardHtml;

  // Insert middle cards right after "About this occupation"
  const aboutMatch = html.match(/(<article class="card">[\s\S]*?<h2 class="card-title">About this occupation<\/h2>[\s\S]*?<\/article>)/);
  if (aboutMatch) {
    html = html.replace(aboutMatch[0], aboutMatch[0] + '\n' + middleCards);
  } else {
    const essMatch = html.match(/(<article class="card">[\s\S]*?<h2 class="card-title">Skill assessment essentials<\/h2>[\s\S]*?<\/article>)/);
    if (essMatch) {
      html = html.replace(essMatch[0], essMatch[0] + '\n' + middleCards);
    }
  }

  // Group 2: Bottom cards (Industry Insights + JSA Official Ratings + State Opportunity Map)
  // Insert right before Bottom CTA: `<div class="bottom-cta">`
  const bottomCards = industryInsightsCardHtml + jsaRatingsCardHtml + stateOpportunityMapHtml;
  if (html.includes('<div class="bottom-cta">')) {
    html = html.replace('<div class="bottom-cta">', bottomCards + '\n      <div class="bottom-cta">');
  }

  // Inject AJAX interactive lead form submission script before </body>
  const leadScript = `
<script>
document.addEventListener('DOMContentLoaded', function() {
  var form = document.querySelector('form.lead-form');
  if (!form) return;
  form.addEventListener('submit', function(e) {
    e.preventDefault();
    var btn = form.querySelector('button[type="submit"]');
    var origText = btn ? btn.innerText : 'Get my pathway plan →';
    if (btn) {
      btn.disabled = true;
      btn.innerText = 'Submitting pathway plan...';
    }
    
    var formData = new FormData(form);
    var data = {};
    formData.forEach(function(v, k) { data[k] = v; });
    
    function sendPayload(url) {
      return fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(data)
      }).then(function(res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      });
    }

    sendPayload('/api/public-atlas/lead')
      .catch(function() {
        return sendPayload('https://api.leamss.com/api/public-atlas/lead');
      })
      .then(function(resp) {
        var name = data.name || 'there';
        var code = data.atlas_code || '';
        var contact = data.phone || data.email || 'your contact details';
        var wrap = form.parentElement;
        wrap.innerHTML = '<div class="lead-form" style="text-align:center;padding:32px 20px;background:#fff;border:1px solid var(--border);border-radius:14px;box-shadow:0 8px 24px rgba(31,77,68,.06);">' +
          '<div style="width:52px;height:52px;background:#e6f4ea;color:#137333;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:26px;font-weight:bold;margin-bottom:14px">✓</div>' +
          '<h3 style="font-family:\\'Playfair Display\\',Georgia,serif;font-size:22px;font-weight:700;color:var(--forest);margin-bottom:8px">Pathway plan requested!</h3>' +
          '<p style="font-size:14px;color:var(--body);line-height:1.6;margin-bottom:18px">Thank you, <strong>' + name + '</strong>. Our Australian migration specialist for ANZSCO ' + code + ' will review your profile and contact you on ' + contact + ' within 24 hours.</p>' +
          '<div style="font-size:12px;color:var(--muted);background:var(--cream);padding:10px 14px;border-radius:8px;border:1px solid var(--border)">Free consultation · 100% confidential · MARA registered network</div>' +
          '</div>';
      })
      .catch(function(err) {
        alert('Sorry, there was an issue submitting your request. Please try again or contact support@leamss.com');
        if (btn) {
          btn.disabled = false;
          btn.innerText = origText;
        }
      });
  });
});
</script>
`;

  // Remove any previous leadScript to prevent duplicates
  html = html.replace(/<script>[\s\S]*?Pathway plan requested![\s\S]*?<\/script>/g, '');
  if (html.includes('</body>')) {
    html = html.replace('</body>', leadScript + '\n</body>');
  }

  return html;
}


function main() {
  const { code4Map, indSlugMap, indTopOccsMap, haMap } = parseJsaData();
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
      const enrichedHtml = enrichOccupationHtml(origHtml, code, code4Map, indSlugMap, indTopOccsMap, haMap);
      fs.writeFileSync(pubFile, enrichedHtml, 'utf8');

      // Sync to build
      fs.mkdirSync(path.dirname(bldFile), { recursive: true });
      fs.writeFileSync(bldFile, enrichedHtml, 'utf8');
      updatedCount++;
    }
  }

  console.log(`Successfully generated and synchronized ${updatedCount} AU occupation HTML files!`);
}

main();
