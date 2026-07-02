# INCIDB Multi-Source & Compressed Archive Pipeline Walkthrough

## What Was Built
We built an end-to-end, high-performance data ingestion pipeline for **INCIDB** (Skincare & Cosmetic Ingredients Database) strictly adhering to **Test-Driven Development (TDD)** across 8 distinct phases:

1.  **Environment Setup & Relational Schema (`src/init.py`, `src/db.py`):**
    *   Configured SQLite database structure (`brands`, `products`, `ingredients`, `product_ingredients`).
    *   Created raw data staging folders under `data/raw/`.
2.  **Sephora Scraper (`src/scraper.py`):**
    *   Implemented HTML parsing using `BeautifulSoup` and web automation via `Playwright`.
3.  **Gemini Normalization & Ingestion (`src/enricher.py`):**
    *   Integrated Google Gen AI SDK (`gemini-2.5-flash` with structured JSON schema) to parse raw ingredient text strings into canonical INCI names (`AQUA`, `NIACINAMIDE`, `CERAMIDE NP`).
4.  **Reference Safety Enrichment (`src/safety_enricher.py`):**
    *   Cross-referenced standard chemical nomenclature with toxicological registries (EWG Skin Deep / CosIng) to assign hazard scores (1-10), comedogenic ratings (0-5), and allergen flags (`PHENOXYETHANOL`, etc.).
5.  **Flat-File Exporters (`src/exporter.py`):**
    *   Converted relational SQLite tables into pipe-delimited UTF-8 CSVs (`|`) and Apache Parquet files (`pyarrow`) under `data/exports/`.
6.  **Open Beauty Facts API Deep Crawl (`src/obf_ingest.py`):**
    *   Connected to Open Beauty Facts JSON API with multi-page pagination loops (`max_pages`) to fetch bulk real cosmetic product records.
7.  **US National Library of Medicine (DailyMed) Clinical Ingestor (`src/dailymed_ingest.py`):**
    *   Integrated NLM DailyMed SPL API (`services/v2/spls.json`) to ingest clinical OTC topical dermatological formulations (sunscreens, ceramide barrier repair lotions, salicylic acid acne creams) with exact FDA active/inactive ingredient breakdowns.
8.  **Offline Bulk Compressed Dump Streaming (`src/obf_ingest.py:ingest_obf_dump`):**
    *   Integrated high-speed `gzip` streaming to read massive offline compressed dataset archives (`openbeautyfacts-products.jsonl.gz`) line by line without exhausting system RAM.
    *   Implemented batched transaction commits and automated INCI normalization.

---

## Verification & Scaled Dataset Scale
Running `run_pipeline.py` ingests across all API sources and streams offline compressed archives, populating the relational database with **5,354 cosmetic formulations** across **2,045 unique brands**, normalizing **15,585 unique INCI ingredients** via **92,443 relational junctions**.

All 19 unit tests passed continuously during TDD iterations:
```
tests/test_dailymed_ingest.py::test_parse_dailymed_item PASSED
tests/test_dailymed_ingest.py::test_save_dailymed_product PASSED
tests/test_dailymed_ingest.py::test_fetch_dailymed_products PASSED
tests/test_db_init.py::test_ensure_directories PASSED
tests/test_db_init.py::test_init_database PASSED
tests/test_enricher.py::test_normalize_ingredients PASSED
tests/test_enricher.py::test_ingest_product_record PASSED
tests/test_enricher.py::test_process_sephora_cache PASSED
tests/test_exporter.py::test_export_to_csv PASSED
tests/test_exporter.py::test_export_to_parquet PASSED
tests/test_obf_dump.py::test_ingest_obf_dump PASSED
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
To run the full multi-source and compressed archive workflow:
```powershell
.\venv\Scripts\python.exe run_pipeline.py
```

### Output:
*   **Database:** `data/incidb.sqlite`
*   **CSV Exports:** `data/exports/csv/` (`brands.csv`, `products.csv`, `ingredients.csv`, `product_ingredients.csv`)
*   **Parquet Exports:** `data/exports/parquet/` (`brands.parquet`, `products.parquet`, `ingredients.parquet`, `product_ingredients.parquet`)
