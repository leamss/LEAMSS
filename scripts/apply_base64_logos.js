const fs = require('fs');
const path = require('path');

const { color, white } = require('./logo_base64.json');

const headerImgTagAtlas = `<a href="/" class="brand-wordmark" aria-label="LEAMSS"><img src="${color}" alt="LEAMSS" style="height:44px;width:auto;vertical-align:middle;display:inline-block"></a>`;
const headerImgTagStart = `<a href="https://leamss.com" class="brand-wordmark"><img src="${color}" alt="LEAMSS" style="height:48px;width:auto;display:inline-block"></a>`;

const footerImgTagAtlas = `<div class="brand-wordmark" style="margin-bottom:12px"><img src="${color}" alt="LEAMSS" style="height:40px;width:auto;display:inline-block"></div>`;
const footerImgTagDark = `<div class="brand-wordmark" style="margin-bottom:14px"><img src="${white}" alt="LEAMSS" style="height:42px;width:auto;display:inline-block"></div>`;

const TEMPLATE_DIR = path.resolve(__dirname, '..', 'backend', 'templates');
const templateFiles = [
  path.join(TEMPLATE_DIR, 'atlas_hub_ssr.html'),
  path.join(TEMPLATE_DIR, 'atlas_country_ssr.html'),
  path.join(TEMPLATE_DIR, 'atlas_occupation_ssr.html')
];

for (const tpl of templateFiles) {
  if (fs.existsSync(tpl)) {
    let html = fs.readFileSync(tpl, 'utf8');
    // Replace header logo
    html = html.replace(/<a href="(?:\/|https:\/\/leamss\.com)" class="brand-wordmark" aria-label="LEAMSS">\s*<img[^>]*>\s*<\/a>/g, headerImgTagAtlas);
    // Replace footer logo
    html = html.replace(/<div class="brand-wordmark" style="margin-bottom:1[24]px">\s*<img[^>]*>\s*<\/div>/g, footerImgTagAtlas);
    fs.writeFileSync(tpl, html, 'utf8');
    console.log('Updated template:', tpl);
  }
}

// Update LeamssPublic.jsx
const leamssPublicFile = path.resolve(__dirname, '..', 'frontend', 'src', 'pages', 'LeamssPublic.jsx');
if (fs.existsSync(leamssPublicFile)) {
  let code = fs.readFileSync(leamssPublicFile, 'utf8');
  code = code.replace(/const LOGO_URL = '[^']*';/, `const LOGO_URL = '${color}';\nconst LOGO_WHITE_URL = '${white}';`);
  code = code.replace(/<img src="\/leamss-logo-white\.png"[^>]*\/>/g, `<img src={LOGO_WHITE_URL} alt="LEAMSS" className="h-11 w-auto mb-3 opacity-95" />`);
  fs.writeFileSync(leamssPublicFile, code, 'utf8');
  console.log('Updated LeamssPublic.jsx');
}

console.log('All templates and React components updated with inline data URI logo!');
