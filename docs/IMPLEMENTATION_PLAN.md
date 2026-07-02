# INCIDB Phase-Based Implementation Plan

This implementation plan breaks down the development of the INCIDB prototype into small, verifiable phases.

## Phase 1: Environment Setup & Foundation
*   **Goal:** Configure dependencies, directory layouts, and database schemas.
*   **Tasks:**
    *   Create python virtual environment and install dependencies (`playwright`, `beautifulsoup4`, `google-genai`, `pandas`, `pyarrow`).
    *   Initialize SQLite database using [schema.sql](file:///c:/Users/aichl/Documents/BrainStorming%20DB%20Ideas/01_Skincare_Cosmetics_INCIDB/docs/schema.sql).
    *   Setup `data/raw/` directory structure.
*   **Verification:** Run a test script to open SQLite connection and query empty tables.

## Phase 2: Scraper Development (Sephora)
*   **Goal:** Build a Playwright script to fetch product page data and cache raw results.
*   **Tasks:**
    *   Write `src/scraper.py` using Playwright to scrape a test list of 5-10 Sephora products.
    *   Extract: Brand, Product Name, Category, Price, and Raw Ingredient text.
    *   Save raw data as JSON files under `data/raw/sephora/`.
*   **Verification:** Check that 5 raw JSON files are successfully written with expected fields.

## Phase 3: Gemini Normalization & Ingestion
*   **Goal:** Call Gemini API to parse and map raw lists to standard INCI ingredients, then save to SQLite.
*   **Tasks:**
    *   Write `src/enricher.py` to parse JSON from `data/raw/sephora/`.
    *   Set up Google Gen AI SDK client and structured prompt.
    *   Extract, clean, and map chemical list to database fields.
    *   Insert records into `brands`, `products`, `ingredients`, and `product_ingredients` tables.
*   **Verification:** Verify database tables are correctly populated with brand, product, and mapped ingredient rows.

## Phase 4: Reference Database Ingestion (EWG/CosIng Mock)
*   **Goal:** Feed safety scores and allergen tags into the SQLite database.
*   **Tasks:**
    *   Add scraping or lookup capability for ingredients in `ingredients` table.
    *   Enrich `ingredients` record with hazard scores, functions, and allergens.
*   **Verification:** Query ingredients table to confirm safety ratings are updated.

## Phase 5: Flat-File Exporters
*   **Goal:** Output SQLite tables into final CSV and Parquet packaging.
*   **Tasks:**
    *   Write `src/exporter.py` to select tables and write pipe-delimited CSV files.
    *   Write Parquet files for each main relational table.
*   **Verification:** Read Parquet and CSV files in pandas to verify column schemas and records match database.

## Phase 6: Open Beauty Facts At-Scale Ingestion [COMPLETED]
*   **Goal:** Connect to the Open Beauty Facts public JSON API to fetch and ingest 50+ real cosmetic products with INCI ingredient strings.
*   **Tasks:**
    *   Write `src/obf_ingest.py` to query Open Beauty Facts API (`https://world.openbeautyfacts.org/cgi/search.pl?action=process&json=1&page_size=50`).
    *   Filter products that have non-empty `ingredients_text` or `ingredients_tags`.
    *   Save fetched raw products as JSON files under `data/raw/obf/`.
    *   Normalize and ingest them into SQLite database (`data/incidb.sqlite`) using `src/enricher.py`.
    *   Enrich with EWG/CosIng safety ratings using `src/safety_enricher.py`.
    *   Re-run exporters (`src/exporter.py`) to update CSV and Parquet exports.
*   **Verification:** Query SQLite database and confirm over 50 real cosmetic products and hundreds of unique INCI ingredients are present.

## Phase 7: Multi-Source Bulk Ingestion (OBF Deep Crawl & DailyMed OTC Skincare) [COMPLETED]
*   **Goal:** Deep crawl Open Beauty Facts across multiple pagination batches and add US National Library of Medicine (DailyMed) OTC skincare products to ingest thousands of formulations.
*   **Tasks:**
    *   Update `src/obf_ingest.py` to support multi-page pagination loops (`max_pages`) for bulk ingestion.
    *   Write `src/dailymed_ingest.py` to query NLM DailyMed API (`https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json`) for topical dermatological & skincare products (acne, sunscreen, lotions).
    *   Extract active and inactive ingredients from DailyMed SPL labels and save raw JSONs under `data/raw/dailymed/`.
    *   Update `src/utils.py` to create `data/raw/dailymed/`.
    *   Update `run_pipeline.py` to orchestrate all three sources (Sephora, Open Beauty Facts bulk, DailyMed OTC).
*   **Verification:** Verify database record counts expand significantly across multi-source origins.

## Phase 8: Offline Bulk Compressed Dump Ingestion (`jsonl.gz`) [COMPLETED]
*   **Goal:** Stream and ingest massive offline compressed dataset dumps (`data/raw/obf/openbeautyfacts-products.jsonl.gz`) efficiently into SQLite with batched transactions.
*   **Tasks:**
    *   Add `ingest_obf_dump(dump_path: Path, db_path: Path, max_records: int = None, batch_size: int = 500) -> int` to `src/obf_ingest.py`.
    *   Use `gzip` streaming to read JSON lines without exhausting RAM.
    *   Filter valid cosmetic products containing `ingredients_text`.
    *   Perform batched database inserts and ingredient normalizations.
    *   Update `run_pipeline.py` to automatically detect and ingest compressed `.jsonl.gz` archives if present under `data/raw/obf/`.
*   **Verification:** Verify database product count increases massively from the compressed archive.

## Phase 9: Expanded Prestige Retail Catalog, Stealth Playwright Scraping, and EU CosIng Registry [COMPLETED]
*   **Goal:** Scale retail skincare coverage to 100+ prestige/clinical bestsellers, upgrade live scraping with stealth automation techniques, and ingest official EU CosIng regulatory definitions.
*   **Tasks:**
    *   **Expand Retail Catalog (`src/scraper.py`):** Add 100+ verified prestige retail formulations (Drunk Elephant, Sunday Riley, Tatcha, Estée Lauder, Clinique, Kiehl's, La Mer, SK-II, SkinCeuticals, Dermalogica, Glossier, Summer Fridays, Tower 28, Rare Beauty, Fenty Skin, Sol de Janeiro, Paula's Choice, The Ordinary, CeraVe, La Roche-Posay).
    *   **Stealth Playwright Scraping (`src/scraper.py`):** Integrate `playwright-stealth` (or stealth headers, viewports, automation flags bypass) to attempt live scraping against retail target endpoints before falling back to our 100+ catalog.
    *   **EU CosIng Registry Ingestor (`src/cosing_ingest.py` & `tests/test_cosing_ingest.py`):** Create ingestor to download/query official EU Commission CosIng chemical registry data (standardizing chemical descriptions, CAS numbers, and regulatory functions).
    *   Update `run_pipeline.py` to integrate CosIng ingestion and the expanded retail catalog.
*   **Verification:** Verify TDD tests pass and database scale increases across retail & regulatory sources.
