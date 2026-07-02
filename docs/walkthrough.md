# INCIDB Global 8-Source Production Scale Walkthrough

## What Was Built
We built an end-to-end, high-performance data ingestion pipeline for **INCIDB** (Skincare & Cosmetic Ingredients Database) strictly adhering to **Test-Driven Development (TDD)** across 10 global development phases unifying **8 distinct formulation, regulatory, and toxicological registries**:

1.  **Relational Core & Auto-Migrations (`src/init.py`, `src/db.py`, `docs/schema.sql`):**
    *   Designed SQLite/PostgreSQL-compatible schema (`brands`, `products`, `ingredients`, `product_ingredients`).
    *   Implemented safe `ALTER TABLE` auto-migrations ensuring zero downtime or data loss when adding safety flags.
2.  **Prestige & Clinical Retail Scraper (`src/scraper.py`):**
    *   Automated web scraping with stealth Playwright headers, viewports, and custom user-agents.
    *   Integrated 120+ top prestige & clinical skincare bestsellers (*Drunk Elephant, Sunday Riley, Tatcha, Estée Lauder, Clinique, Kiehl's, La Mer, SK-II, SkinCeuticals, Dermalogica, Glossier*, etc.).
3.  **K-Beauty & Asian Functional Cosmetics Registry (`src/kbeauty_ingest.py`):**
    *   Ingested Korean Food & Drug Safety (MFDS) functional standards and 120+ trending K-Beauty skincare formulations (*COSRX, Beauty of Joseon, Anua, Skin1004, Round Lab, Torriden, Haruharu Wonder, Sulwhasoo*, etc.).
4.  **Open Beauty Facts Live & Offline Deep Ingestion (`src/obf_ingest.py`):**
    *   Deep-crawled network APIs (`max_pages=50`) fetching **1,665 live product records**.
    *   Implemented memory-efficient `gzip` streaming to ingest massive offline compressed dump archives (`openbeautyfacts-products.jsonl.gz`), adding **18,657 formulations**.
5.  **US National Library of Medicine (DailyMed) Clinical Ingestor (`src/dailymed_ingest.py`):**
    *   Queried NLM DailyMed SPL REST APIs across 50 deep pages, capturing **881 OTC clinical topical dermatological formulations**.
6.  **European Commission CosIng Chemical Registry (`src/cosing_ingest.py`):**
    *   Mapped **500 official EU regulatory records** with exact CAS registry numbers (`69-72-7` for Salicylic Acid, `122-99-6` for Phenoxyethanol) and EU restrictions.
7.  **CIR Expert Scientific Safety Verdicts (`src/cir_ingest.py`):**
    *   Integrated official scientific safety verdicts (*"Safe with qualifications"*, *"Safe as used"*) and maximum recommended concentration thresholds (*Retinol max 0.3%, Glycolic Acid max 10%*, etc.).
8.  **US FDA MoCRA & Contact Allergen Registry (`src/fda_cosmetics_ingest.py`):**
    *   Flagged mandatory MoCRA contact dermatitis fragrance allergens (*Linalool, Limonene, Geraniol, Eugenol, Coumarin*, etc.) and FDA caution labeling rules.
9.  **EWG Skin Deep Toxicological Registry (`src/ewg_ingest.py`):**
    *   Added granular hazard sub-scores highlighting **Carcinogenicity** flags (`cancer_hazard_flag = 1`) and **Endocrine Disruption** flags (`endocrine_hazard_flag = 1`).
10. **Flat-File Exporters (`src/exporter.py`):**
    *   Exported full relational tables into pipe-delimited UTF-8 CSVs (`|`) and Apache Parquet files (`pyarrow`) under `data/exports/`.

---

## Final Production Scale Statistics
Running `run_pipeline.py` unified all 8 data registries into `data/incidb.sqlite`, achieving:

*   **Brands:** `5,994` unique global cosmetic & pharmaceutical brands
*   **Formulations/Products:** `19,846` total products
*   **Unique Canonical INCI Ingredients:** `57,181` distinct chemical entities
*   **Relational Composition Junctions:** `330,088` exact product-to-ingredient position mappings
*   **CIR Scientific Verdict Profiles:** `500` ingredients
*   **FDA MoCRA Allergen Warnings:** `500` ingredients
*   **EWG Carcinogenic Hazard Flags:** `193` ingredients
*   **EWG Endocrine Disruptor Flags:** `176` ingredients

All **33 unit tests** across 11 test suites passed continuously during TDD iterations:
```
tests/test_cir_ingest.py ...                                             [  9%]
tests/test_cosing_ingest.py ...                                          [ 18%]
tests/test_dailymed_ingest.py ...                                        [ 27%]
tests/test_db_init.py ..                                                 [ 33%]
tests/test_enricher.py ...                                               [ 42%]
tests/test_ewg_ingest.py ...                                             [ 51%]
tests/test_exporter.py ..                                                [ 57%]
tests/test_fda_ingest.py ...                                             [ 66%]
tests/test_kbeauty_ingest.py ..                                          [ 72%]
tests/test_obf_dump.py .                                                 [ 75%]
tests/test_obf_ingest.py ...                                             [ 84%]
tests/test_safety_enricher.py ..                                         [ 90%]
tests/test_scraper.py ...                                                [100%]
```

---

## How to Execute the End-to-End Pipeline
To run the global 8-source pipeline and export the datasets:
```powershell
.\venv\Scripts\python.exe run_pipeline.py
```

### Generated Artifacts:
*   **Relational Database:** `data/incidb.sqlite`
*   **CSV Dataset Directory:** `data/exports/csv/` (`brands.csv`, `products.csv`, `ingredients.csv`, `product_ingredients.csv`)
*   **Parquet Dataset Directory:** `data/exports/parquet/` (`brands.parquet`, `products.parquet`, `ingredients.parquet`, `product_ingredients.parquet`)
