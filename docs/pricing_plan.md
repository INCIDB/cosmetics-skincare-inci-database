# INCIDB Commercial Pricing & License Tiers

INCIDB is the industry-standard, multi-language Skincare & Cosmetics INCI Database combining 8 international formulation, clinical, regulatory, and toxicological registries.

We offer transparent, flat-rate data licenses tailored for beauty tech startups, research institutions, e-commerce retailers, and enterprise AI developers.

---

## Comparative Tier Matrix

| Feature / Metric | Free Sample | One-Time Core ($250) | One-Time Full ($500) | Annual Subscription ($2,400/yr) | Lifetime Access ($6,000) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Brands Catalog** | 10 brands | 5,994 brands | 5,994 brands | 5,994+ brands | 5,994+ brands |
| **Cosmetic Formulations** | 10 products | 19,847 products | 19,847 products | 19,847+ products | 19,847+ products |
| **Canonical INCI Compounds** | 15 ingredients | 57,181 ingredients | 57,181 ingredients | 57,181+ ingredients | 57,181+ ingredients |
| **Relational Composition Junctions** | 30 mappings | 330,088 mappings | 330,088 mappings | 330,088+ mappings | 330,088+ mappings |
| **EU CosIng Chemical Registry** | Referenced | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **US FDA MoCRA Contact Allergens** | Referenced | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **EWG Carcinogenic & Endocrine Flags** | Referenced | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| **CIR Scientific Safety Verdicts** | Referenced | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| **NLM DailyMed Clinical Dermatology** | Referenced | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| **Pipe-Delimited CSV Format (`\|`)** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Apache Parquet Format (`pyarrow`)** | Preview only | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| **Updates Frequency** | Static | One-time snapshot | One-time snapshot | Bi-weekly releases (26x/yr) | Permanent VIP Releases |
| **Commercial License Scope** | Internal / Dev | Single App / Site | Multi-App / Enterprise | Unlimited Enterprise | Unlimited Enterprise + Custom |

---

## Detailed Tier breakdown

### 1. Free Sample (`$0`)
* **Best for:** Developers evaluating data schema and integration pipelines before purchase.
* **Includes:** 10 sample records per table across all CSV files (`brands.csv`, `products.csv`, `ingredients.csv`, `product_ingredients.csv`) and Parquet previews under `samples/`.
* **License:** MIT License for evaluation and non-commercial prototyping.

### 2. One-Time Core (`$250 USD`)
* **Best for:** Indie mobile apps, small e-commerce catalogs, and basic ingredient scanner tools.
* **Includes:** Complete CSV dataset (`brands.csv`, `products.csv`, `ingredients.csv`, `product_ingredients.csv`) covering all 19,847 formulations and 57,181 canonical INCI names.
* **Format:** UTF-8 Pipe-delimited CSV (`|`).
* **License:** Perpetual commercial license for 1 production application or web property.

### 3. One-Time Full Database (`$500 USD`)
* **Best for:** AI/ML teams, dermatological research labs, and serious beauty platforms needing clinical safety enrichment.
* **Includes:** Everything in Core + full Apache Parquet datasets (`.parquet`) + complete toxicological profiles (EWG Carcinogenic/Endocrine flags, CIR Scientific Verdicts, NLM DailyMed OTC mappings, FDA MoCRA warning flags).
* **Format:** Both CSV (`|`) and high-performance Apache Parquet (`pyarrow`).
* **License:** Perpetual enterprise commercial license for up to 3 production apps or research pipelines.

### 4. Annual Subscription (`$2,400 USD / year`)
* **Best for:** Fast-growing beauty tech apps, global formulation platforms, and AI formulation advisors requiring live, continuously updated regulatory data.
* **Includes:** Full Parquet & CSV database + automatic bi-weekly releases (new product drops, updated FDA/EU regulatory restrictions, newly published CIR safety verdicts).
* **License:** Unlimited commercial enterprise license across all company products while active.

### 5. Lifetime VIP Access (`$6,000 USD one-time`)
* **Best for:** Established enterprises, major cosmetic conglomerates, and generative AI foundational model builders.
* **Includes:** Perpetual access to all future database releases, custom cross-walk requests (mapping INCI to supplier codes), priority data extraction support, and dedicated SLA.
* **License:** Perpetual, unlimited global enterprise license.
