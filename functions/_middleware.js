// Old Cloudflare Pages host -> canonical domain. Exact-host match so branch-preview
// hosts and the custom domain are never redirected; everything else falls through
// to the static assets (404.html, _headers, _redirects unchanged).
const OLD_HOST = "cosmetics-skincare-database.pages.dev";
const NEW_HOST = "incidb.dataengineered.io";

export async function onRequest({ request, next }) {
  const url = new URL(request.url);
  if (url.hostname === OLD_HOST) {
    url.hostname = NEW_HOST;
    return Response.redirect(url.toString(), 301);
  }
  return next();
}
