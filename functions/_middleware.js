// 1. Old Cloudflare Pages host -> canonical domain. Exact-host match so branch-preview
//    hosts and the custom domain are never redirected.
// 2. Old monograph URLs -> slug-only URLs (since 2026-09-20). Monographs used to live
//    at /landing/inci_<ingredient_id>_<slug>; ingredient_id is a database autoincrement
//    that changed on every full rebuild, so every id ever published 301s to
//    /landing/<slug>, in every locale. One regex here instead of thousands of
//    `_redirects` rules (Pages caps those at 2,000 static).
// 3. Retired monographs -> the closest live page (since 2026-09-27). The monograph set
//    follows the free sample, so a pinned product that leaves the corpus takes the pages
//    of its ingredients with it (10 in the 2026.09 refresh). Each retired slug 301s, in
//    every locale, to its category hub, or an allergen to its entry on the EU allergen
//    page. Only a real 404 is redirected: if a later refresh brings the monograph back,
//    the page is served and its RETIRED row is dead weight to prune.
// Everything else falls through to the static assets (404.html, _headers unchanged).
const OLD_HOST = "cosmetics-skincare-database.pages.dev";
const NEW_HOST = "incidb.dataengineered.io";
const OLD_MONOGRAPH = /^(\/(?:es|de|fr|pt-br))?\/landing\/inci_\d+_([a-z0-9_]+)\/?$/;
const MONOGRAPH = /^(\/(?:es|de|fr|pt-br))?\/landing\/([a-z0-9_]+)\/?$/;
const RETIRED = {
  // 2026.09 refresh (public #21); target = the hub the page linked to, locale prefix added
  acid_orange_7: "/landing/fragrance_colour",
  acid_yellow_3: "/landing/fragrance_colour",
  amylcinnamyl_alcohol: "/eu-fragrance-allergens/#entry-74",
  isopentyldiol: "/landing/solvents",
  mel: "/landing/skin_conditioning",
  ppg_15_stearyl_ether: "/landing/skin_conditioning",
  ppg_9: "/landing/skin_conditioning",
  sodium_cocoamphoacetate: "/landing/surfactants_cleansing",
  succinic_acid: "/landing/fragrance_colour",
  tropolone: "/landing/skin_conditioning",
};

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
  const r = MONOGRAPH.exec(url.pathname);
  if (r && Object.prototype.hasOwnProperty.call(RETIRED, r[2])) {
    const response = await next();
    if (response.status !== 404) return response;
    const [path, hash] = RETIRED[r[2]].split("#");
    url.pathname = `${r[1] || ""}${path}`;
    url.search = "";
    url.hash = hash ? `#${hash}` : "";
    return Response.redirect(url.toString(), 301);
  }
  return next();
}
