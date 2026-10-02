const fs = require('fs');
const path = require('path');

const src = path.join(__dirname, '..', 'frontend', 'public', 'start', 'index.html');
const content = fs.readFileSync(src, 'utf8');

const targets = [
  path.join(__dirname, '..', 'frontend', 'public', 'start.html'),
  path.join(__dirname, '..', 'frontend', 'public', 'calculator', 'index.html'),
  path.join(__dirname, '..', 'frontend', 'public', 'calculator.html'),
  path.join(__dirname, '..', 'frontend', 'public', 'eligibility', 'index.html'),
  path.join(__dirname, '..', 'frontend', 'public', 'eligibility.html'),
  path.join(__dirname, '..', 'frontend', 'build', 'start', 'index.html'),
  path.join(__dirname, '..', 'frontend', 'build', 'start.html'),
  path.join(__dirname, '..', 'frontend', 'build', 'calculator', 'index.html'),
  path.join(__dirname, '..', 'frontend', 'build', 'calculator.html'),
  path.join(__dirname, '..', 'frontend', 'build', 'eligibility', 'index.html'),
  path.join(__dirname, '..', 'frontend', 'build', 'eligibility.html'),
];

for (const t of targets) {
  fs.mkdirSync(path.dirname(t), { recursive: true });
  fs.writeFileSync(t, content, 'utf8');
  console.log('Successfully synced:', t);
}
