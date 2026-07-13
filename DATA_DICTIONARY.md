# INCIDB Data Dictionary & Schema Specification

INCIDB is structured as a normalized relational schema exported into pipe-delimited CSV (`|`) and Apache Parquet formats.

---

## 1. `brands.csv` / `brands.parquet`
Contains canonical brand identities (brand_id, name).

| Field Name | Type | Description | Sample Value |
| :--- | :--- | :--- | :--- |
| `brand_id` | `INTEGER` | Primary key unique identifier | `1` |
| `name` | `STRING` | Standardized commercial brand name | `Laneige` |

---

## 2. `ingredients.csv` / `ingredients.parquet`
Contains 44,816 canonical chemical compounds normalized from public and open regulatory sources (EU CosIng, FDA MoCRA, NLM DailyMed, K-Beauty MFDS standards, and Open Beauty Facts).

| Field Name | Type | Description | Sample Value |
| :--- | :--- | :--- | :--- |
| `ingredient_id` | `INTEGER` | Primary key unique identifier | `1` |
| `inci_name` | `STRING` | International Nomenclature Cosmetic Ingredient name | `DIISOSTEARYL MALATE` |
| `cas_number` | `STRING` | Chemical Abstracts Service registry number | `50-81-7` |
| `common_name` | `STRING` | Plain English common compound name | `Diisostearyl Malate` |
| `primary_function` | `STRING` | Functional category (CosIng taxonomy) | `Skin-Conditioning Agent` |
| `comedogenic_rating` | `FLOAT` | Pore-clogging likelihood scale (`0.0` - `5.0`) — *One-Time Full tier only* | `0.0` |
| `is_common_allergen` | `INTEGER` | FDA MoCRA contact dermatitis allergen (`1`/`0`) | `0` |
| `is_fungal_acne_trigger` | `INTEGER` | Malassezia folliculitis feeding trigger (`1`/`0`) — *One-Time Full tier only* | `0` |
| `description` | `STRING` | Plain-language functional summary | `Standard cosmetic ingredient...` |
| `fda_warning` | `STRING` | US FDA OTC warning monograph | `No warning required` |

---

## 3. `products.csv` / `products.parquet`
Contains 19,645 commercial cosmetic formulations from prestige retailers, K-Beauty brands, and clinical registries.

> **Coverage note:** ~1,300 products have no parseable ingredient declaration (their source label text was empty or unstructured) and therefore have no rows in `product_ingredients`. They are retained for their name/brand/price/barcode metadata.

| Field Name | Type | Description | Sample Value |
| :--- | :--- | :--- | :--- |
| `product_id` | `INTEGER` | Primary key unique identifier | `67455` |
| `brand_id` | `INTEGER` | Foreign key referencing `brands.brand_id` | `46067` |
| `barcode_ean` | `STRING` | Universal GTIN / EAN-13 barcode | `4006381333931` |
| `name` | `STRING` | Full commercial product title | `Good Genes All-In-One Lactic Acid Treatment` |
| `category` | `STRING` | Primary skincare taxonomy category | `Skincare` |
| `retail_price_usd` | `FLOAT` | Retail price in USD | `85.0` |
| `raw_ingredient_text` | `STRING` | Full unbroken ingredient listing from package label | `Botanical Blend [Water/Eau/Aqua...` |
| `created_at` | `STRING` | Ingestion timestamp (ISO 8601) | `2026-07-02T14:01:48Z` |

---

## 4. `product_ingredients.csv` / `product_ingredients.parquet`
Junction table containing 323,730 exact composition mappings preserving ingredient order and concentration index.

| Field Name | Type | Description | Sample Value |
| :--- | :--- | :--- | :--- |
| `product_id` | `INTEGER` | Foreign key referencing `products.product_id` | `67455` |
| `ingredient_id` | `INTEGER` | Foreign key referencing `ingredients.ingredient_id` | `789584` |
| `position_index` | `INTEGER` | 1-indexed order on label (indicates relative concentration) | `1` |
| `concentration_percentage` | `STRING` | Explicit percentage if disclosed, else `'Undisclosed'` | `Undisclosed` |
