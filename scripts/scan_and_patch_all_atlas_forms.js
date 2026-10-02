const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = path.resolve(__dirname, '..');
const PUBLIC_ATLAS_DIR = path.join(PROJECT_ROOT, 'frontend', 'public', 'atlas');
const BUILD_ATLAS_DIR = path.join(PROJECT_ROOT, 'frontend', 'build', 'atlas');

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

    sendPayload('https://app.leamss.com/api/public-atlas/lead')
      .catch(function() {
        return sendPayload('https://api.leamss.com/api/public-atlas/lead');
      })
      .catch(function() {
        return sendPayload('/api/public-atlas/lead');
      })
      .then(function(resp) {
        var name = data.name || 'there';
        var code = data.atlas_code || '';
        var contact = data.phone || data.email || 'your contact details';
        var wrap = form.parentElement;
        wrap.innerHTML = '<div class="lead-form" style="text-align:center;padding:32px 20px;background:#fff;border:1px solid var(--border);border-radius:14px;box-shadow:0 8px 24px rgba(31,77,68,.06);">' +
          '<div style="width:52px;height:52px;background:#e6f4ea;color:#137333;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:26px;font-weight:bold;margin-bottom:14px">✓</div>' +
          '<h3 style="font-family:\\'Playfair Display\\',Georgia,serif;font-size:22px;font-weight:700;color:var(--forest);margin-bottom:8px">Pathway plan requested!</h3>' +
          '<p style="font-size:14px;color:var(--body);line-height:1.6;margin-bottom:18px">Thank you, <strong>' + name + '</strong>. Our migration specialist for ANZSCO ' + code + ' will review your profile and contact you on ' + contact + ' within 24 hours.</p>' +
          '<div style="font-size:12px;color:var(--muted);background:var(--cream);padding:10px 14px;border-radius:8px;border:1px solid var(--border)">Free consultation · 100% confidential · Registered migration network</div>' +
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

function patchDirectory(targetDir) {
  const files = walk(targetDir);
  console.log(`Scanning ${files.length} files in ${targetDir}...`);
  let patchedCount = 0;

  for (const file of files) {
    let html = fs.readFileSync(file, 'utf8');
    let modified = false;

    // Check if file contains a lead form
    if (html.includes('<form') && (html.includes('lead-form') || html.includes('public-atlas/lead') || html.includes('atlas_code'))) {
      // 1. Ensure form action points to app.leamss.com
      if (html.includes('action="/api/public-atlas/lead"')) {
        html = html.replace(/action="\/api\/public-atlas\/lead"/g, 'action="https://app.leamss.com/api/public-atlas/lead"');
        modified = true;
      }

      // 2. Remove older leadScripts if any
      const cleaned = html.replace(/<script>[\s\S]*?Pathway plan requested![\s\S]*?<\/script>/g, '');
      if (cleaned !== html) {
        html = cleaned;
        modified = true;
      }

      // 3. Inject new leadScript if not already present
      if (!html.includes('sendPayload(\'https://app.leamss.com/api/public-atlas/lead\')')) {
        if (html.includes('</body>')) {
          html = html.replace('</body>', leadScript + '\n</body>');
          modified = true;
        }
      }
    }

    if (modified) {
      fs.writeFileSync(file, html, 'utf8');
      patchedCount++;
    }
  }

  console.log(`Patched ${patchedCount} files in ${targetDir}`);
}

patchDirectory(PUBLIC_ATLAS_DIR);
if (fs.existsSync(BUILD_ATLAS_DIR)) {
  patchDirectory(BUILD_ATLAS_DIR);
}
