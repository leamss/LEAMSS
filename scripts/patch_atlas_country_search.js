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
.typeahead-score{font-size:11px;font-weight:700;background:#0f172a;color:#fff;padding:2px 8px;border-radius:999px;flex-shrink:0}
/* Pagination */
.pagination-wrap{display:flex;align-items:center;justify-content:center;gap:6px;margin:40px 0 20px;flex-wrap:wrap;}
.pagination-btn{display:inline-flex;align-items:center;justify-content:center;min-width:38px;height:38px;padding:0 12px;border-radius:10px;border:1.5px solid var(--border);background:#fff;color:var(--ink);font-size:13px;font-weight:700;cursor:pointer;transition:all .15s;text-decoration:none;user-select:none;}
.pagination-btn:hover:not(:disabled):not(.active){border-color:var(--forest);background:var(--cream);color:var(--forest-dark);text-decoration:none;}
.pagination-btn.active{background:var(--forest);border-color:var(--forest);color:#fff;cursor:default;}
.pagination-btn:disabled{opacity:0.35;cursor:not-allowed;pointer-events:none;}
.pagination-ellipsis{display:inline-flex;align-items:center;justify-content:center;width:28px;height:38px;color:var(--muted);font-weight:700;font-size:14px;}`;

const newScript = `<div id="root"></div>
<script>
(function() {
  var form = document.querySelector('form.search-bar');
  var input = form ? form.querySelector('input[name="q"]') : null;
  var clearBtn = form ? form.querySelector('.search-clear-btn') : null;
  var dropdown = document.querySelector('.typeahead-dropdown');
  var grid = document.querySelector('.occ-grid');
  var meta = document.querySelector('.section-title-meta');
  var paginationWrap = document.querySelector('.pagination-wrap');
  var sectionTitleRow = document.querySelector('.section-title-row');
  var pathParts = window.location.pathname.replace(/^\\/atlas\\//, '').split('/').filter(Boolean);
  var countryLower = pathParts[0] || 'au';
  var countryCode = countryLower.toUpperCase();
  var classification = countryCode === 'CA' ? 'NOC' : 'ANZSCO';
  
  if (!form || !input) return;

  var PAGE_SIZE = 50;
  var initialGridHtml = grid ? grid.innerHTML : '';
  var initialMetaText = meta ? meta.textContent : '';
  var initialTotalMatch = (meta ? meta.textContent : '').match(/of\\s+([0-9,]+)/);
  var totalItems = initialTotalMatch ? parseInt(initialTotalMatch[1].replace(/,/g, ''), 10) : (countryCode === 'CA' ? 516 : 1236);
  var currentPage = 1;
  var currentQuery = '';

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

  function renderCards(items) {
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
    return html;
  }

  function renderPagination(total, page, pageSize) {
    if (!paginationWrap) return;
    var totalPages = Math.ceil(total / pageSize);
    if (totalPages <= 1) {
      paginationWrap.innerHTML = '';
      paginationWrap.style.display = 'none';
      return;
    }
    paginationWrap.style.display = 'flex';

    var html = '';
    html += '<button type="button" class="pagination-btn pagination-prev" data-page="' + (page - 1) + '"' + (page === 1 ? ' disabled' : '') + ' aria-label="Previous page">← Prev</button>';

    var pages = [];
    if (totalPages <= 7) {
      for (var i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      var start = Math.max(2, page - 1);
      var end = Math.min(totalPages - 1, page + 1);

      if (page <= 3) {
        end = 4;
      } else if (page >= totalPages - 2) {
        start = totalPages - 3;
      }

      if (start > 2) pages.push('...');
      for (var p = start; p <= end; p++) pages.push(p);
      if (end < totalPages - 1) pages.push('...');
      pages.push(totalPages);
    }

    for (var j = 0; j < pages.length; j++) {
      var item = pages[j];
      if (item === '...') {
        html += '<span class="pagination-ellipsis">…</span>';
      } else {
        var isCurrent = item === page;
        html += '<button type="button" class="pagination-btn' + (isCurrent ? ' active' : '') + '" data-page="' + item + '"' + (isCurrent ? ' aria-current="page"' : '') + '>' + item + '</button>';
      }
    }

    html += '<button type="button" class="pagination-btn pagination-next" data-page="' + (page + 1) + '"' + (page === totalPages ? ' disabled' : '') + ' aria-label="Next page">Next →</button>';

    paginationWrap.innerHTML = html;
  }

  async function fetchPage(page, q, scrollToTop) {
    q = (q || '').trim();
    currentQuery = q;
    currentPage = page || 1;
    hideDropdown();

    if (searchController) {
      searchController.abort();
    }
    searchController = new AbortController();

    if (!q && currentPage === 1 && initialGridHtml) {
      grid.innerHTML = initialGridHtml;
      if (meta) meta.textContent = initialMetaText;
      renderPagination(totalItems, 1, PAGE_SIZE);
      if (window.history.replaceState) {
        var url = new URL(window.location);
        url.searchParams.delete('q');
        url.searchParams.delete('page');
        window.history.replaceState(null, '', url.pathname + (url.search ? url.search : ''));
      }
      if (scrollToTop && sectionTitleRow) {
        sectionTitleRow.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      return;
    }

    if (window.history.replaceState) {
      var url = new URL(window.location);
      if (q) url.searchParams.set('q', q);
      else url.searchParams.delete('q');
      if (currentPage > 1) url.searchParams.set('page', currentPage);
      else url.searchParams.delete('page');
      window.history.replaceState(null, '', url.pathname + (url.search ? url.search : ''));
    }

    if (meta) meta.textContent = q ? ('Searching ' + escapeHtml(q) + '...') : 'Loading page ' + currentPage + '...';

    var offset = (currentPage - 1) * PAGE_SIZE;
    var apiUrl = getApiBase() + '/public-atlas/' + countryCode + '/list?limit=' + PAGE_SIZE + '&offset=' + offset;
    if (q) apiUrl += '&search=' + encodeURIComponent(q);

    try {
      var resp = await fetch(apiUrl, { signal: searchController.signal });
      if (!resp.ok) throw new Error('Request failed (' + resp.status + ')');
      var data = await resp.json();
      var items = data.items || [];
      var total = data.total || 0;

      var start = offset + 1;
      var end = Math.min(offset + items.length, total);

      if (meta) {
        if (q) {
          meta.textContent = total > 0
            ? ('Showing ' + start + '–' + end + ' of ' + total + ' matching occupations for "' + q + '"')
            : ('Found 0 matching occupations for "' + q + '"');
        } else {
          meta.textContent = 'Showing ' + start + '–' + end + ' of ' + total + ' verified · sorted by code';
        }
      }

      if (items.length === 0) {
        var exampleCode = countryCode === 'CA' ? '21231' : '261313';
        grid.innerHTML = '<div style="grid-column: 1 / -1; padding: 48px 20px; text-align: center; background: #fff; border-radius: 16px; border: 1px dashed var(--border);">' +
          '<div style="font-size: 32px; margin-bottom: 10px;">🔍</div>' +
          '<h3 style="font-size: 19px; font-weight: 700; margin-bottom: 8px; color: var(--ink);">No occupations found matching "' + escapeHtml(q) + '"</h3>' +
          '<p style="font-size: 14px; color: var(--muted); margin-bottom: 20px;">Try searching by ' + classification + ' code (e.g. ' + exampleCode + ') or general title (e.g. Engineer, Chef, Nurse).</p>' +
          '<a class="btn btn-primary" href="/start">Free Eligibility Check →</a>' +
        '</div>';
        if (paginationWrap) {
          paginationWrap.innerHTML = '';
          paginationWrap.style.display = 'none';
        }
        return;
      }

      grid.innerHTML = renderCards(items);
      renderPagination(total, currentPage, PAGE_SIZE);

      if (scrollToTop && sectionTitleRow) {
        sectionTitleRow.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      if (meta) meta.textContent = 'Error loading page. Please try again.';
    }
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

  // Event handlers
  form.addEventListener('submit', function(e) {
    e.preventDefault();
    fetchPage(1, input.value, true);
  });

  input.addEventListener('input', function() {
    updateClearBtn();
    clearTimeout(typeaheadTimer);
    var val = input.value;
    if (!val.trim()) {
      hideDropdown();
      fetchPage(1, '', false);
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
      fetchPage(1, '', false);
      input.focus();
    });
  }

  if (paginationWrap) {
    paginationWrap.addEventListener('click', function(e) {
      var btn = e.target.closest('.pagination-btn');
      if (!btn || btn.disabled || btn.classList.contains('active')) return;
      var targetPage = parseInt(btn.getAttribute('data-page'), 10);
      if (targetPage && !isNaN(targetPage)) {
        fetchPage(targetPage, input.value.trim(), true);
      }
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

  // Check URL parameters on page load
  try {
    var initialParams = new URLSearchParams(window.location.search);
    var initialQ = initialParams.get('q');
    var initialP = parseInt(initialParams.get('page'), 10);
    if (initialQ || (initialP && initialP > 1)) {
      if (initialQ) {
        input.value = initialQ;
        updateClearBtn();
      }
      fetchPage(initialP || 1, initialQ || '', false);
    } else {
      renderPagination(totalItems, 1, PAGE_SIZE);
    }
  } catch (e) {
    renderPagination(totalItems, 1, PAGE_SIZE);
  }
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
    if (content.includes('/* Search & Typeahead */')) {
      content = content.replace(/\/\* Search & Typeahead \*\/[\s\S]*?\/\* Section \*\//, newCSS + '\n/* Section */');
    } else {
      content = content.replace(/\/\* Search \*\/[\s\S]*?\.search-bar \.ic\{[^}]+\}/, newCSS);
    }
    
    // 2. Replace HTML Form if needed
    if (!content.includes('class="search-wrapper"')) {
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
    }
    
    // 3. Replace static notice or old pagination with pagination container
    if (content.includes('data-testid="atlas-pagination"')) {
      // already present
    } else if (content.includes('Showing top')) {
      content = content.replace(
        /<p style="text-align:center;margin-top:30px;color:var\(--muted\);font-size:14px;">Showing top [\s\S]*?<\/p>/,
        '<div class="pagination-wrap" data-testid="atlas-pagination"></div>'
      );
    } else {
      content = content.replace(
        /<\/div>\s*<div class="mid-cta">/,
        '</div>\n    <div class="pagination-wrap" data-testid="atlas-pagination"></div>\n    <div class="mid-cta">'
      );
    }
    
    // 4. Replace Bottom Script
    content = content.replace(/<div id="root"><\/div>[\s\S]*?<\/html>/, newScript);
    
    fs.writeFileSync(indexPath, content, 'utf8');
    console.log('Patched:', indexPath);
  }
}
