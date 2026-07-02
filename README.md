# INCIDB — The Skincare & Cosmetics INCI Database

[![License: Commercial](https://img.shields.io/badge/License-Commercial%20%2F%20MIT%20Sample-blue.svg)](docs/pricing_plan.md)
[![Data Scale: 19.8k Products](https://img.shields.io/badge/Formulations-19%2C847-brightgreen.svg)](DATA_DICTIONARY.md)
[![Ingredients: 57.1k INCI](https://img.shields.io/badge/INCI%20Compounds-57%2C181-purple.svg)](SPEC.md)
[![Format: CSV & Parquet](https://img.shields.io/badge/Formats-CSV%20%7C%20Parquet-orange.svg)](#quick-start--reading-datasets)

Comprehensive, multi-source skincare and cosmetic formulation database unifying **19,847 commercial products**, **57,181 canonical INCI ingredients**, **5,994 global brands**, and **330,088 relational composition mappings**.

Enriched with clinical safety monographs, contact dermatitis allergens, and toxicology profiles from **8 international regulatory bodies** (EU CosIng, US FDA MoCRA, NLM DailyMed, CIR Expert Panel, EWG Skin Deep, K-Beauty MFDS Standards, Open Beauty Facts, and Prestige Clinical Best-Sellers).

Available in structured **pipe-delimited CSV (`|`)** and high-performance **Apache Parquet (`pyarrow`)** formats for AI developers, beauty app founders, e-commerce retailers, and dermatological researchers.

---

## Available Datasets

All datasets are normalized, sanitized (zero embedded linebreaks), and audited for 1-to-1 physical line correspondence.

| Dataset | Records | Fields | Description | Formats |
| :--- | :---: | :---: | :--- | :---: |
| **`products`** | 19,847 | 8 | Complete commercial product formulations, prices, barcodes, and raw ingredient listings | CSV / Parquet |
| **`ingredients`** | 57,181 | 14 | Canonical INCI chemical nomenclature enriched with EWG hazard scores, CIR verdicts, and FDA warnings | CSV / Parquet |
| **`brands`** | 5,994 | 5 | Global cosmetic brand profiles, country of origin, cruelty-free, and vegan certifications | CSV / Parquet |
| **`product_ingredients`** | 330,088 | 4 | Exact formulation junction mappings preserving label concentration order (position index) | CSV / Parquet |

See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for full field definitions and sample values.

---

## Key Regulatory & Clinical Enrichments

* **EU Commission CosIng Registry:** Official European chemical restrictions and CAS registry numbers (`69-72-7` Salicylic Acid, `122-99-6` Phenoxyethanol).
* **US FDA MoCRA Allergen Registry:** Flags mandatory Modernization of Cosmetics Regulation Act contact dermatitis allergens (*Linalool, Limonene, Geraniol, Eugenol, Coumarin*).
* **EWG Skin Deep Toxicology:** Granular hazard sub-scores highlighting **Carcinogenicity** alerts (`cancer_hazard_flag = 1`) and **Endocrine Disruption** flags (`endocrine_hazard_flag = 1`).
* **CIR Scientific Safety Verdicts:** Official Expert Panel safety conclusions (*"Safe as used"*, *"Safe with qualifications"*) and concentration ceilings (*Retinol max 0.3%*).
* **K-Beauty MFDS Standards:** Functional whitening, anti-wrinkle, and barrier-repair standards from Korean cosmetic regulations.

---

## Free Parquet & CSV Samples Included

This repository includes free preview samples under `samples/` for integration testing and pipeline validation:

* `samples/products.csv` (10 sample formulations)
* `samples/ingredients.csv` (10 sample INCI profiles)
* `samples/brands.csv` (10 sample brands)
* `samples/product_ingredients.csv` (10 sample junction rows)
* `samples/products_sample.parquet` (25 sample formulations in Parquet)
* `samples/ingredients_sample.parquet` (25 sample INCI profiles in Parquet)
* [SPEC.md](SPEC.md) — Apache Parquet technical schema specification.
* [DATA_DICTIONARY.md](DATA_DICTIONARY.md) — Complete data dictionary.

---

## Tier Availability & Pricing

The INCIDB production datasets ship across transparent commercial tiers tailored to your scale:

| Tier | Price | CSV Core | Parquet Datasets | Toxicological Profiles | Updates Frequency |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Free Sample** | `$0` | 10 rows | Sample preview | Referenced | Static preview |
| **One-Time Core** | `$250` | ✅ Yes | ❌ No | Basic INCI | One-time snapshot |
| **One-Time Full** | `$500` | ✅ Yes | ✅ Yes | ✅ Full toxicology | One-time snapshot |
| **Annual Subscription** | `$2,400/yr` | ✅ Yes | ✅ Yes | ✅ Full toxicology | **Bi-weekly releases (26x/yr)** |
| **Lifetime VIP Access** | `$6,000` | ✅ Yes | ✅ Yes | ✅ Full toxicology | **Permanent VIP releases** |

👉 **Explore interactive live preview & purchase data at our Landing Page (`index.html`) or [docs/pricing_plan.md](docs/pricing_plan.md).**

---

## Quick Start — Reading Datasets

### Python (Pandas & PyArrow)
```python
import pyarrow.parquet as pq
import pandas as pd

# 1. Read commercial products
products = pq.read_table('data/exports/parquet/products.parquet').to_pandas()
print(f"Loaded {len(products):,} formulations across {products['brand_id'].nunique():,} brands.")

# 2. Read canonical INCI ingredients
ingredients = pq.read_table('data/exports/parquet/ingredients.parquet').to_pandas()

# 3. Filter for high-hazard or carcinogenic ingredients
hazards = ingredients[ingredients['cancer_hazard_flag'] == 1]
print(f"Identified {len(hazards)} flagged carcinogenic cosmetic ingredients.")

# 4. Read CSV exports with exact pipe delimiter
csv_products = pd.read_csv('data/exports/csv/products.csv', sep='|', dtype=str)
```

### SQL (DuckDB In-Memory)
```python
import duckdb

# Query top brands by formulation volume directly from Parquet
query = """
SELECT b.name AS brand_name, COUNT(p.product_id) AS total_products
FROM 'data/exports/parquet/products.parquet' p
JOIN 'data/exports/parquet/brands.parquet' b ON p.brand_id = b.brand_id
GROUP BY b.name
ORDER BY total_products DESC
LIMIT 5;
"""
print(duckdb.query(query).to_df())
```

---

## Use Cases

* **Ingredient Scanner Apps (Yuka / ThinkDirty competitors):** Parse raw barcode scans (`barcode_ean`) into instant safety ratings, comedogenic scores (`comedogenic_rating`), and fungal acne alerts.
* **Generative AI Formulation Advisors:** Fine-tune LLMs on 330,000+ real-world product ingredient pairings and chemical concentration indexes (`position_index`).
* **E-Commerce Retailers & Marketplaces:** Enrich product detail pages with automated allergen warnings, vegan badges, and clean-beauty filters.
* **Dermatology & Clinical Research:** Conduct population-scale epidemiological studies comparing cosmetic preservative usage against contact dermatitis rates.

---

## Documentation & Architecture

* [DATA_DICTIONARY.md](DATA_DICTIONARY.md) — Full column descriptions and sample data.
* [SPEC.md](SPEC.md) — Apache Parquet compression and PyArrow schema.
* [docs/pricing_plan.md](docs/pricing_plan.md) — Commercial licensing terms and tier comparison.
* [docs/walkthrough.md](docs/walkthrough.md) — Production ingestion pipeline engineering walkthrough.

---

## License & Support

* **Sample Data (`samples/`):** MIT License for evaluation.
* **Full Datasets (`data/exports/`):** Commercial B2B License (see [docs/pricing_plan.md](docs/pricing_plan.md)).
* **Contact & Enterprise Inquiries:** Contact the INCIDB Data Engineering Team.
