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

## Phase 6: Open Beauty Facts At-Scale Ingestion
*   **Goal:** Connect to the Open Beauty Facts public JSON API to fetch and ingest 50+ real cosmetic products with INCI ingredient strings.
*   **Tasks:**
    *   Write `src/obf_ingest.py` to query Open Beauty Facts API (`https://world.openbeautyfacts.org/cgi/search.pl?action=process&json=1&page_size=50`).
    *   Filter products that have non-empty `ingredients_text` or `ingredients_tags`.
    *   Save fetched raw products as JSON files under `data/raw/obf/`.
    *   Normalize and ingest them into SQLite database (`data/incidb.sqlite`) using `src/enricher.py`.
    *   Enrich with EWG/CosIng safety ratings using `src/safety_enricher.py`.
    *   Re-run exporters (`src/exporter.py`) to update CSV and Parquet exports.
*   **Verification:** Query SQLite database and confirm over 50 real cosmetic products and hundreds of unique INCI ingredients are present.
