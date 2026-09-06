#!/usr/bin/env python3
"""
generate_seo_pages.py — INCIDB INCI monograph & category-hub generator.

Reads the free sample under `samples/` (the same five tables the public can
download) plus `claims.json`, and writes one monograph per ingredient to
`landing/`, one hub per CosIng functional category, and `sitemap.xml`.

Two rules govern everything here, and they are the reason this file was
rewritten:

1. **No defaults.** Earlier versions defaulted `primary_function` to
   "Skin-Conditioning Agent" and `description` to "Standard cosmetic
   ingredient registered in INCI catalog." — so every page claimed a
   function and a description whether or not the data had one. Nothing is
   defaulted now: a field that is empty is simply not rendered.
2. **Hubs are driven by the `functions` values actually recorded.** An
   ingredient is placed in a hub because its CosIng functions match that
   hub's vocabulary, never as a fallback. An ingredient with no CosIng
   function gets no monograph at all — there would be nothing to say about
   it beyond its name, and a page like that is noise for readers and search
   engines alike.

Every count printed on a generated page comes from `claims.json`, which is
itself generated from `data/exports/build_report.json` by
`scripts/render_claims.py`.
"""

import csv
import html
import json
import os
import re
from datetime import datetime, timezone

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(ROOT_DIR, "samples")
LANDING_DIR = os.path.join(ROOT_DIR, "landing")
SITEMAP_PATH = os.path.join(ROOT_DIR, "sitemap.xml")
CLAIMS_PATH = os.path.join(ROOT_DIR, "claims.json")

BASE_URL = "https://incidb.dataengineered.io"

# The owner creates the real Stripe Payment Link for INCIDB Complete and
# swaps it in (Task 13). Until then every buy button carries this literal,
# and `tests/test_public_claims.py::test_no_stripe_placeholder_when_releasing`
# fails the release while it is still present.
STRIPE_COMPLETE_LINK_PLACEHOLDER = "https://buy.stripe.com/REPLACE-WITH-INCIDB-COMPLETE-LINK"

# Hub definitions, evaluated IN THIS ORDER. An ingredient joins the first hub
# whose vocabulary appears in its `functions` value; the substrings below are
# matched against the real CosIng function vocabulary present in the data.
HUBS = [
    ("preservatives", "Preservatives, Antimicrobials & Antioxidants", "preservatives.html",
     ("PRESERVATIVE", "ANTIMICROBIAL", "ANTIOXIDANT", "ANTICORROSIVE", "CHELATING")),
    ("active_treatments", "Active Treatments, Exfoliants & UV Filters", "active_treatments.html",
     ("UV FILTER", "UV ABSORBER", "LIGHT STABILIZER", "EXFOLIATING", "KERATOLYTIC",
      "ANTI-SEBORRHEIC", "ANTI-SEBUM", "ANTIPLAQUE", "ANTIPERSPIRANT", "BLEACHING")),
    ("fragrance_colour", "Fragrance, Perfuming & Colorant Agents", "fragrance_colour.html",
     ("FRAGRANCE", "PERFUMING", "COLORANT", "HAIR DYEING", "FLAVOURING", "DENATURANT")),
    ("surfactants_cleansing", "Surfactants, Cleansing & Emulsifying Agents", "surfactants_cleansing.html",
     ("SURFACTANT", "CLEANSING", "FOAMING")),
    ("solvents", "Solvents, Viscosity & Structure Agents", "solvents.html",
     ("SOLVENT", "VISCOSITY CONTROLLING", "EMULSION STABILISING", "FILM FORMING",
      "GEL FORMING", "BINDING",
      "BULKING", "OPACIFYING", "ABSORBENT", "ABRASIVE", "ANTICAKING", "ANTIFOAMING",
      "PLASTICISER", "PROPELLANT", "BUFFERING", "PH ADJUSTERS", "SLIP MODIFIER")),
    ("skin_conditioning", "Skin-Conditioning & Emollient Agents", "skin_conditioning.html",
     ("SKIN CONDITIONING", "SKIN PROTECTING", "EMOLLIENT", "HUMECTANT", "MOISTURISING",
      "SMOOTHING", "REFATTING", "REFRESHING", "HAIR CONDITIONING", "NAIL CONDITIONING",
      "ANTISTATIC", "DETANGLING", "HAIR FIXING", "HAIR WAVING", "SOOTHING", "ASTRINGENT",
      "DEODORANT", "TONIC", "ORAL CARE")),
]


def clean_slug(name):
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', name.lower()).strip('_')
    return slug or "unknown"


def load_claims():
    with open(CLAIMS_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_data():
    """Loads the sample tables. Missing files yield empty structures."""
    ingredients = []
    products = {}
    prod_ing = {}

    ing_path = os.path.join(SAMPLES_DIR, "ingredients.csv")
    if os.path.exists(ing_path):
        with open(ing_path, mode='r', encoding='utf-8', errors='replace') as f:
            for row in csv.DictReader(f, delimiter='|'):
                ingredients.append(row)

    prod_path = os.path.join(SAMPLES_DIR, "products.csv")
    if os.path.exists(prod_path):
        with open(prod_path, mode='r', encoding='utf-8', errors='replace') as f:
            for row in csv.DictReader(f, delimiter='|'):
                products[row.get('product_id')] = row

    pi_path = os.path.join(SAMPLES_DIR, "product_ingredients.csv")
    if os.path.exists(pi_path):
        with open(pi_path, mode='r', encoding='utf-8', errors='replace') as f:
            for row in csv.DictReader(f, delimiter='|'):
                iid = row.get('ingredient_id')
                pid = row.get('product_id')
                prod_ing.setdefault(iid, [])
                if pid in products:
                    prod_ing[iid].append({
                        'product_name': products[pid].get('name', 'Product #' + pid),
                        'position': row.get('position_index', ''),
                    })

    return ingredients, products, prod_ing


def field(row, name):
    """A field's value, or '' — never a default."""
    return (row.get(name) or '').strip()


def function_list(row):
    """The CosIng functions recorded on this ingredient, as a list."""
    raw = field(row, 'functions')
    return [f.strip() for f in raw.split(';') if f.strip()] if raw else []


def is_flag(row, name):
    """True only for an explicit positive flag; '' and '0' are both False."""
    value = field(row, name)
    return value not in ('', '0', '0.0')


def categorize_ingredient(functions):
    """Returns the hub tuple for these CosIng functions, or None.

    None means "this ingredient has no CosIng function we publish a hub for",
    and the caller skips it: no hub, no monograph, no sitemap entry.
    """
    joined = ";".join(functions).upper()
    if not joined:
        return None
    for hub_key, hub_name, hub_file, vocabulary in HUBS:
        if any(term in joined for term in vocabulary):
            return (hub_key, hub_name, hub_file)
    return None


def ingredient_profile(ing, prod_list):
    """A data-derived prose paragraph. Clauses appear only when the data does."""
    e = html.escape
    inci_name = field(ing, 'inci_name')
    cas = field(ing, 'cas_number')
    ec = field(ing, 'ec_number')
    functions = function_list(ing)
    restriction = field(ing, 'cosing_restriction')
    comedo = field(ing, 'comedogenic_rating')
    allergen = is_flag(ing, 'is_common_allergen')
    fungal = is_flag(ing, 'is_fungal_acne_trigger')

    sentences = []

    ident = f"<strong>{e(inci_name)}</strong>" if inci_name else "This ingredient"
    if functions:
        s1 = (f"{ident} is listed in the European Commission CosIng inventory under "
              f"{'the functional category' if len(functions) == 1 else 'the functional categories'} "
              + ", ".join(e(f.title()) for f in functions))
    else:
        s1 = f"{ident} is catalogued in INCIDB"
    if cas and ec:
        s1 += f", with CAS number {e(cas)} and EC number {e(ec)}."
    elif cas:
        s1 += f", with CAS number {e(cas)}."
    else:
        s1 += ". CosIng records no CAS number for it, so the column is NULL rather than guessed."
    sentences.append(s1)

    if restriction:
        sentences.append(
            f"CosIng records a restriction against it ({e(restriction)}), so check the "
            f"corresponding Annex entry before formulating.")

    n_prod = len(prod_list)
    ranked = [p for p in prod_list if str(p.get('position', '')).strip().isdigit()]
    if n_prod:
        s2 = (f"In the free INCIDB sample it appears on {n_prod} product label"
              + ("s" if n_prod != 1 else ""))
        if ranked:
            best = min(ranked, key=lambda p: int(p['position']))
            best_pos = int(best['position'])
            best_name = (best.get('product_name') or '').strip()
            if best_pos == 1 and best_name:
                s2 += f", leading the declaration on {e(best_name)}"
            elif best_name:
                s2 += f", reaching position {best_pos} on {e(best_name)}"
        s2 += "."
        sentences.append(s2)

    if comedo:
        sentences.append(
            f"Fulton (1989) grades it {e(comedo)} on the 0–5 comedogenicity scale; "
            f"that grade is transcribed as-is and is the only rating source used.")

    if allergen:
        sentences.append(
            "It is on the EU Annex III fragrance-allergen list (Regulation (EC) 1223/2009 "
            "as amended by Regulation (EU) 2023/1545), so labelling rules apply above the "
            "regulated thresholds.")
    if fungal:
        sentences.append(
            "INCIDB's rule-derived heuristic flags it as a possible Malassezia "
            "(fungal-acne) trigger. That is a rule, not a measurement — treat it as a "
            "filter rather than a finding.")

    body = " ".join(sentences)
    return (
        '<p style="font-size: 1rem; color: #CBD5E1; line-height: 1.75; '
        'margin-bottom: 1.75rem; padding-left: 1rem; border-left: 3px solid #06B6D4;">'
        f'{body}</p>'
    )


def generate_monograph(ing, prod_list, hub_info, claims):
    e = html.escape
    iid = field(ing, 'ingredient_id') or '0'
    inci_name = field(ing, 'inci_name') or 'UNKNOWN INCI'
    cas = field(ing, 'cas_number')
    functions = function_list(ing)
    functions_label = ", ".join(f.title() for f in functions)
    description = field(ing, 'chemical_description')
    comedo = field(ing, 'comedogenic_rating')
    allergen = is_flag(ing, 'is_common_allergen')
    fungal = is_flag(ing, 'is_fungal_acne_trigger')
    cosing_matched = field(ing, 'cosing_matched') == '1'

    slug = clean_slug(inci_name)
    filename = f"inci_{iid}_{slug}.html"
    filepath = os.path.join(LANDING_DIR, filename)

    hub_key, hub_name, hub_file = hub_info
    products_total = f"{claims['products']:,}"
    price = claims['price_usd']

    badges = []
    if allergen:
        badges.append('<span style="background: rgba(244, 63, 94, 0.15); color: #F43F5E; border: 1px solid #F43F5E; padding: 0.3rem 0.75rem; border-radius: 99px; font-family: \'JetBrains Mono\', monospace; font-size: 0.8rem; font-weight: 600;">EU Annex III fragrance allergen</span>')
    elif cosing_matched:
        badges.append('<span style="background: rgba(148, 163, 184, 0.12); color: #94A3B8; border: 1px solid #334155; padding: 0.3rem 0.75rem; border-radius: 99px; font-family: \'JetBrains Mono\', monospace; font-size: 0.8rem;">Not on the EU Annex III list</span>')
    if fungal:
        badges.append('<span style="background: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid #F59E0B; padding: 0.3rem 0.75rem; border-radius: 99px; font-family: \'JetBrains Mono\', monospace; font-size: 0.8rem;">Rule-flagged fungal-acne trigger</span>')
    badges_html = "\n                    ".join(badges)

    description_block = ""
    if description:
        description_block = (
            '<p style="font-size: 1.05rem; color: #94A3B8; line-height: 1.7; '
            f'margin-bottom: 1.75rem;">{e(description)}</p>')

    # Fact grid: only facts that exist.
    facts = []
    if cas:
        facts.append(("CAS REGISTRY NUMBER", f'<div style="font-family: \'JetBrains Mono\', monospace; font-size: 1.1rem; color: #38BDF8; font-weight: 600;">{e(cas)}</div>'))
    if field(ing, 'ec_number'):
        facts.append(("EC NUMBER", f'<div style="font-family: \'JetBrains Mono\', monospace; font-size: 1.1rem; color: #38BDF8; font-weight: 600;">{e(field(ing, "ec_number"))}</div>'))
    if functions:
        facts.append(("COSING FUNCTIONS", f'<div style="font-size: 1.05rem; color: #F8FAFC; font-weight: 500;">{e(functions_label)}</div>'))
    if field(ing, 'cosing_restriction'):
        facts.append(("COSING RESTRICTION", f'<div style="font-family: \'JetBrains Mono\', monospace; font-size: 1.05rem; color: #F59E0B;">{e(field(ing, "cosing_restriction"))}</div>'))
    if comedo:
        colour = '#F43F5E' if float(comedo) >= 3 else '#10B981'
        facts.append(("COMEDOGENIC RATING (FULTON 1989)", f'<div style="font-family: \'JetBrains Mono\', monospace; font-size: 1.1rem; color: {colour}; font-weight: 600;">{e(comedo)} / 5</div>'))
    facts_html = "\n".join(
        f'''                <div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #64748B; margin-bottom: 0.25rem;">{label}</div>
                    {value}
                </div>''' for label, value in facts)

    prod_rows = ""
    if prod_list:
        for p in prod_list[:8]:
            prod_rows += f"""
            <tr style="border-bottom: 1px solid #232838;">
                <td style="padding: 0.75rem; color: #F8FAFC; font-weight: 500;">{e(p['product_name'])}</td>
                <td style="padding: 0.75rem; color: #38BDF8; font-family: 'JetBrains Mono', monospace;">#{e(str(p['position']))}</td>
            </tr>
            """
    else:
        prod_rows = f"""
        <tr>
            <td colspan="2" style="padding: 1rem; color: #64748B; text-align: center;">No sample product links this ingredient. The full snapshot covers {products_total} products.</td>
        </tr>
        """

    meta_bits = [f"INCI monograph for {inci_name}"]
    if cas:
        meta_bits.append(f"CAS {cas}")
    if functions:
        meta_bits.append(f"CosIng functions: {functions_label}")
    meta_description = ". ".join(meta_bits) + ". Sourced from the EU CosIng inventory; NULL where CosIng has no value."

    keyword_bits = [inci_name, "INCI database", "cosmetic ingredient"]
    if cas:
        keyword_bits.append(f"CAS {cas}")
    if functions:
        keyword_bits.extend(f.title() for f in functions)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{e(inci_name)} — INCI profile, CosIng functions & CAS number</title>
    <meta name="description" content="{e(meta_description)}">
    <meta name="keywords" content="{e(', '.join(keyword_bits))}">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="{BASE_URL}/landing/{filename[:-5]}">
    <link rel="alternate" hreflang="en" href="{BASE_URL}/landing/{filename[:-5]}">
    <link rel="alternate" hreflang="x-default" href="{BASE_URL}/landing/{filename[:-5]}">

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300..800;1,300..800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
    <noscript><link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300..800;1,300..800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet"></noscript>
    <link rel="stylesheet" href="../index.css">

    <script type="application/ld+json">
    [
      {{
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": "INCI monograph: {e(inci_name)}",
        "description": {json.dumps(meta_description)},
        "url": "{BASE_URL}/landing/{filename[:-5]}",
        "author": {{"@type": "Organization", "name": "INCIDB"}},
        "publisher": {{
          "@type": "Organization",
          "name": "INCIDB",
          "logo": {{"@type": "ImageObject", "url": "{BASE_URL}/favicon.svg"}}
        }},
        "about": {{
          "@type": "ChemicalSubstance",
          "name": {json.dumps(inci_name)}{f', "identifier": {json.dumps(cas)}' if cas else ''}
        }}
      }},
      {{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
          {{"@type": "ListItem", "position": 1, "name": "Home", "item": "{BASE_URL}/"}},
          {{"@type": "ListItem", "position": 2, "name": {json.dumps(hub_name)}, "item": "{BASE_URL}/landing/{hub_file[:-5]}"}},
          {{"@type": "ListItem", "position": 3, "name": {json.dumps(inci_name)}, "item": "{BASE_URL}/landing/{filename[:-5]}"}}
        ]
      }}
    ]
    </script>
</head>
<body style="background: #0A0B0E; color: #F8FAFC; font-family: 'Space Grotesk', -apple-system, sans-serif; min-height: 100vh; display: flex; flex-direction: column;">
    <div class="grid-overlay"></div>

    <header style="border-bottom: 1px solid #232838; padding: 1rem 0; background: rgba(10, 11, 14, 0.85); backdrop-filter: blur(10px); position: sticky; top: 0; z-index: 100;">
        <div class="container" style="display: flex; justify-content: space-between; align-items: center;">
            <a href="/" class="logo" style="font-weight: 700; font-size: 1.3rem; color: #F8FAFC; text-decoration: none;">INCIDB</a>
            <nav style="display: flex; gap: 1.5rem; align-items: center;">
                <a href="/#coverage" style="color: #94A3B8; text-decoration: none; font-size: 0.9rem;">Coverage</a>
                <a href="/landing/{hub_file[:-5]}" style="color: #38BDF8; text-decoration: none; font-size: 0.9rem;">{e(hub_name)}</a>
                <a href="/#pricing" class="btn btn-primary" style="padding: 0.5rem 1rem; font-size: 0.85rem;">Get INCIDB Complete — ${price}</a>
            </nav>
        </div>
    </header>

    <main class="container" style="flex: 1; padding: 3rem 1rem; max-width: 900px;">
        <div style="margin-bottom: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">
            <a href="/" style="color: #64748B; text-decoration: none;">HOME</a> /
            <a href="/landing/{hub_file[:-5]}" style="color: #38BDF8; text-decoration: none;">{e(hub_name.upper())}</a> /
            <span style="color: #F8FAFC;">{e(inci_name)}</span>
        </div>

        <div style="background: #111318; border: 1px solid #232838; border-radius: 16px; padding: 2.5rem; margin-bottom: 2.5rem; box-shadow: 0 10px 30px -15px rgba(0,0,0,0.7);">
            <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 1.5rem;">
                <div>
                    <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #06B6D4; text-transform: uppercase; letter-spacing: 1px;">Canonical INCI monograph</span>
                    <h1 style="font-size: 2.2rem; line-height: 1.2; margin-top: 0.25rem; color: #F8FAFC;">{e(inci_name)}</h1>
                </div>
                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                    {badges_html}
                </div>
            </div>

            {description_block}

            {ingredient_profile(ing, prod_list)}

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.25rem; background: #161922; border: 1px solid #232838; border-radius: 12px; padding: 1.5rem;">
{facts_html}
            </div>
        </div>

        <div style="margin-bottom: 2.5rem;">
            <h2 style="font-size: 1.5rem; margin-bottom: 1rem; color: #F8FAFC;">Sample products containing {e(inci_name)}</h2>
            <p style="color: #94A3B8; font-size: 0.92rem; margin-bottom: 1.25rem;">Label positions from the free INCIDB sample. A lower position means the ingredient is declared earlier, i.e. present in a higher proportion.</p>

            <div style="background: #111318; border: 1px solid #232838; border-radius: 12px; overflow: hidden;">
                <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.92rem;">
                    <thead>
                        <tr style="background: #161922; border-bottom: 1px solid #232838; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #64748B;">
                            <th style="padding: 0.85rem;">PRODUCT</th>
                            <th style="padding: 0.85rem;">LABEL POSITION</th>
                        </tr>
                    </thead>
                    <tbody>
                        {prod_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <div style="background: #161922; border: 1px solid #232838; border-radius: 16px; padding: 2rem;">
            <h3 style="font-size: 1.3rem; margin-bottom: 0.75rem; color: #F8FAFC;">Query {e(inci_name)} in the full snapshot</h3>
            <pre style="background: #0A0B0E; border: 1px solid #232838; padding: 1.25rem; border-radius: 8px; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: #38BDF8; overflow-x: auto; margin-bottom: 1.5rem;"><code>import pyarrow.parquet as pq

ingredients = pq.read_table('ingredients.parquet').to_pandas()
target = ingredients[ingredients['inci_name'] == {json.dumps(inci_name)}]
print(target[['ingredient_id', 'functions', 'cas_number', 'is_common_allergen']])</code></pre>
            <p style="color: #94A3B8; font-size: 0.88rem; margin-bottom: 1.25rem;">The complete snapshot covers {products_total} products. Coverage of each enrichment column is published, both per distinct name and weighted by label occurrence — see the <a href="/#coverage" style="color: #38BDF8;">coverage table</a>.</p>
            <div style="text-align: right;">
                <a href="{STRIPE_COMPLETE_LINK_PLACEHOLDER}" class="btn btn-primary" style="padding: 0.75rem 1.5rem; text-decoration: none;">Get INCIDB Complete — ${price} →</a>
            </div>
        </div>
    </main>

    <footer style="background: #111318; border-top: 1px solid #232838; padding: 2rem 0; text-align: center; font-size: 0.85rem; color: #64748B; margin-top: auto;">
        <div class="container">
            <p>INCIDB · snapshot {claims['snapshot']} · counts generated from the build report</p>
            <p style="margin-top: 0.5rem;"><a href="/schema" style="color: #38BDF8; text-decoration: none;">Schema Specification</a> · <a href="/LICENSE" style="color: #38BDF8; text-decoration: none;">License Terms</a> · <a href="/documentation" style="color: #38BDF8; text-decoration: none;">Documentation</a></p>
            <p style="margin-top: 0.5rem; font-size: 0.78rem;">Product data © Open Beauty Facts contributors (ODbL v1.0). Ingredient enrichment contains data from the European Commission CosIng database.</p>
        </div>
    </footer>
</body>
</html>"""

    with open(filepath, mode='w', encoding='utf-8') as f:
        f.write(page)

    return filename


def generate_hub(hub_name, hub_file, ing_list, claims):
    e = html.escape
    filepath = os.path.join(LANDING_DIR, hub_file)
    price = claims['price_usd']

    cards = ""
    for item in sorted(ing_list, key=lambda i: field(i['ingredient'], 'inci_name')):
        ing = item['ingredient']
        inci = field(ing, 'inci_name')
        cas = field(ing, 'cas_number')
        functions = ", ".join(f.title() for f in function_list(ing))
        allergen = is_flag(ing, 'is_common_allergen')

        flag_tag = ('<span style="color: #F43F5E; font-size: 0.75rem; font-family: \'JetBrains Mono\', '
                    'monospace; font-weight: 600;">[Annex III]</span>') if allergen else ""
        cas_tag = (f'<span style="font-family: \'JetBrains Mono\', monospace; font-size: 0.75rem; '
                   f'color: #06B6D4;">CAS {e(cas)}</span>') if cas else \
                  ('<span style="font-family: \'JetBrains Mono\', monospace; font-size: 0.75rem; '
                   'color: #475569;">no CAS in CosIng</span>')

        cards += f"""
        <a href="/landing/{item['filename'][:-5]}" style="display: block; background: #161922; border: 1px solid #232838; border-radius: 10px; padding: 1.25rem; text-decoration: none;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                {cas_tag}
                {flag_tag}
            </div>
            <h3 style="font-size: 1.05rem; color: #F8FAFC; margin-bottom: 0.35rem;">{e(inci)}</h3>
            <div style="font-size: 0.8rem; color: #94A3B8;">{e(functions)}</div>
        </a>
        """

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{e(hub_name)} — INCI ingredient monographs</title>
    <meta name="description" content="INCI monographs for ingredients whose EU CosIng functions place them under {e(hub_name)}. CAS numbers, functional categories and label occurrences, sourced from CosIng.">
    <meta name="keywords" content="{e(hub_name)}, INCI ingredient directory, CosIng functional categories, cosmetic ingredient monographs">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="{BASE_URL}/landing/{hub_file[:-5]}">
    <link rel="alternate" hreflang="en" href="{BASE_URL}/landing/{hub_file[:-5]}">
    <link rel="alternate" hreflang="x-default" href="{BASE_URL}/landing/{hub_file[:-5]}">

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300..800;1,300..800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
    <noscript><link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300..800;1,300..800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet"></noscript>
    <link rel="stylesheet" href="../index.css">

    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "ItemList",
      "name": {json.dumps(hub_name)},
      "description": {json.dumps(f"INCI monographs whose recorded CosIng functions place them under {hub_name}.")},
      "numberOfItems": {len(ing_list)}
    }}
    </script>
</head>
<body style="background: #0A0B0E; color: #F8FAFC; font-family: 'Space Grotesk', -apple-system, sans-serif; min-height: 100vh; display: flex; flex-direction: column;">
    <div class="grid-overlay"></div>

    <header style="border-bottom: 1px solid #232838; padding: 1rem 0; background: rgba(10, 11, 14, 0.85); backdrop-filter: blur(10px); position: sticky; top: 0; z-index: 100;">
        <div class="container" style="display: flex; justify-content: space-between; align-items: center;">
            <a href="/" class="logo" style="font-weight: 700; font-size: 1.3rem; color: #F8FAFC; text-decoration: none;">INCIDB</a>
            <nav style="display: flex; gap: 1.5rem; align-items: center;">
                <a href="/#coverage" style="color: #94A3B8; text-decoration: none; font-size: 0.9rem;">Coverage</a>
                <a href="/schema" style="color: #94A3B8; text-decoration: none; font-size: 0.9rem;">Schema</a>
                <a href="/#pricing" class="btn btn-primary" style="padding: 0.5rem 1rem; font-size: 0.85rem;">Get INCIDB Complete — ${price}</a>
            </nav>
        </div>
    </header>

    <main class="container" style="flex: 1; padding: 3rem 1rem; max-width: 1100px;">
        <div style="margin-bottom: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">
            <a href="/" style="color: #64748B; text-decoration: none;">HOME</a> /
            <span style="color: #38BDF8;">{e(hub_name.upper())}</span>
        </div>

        <div style="text-align: center; max-width: 820px; margin: 0 auto 3rem auto;">
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #06B6D4; text-transform: uppercase; letter-spacing: 1px;">Category hub</div>
            <h1 style="font-size: 2.5rem; margin-top: 0.35rem; color: #F8FAFC;">{e(hub_name)}</h1>
            <p style="color: #94A3B8; font-size: 1.02rem; margin-top: 0.75rem; line-height: 1.7;">{len(ing_list)} ingredients from the free INCIDB sample whose recorded CosIng <code>functions</code> place them here. Membership is read from the data, not assigned by hand — an ingredient with no CosIng function has no monograph, because there would be nothing to say about it.</p>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.25rem; margin-bottom: 3rem;">
            {cards}
        </div>
    </main>

    <footer style="background: #111318; border-top: 1px solid #232838; padding: 2rem 0; text-align: center; font-size: 0.85rem; color: #64748B; margin-top: auto;">
        <div class="container">
            <p>INCIDB · snapshot {claims['snapshot']} · counts generated from the build report</p>
            <p style="margin-top: 0.5rem;"><a href="/schema" style="color: #38BDF8; text-decoration: none;">Schema Specification</a> · <a href="/LICENSE" style="color: #38BDF8; text-decoration: none;">License Terms</a> · <a href="/documentation" style="color: #38BDF8; text-decoration: none;">Documentation</a></p>
            <p style="margin-top: 0.5rem; font-size: 0.78rem;">Product data © Open Beauty Facts contributors (ODbL v1.0). Ingredient enrichment contains data from the European Commission CosIng database.</p>
        </div>
    </footer>
</body>
</html>"""

    with open(filepath, mode='w', encoding='utf-8') as f:
        f.write(page)


def main():
    os.makedirs(LANDING_DIR, exist_ok=True)

    # Regenerating is authoritative: stale monographs from an earlier schema
    # must not survive as live URLs.
    for existing in os.listdir(LANDING_DIR):
        if existing.endswith(".html"):
            os.remove(os.path.join(LANDING_DIR, existing))

    claims = load_claims()
    ingredients, products, prod_ing = load_data()
    print(f"Loaded {len(ingredients)} sample ingredients and {len(products)} sample products.")

    buckets = {hub_key: [] for hub_key, _, _, _ in HUBS}
    hub_meta = {hub_key: (hub_name, hub_file) for hub_key, hub_name, hub_file, _ in HUBS}

    generated_urls = []
    skipped = 0

    for ing in ingredients:
        hub_info = categorize_ingredient(function_list(ing))
        if hub_info is None:
            skipped += 1
            continue
        hub_key, hub_name, hub_file = hub_info
        p_list = prod_ing.get(field(ing, 'ingredient_id'), [])
        filename = generate_monograph(ing, p_list, hub_info, claims)
        buckets[hub_key].append({'ingredient': ing, 'filename': filename})
        generated_urls.append((f"{BASE_URL}/landing/{filename[:-5]}", "0.8", "monthly"))

    print(f"Skipped {skipped} ingredients with no publishable CosIng function.")

    for hub_key, (hub_name, hub_file) in hub_meta.items():
        ing_list = buckets[hub_key]
        if not ing_list:
            print(f"Hub {hub_file} has no ingredients — not generated.")
            continue
        generate_hub(hub_name, hub_file, ing_list, claims)
        generated_urls.append((f"{BASE_URL}/landing/{hub_file[:-5]}", "0.9", "weekly"))
        print(f"Generated hub {hub_file} ({len(ing_list)} monographs)")

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    sitemap_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    core_pages = [
        (BASE_URL + "/", "1.0", "weekly"),
        (BASE_URL + "/schema", "0.8", "monthly"),
        (BASE_URL + "/documentation", "0.8", "monthly"),
    ]

    for url, prio, freq in core_pages + sorted(generated_urls):
        sitemap_lines.append("  <url>")
        sitemap_lines.append(f"    <loc>{url}</loc>")
        sitemap_lines.append(f"    <lastmod>{now_utc}</lastmod>")
        sitemap_lines.append(f"    <changefreq>{freq}</changefreq>")
        sitemap_lines.append(f"    <priority>{prio}</priority>")
        sitemap_lines.append("  </url>")

    sitemap_lines.append("</urlset>")

    with open(SITEMAP_PATH, mode='w', encoding='utf-8') as f:
        f.write("\n".join(sitemap_lines) + "\n")

    print(f"Sitemap written to {SITEMAP_PATH} with {len(core_pages) + len(generated_urls)} entries.")


if __name__ == "__main__":
    main()
