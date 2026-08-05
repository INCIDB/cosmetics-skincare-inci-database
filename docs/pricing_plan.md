# INCIDB Pricing & Access Plans

INCIDB is a normalized Skincare & Cosmetics INCI database built from public regulatory and open-data sources (EU CosIng, FDA MoCRA, NLM DailyMed, K-Beauty MFDS, and Open Beauty Facts).

> **Licensing:** The dataset is derived from Open Beauty Facts and is licensed under the **Open Database License (ODbL) v1.0** — you may use and redistribute it, including commercially, with **attribution** and **share-alike**. The plans below are **not** a license to the data (which is already open); they cover optional **hosted delivery, ready-to-query formats, incremental updates, and support**, tailored for beauty tech startups, research institutions, e-commerce retailers, and enterprise AI developers.

---

## Comparative Tier Matrix

| Feature / Metric | Free Sample | One-Time Core ($49) | One-Time Full ($99) |
| :--- | :---: | :---: | :---: |
| **Brands Catalog** | 9 brands | 5,994 brands | 5,994 brands |
| **Cosmetic Formulations** | 10 products | 19,645 products | 19,645 products |
| **Canonical INCI Compounds** | 130 ingredients | 44,816 ingredients | 44,816 ingredients |
| **Relational Composition Junctions** | 191 mappings | 323,730 mappings | 323,730 mappings |
| **EU CosIng Functional Categories** | Referenced | ✅ Yes | ✅ Yes |
| **US FDA MoCRA Contact Allergens** | Referenced | ✅ Yes | ✅ Yes |
| **Comedogenic & Fungal-Acne Flags** | Referenced | ❌ No | ✅ Yes |
| **CAS Registry Mapping** | Referenced | ✅ Yes | ✅ Yes |
| **NLM DailyMed Clinical Dermatology** | Referenced | ❌ No | ✅ Yes |
| **Pipe-Delimited CSV Format (`\|`)** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Apache Parquet Format (`pyarrow`)** | Preview only | ❌ No | ✅ Yes |
| **Updates Frequency** | Static | One-time snapshot | One-time snapshot |
| **Support & Delivery Scope** | Self-serve | Single App / Site | Multi-App / Enterprise |

---

## Detailed Tier breakdown

### 1. Free Sample (`$0`)
* **Best for:** Developers evaluating data schema and integration pipelines before purchase.
* **Includes:** a coherent sample slice (10 products with their full ingredient lists, plus referenced ingredients & brands) (`brands.csv`, `products.csv`, `ingredients.csv`, `product_ingredients.csv`) and Parquet previews under `samples/`.
* **License:** Data under ODbL v1.0 (attribution + share-alike) — free for any use, including commercial.

### 2. One-Time Core (`$49 USD`) — [instant Stripe checkout](https://buy.stripe.com/aFa5kEcVybjg37tbeE3840b)
* **Best for:** Indie mobile apps, small e-commerce catalogs, and basic ingredient scanner tools.
* **Includes:** Complete CSV dataset (`brands.csv`, `products.csv`, `ingredients.csv`, `product_ingredients.csv`) covering all 19,645 formulations and 44,816 canonical INCI names, with CosIng functional categories and FDA MoCRA allergen flags. The `comedogenic_rating` and `is_fungal_acne_trigger` columns are Full-tier only.
* **Format:** UTF-8 Pipe-delimited CSV (`|`).
* **Data license:** ODbL v1.0 (attribution + share-alike) — the data is open. **Plan includes:** hosted CSV delivery + integration support for 1 production application.

### 3. One-Time Full Database (`$99 USD`) — [instant Stripe checkout](https://buy.stripe.com/6oU00k6xagDAazV2I83840c)
* **Best for:** AI/ML teams, dermatological research labs, and serious beauty platforms needing full ingredient enrichment.
* **Includes:** Everything in Core + full Apache Parquet datasets (`.parquet`) + complete enrichment fields (CosIng functional categories, comedogenic & fungal-acne flags, NLM DailyMed OTC mappings, FDA MoCRA allergen/warning flags).
* **Format:** Both CSV (`|`) and high-performance Apache Parquet (`pyarrow`).
* **Data license:** ODbL v1.0 (attribution + share-alike) — the data is open. **Plan includes:** priority delivery (CSV + Parquet) + support for up to 3 production apps or research pipelines.
