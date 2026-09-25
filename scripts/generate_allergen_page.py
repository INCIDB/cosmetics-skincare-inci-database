#!/usr/bin/env python3
"""
INCIDB EU fragrance-allergen page generator.

Writes the public list of the fragrance allergens that EU cosmetic labels must name
(Annex III to Regulation (EC) No 1223/2009 as amended by Regulation (EU) 2023/1545), with
each entry's thresholds and transition dates, and how many products in the full INCIDB
corpus declare it:
    eu-fragrance-allergens/index.html   the page (URL /eu-fragrance-allergens/)
    eu-fragrance-allergens/data.json    every figure on the page, machine-readable

What leaves the database is the public legal list plus one count per entry. The
ingredient-level mapping (which INCIDB names match each entry, CAS and CosIng-name matches,
review rows) stays in the paid `fragrance_allergens` table. A monograph link is shown only
where the linked INCI name is printed in the Regulation itself.

Inputs: data/incidb.sqlite (full corpus, gitignored), the committed EUR-Lex reference
data/reference/regulatory/eu_annex_iii_allergens.json, and claims.json. The headline share
must equal claims.json["allergen_products_pct"] or the script stops.

Re-run after each edition build (RELEASING.md, with generate_stats.py), then
`python scripts/generate_seo_pages.py` (sitemap), `python scripts/i18n_common.py build`
and `... check`.

Usage:
    python scripts/generate_allergen_page.py                 # data/incidb.sqlite
    python scripts/generate_allergen_page.py --db PATH       # or INCIDB_SQLITE=PATH
"""
import argparse
import dataclasses
import datetime as dt
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_stats as gs  # noqa: E402
from stats_common import COPY_JS, STATS_CSS, esc, n, pct, tiles  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "eu-fragrance-allergens"
REFERENCE = ROOT / "data" / "reference" / "regulatory" / "eu_annex_iii_allergens.json"
CLAIMS = ROOT / "claims.json"
LANDING = ROOT / "landing"
FIRST_PUBLISHED = "2026-09-25"
SITE = dataclasses.replace(gs.SITE, page_path="/eu-fragrance-allergens/",
                           snippet_label="INCIDB EU fragrance-allergen list")
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
# Consolidated-text footnotes that carry the 2023/1545 transition (see the reference file).
TRANSITIONS = {"37": ("2026-07-31", "2028-07-31", False), "40": ("2026-07-31", "2028-07-31", False),
               "38": ("2026-07-31", "2028-07-31", True)}


def fmt_date(iso):
    y, m, d = iso.split("-")
    return f"{int(d)} {MONTHS[int(m) - 1]} {y}"


def fmt_pct_value(v):
    """0.001 -> '0.001 %' exactly as the Regulation prints it (no float noise)."""
    return f"{v:g} %"


def upper_names(entry):
    """Every name the Regulation prints for the entry (glossary names, printed aliases, label name)."""
    out = set()
    for nm in entry["names"]:
        whole = re.sub(r"\s+", " ", nm["legal_name"]).strip().upper()
        out.add(whole)
        m = re.match(r"^(.*?)\s*\(([^()]*)\)$", whole)
        if m:
            out.update({m.group(1).strip(), m.group(2).strip()})
    if entry.get("label_as"):
        out.add(re.sub(r"\s+", " ", entry["label_as"]).strip().upper())
    return out


def compute(db_path, reference, claims, landing_dir=LANDING):
    conn = sqlite3.connect(db_path)
    q = lambda sql, args=(): conn.execute(sql, args).fetchall()  # noqa: E731
    products = q("select count(*) from products")[0][0]
    rows = []
    for e in reference["entries"]:
        flagged = q("select distinct ingredient_id, inci_name from fragrance_allergens "
                    "where flagged = 1 and annex_iii_ref = ?", (e["ref"],))
        ids = [i for i, _ in flagged]
        count = 0
        if ids:
            marks = ",".join("?" * len(ids))
            count = q(f"select count(distinct product_id) from product_ingredients where ingredient_id in ({marks})", ids)[0][0]
        printed = upper_names(e)
        links = sorted({nm for _, nm in flagged if nm in printed and (landing_dir / f"{_slug(nm)}.html").exists()})
        cas = sorted({c for nm in e["names"] for c in nm["cas"]})
        placing, making, conditional = TRANSITIONS.get(e.get("transition"), (None, None, False))
        rows.append({
            "ref": e["ref"], "legal_names": [nm["legal_name"] for nm in e["names"]], "label_as": e.get("label_as"),
            "cas": cas, "leave_on_pct": e["leave_on_pct"], "rinse_off_pct": e["rinse_off_pct"],
            "placing_on_market_until": placing, "making_available_until": making, "conditional_transition": conditional,
            "instrument": e["instrument"], "products": count, "share_pct": pct(count, products),
            "monographs": [f"/landing/{_slug(nm)}" for nm in links],
        })
    any_flagged = q("select count(distinct pi.product_id) from product_ingredients pi where pi.ingredient_id in "
                    "(select ingredient_id from fragrance_allergens where flagged = 1)")[0][0]
    snapshot = q("select max(retrieved_at) from fragrance_allergens")[0][0]
    try:
        snapshot = json.loads(gs.BUILD_REPORT.read_text(encoding="utf-8"))["generated_at"][:10]
    except (OSError, KeyError, ValueError):
        pass
    conn.close()
    share = pct(any_flagged, products)
    if share != claims["allergen_products_pct"]:
        raise SystemExit(f"headline share {share}% != claims.json allergen_products_pct {claims['allergen_products_pct']}% "
                         "- rebuild claims (scripts/render_claims.py) from the same database first")
    rows.sort(key=lambda r: (-r["products"], int(re.sub(r"\D", "", r["ref"]) or 0)))
    return {"products": products, "products_with_any": any_flagged, "share_pct": share,
            "unsplit_pct": claims["unsplit_allergen_products_pct"], "entries_total": len(rows),
            "entries_in_corpus": sum(1 for r in rows if r["products"]), "rows": rows,
            "list_version": reference["meta"]["consolidated_version"], "eurlex_url": reference["meta"]["consolidated_url"],
            "snapshot_date": snapshot}


def _slug(inci_name):
    return re.sub(r"[^a-zA-Z0-9]+", "_", inci_name.lower()).strip("_") or "unknown"


def _t(v):
    """A legal or data value: kept verbatim by scripts/i18n_common.py."""
    return f'<span translate="no">{esc(v)}</span>'


def table_html(s):
    head = ("<tr><th>Entry</th><th>Name(s) in the Regulation</th><th>Label name</th><th>CAS</th>"
            "<th>Declare above (leave-on / rinse-off)</th><th>Transition (placing / making available)</th>"
            '<th class="num">Products</th><th class="num">Share</th></tr>')
    body = []
    for r in s["rows"]:
        names = "; ".join(r["legal_names"])
        name_html = _t(names)
        if r["monographs"]:
            name_html += " " + " ".join(f'<a href="{esc(u)}">monograph</a>' for u in r["monographs"])
        trans = "—"
        if r["placing_on_market_until"]:
            trans = _t(f'{fmt_date(r["placing_on_market_until"])} / {fmt_date(r["making_available_until"])}')
            if r["conditional_transition"]:
                trans += "&nbsp;*"
        body.append(
            f'<tr id="entry-{esc(r["ref"])}"><td>{_t(r["ref"])}</td><td>{name_html}</td>'
            f'<td>{_t(r["label_as"]) if r["label_as"] else "—"}</td><td>{_t(" / ".join(r["cas"])) if r["cas"] else "—"}</td>'
            f'<td>{_t(fmt_pct_value(r["leave_on_pct"]) + " / " + fmt_pct_value(r["rinse_off_pct"]))}</td><td>{trans}</td>'
            f'<td class="num">{n(r["products"])}</td><td class="num">{r["share_pct"]}%</td></tr>')
    return f'<div class="tbl"><table><thead>{head}</thead><tbody>{"".join(body)}</tbody></table></div>'


def ld_json(site, title, desc, today):
    article = json.dumps({
        "@context": "https://schema.org", "@type": "Article", "headline": title, "description": desc,
        "url": site.page_url, "datePublished": FIRST_PUBLISHED, "dateModified": today, "image": f"{site.base_url}/og-image.png",
        "inLanguage": "en", "author": {"@type": "Organization", "name": site.brand, "url": site.base_url},
        "publisher": {"@type": "Organization", "name": "DataEngineered", "url": "https://dataengineered.io/"},
        "isBasedOn": ["https://eur-lex.europa.eu/eli/reg/2023/1545/oj", site.base_url + "/"],
        "about": ["EU fragrance allergens", "Regulation (EU) 2023/1545", "cosmetic labelling", "INCI"]}, ensure_ascii=False, indent=2)
    crumbs = json.dumps({
        "@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": site.base_url + "/"},
            {"@type": "ListItem", "position": 2, "name": "EU fragrance allergens", "item": site.page_url}]}, ensure_ascii=False, indent=2)
    return (f'  <script type="application/ld+json">\n{article}\n  </script>\n'
            f'  <script type="application/ld+json">\n{crumbs}\n  </script>')


def build_page(s, today=None):
    site = SITE
    today = today or dt.date.today().isoformat()
    snap = s["snapshot_date"]
    first = s["rows"][0]
    lo = fmt_pct_value(first["leave_on_pct"])
    ro = fmt_pct_value(first["rinse_off_pct"])
    title_tag = (f"EU Fragrance Allergens List (Regulation 2023/1545): {s['entries_total']} Annex III Entries, "
                 "Thresholds & Deadlines | INCIDB")
    desc = (f"The {s['entries_total']} EU fragrance allergens that must be named on cosmetic labels above {lo} (leave-on) / "
            f"{ro} (rinse-off), their deadlines, and how often each appears on {n(s['products'])} products.")
    header = gs.chrome()
    n_conditional = sum(1 for r in s["rows"] if r["conditional_transition"])
    dated = next(r for r in s["rows"] if r["placing_on_market_until"])
    tile_html = tiles([("Entries in the list", str(s["entries_total"])), ("Entries found on labels", str(s["entries_in_corpus"])),
                       ("Products declaring one", f"{s['share_pct']}%"), ("Products", n(s["products"])), ("Snapshot", snap)])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{esc(title_tag)}</title>
    <meta name="description" content="{esc(desc)}">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="{site.page_url}">
    <link rel="alternate" hreflang="en" href="{site.page_url}">
    <meta property="og:title" content="EU fragrance allergens: the labelling list of Regulation (EU) 2023/1545">
    <meta property="og:description" content="{esc(desc)}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{site.page_url}">
    <meta property="og:image" content="{site.base_url}/og-image.png">
    <meta name="twitter:card" content="summary_large_image">
    <link rel="icon" href="../favicon.svg" type="image/svg+xml">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300..800;1,300..800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
    <noscript><link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300..800;1,300..800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet"></noscript>
    <link rel="stylesheet" href="{gs.CSS_HREF}">
{ld_json(site, "EU fragrance allergens: the labelling list of Regulation (EU) 2023/1545", desc, today)}
    <style>{gs.CSS}{STATS_CSS}    </style>
</head>
<body>
{header}
<main class="stats-wrap">
  <p class="crumbs"><a href="/">Home</a> &rsaquo; <span>EU fragrance allergens</span></p>
  <p class="eyebrow">EU cosmetics regulation · list of {esc(s['list_version'])}</p>
  <h1>EU fragrance allergens: the labelling list</h1>
  <p class="lede">The {s['entries_total']} fragrance-allergen entries of Annex III to the EU Cosmetics Regulation (Regulation (EC) No 1223/2009 as amended by Regulation (EU) 2023/1545). Each one must be named in a cosmetic's ingredient list when its concentration exceeds {lo} in leave-on products or {ro} in rinse-off products. Next to each entry: how many of the {n(s['products'])} product labels in the INCIDB corpus declare it.</p>
  <ul class="tiles">{tile_html}</ul>

  <section class="stat" id="rule">
    <h2>What the rule requires</h2>
    <p class="finding">Regulation (EU) 2023/1545 rewrote 17 existing Annex III entries and added 45 new ones (entries 327 to 371). Products that do not comply with the amended entries could be placed on the EU market until {fmt_date(dated['placing_on_market_until'])}; that date has passed. Products already on the market may be made available until {fmt_date(dated['making_available_until'])}. For the {n_conditional} entries marked *, that transition applies only to products that met the rules in force on 15 August 2023.</p>
    <p class="method">Some entries prescribe a collective label name (for example <span translate="no">Rose Ketones</span> or <span translate="no">Lemongrass Oil</span>), shown in the Label name column. A dash in the Transition column means the consolidated text sets no transition period for that entry. The legal text is the <a href="{esc(s['eurlex_url'])}">consolidated Regulation on EUR-Lex</a> (version {esc(s['list_version'])}); this page transcribes it and is not legal advice.</p>
  </section>

  <section class="stat" id="list">
    <h2>The {s['entries_total']} entries, by how many products declare them</h2>
    <p class="finding"><strong>{s['share_pct']}%</strong> of the {n(s['products'])} products in the corpus declare at least one of these allergens, and {s['entries_in_corpus']} of the {s['entries_total']} entries appear on at least one label. About {s['unsplit_pct']}% of products list their ingredients as unsplit text that the counts below cannot reach.</p>
    {table_html(s)}
    <p class="method">Products counts how many labels declare an ingredient INCIDB matched to the entry: by the exact name printed in the Regulation, by the prescribed label name, or by CAS number for chemically defined substances. A count of 0 means no label token INCIDB could resolve matched the entry, not that the substance is absent from the market. Monograph links appear only where the ingredient's own name is printed in the Regulation.</p>
  </section>

  <section class="stat" id="method">
    <h2>Sources, reuse and citation</h2>
    <ul class="method">
      <li><strong>Legal list.</strong> Annex III to Regulation (EC) No 1223/2009, consolidated version {esc(s['list_version'])} on <a href="{esc(s['eurlex_url'])}">EUR-Lex</a>, including the corrigendum to Regulation (EU) 2023/1545 published in 2025. © European Union, reused under Commission Decision 2011/833/EU.</li>
      <li><strong>Product counts.</strong> The full INCIDB snapshot of {esc(snap)}: {n(s['products'])} product labels from <a href="https://world.openbeautyfacts.org/">Open Beauty Facts</a> (product data © Open Beauty Facts contributors, <a href="https://opendatacommons.org/licenses/odbl/1-0/">ODbL v1.0</a>). Labels do not state concentrations, so a count says an allergen is declared, not how much is present.</li>
      <li><strong>Reuse.</strong> The counts on this page are published under <a href="https://creativecommons.org/licenses/by/4.0/" rel="license">CC BY 4.0</a> with a link to <span translate="no">{site.page_url}</span>. The machine-readable version is <a href="/eu-fragrance-allergens/data.json">data.json</a>.</li>
      <li><strong>Suggested citation.</strong> <span translate="no">INCIDB ({snap[:4]}). <em>EU fragrance allergens: the labelling list</em>, snapshot {snap}. DataEngineered. {site.page_url}</span></li>
      <li><strong>Questions or corrections:</strong> <a href="/#contact">contact form</a> or incidb@dataengineered.io.</li>
    </ul>
  </section>

  <div class="cta-inline">
    <h3 style="margin:0">Need the ingredient-level mapping?</h3>
    <p>INCIDB Complete ships the <code>fragrance_allergens</code> table: every INCIDB ingredient matched to each entry and how it was matched, the review rows that were not flagged, and the <code>regulatory_status</code> table for EU Annexes II to VI. CSV and Parquet.</p>
    <a class="btn btn-primary" href="/#pricing">Get INCIDB Complete ($79)</a>
  </div>
</main>
<footer>
    <div class="container">
        <p>INCIDB · snapshot {esc(snap[:7].replace('-', '.'))} · EU fragrance-allergen list</p>
        <p style="margin-top: 0.75rem; font-size: 0.8rem; color: var(--text-secondary);">Legal list: Annex III to Regulation (EC) No 1223/2009 as amended by Regulation (EU) 2023/1545, EUR-Lex (© European Union), reused with attribution. Product data © <a href="https://world.openbeautyfacts.org/" style="color: var(--accent-blue); text-decoration: none;">Open Beauty Facts</a> contributors, under the <a href="https://opendatacommons.org/licenses/odbl/1-0/" style="color: var(--accent-blue); text-decoration: none;">Open Database License (ODbL) v1.0</a>.</p>
    </div>
    <div class="catalog-line" style="text-align:center; margin-top:14px; font-size:0.85rem; opacity:0.85;"><a href="https://dataengineered.io/">Part of the DataEngineered catalog →</a> · <a href="https://dataengineered.io/about">About</a> · <a href="https://dataengineered.io/terms">Terms</a> · <a href="https://dataengineered.io/privacy">Privacy</a> · <a href="https://dataengineered.io/refund-policy">Refund policy</a></div>
</footer>
{COPY_JS}
</body>
</html>
"""


def build_data_json(s):
    return {
        "dataset": SITE.brand, "page": SITE.page_url, "generated": dt.date.today().isoformat(), "snapshot": s["snapshot_date"],
        "legal_source": {"text": "Annex III to Regulation (EC) No 1223/2009 as amended by Regulation (EU) 2023/1545",
                         "consolidated_version": s["list_version"], "url": s["eurlex_url"],
                         "reuse": "(c) European Union, reused under Commission Decision 2011/833/EU"},
        "license": "Counts: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), attribute with a link to the page; product data (c) Open Beauty Facts contributors, ODbL v1.0",
        "totals": {"products": s["products"], "products_declaring_any": s["products_with_any"], "share_pct": s["share_pct"],
                   "unsplit_text_products_pct": s["unsplit_pct"], "entries": s["entries_total"], "entries_on_labels": s["entries_in_corpus"]},
        "entries": [{k: r[k] for k in ("ref", "legal_names", "label_as", "cas", "leave_on_pct", "rinse_off_pct",
                                       "placing_on_market_until", "making_available_until", "conditional_transition",
                                       "instrument", "products", "share_pct")} for r in s["rows"]],
    }


def write_outputs(out_dir, page, data_json):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(page, encoding="utf-8", newline="\n")
    (out_dir / "data.json").write_text(json.dumps(data_json, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", default=os.environ.get("INCIDB_SQLITE", str(gs.DEFAULT_DB)))
    ap.add_argument("--out", default=str(OUT_DIR))
    args = ap.parse_args(argv)
    db = Path(args.db)
    if not db.is_file():
        raise SystemExit(f"SQLite snapshot not found: {db}")
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    claims = json.loads(CLAIMS.read_text(encoding="utf-8"))
    s = compute(db, reference, claims)
    write_outputs(Path(args.out), build_page(s), build_data_json(s))
    print(f"{Path(args.out).name}/index.html + data.json  ({s['entries_total']} entries, {s['share_pct']}% of {s['products']:,} products)")


if __name__ == "__main__":
    main()
