#!/usr/bin/env python3
"""
INCIDB statistics page generator.

Reads the FULL snapshot (data/incidb.sqlite, gitignored, never the public sample) and
writes a citable, embeddable statistics page:

    stats/index.html          the page (URL /stats/)
    stats/charts/<slug>.svg   one standalone SVG per chart (for <img> embeds elsewhere)
    stats/data.json           every figure on the page, machine-readable

Only aggregates leave the database -- no row-level data is written. Every figure states
its denominator. Product data is Open Beauty Facts (ODbL), so the page carries the OBF
attribution; ingredient enrichment is CosIng (European Commission).

Re-run after each edition build, then `python scripts/generate_seo_pages.py` (sitemap),
`python scripts/i18n_common.py build` and `... check`.

Usage:
    python scripts/generate_stats.py                 # data/incidb.sqlite
    python scripts/generate_stats.py --db PATH       # or INCIDB_SQLITE=PATH
"""
import argparse
import datetime as dt
import json
import os
import sqlite3
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats_common import (Site, esc, n, pct, data, svg_hbar, figure, table, section, toc, tiles,  # noqa: E402
                          article_ld, COPY_JS, STATS_CSS, write_outputs)

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "stats"
FIRST_PUBLISHED = "2026-09-18"
DEFAULT_DB = ROOT / "data" / "incidb.sqlite"
BUILD_REPORT = ROOT / "data" / "exports" / "build_report.json"

SITE = Site(base_url="https://incidb.dataengineered.io", brand="INCIDB",
            snippet_label="INCIDB cosmetics ingredient statistics",
            surface="#0A0B0E", surface2="#161922", ink="#F8FAFC", muted="#94A3B8", grid="#232838", accent="#38BDF8",
            font="'Space Grotesk', 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif",
            mono="'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace")

# Ingredient groups, defined by canonical INCI name patterns. Each is a plain, auditable
# rule over the canonical name; nothing here is a judgement about safety.
GROUPS = [
    ("Fragrance (Parfum / Fragrance / Aroma)", "i.inci_name in ('PARFUM','FRAGRANCE','AROMA')"),
    ("EU-listed fragrance allergens", "i.is_common_allergen = 1"),
    ("PEG compounds", "i.inci_name like 'PEG-%' or i.inci_name like '% PEG-%'"),
    ("Sulfate surfactants (SLS / SLES)", "i.inci_name like '%LAURETH SULFATE%' or i.inci_name like '%LAURYL SULFATE%'"),
    ("Silicones", "i.inci_name like '%METHICONE%' or i.inci_name like '%SILOXANE%' or i.inci_name like '%SILSESQUIOXANE%'"),
    ("Phenoxyethanol", "i.inci_name = 'PHENOXYETHANOL'"),
    ("Alcohol / Alcohol denat.", "i.inci_name in ('ALCOHOL','ALCOHOL DENAT.','ALCOHOL DENAT')"),
    ("Mineral oil / Petrolatum", "i.inci_name in ('PARAFFINUM LIQUIDUM','MINERAL OIL','PETROLATUM')"),
    ("Parabens", "i.inci_name like '%PARABEN%'"),
]
ACTIVES = [
    ("Vitamin E (Tocopherol, Tocopheryl acetate)", "i.inci_name in ('TOCOPHEROL','TOCOPHERYL ACETATE')"),
    ("Vitamin C and derivatives", "i.inci_name like '%ASCORB%'"),
    ("Hyaluronic acid / Sodium hyaluronate", "i.inci_name like '%HYALURON%'"),
    ("Niacinamide", "i.inci_name = 'NIACINAMIDE'"),
    ("Salicylic acid", "i.inci_name = 'SALICYLIC ACID'"),
    ("Retinoids (Retinol, Retinyl esters)", "i.inci_name like 'RETIN%'"),
    ("Ceramides", "i.inci_name like 'CERAMIDE%'"),
    ("Glycolic / Lactic acid (AHAs)", "i.inci_name in ('GLYCOLIC ACID','LACTIC ACID')"),
]
# Open Beauty Facts category tags (verbatim) with a display label.
CATEGORIES = [
    ("en:shampoos", "Shampoos"), ("en:hair-conditioners", "Hair conditioners"), ("en:shower-gels", "Shower gels"),
    ("en:soaps", "Soaps"), ("en:toothpastes", "Toothpastes"), ("en:deodorants", "Deodorants"),
    ("en:facial-creams", "Facial creams"), ("en:body-creams", "Body creams"), ("en:hand-creams", "Hand creams"),
    ("en:sunscreen", "Sunscreens"), ("en:cleansers", "Cleansers"), ("en:makeup", "Makeup"), ("en:perfumes", "Perfumes"),
]
COUNT_BUCKETS = [("1 to 5", 1, 5), ("6 to 10", 6, 10), ("11 to 15", 11, 15), ("16 to 20", 16, 20),
                 ("21 to 30", 21, 30), ("31 to 50", 31, 50), ("51 or more", 51, 10 ** 6)]


def compute(db_path):
    con = sqlite3.connect(str(db_path))

    def q(sql, *a):
        return con.execute(sql, a).fetchall()

    s = {}
    try:
        s["snapshot_date"] = json.loads(BUILD_REPORT.read_text(encoding="utf-8"))["generated_at"][:10]
    except (OSError, KeyError, ValueError):
        s["snapshot_date"] = q("select max(date(created_at)) from products")[0][0]
    P = q("select count(*) from products")[0][0]
    s["products"] = P
    s["brands"] = q("select count(distinct brand_id) from products where brand_id is not null")[0][0]
    s["ingredient_names"] = q("select count(*) from ingredients")[0][0]
    s["links"] = q("select count(*) from product_ingredients")[0][0]

    # most common ingredients (share of products); AQUA and WATER are the same substance
    top = q("select i.inci_name, count(distinct pi.product_id) from product_ingredients pi join ingredients i using(ingredient_id) "
            "where i.inci_name not in ('AQUA','WATER') group by 1 order by 2 desc limit 19")
    water = q("select count(distinct pi.product_id) from product_ingredients pi join ingredients i using(ingredient_id) "
              "where i.inci_name in ('AQUA','WATER')")[0][0]
    s["top_ingredients"] = sorted([("Aqua / Water", water, pct(water, P))] + [(nm, c, pct(c, P)) for nm, c in top],
                                  key=lambda t: -t[1])[:20]

    # first-listed ingredient
    first = q("select i.inci_name, count(*) from product_ingredients pi join ingredients i using(ingredient_id) "
              "where pi.position_index = 1 group by 1 order by 2 desc limit 12")
    n_first = q("select count(*) from product_ingredients where position_index = 1")[0][0]
    s["first_n"] = n_first
    s["first_ingredient"] = [(nm, c, pct(c, n_first)) for nm, c in first]

    # ingredients per product
    counts = [c for (c,) in q("select count(*) from product_ingredients group by product_id")]
    s["ing_mean"] = round(statistics.mean(counts), 1)
    s["ing_median"] = int(statistics.median(counts))
    s["ing_max"] = max(counts)
    s["ing_buckets"] = [(lbl, sum(1 for c in counts if lo <= c <= hi), pct(sum(1 for c in counts if lo <= c <= hi), len(counts)))
                        for lbl, lo, hi in COUNT_BUCKETS]
    per_product = dict(q("select product_id, count(*) from product_ingredients group by product_id"))
    by_cat = []
    for tag, label in CATEGORIES:
        ids = [pid for (pid,) in q("select product_id from products where obf_categories_tags is not null and "
                                   "(';' || obf_categories_tags || ';') like ?", f"%;{tag};%")]
        vals = [per_product[i] for i in ids if i in per_product]
        if len(vals) >= 100:
            by_cat.append((label, tag, len(vals), int(statistics.median(vals))))
    s["ing_by_category"] = sorted(by_cat, key=lambda t: -t[3])
    s["categorised"] = q("select count(*) from products where obf_categories_tags is not null and obf_categories_tags <> ''")[0][0]

    def share_group(cond):
        return q(f"select count(distinct pi.product_id) from product_ingredients pi join ingredients i using(ingredient_id) where {cond}")[0][0]
    s["groups"] = sorted([(lbl, c, pct(c, P)) for lbl, cond in GROUPS for c in [share_group(cond)]], key=lambda t: -t[1])
    s["actives"] = sorted([(lbl, c, pct(c, P)) for lbl, cond in ACTIVES for c in [share_group(cond)]], key=lambda t: -t[1])
    s["annex_iii_products"] = share_group("i.annex_iii = 1")
    s["annex_iii_pct"] = pct(s["annex_iii_products"], P)
    s["annex_iii_names"] = q("select count(*) from ingredients where annex_iii = 1")[0][0]
    top_a3 = q("select i.inci_name, count(distinct pi.product_id) from product_ingredients pi join ingredients i using(ingredient_id) "
               "where i.annex_iii = 1 group by 1 order by 2 desc limit 10")
    s["annex_iii_top"] = [(nm, c, pct(c, P)) for nm, c in top_a3]

    # CosIng functions, weighted by product-ingredient links
    fn = Counter()
    for functions, c in q("select i.functions, count(*) from product_ingredients pi join ingredients i using(ingredient_id) "
                          "where i.functions is not null and i.functions <> '' group by i.ingredient_id"):
        for f in functions.split(";"):
            f = f.strip()
            if f:
                fn[f] += c
    s["functions_links"] = q("select count(*) from product_ingredients pi join ingredients i using(ingredient_id) "
                             "where i.functions is not null and i.functions <> ''")[0][0]
    s["functions"] = [(f, c, pct(c, s["functions_links"])) for f, c in fn.most_common(12)]

    # coverage honesty
    s["cosing_names"] = q("select count(*) from ingredients where cosing_matched = 1")[0][0]
    s["cosing_links"] = q("select count(*) from product_ingredients pi join ingredients i using(ingredient_id) where i.cosing_matched = 1")[0][0]
    s["cosing_names_pct"] = pct(s["cosing_names"], s["ingredient_names"])
    s["cosing_links_pct"] = pct(s["cosing_links"], s["links"])
    meth = q("select method, count(*) from ingredient_name_map group by 1 order by 2 desc")
    s["map_rows"] = sum(c for _, c in meth)
    s["map_methods"] = [(m, c, pct(c, s["map_rows"])) for m, c in meth]
    con.close()
    return s


CSS = """
    :root { --bg-paper: #0A0B0E; --bg-paper-2: #161922; --text-ink: #F8FAFC; --text-muted: #94A3B8;
            --rule-color: #232838; --accent: #38BDF8; --radius: 12px; }
    .page-header { border-bottom: 1px solid #232838; padding: 1rem 0; background: rgba(10, 11, 14, 0.85); backdrop-filter: blur(10px); position: sticky; top: 0; z-index: 100; }
    .page-header-inner { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 0.75rem 1.5rem; }
    .page-nav { display: flex; flex-wrap: wrap; gap: 0.5rem 1.5rem; align-items: center; }
    .stats-wrap { max-width: 1000px; margin: 0 auto; padding: 3rem 1rem 4rem; }
    .stats-wrap h1 { font-size: clamp(2rem, 3.6vw, 2.8rem); line-height: 1.1; margin: 0 0 0.5rem; }
    .stats-wrap h2 { font-size: 1.5rem; margin: 0; }
    .stats-wrap h3 { font-size: 1.05rem; margin: 1.5rem 0 0; }
    .stats-wrap .lede { font-size: 1.05rem; color: var(--text-muted); margin-top: 0.75rem; max-width: 76ch; }
    .stats-wrap a { color: var(--accent); }
    .crumbs { margin-bottom: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: var(--text-muted); }
    .eyebrow { text-transform: uppercase; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.12em; color: var(--accent); margin: 0 0 0.6rem; }
    .cta-inline { margin-top: 3.5rem; padding: 1.75rem; border: 1px solid var(--rule-color); border-radius: var(--radius); background: var(--bg-paper-2); }
    .cta-inline p { color: var(--text-muted); margin: 0.5rem 0 1rem; }
    @media (max-width: 600px) { .page-header { position: static; } .stats-wrap { padding: 2rem 1rem; } }
"""


def chrome():
    """Header copied from a generated landing page so the nav stays identical."""
    sample = next(p for p in sorted((ROOT / "landing").glob("*.html")))
    src = sample.read_text(encoding="utf-8")
    start = src.index("<header")
    end = src.index("</header>", start) + len("</header>")
    return src[start:end]


def build_page(s, charts):
    site = SITE
    snap = s["snapshot_date"]
    P = s["products"]
    src_note = f"Source: INCIDB, incidb.dataengineered.io/stats · snapshot {snap} · product data © Open Beauty Facts contributors (ODbL) · CC BY 4.0"
    sections = []

    ti = s["top_ingredients"]
    charts["top-ingredients"] = svg_hbar(site, "The most common cosmetic ingredients", f"Share of {n(P)} products listing each INCI name",
                                         [(nm, c, f"{p}%") for nm, c, p in ti[:15]], src_note, label_w=230)
    sections.append(section(
        site, "ingredients", "The most common cosmetic ingredients",
        f"<strong>{ti[0][2]}%</strong> of products list {data(ti[0][0])}, {ti[1][2]}% list {data(ti[1][0])} and {ti[2][2]}% list {data(ti[2][0])}. "
        f"The catalogue holds {n(s['ingredient_names'])} distinct canonical INCI names across {n(s['links'])} ingredient positions.",
        figure(site, "top-ingredients", charts["top-ingredients"], "The most common cosmetic ingredients", f"{n(P)} products"),
        table(["INCI name", "Products", "Share of products"], [(nm, n(c), f"{p}%") for nm, c, p in ti], {1, 2}),
        "Share of products whose parsed ingredient list contains the canonical INCI name at least once. Aqua and Water are two spellings of the same "
        "ingredient and are counted together; every other name is counted as it appears after canonicalisation."))

    gb = s["groups"]
    charts["ingredient-groups"] = svg_hbar(site, "Ingredient groups by share of products", f"Share of {n(P)} products containing at least one ingredient of the group",
                                           [(lbl, c, f"{p}%") for lbl, c, p in gb], src_note, label_w=260)
    frag = next(p for lbl, _, p in gb if lbl.startswith("Fragrance"))
    par = next(p for lbl, _, p in gb if lbl == "Parabens")
    sections.append(section(
        site, "groups", "Fragrance, preservatives, surfactants and silicones",
        f"<strong>{frag}%</strong> of products contain fragrance and {next(p for lbl, _, p in gb if 'allergen' in lbl)}% contain at least one EU-listed fragrance allergen. "
        f"Parabens appear in <strong>{par}%</strong> of products and phenoxyethanol, the preservative that has largely replaced them, in "
        f"{next(p for lbl, _, p in gb if lbl == 'Phenoxyethanol')}%.",
        figure(site, "ingredient-groups", charts["ingredient-groups"], "Ingredient groups by share of products", f"{n(P)} products"),
        table(["Group", "Products", "Share"], [(lbl, n(c), f"{p}%") for lbl, c, p in gb], {1, 2}),
        "Each group is a plain rule over canonical INCI names (for example, any name ending in PARABEN; any name containing METHICONE or SILOXANE; "
        "the EU Annex III fragrance-allergen list for allergens). The rules describe presence on the label, not concentration or safety."))

    ac = s["actives"]
    charts["actives"] = svg_hbar(site, "Skincare actives by share of products", f"Share of {n(P)} products listing the active",
                                 [(lbl, c, f"{p}%") for lbl, c, p in ac], src_note, label_w=260)
    sections.append(section(
        site, "actives", "How common the headline skincare actives are",
        f"{data('Vitamin E')} (tocopherol or tocopheryl acetate) is in <strong>{ac[0][2]}%</strong> of products. "
        f"The actives that drive skincare marketing are rare across the whole catalogue: hyaluronic acid appears in {next(p for lbl, _, p in ac if 'Hyaluronic' in lbl)}%, "
        f"niacinamide in {next(p for lbl, _, p in ac if lbl == 'Niacinamide')}% and retinoids in {next(p for lbl, _, p in ac if 'Retinoids' in lbl)}%.",
        figure(site, "actives", charts["actives"], "Skincare actives by share of products", f"{n(P)} products"),
        table(["Active", "Products", "Share"], [(lbl, n(c), f"{p}%") for lbl, c, p in ac], {1, 2}),
        "Denominator is every product in the catalogue, not only facial skincare, which is why the shares are low. Products span shampoos, soaps, toothpastes, "
        "deodorants and makeup as well as face care."))

    ib = s["ing_buckets"]
    ic = s["ing_by_category"]
    charts["ingredient-count"] = svg_hbar(site, "How many ingredients a product lists", f"Share of {n(P)} products by ingredient count",
                                          [(lbl, c, f"{p}%") for lbl, c, p in ib], src_note, label_w=110)
    charts["ingredients-by-category"] = svg_hbar(site, "Median ingredient count by product type", "Open Beauty Facts category tags with 100+ products",
                                                 [(lbl, m, str(m)) for lbl, _, _, m in ic], src_note, label_w=150)
    sections.append(section(
        site, "ingredient-count", "How long ingredient lists are",
        f"The median product lists <strong>{s['ing_median']} ingredients</strong> (mean {s['ing_mean']}, longest {n(s['ing_max'])}). "
        f"{data(ic[0][0].lower())} have the longest lists at a median of {ic[0][3]}, {data(ic[-1][0].lower())} the shortest at {ic[-1][3]}.",
        figure(site, "ingredient-count", charts["ingredient-count"], "How many ingredients a product lists", f"{n(P)} products")
        + figure(site, "ingredients-by-category", charts["ingredients-by-category"], "Median ingredient count by product type", f"{len(ic)} categories"),
        table(["Ingredient count", "Products", "Share"], [(lbl, n(c), f"{p}%") for lbl, c, p in ib], {1, 2})
        + "<h3>By product type</h3>"
        + table(["Product type", "Category tag", "Products", "Median ingredients"], [(lbl, tag, n(c), str(m)) for lbl, tag, c, m in ic], {2, 3}),
        f"Ingredient count is the number of parsed positions on the label. Product types use the Open Beauty Facts category tags verbatim ({n(s['categorised'])} of {n(P)} products carry a tag); "
        f"a product can carry several tags, so the types overlap. Only tags with at least 100 products are shown."))

    fi = s["first_ingredient"]
    charts["first-ingredient"] = svg_hbar(site, "What is listed first on the label", f"Share of {n(s['first_n'])} products by first-listed ingredient",
                                          [(nm, c, f"{p}%") for nm, c, p in fi[:10]], src_note, label_w=190)
    sections.append(section(
        site, "first-ingredient", "What comes first on the label",
        f"Ingredients are listed in descending order of concentration, so the first name is the bulk of the product. {data(fi[0][0])} leads <strong>{fi[0][2]}%</strong> of labels "
        f"and {data(fi[1][0])} another {fi[1][2]}%; {data(fi[2][0])} tops {fi[2][2]}%, {data(fi[3][0])} (aerosol propellant) {fi[3][2]}%.",
        figure(site, "first-ingredient", charts["first-ingredient"], "What is listed first on the label", f"{n(s['first_n'])} products"),
        table(["First-listed ingredient", "Products", "Share"], [(nm, n(c), f"{p}%") for nm, c, p in fi], {1, 2}),
        "Position 1 of the parsed ingredient list. EU and US labelling rules require descending order of concentration for ingredients above 1%, so the first "
        "position is the dominant ingredient by weight."))

    a3 = s["annex_iii_top"]
    charts["annex-iii"] = svg_hbar(site, "Most common EU Annex III restricted ingredients", f"Share of {n(P)} products; restricted = permitted under conditions",
                                   [(nm, c, f"{p}%") for nm, c, p in a3], src_note, label_w=210)
    sections.append(section(
        site, "regulation", "Regulated ingredients",
        f"<strong>{s['annex_iii_pct']}%</strong> of products contain at least one ingredient listed in Annex III of the EU Cosmetics Regulation, the list of substances "
        f"permitted only under conditions such as a maximum concentration or a mandatory warning. A high share is expected, because Annex III covers everyday preservatives "
        f"and fragrance components, led here by {data(a3[0][0])} ({a3[0][2]}%) and {data(a3[1][0])} ({a3[1][2]}%).",
        figure(site, "annex-iii", charts["annex-iii"], "Most common EU Annex III restricted ingredients", f"{n(s['annex_iii_names'])} Annex III names in the catalogue"),
        table(["INCI name", "Products", "Share"], [(nm, n(c), f"{p}%") for nm, c, p in a3], {1, 2}),
        "Annex III membership comes from the European Commission CosIng inventory, joined on exact canonical name. It records that a substance is regulated, "
        "not whether a given product complies, which depends on concentration and use that labels do not state. Annex II (prohibited substances) is deliberately "
        "not summarised here: exact-name joins on that list produce matches that need case-by-case review before they mean anything."))

    fn = s["functions"]
    charts["functions"] = svg_hbar(site, "What ingredients are for", f"Share of {n(s['functions_links'])} ingredient positions with a CosIng function",
                                   [(f.title(), c, f"{p}%") for f, c, p in fn], src_note, label_w=230)
    sections.append(section(
        site, "functions", "What the ingredients are for",
        f"Weighted by how often they appear on labels, <strong>{fn[0][2]}%</strong> of ingredient positions carry the CosIng function {data(fn[0][0].title())}, "
        f"{fn[1][2]}% {data(fn[1][0].title())} and {fn[2][2]}% {data(fn[2][0].title())}.",
        figure(site, "functions", charts["functions"], "What ingredients are for", f"{n(s['functions_links'])} positions with a function"),
        table(["CosIng function", "Ingredient positions", "Share"], [(f.title(), n(c), f"{p}%") for f, c, p in fn], {1, 2}),
        "CosIng assigns one or more functions to each inventory entry. Each ingredient position on a label counts once per function of its ingredient, "
        f"so shares sum to more than 100%. Denominator: the {n(s['functions_links'])} of {n(s['links'])} positions whose ingredient has a CosIng function."))

    mm = s["map_methods"]
    charts["coverage"] = svg_hbar(site, "How raw label tokens were resolved", f"Share of {n(s['map_rows'])} raw name to canonical name mappings by method",
                                  [(m, c, f"{p}%") for m, c, p in mm], src_note, label_w=140)
    sections.append(section(
        site, "coverage", "How much of the catalogue is enriched, stated two ways",
        f"Only <strong>{s['cosing_names_pct']}%</strong> of the {n(s['ingredient_names'])} distinct canonical names match the CosIng inventory, yet those names fill "
        f"<strong>{s['cosing_links_pct']}%</strong> of all {n(s['links'])} ingredient positions on labels. The long tail of unmatched strings (botanical variants, "
        f"multilingual spellings, marketing tokens) is real but rare on any given label.",
        figure(site, "coverage", charts["coverage"], "How raw label tokens were resolved", f"{n(s['map_rows'])} name-map rows"),
        table(["Resolution method", "Name-map rows", "Share"], [(m, n(c), f"{p}%") for m, c, p in mm], {1, 2}),
        "Every raw label token is mapped to a canonical name with the method recorded per row and shipped with the data. Quoting only the link-weighted figure "
        "would flatter the coverage; quoting only the name-level figure would understate it, so both are published."))

    contents = toc([("ingredients", "Most common ingredients"), ("groups", "Fragrance, preservatives, surfactants, silicones"), ("actives", "Skincare actives"),
                    ("ingredient-count", "Ingredient list length"), ("first-ingredient", "First-listed ingredient"), ("regulation", "Regulated ingredients"),
                    ("functions", "Ingredient functions"), ("coverage", "Enrichment coverage"), ("method", "Method, reuse and citation")])
    tile_html = tiles([("Products", n(P)), ("Brands", n(s["brands"])), ("Canonical INCI names", n(s["ingredient_names"])),
                       ("Ingredient positions", n(s["links"])), ("Median ingredients", str(s["ing_median"])), ("Snapshot", snap)])
    title_tag = f"Cosmetics Ingredient Statistics {snap[:4]} — Most Common INCI Names, Fragrance, Parabens | INCIDB"
    desc = (f"Cosmetics in numbers from {n(P)} product labels: the most common INCI ingredients, share of products with fragrance, parabens, silicones and sulfates, "
            f"skincare actives, ingredient counts by product type, regulated ingredients. Free to cite and embed.")
    ld = article_ld(site, "Cosmetics ingredients in numbers: statistics from the INCIDB label corpus", desc, FIRST_PUBLISHED,
                    f"{site.base_url}/og-image.png", ["cosmetics ingredients", "INCI", "skincare", "fragrance allergens", "parabens"])
    header = chrome()

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
    <meta property="og:title" content="Cosmetics ingredients in numbers — INCIDB statistics {snap[:4]}">
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
    <link rel="stylesheet" href="../index.css">
{ld}
    <style>{CSS}{STATS_CSS}    </style>
</head>
<body>
{header}
<main class="stats-wrap">
  <p class="crumbs"><a href="/">Home</a> &rsaquo; <span>Statistics</span></p>
  <p class="eyebrow">Market statistics · snapshot {esc(snap)}</p>
  <h1>Cosmetics ingredients in numbers</h1>
  <p class="lede">Aggregate statistics computed from the full INCIDB corpus: {n(P)} cosmetic and personal-care product labels from Open Beauty Facts, {n(s['links'])} ordered ingredient positions resolved to {n(s['ingredient_names'])} canonical INCI names and enriched from the European Commission CosIng inventory. Every figure is free to cite, quote and embed with a link to this page.</p>
  <ul class="tiles">{tile_html}</ul>
  <nav class="toc" aria-label="Contents"><strong>On this page</strong><ol>{contents}</ol></nav>

{"".join(sections)}

  <section class="stat" id="method">
    <h2>Method, reuse and citation</h2>
    <ul class="method">
      <li><strong>Source.</strong> The full INCIDB snapshot of {snap}: {n(P)} product labels from <a href="https://world.openbeautyfacts.org/">Open Beauty Facts</a> (product data © Open Beauty Facts contributors, <a href="https://opendatacommons.org/licenses/odbl/1-0/">ODbL v1.0</a>), ingredient lists parsed into ordered positions and resolved to canonical INCI names, with functions, CAS numbers and Annex membership joined from the European Commission CosIng inventory (contains data from the European Commission CosIng database).</li>
      <li><strong>Nothing is inferred.</strong> A figure counts what labels state. Concentrations are not on labels and are never estimated; where a source has no value the field is NULL and excluded from that figure's denominator, which every section states.</li>
      <li><strong>The corpus is what contributors scanned.</strong> Open Beauty Facts over-represents European mass-market products and the categories its contributors photograph. Shares describe this corpus, not the world market.</li>
      <li><strong>Refresh.</strong> INCIDB ships editions; this page and its charts are regenerated with each edition, so figures move. Cite the snapshot date.</li>
      <li><strong>Reuse.</strong> The figures and charts on this page are published under <a href="https://creativecommons.org/licenses/by/4.0/" rel="license">CC BY 4.0</a>: use them in articles, slides and posts with a link to <span translate="no">{site.page_url}</span> and the Open Beauty Facts attribution above. The machine-readable version is <a href="/stats/data.json">data.json</a>. The row-level tables are <a href="/#pricing">INCIDB Complete</a>; a free 200-product sample is in the <a href="https://github.com/INCIDB/cosmetics-skincare-inci-database">public repository</a>.</li>
      <li><strong>Suggested citation.</strong> <span translate="no">INCIDB ({snap[:4]}). <em>Cosmetics ingredients in numbers</em>, snapshot {snap}. DataEngineered. {site.page_url}</span></li>
      <li><strong>Questions or corrections:</strong> <a href="/#contact">contact form</a> or incidb@dataengineered.io.</li>
    </ul>
  </section>

  <div class="cta-inline">
    <h3 style="margin:0">Need the row-level tables behind these numbers?</h3>
    <p>Every product with its ordered ingredient positions, canonical names, CosIng functions, CAS numbers and Annex flags, plus the name map that shows how each label token was resolved. CSV and Parquet.</p>
    <a class="btn btn-primary" href="/#pricing">Get INCIDB Complete ($79)</a>
  </div>
</main>
<footer>
    <div class="container">
        <p>INCIDB · snapshot {esc(snap[:7].replace('-', '.'))} · statistics generated from the full corpus</p>
        <p style="margin-top: 0.75rem; font-size: 0.8rem; color: var(--text-secondary);">Product data © <a href="https://world.openbeautyfacts.org/" style="color: var(--accent-blue); text-decoration: none;">Open Beauty Facts</a> contributors, under the <a href="https://opendatacommons.org/licenses/odbl/1-0/" style="color: var(--accent-blue); text-decoration: none;">Open Database License (ODbL) v1.0</a>. Ingredient enrichment contains data from the European Commission CosIng database, reused with attribution.</p>
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
        "license": "CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/) - attribute with a link to the page; product data (c) Open Beauty Facts contributors, ODbL v1.0; contains data from the European Commission CosIng database",
        "totals": {k: s[k] for k in ("products", "brands", "ingredient_names", "links", "categorised")},
        "top_ingredients": [dict(inci_name=nm, products=c, share_pct=p) for nm, c, p in s["top_ingredients"]],
        "ingredient_groups": [dict(group=lbl, products=c, share_pct=p) for lbl, c, p in s["groups"]],
        "actives": [dict(active=lbl, products=c, share_pct=p) for lbl, c, p in s["actives"]],
        "ingredient_count": {"median": s["ing_median"], "mean": s["ing_mean"], "max": s["ing_max"],
                             "buckets": [dict(bucket=lbl, products=c, share_pct=p) for lbl, c, p in s["ing_buckets"]],
                             "by_category": [dict(label=lbl, tag=tag, products=c, median=m) for lbl, tag, c, m in s["ing_by_category"]]},
        "first_ingredient": {"denominator": s["first_n"], "rows": [dict(inci_name=nm, products=c, share_pct=p) for nm, c, p in s["first_ingredient"]]},
        "annex_iii": {"products_with_any": s["annex_iii_products"], "share_pct": s["annex_iii_pct"], "names_in_catalogue": s["annex_iii_names"],
                      "top": [dict(inci_name=nm, products=c, share_pct=p) for nm, c, p in s["annex_iii_top"]]},
        "functions": {"denominator_positions": s["functions_links"], "rows": [dict(function=f, positions=c, share_pct=p) for f, c, p in s["functions"]]},
        "coverage": {"cosing_matched_names": s["cosing_names"], "cosing_matched_names_pct": s["cosing_names_pct"],
                     "cosing_matched_positions": s["cosing_links"], "cosing_matched_positions_pct": s["cosing_links_pct"],
                     "name_map_rows": s["map_rows"], "methods": [dict(method=m, rows=c, share_pct=p) for m, c, p in s["map_methods"]]},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", default=os.environ.get("INCIDB_SQLITE", str(DEFAULT_DB)))
    args = ap.parse_args()
    db = Path(args.db)
    if not db.is_file():
        raise SystemExit(f"SQLite snapshot not found: {db}")
    s = compute(db)
    charts = {}
    page = build_page(s, charts)
    write_outputs(OUT_DIR, page, charts, build_data_json(s))
    print(f"stats/index.html + {len(charts)} charts + data.json  (snapshot {s['snapshot_date']}, {s['products']:,} products)")


if __name__ == "__main__":
    main()
