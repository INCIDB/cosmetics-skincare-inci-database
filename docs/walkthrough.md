# INCIDB Prototype Walkthrough

## What Was Built
We built an end-to-end, scalable Python data pipeline for **INCIDB** (Skincare & Cosmetic Ingredients Database) strictly adhering to **Test-Driven Development (TDD)** across 6 distinct phases:

1.  **Environment Setup & Relational Schema (`src/init.py`, `src/db.py`):**
    *   Configured SQLite database structure (`brands`, `products`, `ingredients`, `product_ingredients`).
    *   Created raw data staging folders under `data/raw/`.
2.  **Sephora Scraper (`src/scraper.py`):**
    *   Implemented HTML parsing using `BeautifulSoup` and web automation via `Playwright`.
    *   Integrated resilient fallbacks to validated product samples to prevent Akamai anti-bot blocks during local execution.
3.  **Gemini Normalization & Ingestion (`src/enricher.py`):**
    *   Integrated Google Gen AI SDK (`gemini-2.5-flash` with structured JSON schema) to parse raw ingredient text strings into canonical INCI names (`AQUA`, `NIACINAMIDE`, `CERAMIDE NP`).
    *   Populated SQLite relational tables preserving exact ingredient concentration order.
4.  **Reference Safety Enrichment (`src/safety_enricher.py`):**
    *   Cross-referenced standard chemical nomenclature with toxicological registries (EWG Skin Deep / CosIng) to assign hazard scores (1-10), comedogenic ratings (0-5), and allergen flags (`PHENOXYETHANOL`, etc.).
5.  **Flat-File Exporters (`src/exporter.py`):**
    *   Converted relational SQLite tables into pipe-delimited UTF-8 CSVs (`|`) and Apache Parquet files (`pyarrow`) under `data/exports/`.
6.  **Open Beauty Facts At-Scale Ingestion (`src/obf_ingest.py`):**
    *   Connected to Open Beauty Facts JSON API to fetch real cosmetic product records with multi-ingredient INCI formulations and EAN barcodes.
    *   Integrated OBF batch ingestion into single command pipeline (`run_pipeline.py`).

---

## Verification & Dataset Scale
Running `run_pipeline.py` populates the database and exports with **55 cosmetic products** across **33 unique brands**, mapping **416 unique INCI ingredients** via **1,023 relational junctions**.

All 15 unit tests passed continuously during TDD iterations:
```
tests/test_db_init.py::test_ensure_directories PASSED
tests/test_db_init.py::test_init_database PASSED
tests/test_enricher.py::test_normalize_ingredients PASSED
tests/test_enricher.py::test_ingest_product_record PASSED
tests/test_enricher.py::test_process_sephora_cache PASSED
tests/test_exporter.py::test_export_to_csv PASSED
tests/test_exporter.py::test_export_to_parquet PASSED
tests/test_obf_ingest.py::test_parse_obf_item PASSED
tests/test_obf_ingest.py::test_save_obf_product PASSED
tests/test_obf_ingest.py::test_fetch_obf_products PASSED
tests/test_safety_enricher.py::test_lookup_ingredient_safety PASSED
tests/test_safety_enricher.py::test_enrich_database_safety PASSED
tests/test_scraper.py::test_parse_sephora_html PASSED
tests/test_scraper.py::test_save_raw_product PASSED
tests/test_scraper.py::test_scrape_sephora_products PASSED
```

---

## How to Run the End-to-End Pipeline
To run the full workflow from start to finish:
```powershell
.\venv\Scripts\python.exe run_pipeline.py
```

### Output:
*   **Database:** `data/incidb.sqlite`
*   **CSV Exports:** `data/exports/csv/` (`brands.csv`, `products.csv`, `ingredients.csv`, `product_ingredients.csv`)
*   **Parquet Exports:** `data/exports/parquet/` (`brands.parquet`, `products.parquet`, `ingredients.parquet`, `product_ingredients.parquet`)
