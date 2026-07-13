# INCIDB — The Skincare & Cosmetics INCI Database

[![Live Portal](https://img.shields.io/badge/Live_Portal-cosmetics--skincare--database.pages.dev-0080d0?style=flat-square)](https://cosmetics-skincare-database.pages.dev/)
[![License](https://img.shields.io/badge/License-ODbL_v1.0-008080?style=flat-square)](https://opendatacommons.org/licenses/odbl/1-0/)
[![Formulations](https://img.shields.io/badge/Formulations-19%2C645-0080d0?style=flat-square)](https://cosmetics-skincare-database.pages.dev/schema.html)
[![INCI Compounds](https://img.shields.io/badge/INCI_Compounds-44%2C816-d03030?style=flat-square)](https://cosmetics-skincare-database.pages.dev/schema.html)
[![Global Brands](https://img.shields.io/badge/Global_Brands-5%2C994-800080?style=flat-square)](https://cosmetics-skincare-database.pages.dev/schema.html)
[![Relational Pairs](https://img.shields.io/badge/Relational_Pairs-323%2C730-60a020?style=flat-square)](https://cosmetics-skincare-database.pages.dev/schema.html)
[![CSV Files](https://img.shields.io/badge/CSV_Files-4-e06020?style=flat-square)](https://cosmetics-skincare-database.pages.dev/samples/incidb_free_samples.zip)
[![Parquet Files](https://img.shields.io/badge/Parquet_Files-4-7020d0?style=flat-square)](https://cosmetics-skincare-database.pages.dev/samples/incidb_free_samples.zip)
[![Data Sources](https://img.shields.io/badge/Data_Sources-5-008080?style=flat-square)](https://cosmetics-skincare-database.pages.dev/#registries)

> **🌐 Live Database Portal, Interactive Schema & Free Samples:** [https://cosmetics-skincare-database.pages.dev/](https://cosmetics-skincare-database.pages.dev/)

Comprehensive, multi-source skincare and cosmetic formulation database unifying **19,645 commercial products**, **44,816 canonical INCI ingredients**, **5,994 global brands**, and **323,730 relational composition mappings**.

Normalized from public regulatory and open-data sources: **EU CosIng** functional categories, **US FDA MoCRA** contact-allergen flags, **NLM DailyMed** clinical OTC labels, **K-Beauty MFDS** standards, and the **Open Beauty Facts** product corpus (ODbL).

Available in structured **pipe-delimited CSV (`|`)** and high-performance **Apache Parquet (`pyarrow`)** formats for AI developers, beauty app founders, e-commerce retailers, and dermatological researchers.

---

## Available Datasets

All datasets are normalized, sanitized (zero embedded linebreaks), and audited for 1-to-1 physical line correspondence.

| Dataset | Records | Fields | Description | Formats |
| :--- | :---: | :---: | :--- | :---: |
| **`products`** | 19,645 | 8 | Complete commercial product formulations, prices, barcodes, and raw ingredient listings | CSV / Parquet |
| **`ingredients`** | 44,816 | 10 | Canonical INCI nomenclature with CAS numbers, CosIng functional categories, comedogenic ratings, MoCRA allergen flags, and FDA warnings | CSV / Parquet |
| **`brands`** | 5,994 | 2 | Canonical brand identities (`brand_id`, `name`) | CSV / Parquet |
| **`product_ingredients`** | 323,730 | 4 | Exact formulation junction mappings preserving label concentration order (position index) | CSV / Parquet |

See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for full field definitions and sample values.

---

## Key Regulatory & Open-Data Sources

* **EU Commission CosIng Registry:** Official European functional categories and CAS registry numbers (`69-72-7` Salicylic Acid, `122-99-6` Phenoxyethanol).
* **US FDA MoCRA Allergen Registry:** Flags mandatory Modernization of Cosmetics Regulation Act contact dermatitis allergens (*Linalool, Limonene, Geraniol, Eugenol, Coumarin*).
* **NLM DailyMed Clinical OTC:** Topical dermatological drug labels from the US National Library of Medicine.
* **K-Beauty MFDS Standards:** Functional whitening, anti-wrinkle, and barrier-repair standards from Korean cosmetic regulations.
* **Open Beauty Facts:** Community product corpus (barcodes, brands, ingredient lists) under the Open Database License (ODbL). Product data © Open Beauty Facts contributors.

---

## Proof & Audit Verification Results

All dataset releases undergo automated audit verification to ensure relational consistency and zero string anomalies across the flat files:
* **Zero Linebreak Corruption:** Stripped all unescaped carriage returns (`\r`) and multiline linebreaks (`\n`) inside string fields to guarantee exact 1-to-1 physical row parity (`wc -l` exactly matches record counts).
* **Parquet Compression Ratio:** 82% storage reduction compared to raw CSV using Apache PyArrow snappy/zstd compression.
* **Schema Auditing:** Verified complete foreign key integrity across all 323,730 relational mappings linking `products.product_id` to `ingredients.ingredient_id`.

---

## Free Parquet & CSV Samples Included

A free preview is bundled as [`samples/incidb_free_samples.zip`](samples/incidb_free_samples.zip) — a small **coherent slice** (10 products with their full ingredient lists, plus the referenced ingredients and brands) so joins and the recommender work out of the box:

* `products.csv`, `ingredients.csv`, `brands.csv`, `product_ingredients.csv` (pipe-delimited)
* `products_sample.parquet`, `ingredients_sample.parquet` (Parquet previews)

See [SPEC.md](SPEC.md) for the Parquet schema and [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for full field definitions.

---

## Tier Availability & Pricing

The dataset is **open (ODbL)** — free to use and redistribute with attribution and share-alike. Paid plans cover optional **hosted delivery, ready-to-query formats, updates, and support**, not exclusive rights to the data. Checkout is self-serve via Stripe with instant download after payment:

| Plan | Price | CSV Core | Parquet Datasets | Enrichment Fields | Delivery & Support |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Free Sample** | `$0` | Coherent slice | Sample preview | Referenced | Self-serve |
| **One-Time Core** | [`$49`](https://buy.stripe.com/aFa5kEcVybjg37tbeE3840b) | ✅ Yes | ❌ No | CosIng functions + MoCRA allergens | Single app |
| **One-Time Full** | [`$99`](https://buy.stripe.com/6oU00k6xagDAazV2I83840c) | ✅ Yes | ✅ Yes | + comedogenic & fungal-acne flags | Multi-app / priority |

👉 **Explore the interactive live preview at our Landing Page (`index.html`) or [docs/pricing_plan.md](docs/pricing_plan.md).**

---

## Quick Start — Reading Datasets

### Python (Pandas & PyArrow)
```python
import pyarrow.parquet as pq
import pandas as pd

# 1. Read commercial products
products = pq.read_table('products.parquet').to_pandas()
print(f"Loaded {len(products):,} formulations across {products['brand_id'].nunique():,} brands.")

# 2. Read canonical INCI ingredients
ingredients = pq.read_table('ingredients.parquet').to_pandas()

# 3. Filter for FDA MoCRA contact allergens
allergens = ingredients[ingredients['is_common_allergen'] == 1]
print(f"Identified {len(allergens)} MoCRA contact allergens.")

# 4. Read CSV exports with exact pipe delimiter
csv_products = pd.read_csv('products.csv', sep='|', dtype=str)
```

### SQL (DuckDB In-Memory)
```python
import duckdb

# Query top brands by formulation volume directly from Parquet
query = """
SELECT b.name AS brand_name, COUNT(p.product_id) AS total_products
FROM 'products.parquet' p
JOIN 'brands.parquet' b ON p.brand_id = b.brand_id
GROUP BY b.name
ORDER BY total_products DESC
LIMIT 5;
"""
print(duckdb.query(query).to_df())
```

---

## Use Cases

* **Ingredient Scanner Apps (Yuka / ThinkDirty competitors):** Parse raw barcode scans (`barcode_ean`) into MoCRA contact-allergen flags, comedogenic scores (`comedogenic_rating`), and fungal-acne alerts.
* **Generative AI Formulation Advisors:** Fine-tune LLMs on 320,000+ real-world product–ingredient pairings and label position indexes (`position_index`).
* **E-Commerce Retailers & Marketplaces:** Enrich product detail pages with automated allergen warnings, vegan badges, and clean-beauty filters.
* **Dermatology & Clinical Research:** Conduct population-scale epidemiological studies comparing cosmetic preservative usage against contact dermatitis rates.

---

## Documentation & Architecture

* [DATA_DICTIONARY.md](DATA_DICTIONARY.md) — Full column descriptions and sample data.
* [SPEC.md](SPEC.md) — Apache Parquet compression and PyArrow schema.
* [docs/pricing_plan.md](docs/pricing_plan.md) — Pricing & access plans (data is ODbL; plans cover delivery + support).
* [Live schema & interactive explorer](https://cosmetics-skincare-database.pages.dev/schema.html) — full column reference and query demos.

---

## License & Support

* **Data (all tables & samples):** Open Database License (**ODbL v1.0**) — product data © Open Beauty Facts contributors; free to use and redistribute with **attribution** and **share-alike**. https://opendatacommons.org/licenses/odbl/1-0/
* **Schema & documentation:** CC BY 4.0.
* **Paid plans** cover hosted delivery, ready-to-query formats, updates, and support — *not* exclusive rights to the data (see [docs/pricing_plan.md](docs/pricing_plan.md)).
* Provided **as-is, without warranty**; enrichment flags are not medical or safety advice.
