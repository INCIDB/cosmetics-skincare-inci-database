# INCIDB Technical Specification
## Skincare & Cosmetic Ingredients Database (Prototype)

### 1. System Architecture
The system consists of three independent Python execution stages:
1.  **Ingestion & Scraping Script (`src/scraper.py`):** Uses Playwright to extract HTML/JSON and save files locally.
2.  **Normalization & Database Script (`src/enricher.py`):** Parses raw text, queries Gemini API for INCI mapping, and populates SQLite.
3.  **Exporter Script (`src/exporter.py`):** Converts SQLite tables into CSV and Parquet.

### 2. Database Schema
We will implement the schema defined in [schema.sql](file:///c:/Users/aichl/Documents/BrainStorming%20DB%20Ideas/01_Skincare_Cosmetics_INCIDB/docs/schema.sql).

### 3. Pipeline Ingestion & Staging Details
We use a file-system cache structure under `data/raw/` to ensure scraping only happens once:
```
data/
└── raw/
    ├── sephora/
    │   ├── product_123.json
    │   └── product_456.json
    └── ewg/
        ├── ingredient_water.html
        └── ingredient_niacinamide.html
```

---

### 4. Gemini Normalization Engine (Google Gen AI SDK)
We will target the `gemini-2.5-flash` model utilizing structured JSON outputs.

#### System Prompt Example:
```
You are an expert cosmetic chemist database assistant.
Parse the raw cosmetic ingredient list and return a JSON list of ingredients.
Map each raw ingredient string to its canonical INCI name (upper case).
If the ingredient has a common name, provide it.

Format output as a JSON array:
[
  {
    "position": 1,
    "raw_name": "Purified Water",
    "inci_name": "AQUA",
    "common_name": "Water"
  }
]
```

---

### 5. Post-Processing & Export formats
*   **SQLite Database:** `data/incidb.sqlite`
*   **Parquet Export:** Generated using `pandas` or `polars` + `pyarrow` to ensure schema compatibility.
*   **CSV Export:** Standard UTF-8 CSV using pipe (`|`) delimiter to avoid collision with commas in chemical ingredient names.
