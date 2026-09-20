// 1. Old Cloudflare Pages host -> canonical domain. Exact-host match so branch-preview
//    hosts and the custom domain are never redirected.
// 2. Old monograph URLs -> slug-only URLs (since 2026-09-20). Monographs used to live
//    at /landing/inci_<ingredient_id>_<slug>; ingredient_id is a database autoincrement
//    that changed on every full rebuild, so every id ever published 301s to
//    /landing/<slug>, in every locale. One regex here instead of thousands of
//    `_redirects` rules (Pages caps those at 2,000 static).
// Everything else falls through to the static assets (404.html, _headers unchanged).
const OLD_HOST = "cosmetics-skincare-database.pages.dev";
const NEW_HOST = "incidb.dataengineered.io";
const OLD_MONOGRAPH = /^(\/(?:es|de|fr|pt-br))?\/landing\/inci_\d+_([a-z0-9_]+)\/?$/;

export async function onRequest({ request, next }) {
  const url = new URL(request.url);
  if (url.hostname === OLD_HOST) {
    url.hostname = NEW_HOST;
    return Response.redirect(url.toString(), 301);
  }
  const m = OLD_MONOGRAPH.exec(url.pathname);
  if (m) {
    url.pathname = `${m[1] || ""}/landing/${m[2]}`;
    return Response.redirect(url.toString(), 301);
  }
  return next();
}
