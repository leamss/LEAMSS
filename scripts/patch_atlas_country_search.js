const fs = require('fs');
const path = require('path');

const targetDirs = [
  path.join(__dirname, '..', 'frontend', 'public', 'atlas'),
  path.join(__dirname, '..', 'frontend', 'build', 'atlas'),
];

const newCSS = `/* Search & Typeahead */
.search-wrapper{position:relative;max-width:760px;margin:24px 0 20px;}
.search-bar{background:#fff;border:1.5px solid var(--border);border-radius:14px;padding:6px 6px 6px 18px;display:flex;align-items:center;gap:10px;box-shadow:0 4px 18px rgba(31,77,68,.05);width:100%;transition:border-color .15s,box-shadow .15s}
.search-bar:focus-within{border-color:var(--forest);box-shadow:0 6px 22px rgba(31,77,68,.12)}
.search-bar input{flex:1;outline:none;border:none;padding:12px 6px;font-size:14px;color:var(--ink);background:transparent;font-family:inherit;min-width:0}
.search-bar input::placeholder{color:var(--muted)}
.search-bar .ic{color:var(--muted);font-size:18px;flex-shrink:0}
.search-clear-btn{display:none;background:none;border:none;cursor:pointer;color:var(--muted);padding:4px 8px;font-size:16px;border-radius:50%;line-height:1}
.search-clear-btn:hover{color:var(--ink);background:var(--cream)}
.typeahead-dropdown{display:none;position:absolute;left:0;right:0;top:calc(100% + 6px);background:#fff;border:1.5px solid var(--border);border-radius:14px;box-shadow:0 12px 32px rgba(19,51,45,.15);max-height:360px;overflow-y:auto;z-index:100}
.typeahead-item{display:flex;align-items:center;gap:12px;padding:10px 16px;border-bottom:1px solid var(--border);text-decoration:none;color:inherit;transition:background .15s;cursor:pointer}
.typeahead-item:last-child{border-bottom:none}
.typeahead-item:hover, .typeahead-item.active{background:rgba(31,77,68,.06);text-decoration:none}
.typeahead-flag{font-size:12px;font-weight:700;color:var(--forest);background:rgba(31,77,68,.08);padding:3px 8px;border-radius:6px;flex-shrink:0;letter-spacing:.02em}
.typeahead-info{flex:1;min-width:0}
.typeahead-title{font-size:14px;font-weight:700;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.typeahead-sub{font-size:11px;color:var(--muted);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.typeahead-score{font-size:11px;font-weight:700;background:#0f172a;color:#fff;padding:2px 8px;border-radius:999px;flex-shrink:0}`;

const newScript = `<div id="root"></div>
<script>
(function() {
  var form = document.querySelector('form.search-bar');
  var input = form ? form.querySelector('input[name="q"]') : null;
  var clearBtn = form ? form.querySelector('.search-clear-btn') : null;
  var dropdown = document.querySelector('.typeahead-dropdown');
  var grid = document.querySelector('.occ-grid');
  var meta = document.querySelector('.section-title-meta');
  var pathParts = window.location.pathname.replace(/^\\/atlas\\//, '').split('/').filter(Boolean);
  var countryLower = pathParts[0] || 'au';
  var countryCode = countryLower.toUpperCase();
  var classification = countryCode === 'CA' ? 'NOC' : 'ANZSCO';
  
  if (!form || !input) return;
  
  var initialGridHtml = grid ? grid.innerHTML : '';
  var initialMetaText = meta ? meta.textContent : '';
  var typeaheadTimer = null;
  var typeaheadController = null;
  var searchController = null;
  
  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, function(m) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m];
    });
  }

  function updateClearBtn() {
    if (!clearBtn) return;
    clearBtn.style.display = input.value.trim() ? 'block' : 'none';
  }

  function hideDropdown() {
    if (dropdown) {
      dropdown.style.display = 'none';
      dropdown.innerHTML = '';
    }
  }

  function getApiBase() {
    var host = window.location.hostname;
    return (host === 'localhost' || host === '127.0.0.1') ? '/api' : 'https://api.leamss.com/api';
  }

  async function fetchTypeahead(q) {
    q = (q || '').trim();
    if (q.length < 2) {
      hideDropdown();
      return;
    }
    
    if (typeaheadController) {
      typeaheadController.abort();
    }
    typeaheadController = new AbortController();
    
    try {
      var url = getApiBase() + '/public-atlas/' + countryCode + '/typeahead?q=' + encodeURIComponent(q) + '&limit=6';
      var resp = await fetch(url, { signal: typeaheadController.signal });
      if (!resp.ok) return;
      var data = await resp.json();
      var items = data.items || [];
      
      if (items.length === 0 || document.activeElement !== input) {
        hideDropdown();
        return;
      }
      
      var html = '';
      for (var i = 0; i < items.length; i++) {
        var it = items[i];
        var cCode = escapeHtml(it.country_code || countryCode);
        var code = escapeHtml(it.code);
        var title = escapeHtml(it.title || '—');
        var body = escapeHtml(it.assessing_body || '');
        var pw = escapeHtml(it.pathway || '');
        var subParts = [];
        if (body) subParts.push(body);
        if (pw) subParts.push(pw);
        var subText = subParts.join(' · ') || (classification + ' ' + code);
        var score = it.score || 90;
        
        var occUrl = '/atlas/' + (it.country_code || countryCode).toLowerCase() + '/' + code + '/';
        
        html += '<a class="typeahead-item" href="' + occUrl + '" data-code="' + code + '">' +
          '<span class="typeahead-flag">' + cCode + '</span>' +
          '<div class="typeahead-info">' +
            '<div class="typeahead-title">' + code + ' · ' + title + '</div>' +
            '<div class="typeahead-sub">' + subText + '</div>' +
          '</div>' +
          '<span class="typeahead-score">' + score + '%</span>' +
        '</a>';
      }
      
      dropdown.innerHTML = html;
      dropdown.style.display = 'block';
    } catch (err) {
      if (err.name === 'AbortError') return;
      hideDropdown();
    }
  }

  async function performSearch(q) {
    hideDropdown();
    q = (q || '').trim();
    if (!grid) return;
    
    if (!q) {
      grid.innerHTML = initialGridHtml;
      if (meta) meta.textContent = initialMetaText;
      if (window.history.replaceState) {
        var url = new URL(window.location);
        url.searchParams.delete('q');
        window.history.replaceState(null, '', url.pathname + (url.search ? url.search : ''));
      }
      return;
    }
    
    if (window.history.replaceState) {
      var url = new URL(window.location);
      url.searchParams.set('q', q);
      window.history.replaceState(null, '', url.pathname + url.search);
    }
    
    if (meta) meta.textContent = 'Searching ' + escapeHtml(q) + '...';
    
    if (searchController) {
      searchController.abort();
    }
    searchController = new AbortController();
    
    try {
      var apiUrl = getApiBase() + '/public-atlas/' + countryCode + '/list?search=' + encodeURIComponent(q) + '&limit=100';
      var resp = await fetch(apiUrl, { signal: searchController.signal });
      if (!resp.ok) throw new Error('Search request failed (' + resp.status + ')');
      var data = await resp.json();
      var items = data.items || [];
      
      if (meta) {
        meta.textContent = 'Found ' + items.length + ' matching occupation' + (items.length === 1 ? '' : 's') + ' for "' + q + '"';
      }
      
      if (items.length === 0) {
        var exampleCode = countryCode === 'CA' ? '21231' : '261313';
        grid.innerHTML = '<div style="grid-column: 1 / -1; padding: 48px 20px; text-align: center; background: #fff; border-radius: 16px; border: 1px dashed var(--border);">' +
          '<div style="font-size: 32px; margin-bottom: 10px;">🔍</div>' +
          '<h3 style="font-size: 19px; font-weight: 700; margin-bottom: 8px; color: var(--ink);">No occupations found matching "' + escapeHtml(q) + '"</h3>' +
          '<p style="font-size: 14px; color: var(--muted); margin-bottom: 20px;">Try searching by ' + classification + ' code (e.g. ' + exampleCode + ') or general title (e.g. Engineer, Chef, Nurse).</p>' +
          '<a class="btn btn-primary" href="/start">Free Eligibility Check →</a>' +
        '</div>';
        return;
      }
      
      var html = '';
      for (var i = 0; i < items.length; i++) {
        var o = items[i];
        var code = escapeHtml(o.code);
        var title = escapeHtml(o.title || '—');
        var authName = escapeHtml(o.assessing_authority_name || (countryCode === 'AU' ? 'LEAMSS verified' : 'Verified'));
        
        var pillHtml = '';
        if (o.recommended_visa) {
          pillHtml += '<span class="pill-sm pill-sm-amber">⭐ Recommended visa · ' + escapeHtml(o.recommended_visa) + '</span>';
        }
        if (o.skill_level !== undefined && o.skill_level !== null && o.skill_level !== '') {
          pillHtml += '<span class="pill-sm pill-sm-slate">Skill Level ' + escapeHtml(o.skill_level) + '</span>';
        } else if (o.teer_category !== undefined && o.teer_category !== null && o.teer_category !== '') {
          pillHtml += '<span class="pill-sm pill-sm-slate">TEER ' + escapeHtml(o.teer_category) + '</span>';
        }
        if (o.salary_chip) {
          pillHtml += '<span class="pill-sm pill-sm-emerald" title="Median full-time annual earnings (ABS via JSA)">💼 ' + escapeHtml(o.salary_chip) + '</span>';
        }
        if (o.growth_chip) {
          var isStrong = (o.growth_chip || '').indexOf('Strong') !== -1;
          var growthClass = isStrong ? 'pill-sm-emerald' : 'pill-sm-slate';
          pillHtml += '<span class="pill-sm ' + growthClass + '" title="10-year employment outlook (JSA Projections)">📈 ' + escapeHtml(o.growth_chip) + '</span>';
        }
        pillHtml += '<span class="pill-sm pill-sm-emerald">✓ Verified</span>';
        
        html += '<a class="occ-card" href="/atlas/' + countryLower + '/' + code + '/" data-testid="occ-card-' + code + '">' +
          '<div class="code-chip">' + classification + ' ' + code + '</div>' +
          '<div class="title">' + title + '</div>' +
          '<div class="pill-row">' + pillHtml + '</div>' +
          '<div class="meta">' +
            '<span>' + authName + '</span>' +
            '<span class="arrow" aria-hidden="true">↗</span>' +
          '</div>' +
        '</a>';
      }
      grid.innerHTML = html;
    } catch (err) {
      if (err.name === 'AbortError') return;
      if (meta) meta.textContent = 'Search error. Please try again.';
    }
  }

  form.addEventListener('submit', function(e) {
    e.preventDefault();
    performSearch(input.value);
  });

  input.addEventListener('input', function() {
    updateClearBtn();
    clearTimeout(typeaheadTimer);
    var val = input.value;
    if (!val.trim()) {
      hideDropdown();
      performSearch('');
      return;
    }
    typeaheadTimer = setTimeout(function() {
      fetchTypeahead(val);
    }, 180);
  });

  input.addEventListener('focus', function() {
    updateClearBtn();
    if (input.value.trim().length >= 2) {
      fetchTypeahead(input.value);
    }
  });

  if (clearBtn) {
    clearBtn.addEventListener('click', function() {
      input.value = '';
      updateClearBtn();
      hideDropdown();
      performSearch('');
      input.focus();
    });
  }

  // Close dropdown on outside click or Esc
  document.addEventListener('click', function(e) {
    if (!form.contains(e.target) && !dropdown.contains(e.target)) {
      hideDropdown();
    }
  });

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      hideDropdown();
    }
  });

  // Pre-fill and search if URL has ?q= parameter on page load
  try {
    var initialParams = new URLSearchParams(window.location.search);
    var initialQ = initialParams.get('q');
    if (initialQ) {
      input.value = initialQ;
      updateClearBtn();
      performSearch(initialQ);
    }
  } catch (e) {}
})();
</script>
</body>
</html>`;

for (const baseDir of targetDirs) {
  if (!fs.existsSync(baseDir)) continue;
  for (const cc of ['au', 'ca', 'nz']) {
    const indexPath = path.join(baseDir, cc, 'index.html');
    if (!fs.existsSync(indexPath)) continue;
    
    let content = fs.readFileSync(indexPath, 'utf8');
    
    // 1. Replace CSS
    content = content.replace(/\/\* Search \*\/[\s\S]*?\.search-bar \.ic\{[^}]+\}/, newCSS);
    
    // 2. Replace HTML Form
    content = content.replace(
      /<form role="search" class="search-bar" action="\/atlas\/([a-z]+)\/" method="get" aria-label="Search occupations">[\s\S]*?<\/form>/,
      `<div class="search-wrapper">
      <form role="search" class="search-bar" action="/atlas/$1/" method="get" aria-label="Search occupations">
        <span class="ic" aria-hidden="true">🔍</span>
        <input type="search" name="q" placeholder="Search by code, title, alternative title, or industry — e.g., 'marketing', 'software engineer', '225113', 'operations head'…" autocomplete="off" data-testid="atlas-country-search">
        <button type="button" class="search-clear-btn" aria-label="Clear search">✕</button>
        <button class="btn btn-primary" type="submit" aria-label="Search">Search</button>
      </form>
      <div class="typeahead-dropdown" data-testid="typeahead-dropdown"></div>
    </div>`
    );
    
    // 3. Replace Bottom Script
    content = content.replace(/<div id="root"><\/div>[\s\S]*?<\/html>/, newScript);
    
    fs.writeFileSync(indexPath, content, 'utf8');
    console.log('Patched:', indexPath);
  }
}
