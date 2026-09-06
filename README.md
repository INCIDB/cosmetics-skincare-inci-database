# INCIDB — The Skincare & Cosmetics INCI Database

[![Live Portal](https://img.shields.io/badge/Live_Portal-incidb.dataengineered.io-0080d0?style=flat-square)](https://incidb.dataengineered.io/)
[![License](https://img.shields.io/badge/License-ODbL_v1.0-008080?style=flat-square)](https://opendatacommons.org/licenses/odbl/1-0/)
[![Products](https://img.shields.io/badge/Products-18,583-0080d0?style=flat-square)](https://incidb.dataengineered.io/schema)
[![INCI names](https://img.shields.io/badge/INCI_names-46,973-d03030?style=flat-square)](https://incidb.dataengineered.io/schema)
[![Brands](https://img.shields.io/badge/Brands-5,926-800080?style=flat-square)](https://incidb.dataengineered.io/schema)
[![Composition links](https://img.shields.io/badge/Composition_links-318,758-60a020?style=flat-square)](https://incidb.dataengineered.io/schema)
[![Name map rows](https://img.shields.io/badge/Name_map_rows-55,426-e06020?style=flat-square)](https://incidb.dataengineered.io/schema)
[![Snapshot](https://img.shields.io/badge/Snapshot-2026.09-7020d0?style=flat-square)](https://incidb.dataengineered.io/)

> **Live portal, interactive schema & free sample:** [https://incidb.dataengineered.io/](https://incidb.dataengineered.io/)

A normalised, relational snapshot of what is actually printed on cosmetic
ingredient labels: **18,583 products**, **5,926 brands**, **46,973 distinct
canonical INCI names**, **318,758 ordered product→ingredient links**, and the
**55,426-row `ingredient_name_map`** that shows how every raw label token was
resolved to a canonical name.

Product, brand and composition data come from **Open Beauty Facts** (ODbL).
Ingredient enrichment — functions, CAS/EC numbers, chemical descriptions,
Annex II–VI membership, restrictions — comes from the **European Commission
CosIng** inventory, joined on exact canonical name. Nothing is inferred,
filled in, or defaulted: where a source has no value, the column is `NULL`.

Shipped as pipe-delimited UTF-8 CSV (`|`) and Apache Parquet.

---

## What is measured (snapshot 2026.09)

| Table | Rows | What it is |
| :--- | ---: | :--- |
| `products` | 18,583 | One row per Open Beauty Facts product: name, brand FK, EAN, category, raw label text |
| `brands` | 5,926 | Canonical brand identities |
| `ingredients` | 46,973 | Distinct canonical INCI names, plus their CosIng enrichment where CosIng lists them |
| `product_ingredients` | 318,758 | Ordered composition links (`position_index` = label order) |
| `ingredient_name_map` | 55,426 | Raw label token → canonical name, with the resolution `method` and a confidence |

### Enrichment coverage — stated two ways, honestly

CosIng is a finite regulatory inventory; a real-world label corpus contains
far more distinct strings than any inventory lists (botanical variants,
multilingual spellings, marketing tokens, one-off blends). So coverage looks
very different depending on what you count:

| Column | Share of the 46,973 distinct names | Share of the 318,758 label occurrences |
| :--- | ---: | ---: |
| CosIng match (any) | 11.0% | **82.5%** |
| `functions` | 10.9% | **81.5%** |
| `cas_number` | 8.3% | **76.4%** |
| `chemical_description` | 8.5% (3,966 distinct values) | — |

Read it like this: **most distinct names in the long tail are not in CosIng,
but most of the ingredient slots on an actual product label are.** If you are
building an ingredient scanner or a formulation model, the second column is
the one that governs what your users see. If you are building a chemical
reference, the first column is the honest ceiling. Both are printed here so
you can decide before you pay.

### Flags and ratings — small, cited, and `NULL` everywhere else

* **`is_common_allergen` — 99 flagged names.** The EU Annex III fragrance
  allergen list (Regulation (EC) 1223/2009 as amended by Regulation (EU)
  2023/1545), matched on exact canonical name. `allergen_source` records the
  list. The US FDA has not yet published its MoCRA fragrance-allergen list,
  so no US flag exists in this dataset.
* **`comedogenic_rating` — 145 ingredients rated 0–5.** Transcribed from
  Fulton JE Jr., *Comedogenicity and irritancy of commonly used ingredients
  in skin care products*, J Soc Cosmet Chem 1989;40:321–333 (Table I).
  `NULL` for every ingredient the paper does not cover.
* **`is_fungal_acne_trigger` — 270 flags.** A rule-derived heuristic, not a
  measured property: C11–C24 fatty acids and their esters, and polysorbates
  20/40/60/80, applied only to CosIng-matched ingredients. Basis: Saunte et
  al. 2020 (DOI 10.3389/fcimb.2020.00112) and Liebregts et al. 2025 (DOI
  10.1093/femsyr/foaf043). Treat it as a filter, never as a finding.

`rating_source` carries the per-row citation, so every non-`NULL` value is
traceable to the work it came from.

---

## Canonicalisation, and why the name map ships with the data

Raw label text is messy: HTML entities, stray punctuation, percentages,
parenthetical synonyms, slash variants, run-together fragments. Every raw
token is resolved to a canonical INCI name by an explicit, ordered method,
and the method used is recorded per row in `ingredient_name_map.method`:

| `method` | What it means |
| :--- | :--- |
| `exact` | The cleaned token is already a CosIng inventory name |
| `cleaned` | Resolved after entity decoding / character stripping / whitespace collapse |
| `typo_map` | Resolved via a small, explicit typo table |
| `percent_stripped` | A declared percentage was removed (`GLYCERIN 5%`) |
| `paren_stripped` | A parenthetical was removed (`AQUA (WATER)`) |
| `synonym_map` | Resolved via an explicit synonym table |
| `slash_variant` | A slash-joined multilingual variant (`WATER/EAU/AQUA`) |
| `split` | A run-together token split into two names, both of which matched |
| `unresolved` | No canonical match — kept verbatim, flagged, never guessed |

`unresolved` is the largest bucket by distinct name and a small one by label
occurrence — the same long-tail effect as the coverage table above. Shipping
the map means you can audit or override any decision the pipeline made
instead of taking it on trust.

---

## Free sample

[`samples/incidb_free_samples.zip`](samples/incidb_free_samples.zip) — the
same five tables, the same columns, as CSV and Parquet:

* **200 products** spanning all **15** product categories, with their brands,
  their **1,075** referenced ingredients, all their composition links, and
  the name-map rows for those ingredients.
* Selection is disclosed and reproducible
  ([`scripts/make_sample.py`](scripts/make_sample.py)): a product is
  *eligible* when at least 80% of its linked ingredients are CosIng-matched;
  the draw is stratified across categories **on that eligible pool**, seeded,
  with a minimum of one product per category.
* That rule biases the sample toward products with longer, better-resolved
  ingredient lists — i.e. **the sample looks better than the corpus average**.
  The corpus-wide numbers in the table above are the ones to plan against.

---

## INCIDB Complete — $79 one-time

One product. Everything measured above, both formats, instant download.

| | INCIDB Complete |
| :--- | :--- |
| Price | **$79** one-time |
| Tables | All 5 (`products`, `brands`, `ingredients`, `product_ingredients`, `ingredient_name_map`) |
| Formats | Pipe-delimited CSV (`\|`) **and** Apache Parquet |
| Enrichment | Every CosIng column, allergen flags, authored ratings — at the coverage stated above |
| Extras | `build_report.json` (per-column fill rates and source hashes), data dictionary, licence |
| Delivery | Stripe checkout, instant download |
| Updates | One-time snapshot (2026.09) |

👉 [Buy INCIDB Complete](https://buy.stripe.com/REPLACE-WITH-INCIDB-COMPLETE-LINK) ·
[pricing details](docs/pricing_plan.md)

What you are paying for is the engineering: a corpus of raw label strings
turned into normalised, canonicalised, joined, measured tables, delivered
ready to query. **You are not paying for exclusive rights to the data** — the
product data is ODbL and stays ODbL (see *Licence* below).

---

## Quick start

```python
import pandas as pd
import pyarrow.parquet as pq

ingredients = pq.read_table("ingredients.parquet").to_pandas()
links = pq.read_table("product_ingredients.parquet").to_pandas()

# Coverage on YOUR slice, weighted the way it actually matters:
merged = links.merge(ingredients, on="ingredient_id", how="left")
print(merged["functions"].notna().mean())   # share of label slots with a CosIng function

# EU Annex III fragrance allergens
allergens = ingredients[ingredients["is_common_allergen"] == 1]

# Audit how a raw label token was resolved
name_map = pd.read_csv("ingredient_name_map.csv", sep="|", dtype=str)
print(name_map[name_map["raw_name"].str.contains("AQUA", na=False)][["raw_name", "canonical_name", "method"]])
```

```python
import duckdb

duckdb.query("""
    SELECT f.function, COUNT(*) AS label_slots
    FROM 'product_ingredients.parquet' pi
    JOIN 'ingredients.parquet' i USING (ingredient_id)
    CROSS JOIN UNNEST(string_split(i.functions, ';')) AS f(function)
    WHERE i.functions IS NOT NULL
    GROUP BY 1 ORDER BY 2 DESC LIMIT 10
""").show()
```

---

## Use cases

* **Ingredient scanner apps** — resolve a scanned label to canonical names via
  `ingredient_name_map`, then surface CosIng functions and EU Annex III
  allergen flags for the slots you can resolve.
* **Formulation and recommender models** — 318,758 ordered links give you
  position-weighted composition vectors across 18,583 products.
* **Retail and marketplace enrichment** — attach functions and restrictions to
  product pages, with `NULL` where nothing is known rather than a guess.
* **Regulatory and research work** — Annex II–VI membership per ingredient,
  plus the raw→canonical audit trail the join was built on.

---

## Documentation

* [DATA_DICTIONARY.md](DATA_DICTIONARY.md) — every column, its source, its
  measured fill rate, and the method notes.
* [Live schema](https://incidb.dataengineered.io/schema) — the same reference on the web.
* [docs/pricing_plan.md](docs/pricing_plan.md) — what the $79 covers.
* [claims.json](claims.json) — the numbers on this page, generated from the
  build report by [`scripts/render_claims.py`](scripts/render_claims.py) and
  enforced by a test. If the copy and the corpus ever disagree, the build fails.

---

## Licence & attribution

* **Product, brand and composition data:** derived from
  [Open Beauty Facts](https://world.openbeautyfacts.org/) under the
  [Open Database License (ODbL) v1.0](https://opendatacommons.org/licenses/odbl/1-0/).
  Free to use and redistribute, including commercially, with **attribution**
  ("Product data © Open Beauty Facts contributors") and **share-alike**.
* **Ingredient enrichment:** contains data from the European Commission
  CosIng database, reused under the Commission's public-sector information
  reuse policy, with attribution.
* **Schema & documentation:** CC BY 4.0.
* Provided **as-is, without warranty**. The flags and ratings are
  informational; they are not medical, safety or regulatory-compliance advice.
