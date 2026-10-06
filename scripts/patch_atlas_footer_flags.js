/**
 * Script to update all static Atlas HTML files in frontend/public/atlas and frontend/build/atlas:
 * 1. Replace emoji/letter country codes in header with crisp flag images (AU, CA, NZ)
 * 2. Update email support@leamss.com -> info@leamss.com in Atlas footers & scripts
 * 3. Remove MARA-registered network from Atlas Trust lists & cards
 * 4. Replace footer country links with flag images (Australia, Canada, New Zealand)
 */
const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = path.resolve(__dirname, '..');
const PUBLIC_ATLAS_DIR = path.join(PROJECT_ROOT, 'frontend', 'public', 'atlas');
const BUILD_ATLAS_DIR = path.join(PROJECT_ROOT, 'frontend', 'build', 'atlas');

const auFlagHeader = '<a href="/atlas/au/"><img src="https://flagcdn.com/w20/au.png" srcset="https://flagcdn.com/w40/au.png 2x" width="20" height="15" alt="AU" style="vertical-align:-2px;border-radius:2px;margin-right:5px;display:inline-block">AU</a>';
const caFlagHeader = '<a href="/atlas/ca/"><img src="https://flagcdn.com/w20/ca.png" srcset="https://flagcdn.com/w40/ca.png 2x" width="20" height="15" alt="CA" style="vertical-align:-2px;border-radius:2px;margin-right:5px;display:inline-block">CA</a>';
const nzFlagHeader = '<a href="/atlas/nz/"><img src="https://flagcdn.com/w20/nz.png" srcset="https://flagcdn.com/w40/nz.png 2x" width="20" height="15" alt="NZ" style="vertical-align:-2px;border-radius:2px;margin-right:5px;display:inline-block">NZ</a>';

const auFlagFooter = '<li><a href="/atlas/au/"><img src="https://flagcdn.com/w20/au.png" srcset="https://flagcdn.com/w40/au.png 2x" width="20" height="15" alt="Australia" style="vertical-align:-2px;border-radius:2px;margin-right:6px;display:inline-block">Australia</a></li>';
const caFlagFooter = '<li><a href="/atlas/ca/"><img src="https://flagcdn.com/w20/ca.png" srcset="https://flagcdn.com/w40/ca.png 2x" width="20" height="15" alt="Canada" style="vertical-align:-2px;border-radius:2px;margin-right:6px;display:inline-block">Canada</a></li>';
const nzFlagFooter = '<li><a href="/atlas/nz/"><img src="https://flagcdn.com/w20/nz.png" srcset="https://flagcdn.com/w40/nz.png 2x" width="20" height="15" alt="New Zealand" style="vertical-align:-2px;border-radius:2px;margin-right:6px;display:inline-block">New Zealand</a></li>';

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

function patchHtml(html) {
  let content = html;

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

  return content;
}

function processDirectory(dirName, dirPath) {
  const files = walk(dirPath);
  console.log(`Processing ${files.length} files in ${dirName}...`);
  let count = 0;
  for (const file of files) {
    const orig = fs.readFileSync(file, 'utf8');
    const patched = patchHtml(orig);
    if (patched !== orig) {
      fs.writeFileSync(file, patched, 'utf8');
      count++;
    }
  }
  console.log(`Updated ${count} files in ${dirName}.`);
}

function main() {
  processDirectory('frontend/public/atlas', PUBLIC_ATLAS_DIR);
  processDirectory('frontend/build/atlas', BUILD_ATLAS_DIR);
  console.log('All Atlas static HTML files successfully updated!');
}

main();
