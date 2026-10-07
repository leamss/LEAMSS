/**
 * Script to update all static HTML files in frontend/public and frontend/build:
 * 1. Replace emoji/letter country codes in header with crisp flag images (AU, CA, NZ)
 * 2. Update email support@leamss.com -> info@leamss.com in Atlas footers & scripts
 * 3. Remove MARA-registered network from Atlas Trust lists & cards
 * 4. Replace footer country links with flag images (Australia, Canada, New Zealand)
 * 5. Update lead form privacy policy link to https://leamss.com/privacy-policy
 * 6. Replace country card flags in atlas/index.html with flag images
 * 7. Change "Book Free Consultation" -> "Book a Consultation"
 * 8. Change "since 2014" -> "since 2024"
 * 9. Ensure crisp, high-res transparent LEAMSS logo in header and footer across all pages
 */
const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = path.resolve(__dirname, '..');
const PUBLIC_DIR = path.join(PROJECT_ROOT, 'frontend', 'public');
const BUILD_DIR = path.join(PROJECT_ROOT, 'frontend', 'build');

const { color: logoColorBase64, white: logoWhiteBase64 } = require('./logo_base64.json');

const auFlagHeader = '<a href="/atlas/au/"><img src="https://flagcdn.com/w20/au.png" srcset="https://flagcdn.com/w40/au.png 2x" width="20" height="15" alt="AU" style="vertical-align:-2px;border-radius:2px;margin-right:5px;display:inline-block">AU</a>';
const caFlagHeader = '<a href="/atlas/ca/"><img src="https://flagcdn.com/w20/ca.png" srcset="https://flagcdn.com/w40/ca.png 2x" width="20" height="15" alt="CA" style="vertical-align:-2px;border-radius:2px;margin-right:5px;display:inline-block">CA</a>';
const nzFlagHeader = '<a href="/atlas/nz/"><img src="https://flagcdn.com/w20/nz.png" srcset="https://flagcdn.com/w40/nz.png 2x" width="20" height="15" alt="NZ" style="vertical-align:-2px;border-radius:2px;margin-right:5px;display:inline-block">NZ</a>';

const auFlagFooter = '<li><a href="/atlas/au/"><img src="https://flagcdn.com/w20/au.png" srcset="https://flagcdn.com/w40/au.png 2x" width="20" height="15" alt="Australia" style="vertical-align:-2px;border-radius:2px;margin-right:6px;display:inline-block">Australia</a></li>';
const caFlagFooter = '<li><a href="/atlas/ca/"><img src="https://flagcdn.com/w20/ca.png" srcset="https://flagcdn.com/w40/ca.png 2x" width="20" height="15" alt="Canada" style="vertical-align:-2px;border-radius:2px;margin-right:6px;display:inline-block">Canada</a></li>';
const nzFlagFooter = '<li><a href="/atlas/nz/"><img src="https://flagcdn.com/w20/nz.png" srcset="https://flagcdn.com/w40/nz.png 2x" width="20" height="15" alt="New Zealand" style="vertical-align:-2px;border-radius:2px;margin-right:6px;display:inline-block">New Zealand</a></li>';

const privacyPolicyReplacement = '<a href="https://leamss.com/privacy-policy" target="_blank" rel="noopener noreferrer">privacy policy</a>';

const headerLogoAtlas = `<a href="/" class="brand-wordmark" aria-label="LEAMSS"><img src="${logoColorBase64}" alt="LEAMSS" style="height:44px;width:auto;vertical-align:middle;display:inline-block"></a>`;
const headerLogoStart = `<a href="https://leamss.com" class="brand-wordmark"><img src="${logoColorBase64}" alt="LEAMSS" style="height:46px;width:auto;display:inline-block"></a>`;

const footerLogoAtlas = `<div class="brand-wordmark" style="margin-bottom:12px"><img src="${logoColorBase64}" alt="LEAMSS" style="height:40px;width:auto;display:inline-block"></div>`;
const footerLogoDark = `<div class="brand-wordmark" style="margin-bottom:14px"><img src="${logoWhiteBase64}" alt="LEAMSS" style="height:42px;width:auto;display:inline-block"></div>`;

function walk(dir, results = []) {
  if (!fs.existsSync(dir)) return results;
  const list = fs.readdirSync(dir);
  for (const file of list) {
    const full = path.join(dir, file);
    const stat = fs.statSync(full);
    if (stat.isDirectory()) {
      walk(full, results);
    } else if (file.endsWith('.html')) {
      results.push(full);
    }
  }
  return results;
}

function patchHtml(html, filePath) {
  let content = html;
  const isStartOrCalc = filePath && (filePath.includes('start') || filePath.includes('calculator') || filePath.includes('eligibility'));

  // 1. Header flag links - match any variant of AU, CA, NZ in nav
  content = content.replace(/<a href="\/atlas\/au\/">\s*(?:[\uD83C][\uDDE6][\uD83C][\uDDFA]|🇦🇺|AU|\?+)?\s*AU\s*<\/a>/g, auFlagHeader);
  content = content.replace(/<a href="\/atlas\/ca\/">\s*(?:[\uD83C][\uDDE8][\uD83C][\uDDE6]|🇨🇦|CA|\?+)?\s*CA\s*<\/a>/g, caFlagHeader);
  content = content.replace(/<a href="\/atlas\/nz\/">\s*(?:[\uD83C][\uDDF3][\uD83C][\uDDFF]|🇳🇿|NZ|\?+)?\s*NZ\s*<\/a>/g, nzFlagHeader);

  // Also match cases where header has existing flag image or variations
  content = content.replace(/<a href="\/atlas\/au\/">.*?AU<\/a>/g, auFlagHeader);
  content = content.replace(/<a href="\/atlas\/ca\/">.*?CA<\/a>/g, caFlagHeader);
  content = content.replace(/<a href="\/atlas\/nz\/">.*?NZ<\/a>/g, nzFlagHeader);

  // 2. Footer country links
  content = content.replace(/<li><a href="\/atlas\/au\/">\s*(?:[\uD83C][\uDDE6][\uD83C][\uDDFA]|🇦🇺|AU|\?+)?\s*Australia\s*<\/a><\/li>/g, auFlagFooter);
  content = content.replace(/<li><a href="\/atlas\/ca\/">\s*(?:[\uD83C][\uDDE8][\uD83C][\uDDE6]|🇨🇦|CA|\?+)?\s*Canada\s*<\/a><\/li>/g, caFlagFooter);
  content = content.replace(/<li><a href="\/atlas\/nz\/">\s*(?:[\uD83C][\uDDF3][\uD83C][\uDDFF]|🇳🇿|NZ|\?+)?\s*New Zealand\s*<\/a><\/li>/g, nzFlagFooter);

  // 3. Email in footer and alerts: support@leamss.com -> info@leamss.com
  content = content.replace(/support@leamss\.com/g, 'info@leamss.com');

  // 4. Remove MARA-registered network from Trust column in footer
  content = content.replace(/\s*<li>\s*MARA-registered network\s*<\/li>/gi, '');
  content = content.replace(/\s*<li>\s*MARA registered network\s*<\/li>/gi, '');
  content = content.replace(/\s*·\s*MARA registered network/gi, '');
  content = content.replace(/\s*·\s*MARA-registered network/gi, '');
  content = content.replace(/\s*&middot;\s*MARA-registered network/gi, '');
  content = content.replace(/\s*&middot;\s*MARA registered network/gi, '');

  // 5. Privacy Policy Link in lead form and footer
  content = content.replace(/<a href="\/privacy">\s*privacy policy\s*<\/a>/gi, privacyPolicyReplacement);
  content = content.replace(/<a href="\/privacy-policy">\s*privacy policy\s*<\/a>/gi, privacyPolicyReplacement);

  // 6. Hub Country Destination Cards Flags
  content = content.replace(/<div class="country-name"><span class="country-flag">[^<]*<\/span>Australia<\/div>/g, '<div class="country-name"><img class="country-flag-img" src="https://flagcdn.com/w80/au.png" width="34" height="24" alt="Australia flag">Australia</div>');
  content = content.replace(/<div class="country-name"><span class="country-flag">[^<]*<\/span>Canada<\/div>/g, '<div class="country-name"><img class="country-flag-img" src="https://flagcdn.com/w80/ca.png" width="34" height="24" alt="Canada flag">Canada</div>');
  content = content.replace(/<div class="country-name"><span class="country-flag">[^<]*<\/span>New Zealand<\/div>/g, '<div class="country-name"><img class="country-flag-img" src="https://flagcdn.com/w80/nz.png" width="34" height="24" alt="New Zealand flag">New Zealand</div>');

  // Country card CSS styling if present
  if (content.includes('.country-card .country-flag{') && !content.includes('.country-card .country-flag-img{')) {
    content = content.replace(
      '.country-card .country-flag{margin-right:8px;font-size:32px;vertical-align:middle}',
      '.country-card .country-flag-img{margin-right:10px;width:34px;height:24px;border-radius:4px;display:inline-block;vertical-align:middle;box-shadow:0 2px 8px rgba(0,0,0,0.35)}'
    );
  }
  if (content.includes('.country-card .country-name{font-family:\'Playfair Display\',Georgia,serif;font-size:34px;font-weight:800;letter-spacing:-.01em;margin-bottom:10px;line-height:1.05}') && !content.includes('display:flex;align-items:center')) {
    content = content.replace(
      '.country-card .country-name{font-family:\'Playfair Display\',Georgia,serif;font-size:34px;font-weight:800;letter-spacing:-.01em;margin-bottom:10px;line-height:1.05}',
      '.country-card .country-name{font-family:\'Playfair Display\',Georgia,serif;font-size:34px;font-weight:800;letter-spacing:-.01em;margin-bottom:10px;line-height:1.05;display:flex;align-items:center}'
    );
  }

  // 7. Button CTA name: "Book Free Consultation" -> "Book a Consultation"
  content = content.replace(/Book Free Consultation/g, 'Book a Consultation');
  content = content.replace(/Book a free consultation/g, 'Book a consultation');

  // 8. Change "since 2014" -> "since 2024"
  content = content.replace(/since 2014/g, 'since 2024');
  content = content.replace(/Trusted since 2014/g, 'Trusted since 2024');
  content = content.replace(/"foundingDate":\s*"2014"/g, '"foundingDate": "2024"');

  // 9. Header logo replacement
  if (isStartOrCalc) {
    content = content.replace(/<a href="https:\/\/leamss\.com" class="brand-wordmark">\s*<img[^>]*>\s*<\/a>/g, headerLogoStart);
    content = content.replace(/<img src="[^"]*logo\.(?:webp|png)" alt="LEAMSS Logo"[^>]*>/g,
      '<img src="/start/leamss-logo.png" alt="LEAMSS" style="height:46px;width:auto" onerror="this.onerror=null;this.src=\'/leamss-logo.png\'">'
    );
  } else {
    content = content.replace(/<a href="(?:\/|https:\/\/leamss\.com)" class="brand-wordmark" aria-label="LEAMSS">\s*(?:<img[^>]*>|<span style="color:#2a777a">LE<\/span><span style="color:#f7620b">AM<\/span><span style="color:#d81f26">SS<\/span><span style="color:#1F4D44">\.<\/span>(?:\s*<span class="brand-tagline-pill">.*?<\/span>)?)\s*<\/a>/g,
      headerLogoAtlas
    );
  }

  // 10. Footer logo replacement
  if (isStartOrCalc) {
    content = content.replace(/<div class="brand-wordmark" style="margin-bottom:1[24]px">\s*<img[^>]*>\s*<\/div>/g, footerLogoDark);
    content = content.replace(/<div class="brand-wordmark" style="font-size:2[24]px;margin-bottom:1[02]px">\s*<span style="color:#2a777a">LE<\/span><span style="color:#f7620b">AM<\/span><span style="color:#d81f26">SS<\/span><span style="color:#[A-Za-z0-9]+">\.<\/span>\s*<\/div>/g, footerLogoDark);
  } else {
    content = content.replace(/<div class="brand-wordmark" style="margin-bottom:1[24]px">\s*<img[^>]*>\s*<\/div>/g, footerLogoAtlas);
    content = content.replace(/<div class="brand-wordmark" style="font-size:2[24]px;margin-bottom:1[02]px">\s*<span style="color:#2a777a">LE<\/span><span style="color:#f7620b">AM<\/span><span style="color:#d81f26">SS<\/span><span style="color:#[A-Za-z0-9]+">\.<\/span>\s*<\/div>/g, footerLogoAtlas);
  }

  return content;
}

function processDirectory(dirName, dirPath) {
  const files = walk(dirPath);
  console.log(`Processing ${files.length} files in ${dirName}...`);
  let count = 0;
  for (const file of files) {
    const orig = fs.readFileSync(file, 'utf8');
    const patched = patchHtml(orig, file);
    if (patched !== orig) {
      fs.writeFileSync(file, patched, 'utf8');
      count++;
    }
  }
  console.log(`Updated ${count} files in ${dirName}.`);
}

function main() {
  processDirectory('frontend/public', PUBLIC_DIR);
  if (fs.existsSync(BUILD_DIR)) {
    processDirectory('frontend/build', BUILD_DIR);
  }
  console.log('All static HTML files successfully updated!');
}

main();
