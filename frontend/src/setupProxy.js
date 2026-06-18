/**
 * Phase 19 — File-first middleware for /atlas/* and /sitemap.xml
 *
 * Goal: bots and direct HTTP requests should be served the pre-rendered static
 * HTML files at /app/frontend/public/atlas/.../index.html (and the static
 * /app/frontend/public/sitemap.xml). The React SPA bundle is appended at the
 * bottom of every generated HTML so client-side hydration still works for
 * users who navigate via SPA.
 *
 * Routes covered:
 *   /atlas                                  -> public/atlas/index.html
 *   /atlas/{country}                        -> public/atlas/{country}/index.html
 *   /atlas/{country}/{code}                 -> public/atlas/{country}/{code}/index.html
 *   /sitemap.xml                            -> public/sitemap.xml
 *
 * The middleware is intentionally read-only and stateless. If the static file
 * does not exist (record not verified yet), control falls through to the
 * normal CRA dev-server, which returns the SPA shell and lets React render
 * client-side.
 *
 * CRA only picks this file up automatically when it's named exactly
 * `setupProxy.js` and lives in /app/frontend/src. craco does not override the
 * dev-server pipeline for this file.
 */
const path = require('path');
const fs = require('fs');

const PUBLIC_DIR = path.resolve(__dirname, '..', 'public');
const ATLAS_DIR = path.join(PUBLIC_DIR, 'atlas');

function sendStaticFile(req, res, filePath, contentType) {
  fs.readFile(filePath, (err, data) => {
    if (err) {
      // Fall through to CRA's normal SPA handling
      res.statusCode = 404;
      res.end();
      return;
    }
    res.setHeader('Content-Type', contentType);
    res.setHeader('Cache-Control', 'public, max-age=300');
    res.setHeader('X-LEAMSS-SSG', '1');
    res.statusCode = 200;
    res.end(data);
  });
}

module.exports = function setupProxy(app) {
  // /sitemap.xml — static SSG-generated sitemap
  app.get('/sitemap.xml', (req, res, next) => {
    const f = path.join(PUBLIC_DIR, 'sitemap.xml');
    if (fs.existsSync(f)) {
      return sendStaticFile(req, res, f, 'application/xml; charset=utf-8');
    }
    return next();
  });

  // /atlas/* — static SSG-generated HTML
  app.get(/^\/atlas(\/.*)?$/, (req, res, next) => {
    // Don't intercept React bundle assets or files with extensions other than html
    const urlPath = req.path || '';
    const parts = urlPath.split('/').filter(Boolean);
    // Reject path traversal / asset-style requests
    if (parts.some((p) => p.includes('..'))) return next();
    if (urlPath.match(/\.(js|css|map|png|jpg|jpeg|svg|webp|ico|woff2?|ttf)$/i)) return next();

    let target;
    if (parts.length === 1) {
      // /atlas
      target = path.join(ATLAS_DIR, 'index.html');
    } else if (parts.length === 2) {
      // /atlas/{country}
      const country = parts[1].toLowerCase();
      if (!/^[a-z]{2}$/.test(country)) return next();
      target = path.join(ATLAS_DIR, country, 'index.html');
    } else if (parts.length === 3) {
      // /atlas/{country}/{code}
      const country = parts[1].toLowerCase();
      const code = parts[2];
      if (!/^[a-z]{2}$/.test(country)) return next();
      if (!/^[a-zA-Z0-9_-]{1,20}$/.test(code)) return next();
      target = path.join(ATLAS_DIR, country, code, 'index.html');
    } else if (parts.length === 4 && parts[2] === 'industry') {
      // Phase 19.4c — /atlas/{country}/industry/{slug}
      const country = parts[1].toLowerCase();
      const slug = parts[3];
      if (!/^[a-z]{2}$/.test(country)) return next();
      if (!/^[a-z0-9-]{1,80}$/.test(slug)) return next();
      target = path.join(ATLAS_DIR, country, 'industry', slug, 'index.html');
    } else {
      return next();
    }

    if (fs.existsSync(target)) {
      return sendStaticFile(req, res, target, 'text/html; charset=utf-8');
    }
    return next();
  });
};
