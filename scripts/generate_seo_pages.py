#!/usr/bin/env python3
"""
generate_seo_pages.py — INCIDB Static INCI Monograph & Directory Hub Generator
Generates standalone SEO diagnostic monograph pages (`landing/*.html`), category hubs,
and a fully automated `sitemap.xml` with timezone-safe UTC timestamps.
"""

import os
import re
import csv
from datetime import datetime, timezone

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(ROOT_DIR, "samples")
LANDING_DIR = os.path.join(ROOT_DIR, "landing")
SITEMAP_PATH = os.path.join(ROOT_DIR, "sitemap.xml")

BASE_URL = "https://cosmetics-skincare-database.pages.dev"

def clean_slug(name):
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', name.lower()).strip('_')
    return slug or "unknown"

def load_data():
    ingredients = []
    products = {}
    prod_ing = {}

    ing_path = os.path.join(SAMPLES_DIR, "ingredients.csv")
    if os.path.exists(ing_path):
        with open(ing_path, mode='r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f, delimiter='|')
            for row in reader:
                ingredients.append(row)

    prod_path = os.path.join(SAMPLES_DIR, "products.csv")
    if os.path.exists(prod_path):
        with open(prod_path, mode='r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f, delimiter='|')
            for row in reader:
                products[row.get('product_id')] = row

    pi_path = os.path.join(SAMPLES_DIR, "product_ingredients.csv")
    if os.path.exists(pi_path):
        with open(pi_path, mode='r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f, delimiter='|')
            for row in reader:
                iid = row.get('ingredient_id')
                pid = row.get('product_id')
                pos = row.get('position_index', '?')
                if iid not in prod_ing:
                    prod_ing[iid] = []
                if pid in products:
                    prod_ing[iid].append({
                        'product_name': products[pid].get('name', 'Formulation #'+pid),
                        'brand_id': products[pid].get('brand_id', 'N/A'),
                        'category': products[pid].get('category', 'Cosmetic'),
                        'position': pos
                    })

    return ingredients, products, prod_ing

def categorize_ingredient(primary_func):
    func = (primary_func or "").lower()
    if any(k in func for k in ['preservative', 'antimicrobial']):
        return ('preservatives', 'Preservatives & Antimicrobial Stabilizers', 'preservatives.html')
    elif any(k in func for k in ['solvent', 'viscosity']):
        return ('solvents', 'Solvents & Viscosity Controlling Agents', 'solvents.html')
    elif any(k in func for k in ['exfoliant', 'humectant', 'active']):
        return ('active_treatments', 'Active Treatments, Exfoliants & Humectants', 'active_treatments.html')
    else:
        return ('skin_conditioning', 'Skin-Conditioning Agents & Emollients', 'skin_conditioning.html')

def generate_monograph(ing, prod_list, hub_info):
    iid = ing.get('ingredient_id', '0')
    inci_name = ing.get('inci_name', 'UNKNOWN INCI').strip()
    cas = ing.get('cas_number', '').strip() or "Unassigned / Mixture"
    common = ing.get('common_name', '').strip() or inci_name
    func = ing.get('primary_function', 'Skin-Conditioning Agent').strip()
    comedo = ing.get('comedogenic_rating', '0.0').strip()
    allergen = (ing.get('is_common_allergen', '0').strip() == '1')
    fungal = (ing.get('is_fungal_acne_trigger', '0').strip() == '1')
    desc = ing.get('description', 'Standard cosmetic ingredient registered in INCI catalog.').strip()
    warning = ing.get('fda_warning', '').strip()

    slug = clean_slug(inci_name)
    filename = f"inci_{iid}_{slug}.html"
    filepath = os.path.join(LANDING_DIR, filename)

    hub_key, hub_name, hub_file = hub_info

    allergen_badge = """<span style="background: rgba(244, 63, 94, 0.15); color: #F43F5E; border: 1px solid #F43F5E; padding: 0.3rem 0.75rem; border-radius: 99px; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; font-weight: 600;">FDA MoCRA Contact Allergen Flagged</span>""" if allergen else """<span style="background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid #10B981; padding: 0.3rem 0.75rem; border-radius: 99px; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; font-weight: 600;">No MoCRA Allergen Alert</span>"""

    fungal_badge = """<span style="background: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid #F59E0B; padding: 0.3rem 0.75rem; border-radius: 99px; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;">Malassezia (Fungal Acne) Trigger</span>""" if fungal else """<span style="background: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid #38BDF8; padding: 0.3rem 0.75rem; border-radius: 99px; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;">Fungal Acne Safe</span>"""

    warning_block = f"""
    <div style="background: rgba(245, 158, 11, 0.12); border-left: 4px solid #F59E0B; padding: 1.25rem; border-radius: 0 8px 8px 0; margin: 1.5rem 0;">
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #F59E0B; font-weight: 600; text-transform: uppercase; margin-bottom: 0.35rem;">Regulatory / Clinical Alert</div>
        <div style="color: #F8FAFC; font-size: 0.95rem;">{warning}</div>
    </div>
    """ if warning and "No warning required" not in warning else ""

    prod_rows = ""
    if prod_list:
        for p in prod_list[:8]:
            prod_rows += f"""
            <tr style="border-bottom: 1px solid #232838;">
                <td style="padding: 0.75rem; color: #F8FAFC; font-weight: 500;">{p['product_name']}</td>
                <td style="padding: 0.75rem; color: #94A3B8;">{p['category']}</td>
                <td style="padding: 0.75rem; color: #38BDF8; font-family: 'JetBrains Mono', monospace;">Rank #{p['position']}</td>
            </tr>
            """
    else:
        prod_rows = """
        <tr>
            <td colspan="3" style="padding: 1rem; color: #64748B; text-align: center;">No sample formulations indexed for this specific INCI compound in the free preview partition. Available in complete 19,645-product dataset.</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{inci_name} — INCI Composition, CAS Number & CosIng Safety Profile</title>
    <meta name="description" content="Detailed INCI chemical profile for {inci_name} (CAS: {cas}). Functional role: {func}. Comedogenic rating: {comedo}/5.0. FDA MoCRA contact allergen status and sample formulations.">
    <meta name="keywords" content="{inci_name}, CAS {cas}, {common}, INCI skincare database, {func}, comedogenic rating {comedo}, MoCRA contact allergen, cosmetic chemical specification">
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
        "headline": "INCI Monograph: {inci_name} ({common})",
        "description": "Technical INCI specification, EU CosIng functional category ({func}), CAS registry number ({cas}), and comedogenic profile for {inci_name}.",
        "url": "{BASE_URL}/landing/{filename[:-5]}",
        "author": {{
          "@type": "Organization",
          "name": "INCIDB"
        }},
        "publisher": {{
          "@type": "Organization",
          "name": "INCIDB",
          "logo": {{
            "@type": "ImageObject",
            "url": "{BASE_URL}/favicon.svg"
          }}
        }},
        "about": {{
          "@type": "ChemicalSubstance",
          "name": "{inci_name}",
          "alternateName": "{common}",
          "identifier": "{cas}"
        }}
      }},
      {{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
          {{"@type": "ListItem", "position": 1, "name": "Home", "item": "{BASE_URL}/"}},
          {{"@type": "ListItem", "position": 2, "name": "{hub_name}", "item": "{BASE_URL}/landing/{hub_file[:-5]}"}},
          {{"@type": "ListItem", "position": 3, "name": "{inci_name}", "item": "{BASE_URL}/landing/{filename[:-5]}"}}
        ]
      }}
    ]
    </script>
</head>
<body style="background: #0A0B0E; color: #F8FAFC; font-family: 'Space Grotesk', -apple-system, sans-serif; min-height: 100vh; display: flex; flex-direction: column;">
    <div class="grid-overlay"></div>

    <header style="border-bottom: 1px solid #232838; padding: 1rem 0; background: rgba(10, 11, 14, 0.85); backdrop-filter: blur(10px); position: sticky; top: 0; z-index: 100;">
        <div class="container" style="display: flex; justify-content: space-between; align-items: center;">
            <a href="../" class="logo" style="font-weight: 700; font-size: 1.3rem; color: #F8FAFC; text-decoration: none;">INCIDB</a>
            <nav style="display: flex; gap: 1.5rem; align-items: center;">
                <a href="../#explorer" style="color: #94A3B8; text-decoration: none; font-size: 0.9rem;">Explorer</a>
                <a href="../landing/{hub_file[:-5]}" style="color: #38BDF8; text-decoration: none; font-size: 0.9rem;">{hub_name}</a>
                <a href="../#pricing" class="btn btn-primary" style="padding: 0.5rem 1rem; font-size: 0.85rem;">Get Full Parquet</a>
            </nav>
        </div>
    </header>

    <main class="container" style="flex: 1; padding: 3rem 1rem; max-width: 900px;">
        <div style="margin-bottom: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">
            <a href="../" style="color: #64748B; text-decoration: none;">HOME</a> / 
            <a href="{hub_file}" style="color: #38BDF8; text-decoration: none;">{hub_name.upper()}</a> / 
            <span style="color: #F8FAFC;">{inci_name}</span>
        </div>

        <div style="background: #111318; border: 1px solid #232838; border-radius: 16px; padding: 2.5rem; margin-bottom: 2.5rem; box-shadow: 0 10px 30px -15px rgba(0,0,0,0.7);">
            <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 1.5rem;">
                <div>
                    <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #06B6D4; text-transform: uppercase; letter-spacing: 1px;">Canonical INCI Monograph #{iid}</span>
                    <h1 style="font-size: 2.2rem; line-height: 1.2; margin-top: 0.25rem; color: #F8FAFC;">{inci_name}</h1>
                </div>
                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                    {allergen_badge}
                    {fungal_badge}
                </div>
            </div>

            <p style="font-size: 1.05rem; color: #94A3B8; line-height: 1.7; margin-bottom: 1.75rem;">{desc}</p>

            {warning_block}

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.25rem; background: #161922; border: 1px solid #232838; border-radius: 12px; padding: 1.5rem;">
                <div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #64748B; margin-bottom: 0.25rem;">CAS REGISTRY NUMBER</div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 1.1rem; color: #38BDF8; font-weight: 600;">{cas}</div>
                </div>
                <div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #64748B; margin-bottom: 0.25rem;">COSING PRIMARY FUNCTION</div>
                    <div style="font-size: 1.05rem; color: #F8FAFC; font-weight: 500;">{func}</div>
                </div>
                <div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #64748B; margin-bottom: 0.25rem;">COMEDOGENIC RATING</div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 1.1rem; color: {'#F43F5E' if float(comedo or 0) >= 3 else '#10B981'}; font-weight: 600;">{comedo} / 5.0</div>
                </div>
                <div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #64748B; margin-bottom: 0.25rem;">COMMON SYNONYM</div>
                    <div style="font-size: 1.05rem; color: #94A3B8;">{common}</div>
                </div>
            </div>
        </div>

        <div style="margin-bottom: 2.5rem;">
            <h2 style="font-size: 1.5rem; margin-bottom: 1rem; color: #F8FAFC;">Sample Commercial Formulations with {inci_name}</h2>
            <p style="color: #94A3B8; font-size: 0.92rem; margin-bottom: 1.25rem;">Verified concentration ranks from the free INCIDB sample partition. Full data mapping covers 19,645 commercial formulations.</p>
            
            <div style="background: #111318; border: 1px solid #232838; border-radius: 12px; overflow: hidden;">
                <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.92rem;">
                    <thead>
                        <tr style="background: #161922; border-bottom: 1px solid #232838; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #64748B;">
                            <th style="padding: 0.85rem;">PRODUCT NAME</th>
                            <th style="padding: 0.85rem;">CATEGORY</th>
                            <th style="padding: 0.85rem;">CONCENTRATION RANK</th>
                        </tr>
                    </thead>
                    <tbody>
                        {prod_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <div style="background: #161922; border: 1px solid #232838; border-radius: 16px; padding: 2rem;">
            <h3 style="font-size: 1.3rem; margin-bottom: 0.75rem; color: #F8FAFC;">Query {inci_name} via PyArrow Parquet</h3>
            <p style="color: #94A3B8; font-size: 0.9rem; margin-bottom: 1.25rem;">Filter sub-second high-performance columnar Parquet files across all 19,645 beauty formulations.</p>
            <pre style="background: #0A0B0E; border: 1px solid #232838; padding: 1.25rem; border-radius: 8px; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: #38BDF8; overflow-x: auto; margin-bottom: 1.5rem;"><code>import pyarrow.parquet as pq

# Load normalized INCI ingredients dataset
ingredients = pq.read_table('ingredients.parquet').to_pandas()

# Locate exact compound ID and regulatory flags
target = ingredients[ingredients['inci_name'] == "{inci_name}"]
print(target[['ingredient_id', 'cas_number', 'is_common_allergen']])</code></pre>
            <div style="text-align: right;">
                <a href="../#pricing" class="btn btn-primary" style="padding: 0.75rem 1.5rem; text-decoration: none;">Download Full 19,645-Product Parquet ($99) →</a>
            </div>
        </div>
    </main>

    <footer style="background: #111318; border-top: 1px solid #232838; padding: 2rem 0; text-align: center; font-size: 0.85rem; color: #64748B; margin-top: auto;">
        <div class="container">
            <p>INCIDB Data Engineering Pipeline v1.0.0 · Normalized & Audited July 2026</p>
            <p style="margin-top: 0.5rem;"><a href="/schema" style="color: #38BDF8; text-decoration: none;">Schema Specification</a> · <a href="../LICENSE" style="color: #38BDF8; text-decoration: none;">License Terms</a> · <a href="/documentation" style="color: #38BDF8; text-decoration: none;">Documentation</a></p>
        </div>
    </footer>
</body>
</html>"""

    with open(filepath, mode='w', encoding='utf-8') as f:
        f.write(html)

    return filename


def generate_hub(hub_key, hub_name, hub_file, ing_list):
    filepath = os.path.join(LANDING_DIR, hub_file)

    cards = ""
    for item in ing_list:
        inci = item['ingredient'].get('inci_name', 'Unknown').strip()
        cas = item['ingredient'].get('cas_number', 'N/A').strip() or "N/A"
        func = item['ingredient'].get('primary_function', 'Skin-Conditioning').strip()
        comedo = item['ingredient'].get('comedogenic_rating', '0.0').strip()
        allergen = (item['ingredient'].get('is_common_allergen', '0').strip() == '1')

        flag_tag = """<span style="color: #F43F5E; font-size: 0.75rem; font-family: 'JetBrains Mono', monospace; font-weight: 600;">[MoCRA Alert]</span>""" if allergen else ""

        cards += f"""
        <a href="{item['filename']}" style="display: block; background: #161922; border: 1px solid #232838; border-radius: 10px; padding: 1.25rem; text-decoration: none; transition: border-color 0.2s;" onmouseover="this.style.borderColor='#38BDF8'" onmouseout="this.style.borderColor='#232838'">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #06B6D4;">CAS: {cas}</span>
                {flag_tag}
            </div>
            <h3 style="font-size: 1.1rem; color: #F8FAFC; margin-bottom: 0.35rem;">{inci}</h3>
            <div style="display: flex; justify-content: space-between; font-size: 0.82rem; color: #94A3B8;">
                <span>{func}</span>
                <span style="font-family: 'JetBrains Mono', monospace; color: {'#F43F5E' if float(comedo or 0) >= 3 else '#10B981'};">Comedogenic: {comedo}</span>
            </div>
        </a>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{hub_name} — INCI Cosmetic Ingredient Monographs & Safety Directory</title>
    <meta name="description" content="Comprehensive INCI monograph directory for {hub_name}. Explore CAS registry numbers, comedogenic ratings, MoCRA allergen alerts, and formulation data.">
    <meta name="keywords" content="{hub_name}, INCI ingredient directory, cosmetic chemical monographs, skincare formulations, CAS registry lookup">
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
      "name": "{hub_name} Directory",
      "description": "INCI chemical monographs classified under {hub_name}.",
      "numberOfItems": {len(ing_list)},
      "itemListElement": [
        {{"@type": "ListItem", "position": 1, "name": "Back to Live Explorer", "url": "{BASE_URL}/#explorer"}}
      ]
    }}
    </script>
</head>
<body style="background: #0A0B0E; color: #F8FAFC; font-family: 'Space Grotesk', -apple-system, sans-serif; min-height: 100vh; display: flex; flex-direction: column;">
    <div class="grid-overlay"></div>

    <header style="border-bottom: 1px solid #232838; padding: 1rem 0; background: rgba(10, 11, 14, 0.85); backdrop-filter: blur(10px); position: sticky; top: 0; z-index: 100;">
        <div class="container" style="display: flex; justify-content: space-between; align-items: center;">
            <a href="../" class="logo" style="font-weight: 700; font-size: 1.3rem; color: #F8FAFC; text-decoration: none;">INCIDB</a>
            <nav style="display: flex; gap: 1.5rem; align-items: center;">
                <a href="../#explorer" style="color: #94A3B8; text-decoration: none; font-size: 0.9rem;">Explorer</a>
                <a href="../#pricing" class="btn btn-primary" style="padding: 0.5rem 1rem; font-size: 0.85rem;">Get Full Parquet</a>
            </nav>
        </div>
    </header>

    <main class="container" style="flex: 1; padding: 3rem 1rem; max-width: 1100px;">
        <div style="margin-bottom: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">
            <a href="../" style="color: #64748B; text-decoration: none;">HOME</a> / 
            <span style="color: #38BDF8;">{hub_name.upper()}</span>
        </div>

        <div style="text-align: center; max-width: 800px; margin: 0 auto 3rem auto;">
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #06B6D4; text-transform: uppercase; letter-spacing: 1px;">Category Hub Index</div>
            <h1 style="font-size: 2.5rem; margin-top: 0.35rem; color: #F8FAFC;">{hub_name}</h1>
            <p style="color: #94A3B8; font-size: 1.05rem; margin-top: 0.5rem;">Explore canonical chemical monographs, safety specifications, and sample formulation mappings for {len(ing_list)} verified INCI ingredients.</p>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.25rem; margin-bottom: 3rem;">
            {cards}
        </div>
    </main>

    <footer style="background: #111318; border-top: 1px solid #232838; padding: 2rem 0; text-align: center; font-size: 0.85rem; color: #64748B; margin-top: auto;">
        <div class="container">
            <p>INCIDB Data Engineering Pipeline v1.0.0 · Normalized & Audited July 2026</p>
            <p style="margin-top: 0.5rem;"><a href="/schema" style="color: #38BDF8; text-decoration: none;">Schema Specification</a> · <a href="../LICENSE" style="color: #38BDF8; text-decoration: none;">License Terms</a> · <a href="/documentation" style="color: #38BDF8; text-decoration: none;">Documentation</a></p>
        </div>
    </footer>
</body>
</html>"""

    with open(filepath, mode='w', encoding='utf-8') as f:
        f.write(html)


def main():
    if not os.path.exists(LANDING_DIR):
        os.makedirs(LANDING_DIR, exist_ok=True)

    ingredients, products, prod_ing = load_data()
    print(f"Loaded {len(ingredients)} INCI ingredients and {len(products)} products from sample partition.")

    hubs = {
        'skin_conditioning': ('skin_conditioning', 'Skin-Conditioning Agents & Emollients', 'skin_conditioning.html', []),
        'preservatives': ('preservatives', 'Preservatives & Antimicrobial Stabilizers', 'preservatives.html', []),
        'solvents': ('solvents', 'Solvents & Viscosity Controlling Agents', 'solvents.html', []),
        'active_treatments': ('active_treatments', 'Active Treatments, Exfoliants & Humectants', 'active_treatments.html', [])
    }

    generated_urls = []

    for ing in ingredients:
        func = ing.get('primary_function', '')
        hub_key, hub_name, hub_file = categorize_ingredient(func)
        hub_info = hubs[hub_key][:3]

        iid = ing.get('ingredient_id')
        p_list = prod_ing.get(iid, [])

        filename = generate_monograph(ing, p_list, hub_info)
        hubs[hub_key][3].append({'ingredient': ing, 'filename': filename})
        generated_urls.append((f"{BASE_URL}/landing/{filename[:-5]}", "0.8", "monthly"))

    for hub_key, hub_tuple in hubs.items():
        hk, hname, hfile, ilist = hub_tuple
        generate_hub(hk, hname, hfile, ilist)
        generated_urls.append((f"{BASE_URL}/landing/{hfile[:-5]}", "0.9", "weekly"))
        print(f"Generated Category Hub: {hfile} ({len(ilist)} monographs)")

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    sitemap_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]

    core_pages = [
        (BASE_URL + "/", "1.0", "weekly"),
        (BASE_URL + "/schema", "0.8", "monthly"),
        (BASE_URL + "/documentation", "0.8", "monthly")
    ]

    for url, prio, freq in core_pages + generated_urls:
        sitemap_lines.append("  <url>")
        sitemap_lines.append(f"    <loc>{url}</loc>")
        sitemap_lines.append(f"    <lastmod>{now_utc}</lastmod>")
        sitemap_lines.append(f"    <changefreq>{freq}</changefreq>")
        sitemap_lines.append(f"    <priority>{prio}</priority>")
        sitemap_lines.append("  </url>")

    sitemap_lines.append("</urlset>")

    with open(SITEMAP_PATH, mode='w', encoding='utf-8') as f:
        f.write("\n".join(sitemap_lines) + "\n")

    print(f"Sitemap successfully generated at {SITEMAP_PATH} with {len(core_pages) + len(generated_urls)} entries.")

if __name__ == "__main__":
    main()
